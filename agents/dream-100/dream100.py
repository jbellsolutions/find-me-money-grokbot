#!/usr/bin/env python3
"""Dream 100 helpers. Finds nobody and sends nothing.

  dream100.py check-settings <settings.json>     is the file filled in enough to work from
  dream100.py score <settings.json> --scores '{"audience_fit": 28, ...}'     add up one candidate

check-settings exits 1 with what is missing. The one thing it refuses rather than
reports is a contact detail in the file: the owner's rule is that a pack never holds
contact lists.
"""
import argparse
import json
import re
import sys


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"cannot read settings: {e}")
        sys.exit(2)


def settings_problems(s):
    p = []
    if not isinstance(s.get("rank_on"), dict) or not s["rank_on"]:
        p.append("rank_on is empty: nothing to score candidates on")
    offer = s.get("offer", {})
    for k in ("free_value", "for_their_audience", "ask"):
        if not str(offer.get(k, "")).strip():
            p.append(f"offer.{k} is empty")
    if not any(c.get("on") for c in s.get("channels", {}).values() if isinstance(c, dict)):
        p.append("no channel is on")
    if not any(c.get("on") for c in s.get("sources", {}).values() if isinstance(c, dict)):
        p.append("no source is on")
    if re.search(r"[\w.+-]+@[\w-]+\.\w+", json.dumps(s)):
        p.append("an email address is in the settings (the owner's rule: a pack never holds contact lists)")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("check-settings")
    a.add_argument("settings")
    b = sub.add_parser("score")
    b.add_argument("settings")
    b.add_argument("--scores", required=True)
    args = ap.parse_args()
    s = load(args.settings)
    if args.cmd == "check-settings":
        problems = settings_problems(s)
        if problems:
            print("NOT READY")
            for x in problems:
                print("- " + x)
            sys.exit(1)
        print("settings ok")
        return
    try:
        scores = json.loads(args.scores)
    except ValueError:
        print("--scores is not JSON")
        sys.exit(2)
    rank = s.get("rank_on", {})
    total = sum(float(scores.get(k, 0)) for k in rank)
    print(json.dumps({"total": total, "out_of": sum(rank.values()),
                      "not_scored": [k for k in rank if k not in scores]}))


if __name__ == "__main__":
    main()
