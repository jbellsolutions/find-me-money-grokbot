#!/usr/bin/env python3
"""Check a campaign file against agents.json and print its gap list.

    python3 tools/check_campaign.py <campaign.json> [more.json ...]     exit 1 on any failure
    python3 tools/check_campaign.py --table <campaign.json> ...         one markdown table across the campaigns

Fails on: a missing or unknown agent, a state outside the list, a
LinkedIn mode that signs in on the bot's computer, a LinkedIn cap above the template's, a second CRM writer,
or a key-shaped value anywhere in the file."""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "agents.json").read_text())
AGENTS, LANES = REG["agents"], {k for k in REG["lanes"] if not k.startswith("_")}
STATES = ("on", "test", "paused", "partial", "missing", "off")
SECRET = re.compile(r"(agt_[A-Za-z0-9_-]{20,}|sk-(?:ant-|or-|proj-)?[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|pit-[0-9a-f-]{30,}|eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,})")
sys.path.insert(0, str(ROOT / "linkedin"))
from lane import DEFAULT_CAPS  # noqa: E402


def check(path):
    raw = pathlib.Path(path).read_text()
    c, bad = json.loads(raw), []
    if SECRET.search(raw):
        bad.append("a key-shaped value is in the file")
    for k in ("campaign", "business", "kind", "grok", "approver", "crm", "engines", "linkedin", "agents"):
        if k not in c:
            bad.append(f"missing '{k}'")
    ag = c.get("agents", {})
    for a in AGENTS:
        if a not in ag:
            bad.append(f"agent '{a}' is not listed (say off if it is not wanted)")
        elif ag[a].get("state") not in STATES:
            bad.append(f"agent '{a}': state must be one of {', '.join(STATES)}")
    bad += [f"unknown agent '{a}'" for a in ag if a not in AGENTS]
    for a, o in c.get("engines", {}).get("overrides", {}).items():
        if a not in AGENTS or o.get("engine") not in REG["engines"]:
            bad.append(f"engine override for '{a}': unknown agent or engine")
    li = c.get("linkedin", {})
    if li.get("mode") not in ("outflo+local", "local-only", "off"):
        bad.append("linkedin.mode must be outflo+local, local-only or off")
    for k, v in li.get("caps", {}).items():
        if k not in DEFAULT_CAPS or int(v) > DEFAULT_CAPS[k]:
            bad.append(f"linkedin cap '{k}' is unknown or above the template's {DEFAULT_CAPS.get(k)}")
    if c.get("crm", {}).get("writer") not in ("sales-crm", "none"):
        bad.append("crm.writer must be sales-crm (the one writer), or none while another system owns the CRM")
    bad += [f"unknown lane '{x}'" for x in c.get("lanes", []) if x not in LANES]
    return c, bad


def engine_of(c, a):
    return c.get("engines", {}).get("overrides", {}).get(a, {}).get("engine", AGENTS[a]["engine"])


def main(a):
    table = "--table" in a
    paths = [x for x in a if not x.startswith("--")]
    if not paths:
        print(__doc__); return 2
    loaded, failed = [], False
    for p in paths:
        c, bad = check(p)
        loaded.append(c)
        failed |= bool(bad)
        if table:
            for b in bad:
                print(f"FAIL {p}: {b}", file=sys.stderr)
            continue
        print(f"# {c.get('business', p)} ({c.get('campaign', '?')}): {'FAIL' if bad else 'ok'}")
        for b in bad:
            print(f"  FAIL {b}")
        for k in AGENTS:
            s = c.get("agents", {}).get(k, {})
            print(f"  {k:11} {engine_of(c, k):8} {s.get('state', '?'):8} {s.get('waits_on', '') or ''}")
        gaps = [k for k in AGENTS if c.get("agents", {}).get(k, {}).get("state") in ("partial", "missing")]
        print(f"  gaps: {', '.join(gaps) or 'none'}\n")
    if table:
        print("| Agent | Engine | " + " | ".join(c["business"] for c in loaded) + " |")
        print("|---|---|" + "---|" * len(loaded))
        for k, v in AGENTS.items():
            print(f"| {v['name']} | {v['engine']} | " + " | ".join(c["agents"].get(k, {}).get("state", "?") for c in loaded) + " |")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
