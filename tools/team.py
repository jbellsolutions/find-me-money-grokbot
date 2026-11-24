#!/usr/bin/env python3
"""The team (team.json): two main agents, one per campaign, and one agent per Revenue OS function.

    python3 tools/team.py list             every agent, its role and its routines
    python3 tools/team.py line <role>      the one line that turns a new bot into that agent
    python3 tools/team.py lines            that line for every agent
    python3 tools/team.py setup <role>     what that agent does to set itself up: its memory block, then its routines
    python3 tools/team.py ready <role>     write that agent's row in context/team-registry.md and its first heartbeat
    python3 tools/team.py check            exit 1 unless the team file, the role charters and the engine map agree
"""
import json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = 50


def load():
    return json.load(open(os.path.join(ROOT, "team.json")))


def where(team):
    """The workspace: BOT_HOME, else the folder this pack's repo/ sits in, else the name in team.json."""
    return os.environ.get("BOT_HOME") or (os.path.dirname(ROOT) if os.path.basename(ROOT) == "repo" else team["workspace"])


def agent(team, role):
    return next((a for a in team["agents"] if a["role"] == role), None)


def block(path):
    m = re.search(r"```\n(.*?)\n```", open(path, encoding="utf-8").read(), re.S)
    return m.group(1) if m else ""


def memory(role):
    """The agent's whole memory: the team's master prompt, then its own role section. Nothing else."""
    return block(os.path.join(ROOT, "MASTER-PROMPT.md")) + "\n\n" + block(os.path.join(ROOT, "roles", role + ".md"))


def line(team, a):
    ws = where(team)
    return (f"You are {a['bot']}, one agent on the {team['name']} team. If {ws}/repo/INSTALL.md is not on your computer, download "
            f"{team['link']}, unpack it into {ws}/repo/ and run python3 {ws}/repo/tools/install.py. Then run "
            f"python3 {ws}/repo/tools/team.py setup {a['role']} and do the three things it prints. Ask me nothing until you are done. "
            f"Nothing sends, posts, spends or writes to a CRM or a site until I say yes.")


def setup(team, a):
    ws = where(team)
    out = [f"# {a['bot']}: set yourself up ({a['role']})", "",
           "1. SAVE THIS TO YOUR MEMORY, word for word, and nothing else from the pack:", "", "-----", memory(a["role"]), "-----", "",
           "2. CREATE THESE ROUTINES (time zone UTC). Each runs; the switch file keeps it on test, so it only drafts:", ""]
    for name, cron, does in a["routines"]:
        out += [f"   - Name: {name}", f"     Schedule: {cron}",
                f"     Prompt: Role: {a['role']}. Routine: {name}. {does}. Follow your memory's run steps."]
    out += ["", f"3. RUN: python3 {ws}/repo/tools/team.py ready {a['role']}", "   Then answer \"ready\" in one line, with anything you could not do."]
    return "\n".join(out)


def problems():
    team, bad = load(), []
    roles = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "roles")) if f.endswith(".md"))
    have = [a["role"] for a in team["agents"]]
    bad += [f"roles/{r}.md has no agent in team.json" for r in roles if r not in have]
    bad += [f"agent '{r}' has no roles/{r}.md" for r in have if r not in roles]
    bad += [f"role '{r}' is listed {have.count(r)} times" for r in sorted(set(have)) if have.count(r) > 1]
    bots = [a["bot"] for a in team["agents"]]
    bad += [f"two agents are named '{b}'" for b in sorted(set(bots)) if bots.count(b) > 1]
    mains = [a.get("campaign") for a in team["agents"] if a["kind"] == "main"]
    bad += [f"campaign '{c}' has {mains.count(c)} main agents; it must have one" for c in team["campaigns"] if mains.count(c) != 1]
    bad += [f"campaign '{c}' has no folder in campaigns/" for c in team["campaigns"] if not os.path.isdir(os.path.join(ROOT, "campaigns", c))]
    reg = json.load(open(os.path.join(ROOT, "agents.json")))
    known = set(reg["agents"]) | set(reg.get("aliases", {}))
    bad += [f"agent '{a['role']}' names engine '{a.get('engine')}', which agents.json does not have" for a in team["agents"] if a["kind"] == "function" and a.get("engine") not in known]
    names = [r[0] for a in team["agents"] for r in a["routines"]]
    bad += [f"two routines are named '{n}'" for n in sorted(set(names)) if names.count(n) > 1]
    bad += [f"agent '{a['role']}' has more than the {CAP} routines one bot allows" for a in team["agents"] if len(a["routines"]) > CAP]
    for a in team["agents"]:
        if a["role"] in roles and f"Role: {a['role']}." not in block(os.path.join(ROOT, "roles", a["role"] + ".md")):
            bad.append(f"roles/{a['role']}.md has no memory block that starts 'Role: {a['role']}.'")
    return bad, team


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    bad, team = problems()
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    a = agent(team, arg) if arg else None
    if cmd == "check":
        n = sum(len(x["routines"]) for x in team["agents"])
        print("\n".join(bad) if bad else f"ok: {len(team['agents'])} agents ({sum(1 for x in team['agents'] if x['kind'] == 'main')} main, one per campaign), {n} routines")
        return 1 if bad else 0
    if cmd == "list":
        for x in team["agents"]:
            print(f"{x['bot']} | {x['kind']} | role {x['role']} | " + "; ".join(f"{n} ({c})" for n, c, _ in x["routines"]))
        return 0
    if cmd == "lines":
        for x in team["agents"]:
            print(f"## {x['bot']}\n\n{line(team, x)}\n")
        return 0
    if cmd in ("line", "setup", "ready") and not a:
        print(f"no agent for role '{arg}'. Roles: " + ", ".join(x["role"] for x in team["agents"])); return 1
    if cmd == "line":
        print(line(team, a)); return 0
    if cmd == "setup":
        print(setup(team, a)); return 0
    if cmd == "ready":
        ws = where(team)
        reg = os.path.join(ws, "context", "team-registry.md")
        os.makedirs(os.path.dirname(reg), exist_ok=True)
        rows = open(reg, encoding="utf-8").read().splitlines() if os.path.exists(reg) else ["# Team registry", "", "| Agent | Role | Routines | Set up (UTC) |", "|---|---|---|---|"]
        rows = [r for r in rows if not r.startswith(f"| {a['bot']} |")]
        rows.append(f"| {a['bot']} | {a['role']} | " + "; ".join(f"{n} `{c}`" for n, c, _ in a["routines"]) + f" | {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} |")
        open(reg, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        env = dict(os.environ, BOT_HOME=ws)
        subprocess.run([sys.executable, os.path.join(ROOT, "guards", "scripts", "beat.py"), "write", a["role"], "set up", "found=0", "drafted=0", "sent=0"], env=env, capture_output=True)
        done = sum(1 for r in rows if r.startswith("| ") and not r.startswith("| Agent") and not r.startswith("|---"))
        print(f"ok: {a['bot']} is in the registry ({done} of {len(team['agents'])} agents set up)")
        return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main())
