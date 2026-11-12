#!/usr/bin/env python3
"""
enrich.py — recover real, deliverable emails (+ LinkedIn URL + phone) for
REVIEW/RETRY leads, low/no cost, and NEVER ship an unconfirmed guess.

For every company DOMAIN in a list, it:
  1. Scrapes the public site (contact/about/team pages) for real on-domain
     emails + phone + LinkedIn links.                                       [FREE]
  2. (optional) Google-dorks via Bright Data SERP:
       - `"@domain"`        → REAL emails already published on the open web  [~cents]
       - `site:linkedin.com/in "Company"` → named people + their profile URL
     Names feed a pattern GUESS; the open-web emails are real (not guessed).
  3. Re-verifies every candidate through your own Reacher.                   [free]
  4. Grades each result so ONLY confirmed addresses ship:
       DELIVERABLE            = SMTP-confirmed safe (incl. a guess the mailbox proved live)
       ACCEPT-ALL          = a REAL email published on the company's own site/open web,
                         but the domain is catch-all so SMTP can't confirm it
       SEARCH-VERIFIED = a guessed address that shows up published in Google
                         (exact-match) — corroborated, per the "put it in Google" rule
       UNDELIVERABLE            = invalid, or a guess that is neither SMTP-safe nor search-found
     A pattern guess that can't be confirmed either way is DROPPED, never emailed.

No rented-answer SaaS (Hunter/Apollo/Clay/ZoomInfo). Just your own scraping + verifier.

Config (same as the reacher CLI / dashboard):
  REACHER_URL / REACHER_BACKEND   backend base URL (else the reacher CLI config, else the prod droplet)
  REACHER_SECRET                  x-reacher-secret (else the reacher CLI config)
  BRIGHTDATA_API_KEY + BRIGHTDATA_SERP_ZONE   (optional) enables the open-web / LinkedIn / search-verify layer
  BRIGHTDATA_UNLOCK_ZONE          (optional) Web Unlocker zone for JS/anti-bot sites (default mcp_unlocker)

Usage:
  python3 enrich.py review.csv -o enriched_out
  python3 enrich.py review.csv -o out --max-domains 50 --no-serp
  python3 enrich.py review.csv -o out --search-verify-cap 300
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reacher_verify import (EMAIL_RE, classify, fetch_results, get_progress,  # noqa: E402
                            row_for, submit_bulk)

EMAIL_FIND = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# name-ish LinkedIn SERP title: "First Last - Title - Company | LinkedIn"
LINKEDIN_TITLE = re.compile(r"^([A-Z][a-zA-Z'\-]+)\s+([A-Z][a-zA-Z'\-]+)")
# a linkedin.com/in/<slug> or /company/<slug> URL
LINKEDIN_URL = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9\-_%.]+", re.I)
# phone with structure (requires separators/parens so we don't match long id strings)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]\d{3}[\s.\-]\d{4}")
TEL_HREF = re.compile(r"tel:\s*(\+?[0-9()\s.\-]{7,}\d)", re.I)
PAGES = ["", "/contact", "/contact-us", "/about", "/about-us", "/team", "/our-team",
         "/people", "/company", "/staff", "/leadership", "/meet-the-team"]
SKIP_LOCAL = {"info", "support", "sales", "hello", "contact", "admin", "office",
              "help", "team", "no-reply", "noreply", "privacy", "legal", "careers",
              "jobs", "media", "press", "webmaster", "postmaster", "marketing",
              "coach", "inquiries", "enquiries", "customercare", "customerservice",
              "bookings", "booking", "accounts", "billing", "hr", "recruiting",
              "newsletter", "subscribe", "hey", "connect", "general", "mail", "email"}
UA = "Mozilla/5.0 (compatible; lead-enrich/1.0)"

# candidate source prefixes → origin class
#   site:<path>   real email published on the company's own site
#   openweb       real email published elsewhere on the open web ("@domain" dork)
#   guess:<pat>   pattern-guessed from a name we found (must be confirmed to ship)
SITE_SRC = "site:"
OPENWEB_SRC = "openweb"
GUESS_SRC = "guess:"


# ------------------------------------------------------------------ config

def resolve_backend():
    url = os.environ.get("REACHER_URL") or os.environ.get("REACHER_BACKEND")
    secret = os.environ.get("REACHER_SECRET")
    if not url or not secret:
        try:
            import pathlib
            import tomllib
            p = pathlib.Path.home() / ".config" / "reacher-pp-cli" / "config.toml"
            if p.exists():
                cfg = tomllib.loads(p.read_text())
                url = url or cfg.get("base_url")
                secret = secret or cfg.get("authorization")
        except Exception:
            pass
    return (url or "").rstrip("/"), secret  # REACHER_URL, set at intake; no default host


def resolve_brightdata():
    """Bright Data token + SERP zone from env, else the brightdata-pp-cli config."""
    key = os.environ.get("BRIGHTDATA_API_KEY") or os.environ.get("BRIGHTDATA_TOKEN")
    zone = os.environ.get("BRIGHTDATA_SERP_ZONE")
    if not key:
        try:
            import pathlib
            import tomllib
            p = pathlib.Path.home() / ".config" / "brightdata-pp-cli" / "config.toml"
            if p.exists():
                key = tomllib.loads(p.read_text()).get("token")
        except Exception:
            pass
    return key, (zone or "serp_api1")  # serp_api1 = this account's SERP zone


def resolve_unlock_zone():
    return os.environ.get("BRIGHTDATA_UNLOCK_ZONE", "mcp_unlocker")


# ----------------------------------------------------------------- scrape

def _fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            if "html" not in ct and "text" not in ct:
                return ""
            return r.read(1_500_000).decode("utf-8", "replace")
    except Exception:
        return ""


def _unlock_fetch(url, api_key, zone, timeout=45):
    """Bright Data Web Unlocker for JS/anti-bot/Cloudflare pages. Costs per request."""
    if not api_key:
        return ""
    body = json.dumps({"zone": zone, "url": url, "format": "raw"}).encode()
    req = urllib.request.Request(
        "https://api.brightdata.com/request", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(1_500_000).decode("utf-8", "replace")
    except Exception:
        return ""


def _clean_phone(raw):
    s = re.sub(r"[^\d+]", "", raw)
    digits = re.sub(r"\D", "", s)
    if len(digits) < 7 or len(digits) > 15:
        return None
    return raw.strip()


def scrape_site(domain, unlock_key=None, unlock_zone=None):
    """Scrape public pages. Return (emails{email:path}, phones[set], linkedins[set]).

    emails = on-domain personal/role emails; phones/linkedins are domain-level
    (company) contacts found anywhere on the pages. FREE, with an optional
    Web Unlocker retry when the plain fetch is blocked.
    """
    emails, phones, linkedins = {}, set(), set()
    for scheme in ("https://", "http://"):
        base = scheme + domain
        reached = False
        for path in PAGES:
            page = _fetch(base + path)
            if not page and path in ("", "/contact", "/about") and unlock_key:
                page = _unlock_fetch(base + path, unlock_key, unlock_zone)  # blocked? unlock it
            if not page:
                continue
            reached = True
            text = html.unescape(page)
            for raw in EMAIL_FIND.findall(text):
                e = raw.lower().strip(".")
                if e.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
                    continue
                if e.endswith("@" + domain) and EMAIL_RE.match(e):
                    emails.setdefault(e, path or "/")
            for m in TEL_HREF.findall(page):
                ph = _clean_phone(m)
                if ph:
                    phones.add(ph)
            for m in PHONE_RE.findall(text):
                ph = _clean_phone(m)
                if ph:
                    phones.add(ph)
            for u in LINKEDIN_URL.findall(page):
                linkedins.add(u)
        if reached:
            break  # https reached the host; don't also try http
    return emails, phones, linkedins


def infer_pattern(on_domain_emails):
    """Guess the local-part shape from real on-domain personal emails."""
    locals_ = [e.split("@")[0] for e in on_domain_emails
               if e.split("@")[0] not in SKIP_LOCAL]
    dotted = sum("." in lp for lp in locals_)
    if locals_ and dotted / len(locals_) >= 0.5:
        return "first.last"
    if locals_ and all(len(lp) <= 8 and "." not in lp for lp in locals_):
        return "flast"  # e.g. jsmith
    return "first"      # weakest default


def candidate_from_name(first, last, domain, pattern):
    first, last = first.lower(), last.lower()
    if pattern == "first.last":
        lp = f"{first}.{last}"
    elif pattern == "flast":
        lp = f"{first[0]}{last}"
    else:
        lp = first
    e = f"{lp}@{domain}"
    return e if EMAIL_RE.match(e) else None


# ----------------------------------------------------------- Bright Data SERP

def brightdata_serp(query, api_key, zone, timeout=45):
    """Google SERP via Bright Data SERP API, returning STRUCTURED JSON (brd_json=1)."""
    url = ("https://www.google.com/search?q=" + urllib.parse.quote(query)
           + "&num=20&brd_json=1")
    body = json.dumps({"zone": zone, "url": url, "format": "raw"}).encode()
    req = urllib.request.Request(
        "https://api.brightdata.com/request", data=body, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        sys.stderr.write(f"  [serp] {query[:50]}… -> {e}\n")
        return {}


def _organic(data):
    return data.get("organic", []) if isinstance(data, dict) else []


def people_from_linkedin_serp(domain, company, api_key, zone):
    """Dork LinkedIn for people at the company. Return [(first, last, linkedin_url)].

    LinkedIn snippets carry NAMES, not emails — so this is a name + profile-URL
    source. The name feeds a pattern guess; the URL rides along as multi-field.
    """
    q = f'site:linkedin.com/in "{company}"' if company else f'site:linkedin.com/in "{domain}"'
    data = brightdata_serp(q, api_key, zone)
    seen, out = set(), []
    for item in _organic(data):
        title = html.unescape((item.get("title") or "").strip())
        nm = LINKEDIN_TITLE.match(title)
        if not nm:
            continue
        key = (nm.group(1).lower(), nm.group(2).lower())
        if key in seen:
            continue
        seen.add(key)
        link = (item.get("link") or "").strip()
        url = link if LINKEDIN_URL.match(link) else ""
        out.append((nm.group(1), nm.group(2), url))
    return out[:5]


def emails_from_openweb_serp(domain, api_key, zone):
    """Dork the open web for `"@domain"` → REAL published emails (+ a phone if nearby).

    Return {email: phone_or_None}. These are found, not guessed.
    """
    data = brightdata_serp(f'"@{domain}"', api_key, zone)
    out = {}
    for item in _organic(data):
        blob = html.unescape(
            (item.get("title") or "") + "  " + (item.get("description") or ""))
        ph = None
        pm = PHONE_RE.search(blob)
        if pm:
            ph = _clean_phone(pm.group(0))
        for raw in EMAIL_FIND.findall(blob):
            e = raw.lower().strip(".")
            if e.endswith("@" + domain) and EMAIL_RE.match(e) \
                    and e.split("@")[0] not in SKIP_LOCAL:
                out.setdefault(e, ph)
    return out


# email-aggregators that REPUBLISH scraped/guessed addresses — an appearance here is
# NOT evidence of a real mailbox, so it doesn't count as a "verified listing".
SEARCH_DENY = ("rocketreach", "signalhire", "leadiq", "apollo.io", "zoominfo", "lusha",
               "contactout", "hunter.io", "snov.io", "clearbit", "kaspr", "uplead",
               "adapt.io", "seamless.ai", "findymail", "emailfinder", "voilanorbert",
               "getprospect", "anymailfinder", "skrapp", "datagma", "wiza")


def search_verify(email, api_key, zone):
    """True only if the EXACT address literally appears in a Google result on a
    NON-aggregator page.

    A quoted-email search still returns APPROXIMATE matches (pages about the domain
    or the name), so `organic != []` is far too loose. And an appearance on a
    contact-scraper aggregator (RocketReach, Apollo, …) is just another tool's guess,
    not a real listing. So we require the literal address on a page that is NOT one of
    those — an honest "shows up on a verified listing" test, per the no-unconfirmed-
    guess rule.
    """
    data = brightdata_serp(f'"{email}"', api_key, zone)
    needle = email.lower()
    for it in _organic(data):
        link = (it.get("link") or "").lower()
        if any(d in link for d in SEARCH_DENY):
            continue
        blob = ((it.get("title") or "") + " " + (it.get("description") or "")
                + " " + link + " " + (it.get("displayed_link") or "")).lower()
        if needle in blob:
            return True
    return False


# ------------------------------------------------------------ enrich a domain

def enrich_domain(domain, company, use_serp, bd_key, bd_zone, unlock_key=None, unlock_zone=None):
    """Return {domain, candidates:{email:{source,linkedin_url,phone}}, pattern, serp_people}."""
    result = {"domain": domain, "candidates": {}, "pattern": None, "serp_people": 0}
    emails, phones, linkedins = scrape_site(domain, unlock_key, unlock_zone)
    company_phone = next(iter(phones), "")
    company_linkedin = next((u for u in linkedins if "/company/" in u.lower()), "")

    # real emails published on the company's own site
    for e, path in emails.items():
        if e.split("@")[0] not in SKIP_LOCAL:  # skip role/no-reply for SEND candidates
            result["candidates"][e] = {"source": f"{SITE_SRC}{path}",
                                       "linkedin_url": company_linkedin, "phone": company_phone}

    pattern = infer_pattern(list(emails.keys()))
    result["pattern"] = pattern

    if use_serp and bd_key and bd_zone:
        # real emails published elsewhere on the open web (found, not guessed)
        try:
            for e, ph in emails_from_openweb_serp(domain, bd_key, bd_zone).items():
                result["candidates"].setdefault(e, {
                    "source": OPENWEB_SRC, "linkedin_url": "", "phone": ph or company_phone})
        except Exception as e:
            sys.stderr.write(f"  [openweb] {domain} -> {e}\n")
        # named people → pattern GUESS (must be confirmed downstream to ship)
        try:
            people = people_from_linkedin_serp(domain, company, bd_key, bd_zone)
            result["serp_people"] = len(people)
            for first, last, url in people:
                cand = candidate_from_name(first, last, domain, pattern)
                if cand and cand not in result["candidates"]:
                    result["candidates"][cand] = {"source": f"{GUESS_SRC}{pattern}",
                                                  "linkedin_url": url, "phone": company_phone}
        except Exception as e:
            sys.stderr.write(f"  [linkedin] {domain} -> {e}\n")
    return result


# ------------------------------------------------------------------- main

def read_domains(path):
    """Read the input list → {domain: company_guess}. Accepts our REVIEW csv or any csv/txt."""
    domains = {}
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        if path.lower().endswith((".csv", ".tsv")):
            delim = "\t" if path.lower().endswith(".tsv") else ","
            rows = [r for r in csv.reader(f, delimiter=delim) if r]
            hdr = rows[0]
            ecol = next((i for i, c in enumerate(hdr)
                         if (c or "").strip().lower() in ("email", "email_address", "mail")), 0)
            start = 0 if any(EMAIL_RE.match((c or "").strip()) for c in hdr) else 1
            vals = [r[ecol].strip() for r in rows[start:] if ecol < len(r) and r[ecol].strip()]
        else:
            vals = [ln.strip() for ln in f if ln.strip()]
    for v in vals:
        if "@" in v:
            dom = v.split("@", 1)[1].lower().strip()
            if "." in dom:
                domains.setdefault(dom, dom.rsplit(".", 1)[0].replace("-", " "))
    return domains


def verify_all(emails, base, secret, poll=3):
    """Submit candidates to Reacher, poll, return classified rows."""
    if not emails:
        return []
    job = submit_bulk(base, emails, secret)
    while True:
        p = get_progress(base, job, secret)
        done, total = p.get("total_processed") or 0, p.get("total_records") or len(emails)
        sys.stdout.write(f"\r  verifying candidates {done}/{total} …   ")
        sys.stdout.flush()
        if p.get("job_status") == "Completed" or (total and done >= total):
            break
        time.sleep(poll)
    print()
    return [row_for(r) for r in fetch_results(base, job, secret)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="a REVIEW csv (or any csv/txt with emails)")
    ap.add_argument("-o", "--outdir", default="enriched_out")
    ap.add_argument("--max-domains", type=int, default=0, help="cap domains processed (0 = all)")
    ap.add_argument("--workers", type=int, default=12, help="concurrent domain scrapes")
    ap.add_argument("--no-serp", action="store_true", help="skip the Bright Data open-web/LinkedIn layer")
    ap.add_argument("--no-unlock", action="store_true", help="skip the Web Unlocker fallback on blocked pages")
    ap.add_argument("--search-verify-cap", type=int, default=400,
                    help="max exact-match Google search-verify calls (cost guard; 0 = unlimited)")
    args = ap.parse_args()

    base, secret = resolve_backend()
    if not base:
        sys.exit("error: no REACHER_URL (set it at intake)")
    if not secret:
        sys.exit("error: no REACHER_SECRET (set env or run `reacher auth set-token`)")
    bd_key, bd_zone = resolve_brightdata()
    use_serp = not args.no_serp and bool(bd_key and bd_zone)
    unlock_key = None if args.no_unlock else bd_key
    unlock_zone = resolve_unlock_zone()

    domains = read_domains(args.input)
    dom_items = list(domains.items())
    if args.max_domains:
        dom_items = dom_items[: args.max_domains]
    print(f"→ backend: {base}")
    print(f"→ {len(domains)} unique domains" + (f" (capped to {len(dom_items)})" if args.max_domains else ""))
    print(f"→ SERP layer: {'ON (Bright Data)' if use_serp else 'off' + (' (no BRIGHTDATA_API_KEY/ZONE)' if not (bd_key and bd_zone) else '')}")
    print(f"→ Web Unlocker fallback: {'ON' if (unlock_key and not args.no_unlock) else 'off'}")

    # scrape + candidate-build (concurrent)
    per_domain = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(enrich_domain, d, c, use_serp, bd_key, bd_zone, unlock_key, unlock_zone): d
                for d, c in dom_items}
        n = 0
        for fut in as_completed(futs):
            n += 1
            r = fut.result()
            per_domain.append(r)
            if r["candidates"]:
                sys.stdout.write(f"\r  scraped {n}/{len(dom_items)} domains — {sum(len(x['candidates']) for x in per_domain)} candidates   ")
                sys.stdout.flush()
    print()

    # collect unique candidate emails + their source/domain/multi-field
    src = {}
    for r in per_domain:
        for e, meta in r["candidates"].items():
            src.setdefault(e, {"domain": r["domain"], **meta})
    candidates = list(src.keys())
    print(f"→ {len(candidates)} candidate emails across {sum(1 for r in per_domain if r['candidates'])} domains")

    # verify them all through Reacher
    verified = verify_all(candidates, base, secret)

    # ---- confidence tier per verified candidate (NOTHING unconfirmed ships) ----
    # DELIVERABLE            = SMTP-confirmed safe (incl. a guess whose mailbox proved live)
    # ACCEPT-ALL          = a REAL published email; domain catch-all so SMTP can't confirm
    # SEARCH-VERIFIED = a guess that Google shows published (exact-match) — corroborated
    # UNDELIVERABLE            = invalid, or a guess neither SMTP-safe nor search-found
    sv_budget = [args.search_verify_cap] if args.search_verify_cap else None
    sv_cache = {}

    def tier_for(v):
        reach = v["is_reachable"]
        if reach == "safe":
            return "DELIVERABLE"
        if reach == "invalid":
            return "UNDELIVERABLE"
        source = src.get(v["email"], {}).get("source", "")
        if source.startswith(SITE_SRC) or source == OPENWEB_SRC:
            return "ACCEPT-ALL"  # real, published, but domain catch-all/unknown
        # a pattern guess → only ships if Google shows it published
        if not (use_serp and bd_key):
            return "UNDELIVERABLE"
        if sv_budget is not None and sv_budget[0] <= 0:
            return "UNDELIVERABLE"  # cost cap hit
        e = v["email"]
        if e not in sv_cache:
            if sv_budget is not None:
                sv_budget[0] -= 1
            sv_cache[e] = search_verify(e, bd_key, bd_zone)
        return "SEARCH-VERIFIED" if sv_cache[e] else "UNDELIVERABLE"

    os.makedirs(args.outdir, exist_ok=True)
    fields = ["email", "domain", "tier", "source", "linkedin_url", "phone",
              "is_reachable", "is_catch_all", "is_role_account", "reason"]
    order = {"DELIVERABLE": 0, "ACCEPT-ALL": 1, "SEARCH-VERIFIED": 2, "UNDELIVERABLE": 3}
    guessed_nonsafe = sum(1 for v in verified
                          if v["is_reachable"] not in ("safe", "invalid")
                          and src.get(v["email"], {}).get("source", "").startswith(GUESS_SRC))
    if guessed_nonsafe:
        print(f"  search-verifying up to {min(guessed_nonsafe, args.search_verify_cap or guessed_nonsafe)} guessed catch-all candidates …")
    all_rows = []
    for v in verified:
        meta = src.get(v["email"], {})
        all_rows.append({"email": v["email"], "domain": meta.get("domain", ""),
                         "tier": tier_for(v), "source": meta.get("source", ""),
                         "linkedin_url": meta.get("linkedin_url", ""), "phone": meta.get("phone", ""),
                         "is_reachable": v["is_reachable"], "is_catch_all": v["is_catch_all"],
                         "is_role_account": v["is_role_account"], "reason": v["reason"]})
    all_rows.sort(key=lambda r: order.get(r["tier"], 9))
    mailable = [r for r in all_rows if r["tier"] in ("DELIVERABLE", "ACCEPT-ALL", "SEARCH-VERIFIED")]
    for name, rows in (("enriched_all.csv", all_rows), ("enriched_mailable.csv", mailable)):
        with open(os.path.join(args.outdir, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    c = {t: sum(1 for r in all_rows if r["tier"] == t) for t in order}
    print("\n" + "=" * 60)
    print(f"  ENRICHMENT COMPLETE — {len(dom_items)} domains, {len(candidates)} candidates")
    print("=" * 60)
    print(f"  ✅ DELIVERABLE             {c['DELIVERABLE']:>5}   SMTP-confirmed deliverable")
    print(f"  📬 ACCEPT-ALL           {c['ACCEPT-ALL']:>5}   real (published) — catch-all, mailable")
    print(f"  🔎 SEARCH-VERIFIED  {c['SEARCH-VERIFIED']:>5}   guess corroborated by Google")
    print(f"  ⛔ UNDELIVERABLE             {c['UNDELIVERABLE']:>5}   invalid / unconfirmed guess (not shipped)")
    print("=" * 60)
    print(f"  → {args.outdir}/enriched_mailable.csv  ({len(mailable)} SEND+LIKELY+SEARCH-VERIFIED)")
    print(f"  → {args.outdir}/enriched_all.csv       ({len(all_rows)} with tier + source + linkedin + phone)")
    if not use_serp:
        print("\n  Tip: set BRIGHTDATA_API_KEY + BRIGHTDATA_SERP_ZONE to add the open-web/LinkedIn")
        print("       layer — finds real published emails + named people even without a team page.")


if __name__ == "__main__":
    main()
