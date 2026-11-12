#!/usr/bin/env python3
"""Watch a page: print only what changed since the last run, or nothing.

usage: page_diff.py <url> <state-dir> [--max-lines 40]
Exit 0 and print nothing when unchanged, so a routine can end with [SILENT].
For many pages or minute-level checks, a self-hosted changedetection.io does this outside the bot.
"""
import argparse
import difflib
import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from clean_page import clean, fetch  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("state")
    ap.add_argument("--max-lines", type=int, default=40)
    a = ap.parse_args()
    d = pathlib.Path(a.state)
    d.mkdir(parents=True, exist_ok=True)
    f = d / (hashlib.sha1(a.url.encode()).hexdigest()[:12] + ".txt")
    new = clean(fetch(a.url)).splitlines()
    old = f.read_text().splitlines() if f.exists() else None
    f.write_text("\n".join(new))
    if old is None:
        print(f"page_diff: first snapshot saved ({len(new)} lines); nothing to compare yet")
        return
    diff = [l for l in difflib.unified_diff(old, new, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    if diff:
        print(f"page_diff: {len(diff)} changed lines on {a.url}")
        print("\n".join(diff[: a.max_lines]))


if __name__ == "__main__":
    main()
