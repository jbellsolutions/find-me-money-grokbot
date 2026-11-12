#!/usr/bin/env python3
"""muse_to_radar.py - turn Muse's pipe-delimited lead rows into a Funding Radar import body.

Input: the text between BEGIN-<ID> and END-<ID> that `muse.py wait-marker` prints,
one lead per line in the LEAD ROW format from metamuse-leads/references/prompts.md:

  platform | source | posted_at | url | author | need | category | fit | quote

Lines that don't parse are reported and skipped. Output: the JSON body of the Funding
Radar's POST /api/leads/import (MetaMuse charter Part F), lane "metamuse".

  muse_to_radar.py rows.txt                 # dry run: prints the body + counts
  muse_to_radar.py rows.txt -o batch.json   # write the body
  muse_to_radar.py rows.txt --post --yes    # POST it (needs RADAR_IMPORT_TOKEN in env; Justin's yes first)

The radar dedupes by URL, so a re-post of the same batch does nothing.
"""
import argparse, datetime, json, os, re, sys, urllib.request

ENDPOINT = os.environ.get("RADAR_IMPORT_URL", "")  # the Funding Radar import endpoint, set at intake
FIELDS = ["platform", "source", "posted_at", "url", "author", "need", "category", "fit", "quote"]
CAT_PREFIX = ("real-estate", "small-business", "trucking", "creator", "gig", "credit")


def parse(text):
    leads, bad = [], []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip().strip("`")
        if not line or "|" not in line or line.lower().startswith(("platform |", "tools used", "note")):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            bad.append((n, "too few fields", line[:120])); continue
        parts += [""] * (len(FIELDS) - len(parts))
        r = dict(zip(FIELDS, parts[:len(FIELDS)]))
        r["platform"] = r["platform"].lower()
        r["fit"] = r["fit"].lower()
        if not re.match(r"https?://", r["url"]):
            bad.append((n, "no url", line[:120])); continue
        if r["platform"] not in ("facebook", "instagram", "threads", "tiktok"):
            bad.append((n, "platform?", line[:120])); continue
        lead = {"url": r["url"], "platform": r["platform"], "need": r["need"][:300]}
        if r["fit"] in ("high", "medium"):
            lead["fit"] = r["fit"]
        elif r["fit"] == "low":
            lead["kind"] = "prospect"   # LOW goes to Prospects, per the charter
        else:
            bad.append((n, "fit must be high/medium/low", line[:120])); continue
        cat = r["category"].lower()
        if cat.startswith(CAT_PREFIX):
            lead["category"] = cat[:80]
        if r["source"]:
            lead["source"] = r["source"][:120]
        if r["author"]:
            lead["author"] = r["author"][:120]
        if r["quote"]:
            lead["quote"] = r["quote"][:280]
        if r["posted_at"]:
            lead["posted_at"] = r["posted_at"]
        leads.append(lead)
    return leads, bad


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rows"); p.add_argument("-o")
    p.add_argument("--post", action="store_true"); p.add_argument("--yes", action="store_true")
    a = p.parse_args()
    leads, bad = parse(open(a.rows).read())
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    for i, l in enumerate(leads, 1):
        l.setdefault("id", f"MUSE-{stamp}-{i:03d}")
    body = {"lane": "metamuse", "leads": leads}
    print(f"parsed {len(leads)} leads ({sum('fit' in l for l in leads)} high/medium, "
          f"{sum(l.get('kind') == 'prospect' for l in leads)} prospects); skipped {len(bad)}", file=sys.stderr)
    for n, why, line in bad:
        print(f"  skip line {n}: {why}: {line}", file=sys.stderr)
    out = json.dumps(body, indent=2)
    if a.o:
        open(a.o, "w").write(out); print(f"wrote {a.o}", file=sys.stderr)
    if not a.post:
        if not a.o:
            print(out)
        return
    if not a.yes:
        sys.exit("--post writes to the live Funding Radar. Re-run with --yes only after Justin's yes.")
    if not ENDPOINT:
        sys.exit("RADAR_IMPORT_URL not set (intake)")
    tok = os.environ.get("RADAR_IMPORT_TOKEN")
    if not tok:
        sys.exit("RADAR_IMPORT_TOKEN not set (never paste it in chat; load it from the lending-hub .env.local)")
    req = urllib.request.Request(ENDPOINT, data=out.encode(), method="POST",
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(r.status, r.read().decode()[:2000])
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")


if __name__ == "__main__":
    main()
