#!/usr/bin/env python3
"""Shorten long command output: keep errors/warnings, the head and the tail, drop repeats.

usage: <command> 2>&1 | shorten.py [--head 15] [--tail 25]
(rtk does this for developer commands, if the owner installs it.)
"""
import argparse
import re
import sys

KEY = re.compile(r"error|fail|warn|exception|traceback|denied|not found|refused|timeout", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", type=int, default=15)
    ap.add_argument("--tail", type=int, default=25)
    a = ap.parse_args()
    lines, seen = [], set()
    for l in sys.stdin:
        l = l.rstrip()
        if l in seen and not KEY.search(l):
            continue  # drop exact repeats
        seen.add(l)
        lines.append(l)
    if len(lines) <= a.head + a.tail:
        print("\n".join(lines))
        return
    mid = lines[a.head:-a.tail]
    keys = [l for l in mid if KEY.search(l)][:30]
    print("\n".join(lines[: a.head]))
    print(f"[... {len(mid)} lines cut; {len(keys)} error/warning lines kept below]")
    if keys:
        print("\n".join(keys))
    print("\n".join(lines[-a.tail:]))


if __name__ == "__main__":
    main()
