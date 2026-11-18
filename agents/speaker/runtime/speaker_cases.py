#!/usr/bin/env python3
"""Repair SpeakerAgent case files whose compensation status its validator refuses, so one bad case can't fail every run.

SpeakerAgent's research.py rejects the whole run on "invalid compensation status". On 2026-11-08 four cases written as
`none_stated` failed every podcast research run that day. Nothing stated about pay is `unknown`, so any status
outside the validator's set becomes `unknown`, and the old word is printed. speaker_cycle.py runs it before every
research run, and install.sh on each push. It adds no key, so the validator sees only the fields it knows.

    python3 speaker_cases.py <cases dir>
"""
import json
import sys
from pathlib import Path

# The same set as research.py's pay_states.
VALID = {"confirmed_paid", "likely_paid", "expenses_only", "confirmed_unpaid", "mixed_by_session_type", "unknown", "pay_to_speak"}


def repair(folder):
    fixed = []
    for path in sorted(Path(folder).glob("*.json")):
        try:
            case = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        comp = case.get("compensation") if isinstance(case, dict) else None
        if isinstance(comp, dict) and comp.get("status") not in VALID:
            was, comp["status"] = comp.get("status"), "unknown"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(case, indent=2))
            tmp.replace(path)
            fixed.append(f"{path.name} was {was}")
    return fixed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__.strip())
    done = repair(sys.argv[1]) if Path(sys.argv[1]).is_dir() else []
    print(f"speaker cases repaired: {len(done)}" + (f" ({', '.join(done)})" if done else ""))
