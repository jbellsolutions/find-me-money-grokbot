#!/usr/bin/env python3
"""
reacher_verify.py — Upload a list, fully verify every email, get a clean report.

A thin, dependency-free pipeline on top of a self-hosted Reacher backend:

    CSV / TXT  ->  POST /v1/bulk  ->  poll progress  ->  fetch JSON results
               ->  classify (DELIVERABLE / ACCEPT-ALL / UNDELIVERABLE / RETRY)  ->  CSVs + summary

The open-source Reacher backend exposes a bulk API but no friendly upload/report
layer (and its native CSV export is broken in v0.11.7). This script is that layer.

Stdlib only — runs with any Python 3.8+, no `pip install` required.

Examples
--------
    # Verify a list (auto-detects the email column), write reports to ./out
    python3 reacher_verify.py emails.csv

    # Point at a remote backend with a shared secret, custom output dir
    python3 reacher_verify.py list.csv \
        --backend https://verify.example.com --secret "$RCH_SECRET" -o run1

    # Plain text, one email per line
    python3 reacher_verify.py emails.txt

What the buckets mean — send list = DELIVERABLE + ACCEPT-ALL (both receive mail)
-------------------------------------------------------------------------------
    DELIVERABLE   (safe)             confirmed mailbox                 -> mail these
    ACCEPT-ALL    (catch-all/role)   accepts mail, unconfirmable       -> mail + enrich to a person
    UNDELIVERABLE (invalid/disposable) doesn't exist / junk            -> remove (hard bounce)
    RETRY         (greylisted/full)  probe blocked or inbox full       -> re-verify (via a proxy)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Deliverable-first buckets. Send list = DELIVERABLE + ACCEPT_ALL (both receive mail
# without bouncing). Accept-all = catch-all/role — sendable, and the enrichment target
# (enrich to reach a named person). Disposable is junk (undeliverable); a full inbox
# soft-bounces now so it goes to RETRY.
DELIVERABLE = "DELIVERABLE"    # safe — mailbox confirmed
ACCEPT_ALL = "ACCEPT_ALL"      # catch-all / role — accepts mail, mailbox unconfirmable
UNDELIVERABLE = "UNDELIVERABLE"  # invalid / disposable — will hard-bounce or is junk
RETRY = "RETRY"                # greylisted probe, or full inbox — re-verify later
BUCKETS = (DELIVERABLE, ACCEPT_ALL, UNDELIVERABLE, RETRY)
SENDABLE = (DELIVERABLE, ACCEPT_ALL)
# legacy alias (raw reachability → coarse bucket), kept for any external callers
BUCKET = {"safe": DELIVERABLE, "invalid": UNDELIVERABLE, "risky": ACCEPT_ALL, "unknown": RETRY}


def bucket_for(r):
    """Deliverable-first bucket for a Reacher result. Catch-all/role → ACCEPT_ALL (send)."""
    reach = r.get("is_reachable", "unknown")
    smtp = r.get("smtp") or {}
    misc = r.get("misc") or {}
    if reach == "safe":
        return DELIVERABLE
    if reach == "invalid":
        return UNDELIVERABLE
    if reach == "unknown":
        return RETRY
    # risky: it accepts mail — decide if it's sendable, junk, or a soft-bounce
    if misc.get("is_disposable"):
        return UNDELIVERABLE       # throwaway/temp domain — junk, spam-trap risk
    if smtp.get("has_full_inbox"):
        return RETRY               # over quota — soft-bounces now, may clear
    return ACCEPT_ALL              # catch-all / role / accepts → sendable (+ enrich)


# --------------------------------------------------------------------------- IO

def read_emails(path, email_column=None):
    """Return a de-duplicated, order-preserving list of email-looking strings."""
    if not os.path.exists(path):
        sys.exit(f"error: input file not found: {path}")

    rows = []
    is_csv = path.lower().endswith((".csv", ".tsv"))
    if is_csv:
        delim = "\t" if path.lower().endswith(".tsv") else ","
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f, delimiter=delim)
            rows = [r for r in reader if r]
    else:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            rows = [[line.strip()] for line in f if line.strip()]

    if not rows:
        sys.exit("error: input file is empty")

    emails = []
    if is_csv:
        header = rows[0]
        col = _resolve_email_column(header, rows, email_column)
        start = 1 if _looks_like_header(header) else 0
        for r in rows[start:]:
            if col < len(r):
                emails.append(r[col].strip())
    else:
        emails = [r[0] for r in rows]

    # Keep every non-blank value (de-duped, case-insensitive, first spelling wins).
    # We do NOT drop malformed values here — they flow through so the user sees a
    # verdict for every row they uploaded. Reacher (or a local check) marks them.
    seen, out = set(), []
    for e in emails:
        e = e.strip().strip('"').strip("'")
        if not e:
            continue
        key = e.lower()
        if key not in seen:
            seen.add(key)
            out.append(e)
    if not out:
        sys.exit("error: no values found in the email column (try --email-column N)")
    return out


def synthetic_invalid(email):
    """A local 'invalid syntax' result for values that aren't even email-shaped,
    so they appear in the report without a pointless backend round-trip."""
    return {
        "input": email,
        "is_reachable": "invalid",
        "syntax": {"is_valid_syntax": False, "domain": "", "username": "", "suggestion": None},
        "mx": {"accepts_mail": False, "records": []},
        "smtp": {"can_connect_smtp": False, "has_full_inbox": False,
                 "is_catch_all": False, "is_deliverable": False, "is_disabled": False},
        "misc": {"is_disposable": False, "is_role_account": False,
                 "gravatar_url": None, "haveibeenpwned": None},
    }


def _looks_like_header(header):
    return not any(EMAIL_RE.match((c or "").strip()) for c in header)


def _resolve_email_column(header, rows, email_column):
    if email_column is not None:
        return email_column
    # Prefer a column literally named like an email field.
    for i, name in enumerate(header):
        if (name or "").strip().lower() in ("email", "email_address", "e-mail", "mail"):
            return i
    # Otherwise pick the column with the most email-shaped values in a sample.
    sample = rows[: min(len(rows), 50)]
    best_i, best_hits = 0, -1
    width = max(len(r) for r in sample)
    for i in range(width):
        hits = sum(1 for r in sample if i < len(r) and EMAIL_RE.match((r[i] or "").strip()))
        if hits > best_hits:
            best_i, best_hits = i, hits
    return best_i


# ---------------------------------------------------------------------- HTTP

def _req(method, url, secret, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["x-reacher-secret"] = secret
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"error: {method} {url} -> HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"error: cannot reach backend at {url}: {e.reason}\n"
                 f"       is the stack up?  (cd deploy/local && docker compose ps)")


def submit_bulk(base, emails, secret):
    out = _req("POST", f"{base}/v1/bulk", secret, {"input": emails})
    return out["job_id"]


def get_progress(base, job_id, secret):
    return _req("GET", f"{base}/v1/bulk/{job_id}", secret)


def fetch_results(base, job_id, secret, page=1000):
    results, offset = [], 0
    while True:
        url = f"{base}/v1/bulk/{job_id}/results?format=json&limit={page}&offset={offset}"
        batch = _req("GET", url, secret).get("results", [])
        results.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return results


# ------------------------------------------------------------------ classify

def classify(r):
    """Return (bucket, reach, reason) explaining deliverability in plain English."""
    bucket = bucket_for(r)
    reach = r.get("is_reachable", "unknown")
    smtp = r.get("smtp", {}) or {}
    mx = r.get("mx", {}) or {}
    misc = r.get("misc", {}) or {}
    syntax = r.get("syntax", {}) or {}
    # Reacher folds a disposable/known-bad blocklist (the `mailchecker` crate) into
    # its syntax check, so a structurally-valid address can come back
    # is_valid_syntax=false. Distinguish that from a genuinely malformed address.
    structurally_email = bool(EMAIL_RE.match(r.get("input", "")))

    if bucket == DELIVERABLE:
        reason = "deliverable — mailbox confirmed, accepts mail"
    elif bucket == UNDELIVERABLE:
        if reach == "risky" and misc.get("is_disposable"):
            reason = "disposable / throwaway address — do not send"
        elif not syntax.get("is_valid_syntax", True):
            reason = ("disposable / known-bad domain (blocklisted) — undeliverable"
                      if structurally_email else "malformed address (invalid syntax)")
        elif not mx.get("accepts_mail", True):
            reason = "domain has no mail server (cannot receive email)"
        elif smtp.get("is_disabled"):
            reason = "mailbox disabled by the provider"
        else:
            reason = "mailbox does not exist (hard bounce)"
    elif bucket == ACCEPT_ALL:
        bits = []
        if smtp.get("is_catch_all"):
            bits.append("catch-all domain (accepts all mail)")
        if misc.get("is_role_account"):
            bits.append("role account (e.g. info@/inquiries@)")
        detail = "; ".join(bits) or "server accepts mail (mailbox unconfirmable)"
        reason = f"accepts mail — {detail} — sendable; enrich to reach a named person"
    else:  # RETRY
        if reach == "risky" and smtp.get("has_full_inbox"):
            reason = "inbox full (soft-bounce now) — retry later"
        else:
            err = ((r.get("debug") or {}).get("smtp") or {}).get("error")
            reason = "provider blocked the probe (greylisting/rate-limit) — retry via proxy"
            if isinstance(err, dict) and err.get("message"):
                reason += f" [{err['message'][:80]}]"
    return bucket, reach, reason


FIELDS = [
    "email", "bucket", "is_reachable", "reason",
    "mx_accepts_mail", "smtp_can_connect", "is_deliverable",
    "is_catch_all", "is_disabled", "has_full_inbox",
    "is_role_account", "is_disposable", "suggestion",
]


def row_for(r):
    smtp = r.get("smtp", {}) or {}
    mx = r.get("mx", {}) or {}
    misc = r.get("misc", {}) or {}
    syntax = r.get("syntax", {}) or {}
    bucket, reach, reason = classify(r)
    return {
        "email": r.get("input", ""),
        "bucket": bucket,
        "is_reachable": reach,
        "reason": reason,
        "mx_accepts_mail": mx.get("accepts_mail"),
        "smtp_can_connect": smtp.get("can_connect_smtp"),
        "is_deliverable": smtp.get("is_deliverable"),
        "is_catch_all": smtp.get("is_catch_all"),
        "is_disabled": smtp.get("is_disabled"),
        "has_full_inbox": smtp.get("has_full_inbox"),
        "is_role_account": misc.get("is_role_account"),
        "is_disposable": misc.get("is_disposable"),
        "suggestion": syntax.get("suggestion") or "",
    }


def write_outputs(results, outdir, split):
    os.makedirs(outdir, exist_ok=True)
    rows = [row_for(r) for r in results]

    all_path = os.path.join(outdir, "results.csv")
    with open(all_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    written = {"results.csv": len(rows)}
    if split:
        # sendable.csv = the whole send list (deliverable + accept-all), then per-bucket
        groups = [("sendable", SENDABLE)] + [(b.lower(), (b,)) for b in BUCKETS]
        for name, buckets in groups:
            sub = [r for r in rows if r["bucket"] in buckets]
            if not sub:
                continue
            fname = f"{name}.csv"
            with open(os.path.join(outdir, fname), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(sub)
            written[fname] = len(sub)
    return rows, written


# ----------------------------------------------------------------- pipeline

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def run(args):
    base = args.backend.rstrip("/")
    print(f"→ backend: {base}")
    emails = read_emails(args.input, args.email_column)
    to_verify = [e for e in emails if "@" in e]
    not_emails = [e for e in emails if "@" not in e]
    print(f"→ {len(emails)} unique values "
          f"({len(to_verify)} to verify, {len(not_emails)} not email-shaped)")

    all_results = [synthetic_invalid(e) for e in not_emails]
    batches = list(chunks(to_verify, args.chunk_size)) if to_verify else []
    for bi, batch in enumerate(batches, 1):
        if len(batches) > 1:
            print(f"\n── chunk {bi}/{len(batches)} ({len(batch)} emails) ──")
        job_id = submit_bulk(base, batch, args.secret)
        print(f"→ submitted job {job_id}; verifying…")

        last = -1
        while True:
            p = get_progress(base, job_id, secret=args.secret)
            done = p.get("total_processed") or 0
            total = p.get("total_records") or len(batch)
            status = p.get("job_status", "Running")
            if done != last:
                s = p.get("summary", {}) or {}
                bar = _bar(done, total)
                sys.stdout.write(
                    f"\r  {bar} {done}/{total}  "
                    f"safe={s.get('total_safe',0)} risky={s.get('total_risky',0)} "
                    f"invalid={s.get('total_invalid',0)} unknown={s.get('total_unknown',0)}   "
                )
                sys.stdout.flush()
                last = done
            if status == "Completed" or (total and done >= total):
                break
            time.sleep(args.poll_interval)
        print()  # newline after the progress line

        all_results.extend(fetch_results(base, job_id, args.secret))

    rows, written = write_outputs(all_results, args.outdir, args.split)
    _summary(rows, written, args.outdir)
    return 0


def _bar(done, total, width=24):
    if not total:
        return "[" + " " * width + "]"
    filled = int(width * done / total)
    return "[" + "█" * filled + " " * (width - filled) + "]"


def _summary(rows, written, outdir):
    n = len(rows)
    counts = {b: 0 for b in BUCKETS}
    for r in rows:
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
    sendable = counts[DELIVERABLE] + counts[ACCEPT_ALL]

    def pct(x):
        return f"{(100*x/n):.1f}%" if n else "0%"

    print("\n" + "=" * 60)
    print(f"  VERIFICATION COMPLETE — {n} emails")
    print("=" * 60)
    print(f"  ✅ DELIVERABLE    {counts[DELIVERABLE]:>7}  {pct(counts[DELIVERABLE]):>6}   confirmed mailbox")
    print(f"  📬 ACCEPT-ALL     {counts[ACCEPT_ALL]:>7}  {pct(counts[ACCEPT_ALL]):>6}   catch-all/role — sendable, enrich")
    print(f"  ⛔ UNDELIVERABLE  {counts[UNDELIVERABLE]:>7}  {pct(counts[UNDELIVERABLE]):>6}   hard-bounce/disposable — remove")
    print(f"  🔁 RETRY          {counts[RETRY]:>7}  {pct(counts[RETRY]):>6}   greylisted/full — re-verify")
    print("  " + "-" * 58)
    print(f"  📨 SEND LIST      {sendable:>7}  {pct(sendable):>6}   deliverable + accept-all")
    print("=" * 60)
    print(f"  Wrote to {outdir}/:")
    for name, c in written.items():
        print(f"    • {name:<16} {c} rows")
    if counts[RETRY]:
        print("\n  Tip: RETRY rows mean the provider blocked the probe from this IP.")
        print("       Re-run those via an SMTP SOCKS5 proxy for a clean answer.")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Verify an email list against a self-hosted Reacher backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input", help="path to a .csv, .tsv, or .txt list of emails")
    ap.add_argument("-b", "--backend", default=os.environ.get("REACHER_BACKEND", "http://localhost:8080"),
                    help="backend base URL (env REACHER_BACKEND; default http://localhost:8080)")
    ap.add_argument("-s", "--secret", default=os.environ.get("REACHER_SECRET"),
                    help="x-reacher-secret header value (env REACHER_SECRET)")
    ap.add_argument("-o", "--outdir", default="reacher_out", help="output directory (default reacher_out)")
    ap.add_argument("--email-column", type=int, default=None,
                    help="0-based column index of the email field (default: auto-detect)")
    ap.add_argument("--chunk-size", type=int, default=20000,
                    help="emails per bulk job (default 20000)")
    ap.add_argument("--poll-interval", type=float, default=3.0,
                    help="seconds between progress polls (default 3)")
    ap.add_argument("--no-split", dest="split", action="store_false",
                    help="don't write per-bucket CSVs (send/drop/review/retry)")
    args = ap.parse_args()
    try:
        sys.exit(run(args))
    except KeyboardInterrupt:
        sys.exit("\ninterrupted")


if __name__ == "__main__":
    main()
