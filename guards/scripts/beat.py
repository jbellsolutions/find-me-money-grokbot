#!/usr/bin/env python3
"""Heartbeat. Every run ends with a beat; the lead's watchdog reads them.

    beat.py write <role> '<line>' [found=N drafted=N sent=N replies=N blocked=N ...]
    beat.py status [--hours 26]     one line per role; SILENT for any role past the limit; exit 1 if any

Roles come from repo/roles/*.md (files starting with _ are skipped). Beats go to state/heartbeat.jsonl."""
import sys, json, time, pathlib
from _ws import p

def roles():
    d = pathlib.Path(__file__).resolve().parents[2] / "roles"
    return sorted(f.stem for f in d.glob("*.md") if not f.stem.startswith("_"))

def main(a):
    hb = p("state", "heartbeat.jsonl")
    if len(a) >= 3 and a[0] == "write":
        nums = dict(x.split("=", 1) for x in a[3:] if "=" in x)
        hb.parent.mkdir(parents=True, exist_ok=True)
        with hb.open("a") as h: h.write(json.dumps({"t": int(time.time()), "role": a[1], "line": a[2], **nums}) + "\n")
        print("ok"); return 0
    if a and a[0] == "status":
        hours = float(a[a.index("--hours") + 1]) if "--hours" in a else 26
        last = {}
        if hb.exists():
            for l in hb.read_text().splitlines():
                try: r = json.loads(l); last[r["role"]] = r
                except (ValueError, KeyError): pass
        bad = 0
        for r in roles():
            b = last.get(r)
            age = (time.time() - b["t"]) / 3600 if b else None
            if age is None or age > hours: bad += 1; print(f"SILENT {r}: " + ("never" if b is None else f"{age:.0f}h ago"))
            else: print(f"ok {r}: {age:.1f}h ago, {b.get('line', '')}")
        return 1 if bad else 0
    print(__doc__); return 2

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
