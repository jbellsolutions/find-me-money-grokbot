#!/usr/bin/env python3
"""Retry a flaky command with backoff, so the bot doesn't redo the whole job.

usage: retry.py [--tries 3] [--wait 2] -- <command> [args...]
Exit code is the last try's. In Python code, the tenacity library does the same (@retry).
"""
import argparse
import subprocess
import sys
import time


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        sys.exit("usage: retry.py [--tries N] [--wait S] -- <command>")
    i = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--wait", type=float, default=2.0)
    a = ap.parse_args(argv[:i])
    cmd = argv[i + 1:]
    rc = 1
    for n in range(1, a.tries + 1):
        rc = subprocess.call(cmd)
        if rc == 0:
            if n > 1:
                sys.stderr.write(f"retry: ok on try {n}\n")
            return 0
        sys.stderr.write(f"retry: try {n}/{a.tries} failed (exit {rc})\n")
        if n < a.tries:
            time.sleep(a.wait * (2 ** (n - 1)))
    return rc


if __name__ == "__main__":
    sys.exit(main())
