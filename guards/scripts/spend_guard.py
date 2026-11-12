#!/usr/bin/env python3
"""Spend guard. Run before any paid call, pull, scrape, top-up or plan change.

    spend_guard.py <plan-id> <usd>

Prints approved or held. Exit 0 only for approved. A spend is approved only if
context/spend-approvals.md has a line `<plan-id>: approved <cap-usd>` (Justin's yes, written by the
bot with his words beside it) and <usd> is at or under the cap, and STOP doesn't exist.
Held means: write the plan with its cost into requests/justin/ and stop."""
import sys, re
from _ws import p, stopped

def main(a):
    if len(a) < 2: print(__doc__); return 2
    pid, usd = a[0], float(a[1])
    f = p("context", "spend-approvals.md")
    if stopped() or not f.exists(): print("held"); return 1
    for l in f.read_text(errors="ignore").splitlines():
        m = re.match(rf"\s*{re.escape(pid)}\s*:\s*approved\s+\$?([0-9.]+)", l, re.I)
        if m and usd <= float(m.group(1)): print("approved"); return 0
    print("held"); return 1

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
