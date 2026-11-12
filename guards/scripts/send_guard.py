#!/usr/bin/env python3
"""Send guard. Run before anything reaches a person.

    send_guard.py <message-type> [--routine <NAME>]

Prints one of: auto (send), draft (put it in requests/justin/ and stop), stopped (context/STOP exists).
Exit 0 only for auto. A type is auto only if a line in context/standing-approvals.md starts with
`<message-type>:` and contains the word `auto`. A routine whose line in context/routines-on.md is
`test` (or not `on`) always gets draft."""
import sys, re
from _ws import p, stopped

def line_for(f, key):
    f = p("context", f)
    if not f.exists(): return ""
    for l in f.read_text(errors="ignore").splitlines():
        if re.match(rf"\s*{re.escape(key)}\s*:", l, re.I): return l.split(":", 1)[1].strip().lower()
    return ""

def main(a):
    if not a or a[0].startswith("-"): print(__doc__); return 2
    kind = a[0]
    routine = a[a.index("--routine") + 1] if "--routine" in a else None
    if stopped(): print("stopped"); return 1
    if routine and line_for("routines-on.md", routine) != "on": print("draft"); return 1
    print("auto" if re.search(r"\bauto\b", line_for("standing-approvals.md", kind)) else "draft")
    return 0 if re.search(r"\bauto\b", line_for("standing-approvals.md", kind)) else 1

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
