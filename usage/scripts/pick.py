#!/usr/bin/env python3
"""Keep only the fields you need from a big JSON reply.

usage: pick.py <file.json or -> [--path a.b.items] [--fields name,stars,url] [--limit 50]
Prints one compact JSON object per line. (jq does the same: jq -c '.items[] | {name,stars}')
"""
import argparse
import json
import sys


def walk(d, path):
    for part in [p for p in path.split(".") if p]:
        if isinstance(d, list):
            d = d[int(part)]
        else:
            d = d.get(part) if isinstance(d, dict) else None
    return d


def get(o, dotted):
    for k in dotted.split("."):
        o = o.get(k) if isinstance(o, dict) else None
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--path", default="")
    ap.add_argument("--fields", default="")
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args()
    data = json.load(sys.stdin if a.src == "-" else open(a.src))
    node = walk(data, a.path)
    rows = node if isinstance(node, list) else [node]
    fields = [f for f in a.fields.split(",") if f]
    for r in rows[: a.limit]:
        out = {f: get(r, f) for f in fields} if fields else r
        print(json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    if len(rows) > a.limit:
        print(f"[... {len(rows) - a.limit} more rows; raise --limit]")


if __name__ == "__main__":
    main()
