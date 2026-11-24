#!/usr/bin/env python3
"""The bot (team.json): one Grok bot that orchestrates, and the routines that hand each job to the Claude Code CLI.

    python3 tools/team.py list             the bot and its routines
    python3 tools/team.py line [role]      the one line that sets a bot up
    python3 tools/team.py setup [role]     what the bot does to set itself up: memory, the CLI skill, routines
    python3 tools/team.py ready [role]     write the bot's row in context/team-registry.md and its first heartbeat
    python3 tools/team.py check            exit 1 unless team.json, roles/ and jobs/ agree
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
    """The bot's whole memory section: the master prompt, then its role block. Nothing else."""
    return block(os.path.join(ROOT, "MASTER-PROMPT.md")) + "\n\n" + block(os.path.join(ROOT, "roles", role + ".md"))


def line(team, a):
    ws = team["workspace"]
    return (f"{'Add' if team.get('memory') == 'add' else 'Install'} {team['name']}. Download {team['link']}, unpack it into {ws}/repo/, run python3 {ws}/repo/tools/install.py "
            f"and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. "
            f"Nothing sends, posts, spends or writes to a CRM or a site until I say yes.")


def setup(team, a):
    ws = where(team)
    add = team.get("memory") == "add"
    out = [f"# {a['bot']}: set yourself up", "",
           ("1. ADD THIS SECTION TO YOUR MEMORY, word for word. Keep everything already in your memory: this is one more job, not a new identity."
            if add else
            "1. SAVE THIS TO YOUR MEMORY, word for word. It replaces anything an older install of this pack saved there."), "",
           "-----", memory(a["role"]), "-----", "",
           f"2. SAVE THE SKILL: the file {ws}/repo/skills/claude-code-cli/SKILL.md, as a skill named {team.get('skill_name', 'claude-code-cli')}.", "",
           "3. CREATE THESE ROUTINES (time zone UTC). Each runs; the switch file keeps it on test, so it only drafts:", ""]
    for name, cron, does in a["routines"]:
        out += [f"   - Name: {name}", f"     Schedule: {cron}",
                f"     Prompt: Routine: {name}. {does}. Follow the run steps in your memory{' (the ' + team['name'] + ' section)' if add else ''}."]
    out += ["", f"4. RUN: python3 {ws}/repo/tools/team.py ready {a['role']}"]
    return "\n".join(out)


def problems():
    team, bad = load(), []
    roles = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "roles")) if f.endswith(".md"))
    have = [a["role"] for a in team["agents"]]
    bad += [f"roles/{r}.md has no agent in team.json" for r in roles if r not in have]
    bad += [f"agent '{r}' has no roles/{r}.md" for r in have if r not in roles]
    names = [r[0] for a in team["agents"] for r in a["routines"]]
    bad += [f"two routines are named '{n}'" for n in sorted(set(names)) if names.count(n) > 1]
    bad += [f"agent '{a['role']}' has more than the {CAP} routines one bot allows" for a in team["agents"] if len(a["routines"]) > CAP]
    jobs = sorted(f[:-3] for f in os.listdir(os.path.join(ROOT, "jobs")) if f.endswith(".md"))
    used = set()
    for a in team["agents"]:
        if a["role"] in roles:
            b = block(os.path.join(ROOT, "roles", a["role"] + ".md"))
            if f"Role: {a['role']}." not in b:
                bad.append(f"roles/{a['role']}.md has no memory block that starts 'Role: {a['role']}.'")
            bad += [f"routine '{n}' is not named in roles/{a['role']}.md" for n, _, _ in a["routines"] if f'"{n}"' not in b]
        for n, _, does in a["routines"]:
            m = re.search(r"job\.py run ([a-z0-9-]+)", does)
            if not m:
                bad.append(f"routine '{n}' does not hand a job to tools/job.py")
            elif m.group(1) not in jobs:
                bad.append(f"routine '{n}' runs job '{m.group(1)}', which has no file in jobs/")
            else:
                used.add(m.group(1))
    bad += [f"jobs/{j}.md is run by no routine" for j in jobs if j not in used]
    if "job.py" not in block(os.path.join(ROOT, "MASTER-PROMPT.md")):
        bad.append("MASTER-PROMPT.md does not carry the rule that every task goes through tools/job.py")
    return bad, team


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    bad, team = problems()
    a = agent(team, sys.argv[2]) if len(sys.argv) > 2 else team["agents"][0]
    if cmd == "check":
        n = sum(len(x["routines"]) for x in team["agents"])
        print("\n".join(bad) if bad else f"ok: {len(team['agents'])} bot, {n} routines, every routine hands a job to the CLI")
        return 1 if bad else 0
    if cmd == "list":
        for x in team["agents"]:
            print(f"{x['bot']} | role {x['role']}")
            for n, c, d in x["routines"]:
                print(f"  {n} ({c}): {d}")
        return 0
    if not a:
        print("no such role. Roles: " + ", ".join(x["role"] for x in team["agents"])); return 1
    if cmd == "line":
        print(line(team, a)); return 0
    if cmd == "setup":
        print(setup(team, a)); return 0
    if cmd == "ready":
        ws = where(team)
        reg = os.path.join(ws, "context", "team-registry.md")
        os.makedirs(os.path.dirname(reg), exist_ok=True)
        rows = open(reg, encoding="utf-8").read().splitlines() if os.path.exists(reg) else ["# Registry", "", "| Bot | Role | Routines | Set up (UTC) |", "|---|---|---|---|"]
        rows = [r for r in rows if not r.startswith(f"| {a['bot']} |")]
        rows.append(f"| {a['bot']} | {a['role']} | " + "; ".join(f"{n} `{c}`" for n, c, _ in a["routines"]) + f" | {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} |")
        open(reg, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        subprocess.run([sys.executable, os.path.join(ROOT, "guards", "scripts", "beat.py"), "write", a["role"], "set up", "found=0", "drafted=0", "sent=0"],
                       env=dict(os.environ, BOT_HOME=ws), capture_output=True)
        print(f"ok: {a['bot']} is in the registry with {len(a['routines'])} routines")
        return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main())
