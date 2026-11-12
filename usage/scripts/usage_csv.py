#!/usr/bin/env python3
"""Summarize a usage export (CSV) locally, so the export never has to be pasted into a bot chat.

usage: usage_csv.py <export.csv> [--by COLUMN] [--top 15]
Download the CSV from the usage dashboard (grok.com/dashboard → Usage, or cursor.com/dashboard → Usage →
Export CSV on Cursor-linked plans). Column names are not documented, so it guesses: it groups by any
column whose name mentions bot/agent/kind/type/model/source and sums any column mentioning token/cost/
usage/credit. Pass --by to choose. Prints shares, biggest first.
"""
import argparse
import csv
import re
import sys
from collections import defaultdict


def num(v):
    try:
        return float(re.sub(r"[^0-9.\-]", "", v or "") or 0)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--by", default="")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    with open(a.csv, newline="", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("usage_csv: empty file")
    cols = list(rows[0].keys())
    measures = [c for c in cols if re.search(r"token|cost|usage|credit|amount", c, re.I)]
    groups = [a.by] if a.by else [c for c in cols if re.search(r"bot|agent|kind|type|model|source|routine|name", c, re.I) and c not in measures]
    print(f"usage_csv: {len(rows)} rows; columns: {', '.join(cols)}")
    if not measures:
        print("usage_csv: no token/cost column found; pass a file with one")
        return
    for g in groups[:4]:
        for m in measures[:3]:
            tot = defaultdict(float)
            for r in rows:
                tot[(r.get(g) or "(blank)").strip()] += num(r.get(m))
            s = sum(tot.values()) or 1
            print(f"\n## {m} by {g}")
            for k, v in sorted(tot.items(), key=lambda kv: -kv[1])[: a.top]:
                print(f"{100 * v / s:5.1f}%  {v:,.0f}  {k[:60]}")


if __name__ == "__main__":
    main()
