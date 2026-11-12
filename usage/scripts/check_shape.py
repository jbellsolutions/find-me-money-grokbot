#!/usr/bin/env python3
"""Check a result has the right shape before using it; list only the bad fields.

usage: check_shape.py <shape.json> <data.json>
shape.json: {"required": {"name": "str", "email": "email", "stars": "int", "url": "url"}}
data.json: one object or a list of objects. Prints PASS, or one line per problem.
(pydantic does this in Python code.)
"""
import json
import re
import sys

CHECK = {
    "str": lambda v: isinstance(v, str) and v.strip() != "",
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "bool": lambda v: isinstance(v, bool),
    "url": lambda v: isinstance(v, str) and re.match(r"^https?://\S+$", v) is not None,
    "email": lambda v: isinstance(v, str) and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v) is not None,
    "list": lambda v: isinstance(v, list),
}


def main():
    shape = json.load(open(sys.argv[1]))["required"]
    data = json.load(open(sys.argv[2]))
    rows = data if isinstance(data, list) else [data]
    bad = 0
    for i, r in enumerate(rows):
        for field, kind in shape.items():
            v = r.get(field) if isinstance(r, dict) else None
            if v is None:
                print(f"row {i}: {field} missing")
                bad += 1
            elif not CHECK.get(kind, lambda _: True)(v):
                print(f"row {i}: {field} should be {kind}, got {json.dumps(v)[:60]}")
                bad += 1
    print("PASS" if not bad else f"FAIL {bad} problem(s) in {len(rows)} row(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
