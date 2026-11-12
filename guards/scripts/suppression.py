#!/usr/bin/env python3
"""Suppression guard. Run before any draft to a person.

    suppression.py check "<name, business, email or url>"   prints clear or held; exit 0 clear, 1 held
    suppression.py add "<who>" "<reason>"                    someone said no: done for every role

The list is context/suppression.csv (one entry per line, first column). Never print it."""
import sys, datetime
from _ws import p, norm

def entries():
    f = p("context", "suppression.csv")
    if not f.exists(): return []
    return [norm(l.split(",")[0]) for l in f.read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")]

def main(a):
    if len(a) >= 2 and a[0] == "check":
        q = norm(a[1])
        if not p("context", "suppression.csv").exists():
            print("held: no suppression list yet (context/suppression.csv); ask Justin"); return 1
        for e in entries():
            if len(e) >= 3 and (e == q or e in q.split() or (len(e) >= 6 and (e in q or q in e))):
                print("held"); return 1
        print("clear"); return 0
    if len(a) >= 2 and a[0] == "add":
        f = p("context", "suppression.csv"); f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a") as h: h.write(f"{a[1].replace(',', ' ')},{(a[2] if len(a) > 2 else 'said no').replace(',', ' ')},{datetime.date.today()}\n")
        print("added"); return 0
    print(__doc__); return 2

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
