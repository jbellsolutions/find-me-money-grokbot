#!/usr/bin/env python3
"""The team: one Grok agent per role (team.json).

    python3 tools/team.py list             every agent: its name in Grok, its role, its Revenue OS function, its routines
    python3 tools/team.py message <role>   the setup message to give that agent (the lead sends it, or Justin pastes it)
    python3 tools/team.py messages         the setup message for every agent created at install, for the owner-step fallback
    python3 tools/team.py check            exit 1 unless every role has exactly one agent and every Revenue OS function has one
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = 50


def load():
    return json.load(open(os.path.join(ROOT, "team.json")))


def routines():
    """role -> [(name, cron)] from the role sections of TRIGGER-MAP.md."""
    out, role = {}, None
    for line in open(os.path.join(ROOT, "TRIGGER-MAP.md"), encoding="utf-8"):
        m = re.match(r"^### (\S+)", line)
        if m:
            role = m.group(1)
            continue
        if line.startswith("## "):
            role = None
        m = re.match(r"^\| Schedule \| `([^`]+)` \| ([^|]+?) \|", line)
        if m and role:
            out.setdefault(role, []).append((m.group(2).strip(), m.group(1)))
    return out


def message(a, team):
    ws = team["workspace"]
    names = ", ".join(f'"{n}"' for n, _ in routines().get(a["role"], [])) or "none yet"
    return (f"You are {a['bot']}, the {a['role']} agent of the Find Me Money team. The team's pack is already on this computer at "
            f"{ws}/repo/. Open {ws}/repo/TEAM.md and do \"An agent sets itself up\" as role {a['role']}: save the block in "
            f"repo/MASTER-PROMPT.md and the system prompt section of repo/roles/{a['role']}.md to your memory word for word, read "
            f"repo/CHARTER.md, create your routines ({names}) from repo/TRIGGER-MAP.md, paused, and write your line in "
            f"context/team-registry.md. Then answer \"ready\" with what you could not do. Nothing sends, posts, spends or writes "
            f"to a CRM or a site.")


def problems():
    team, rt = load(), routines()
    roles = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "roles")) if f.endswith(".md") and not f.startswith("_"))
    by_role = {}
    for a in team["agents"]:
        by_role.setdefault(a["role"], []).append(a)
    bad = []
    bad += [f"role '{r}' has no agent in team.json" for r in roles if r not in by_role]
    bad += [f"agent '{a[0]['bot']}' has no roles/{r}.md" for r, a in by_role.items() if r not in roles]
    bad += [f"role '{r}' has {len(a)} agents; it must have one" for r, a in by_role.items() if len(a) != 1]
    bots = [a["bot"] for a in team["agents"]]
    bad += [f"two agents are named '{b}'" for b in sorted(set(bots)) if bots.count(b) > 1]
    if sum(1 for a in team["agents"] if a.get("created") == "by_justin") != 1:
        bad.append("exactly one agent (the lead) must be created by_justin")
    fns = [a["function"] for a in team["agents"] if a.get("function")]
    try:
        want = sorted(json.load(open(os.path.join(ROOT, "agents.json")))["agents"])
    except Exception:
        want = []
    bad += [f"Revenue OS function '{f}' has no agent" for f in want if f not in fns]
    bad += [f"Revenue OS function '{f}' has {fns.count(f)} agents" for f in sorted(set(fns)) if fns.count(f) > 1]
    bad += [f"function '{f}' is not in agents.json" for f in fns if want and f not in want]
    bad += [f"TRIGGER-MAP section '{r}' has no agent" for r in rt if r not in by_role]
    bad += [f"agent for '{r}' has {len(v)} routines, over the {CAP} one agent allows" for r, v in rt.items() if len(v) > CAP]
    return bad, team, rt


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    bad, team, rt = problems()
    if cmd == "check":
        print("\n".join(bad) if bad else f"ok: {len(team['agents'])} agents, one per role")
        return 1 if bad else 0
    if cmd == "list":
        for a in team["agents"]:
            r = "; ".join(f"{n} ({c})" for n, c in rt.get(a["role"], [])) or "-"
            when = "" if a.get("created") != "later" else f" [created later: {a.get('waits_on', '')}]"
            print(f"{a['bot']} | role {a['role']} | function {a.get('function') or '-'} | {r}{when}")
        return 0
    if cmd == "message" and len(sys.argv) > 2:
        a = next((x for x in team["agents"] if x["role"] == sys.argv[2]), None)
        if not a:
            print(f"no agent for role '{sys.argv[2]}'"); return 1
        print(message(a, team)); return 0
    if cmd == "messages":
        for a in team["agents"]:
            if a.get("created") == "at_install":
                print(f"## {a['bot']}\n\n{message(a, team)}\n")
        return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main())
