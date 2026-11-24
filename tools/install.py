#!/usr/bin/env python3
"""Set up the team's workspace. One command, no questions, safe to run again.

    python3 /workspace/revenue-os/repo/tools/install.py

It makes the folders and the switch files, copies each campaign's settings to where the agents read them, writes each
agent's setup page and the fallback list of paste lines, runs the pack's checks, and prints what the installing agent
does next. It uses no network, installs nothing, asks nothing and never overwrites a file it wrote before: Justin's
answers in context/ survive a second run and a new pack version.
"""
import json, os, shutil, subprocess, sys, time, uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import team as T


def main():
    team = T.load()
    ws = T.where(team)
    made, kept = [], []

    def d(*parts, mode=None):
        p = os.path.join(ws, *parts)
        os.makedirs(p, exist_ok=True)
        if mode:
            os.chmod(p, mode)
        return p

    def w(rel, text, mode=None, fresh=False):
        p = os.path.join(ws, rel)
        if os.path.exists(p) and not fresh:
            kept.append(rel); return
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        if mode:
            os.chmod(p, mode)
        made.append(rel)

    roles = [a["role"] for a in team["agents"]]
    for x in ("context", "daily", "log", "state", "state/test", "approved", "content", "vault/Daily", "vault/People", "team",
              "requests/justin", "requests/partners", *[f"requests/{r}" for r in roles]):
        d(*x.split("/"))
    for x in ("data", "data/referral", "context/referral", "context/messaging", ".secrets"):
        d(*x.split("/"), mode=0o700)

    routines = [n for a in team["agents"] for n, _, _ in a["routines"]]
    w("context/routines-on.md", "# Routines: on, test or off\n\ntest means the routine runs and only drafts. Justin changes a line by saying it in an agent's chat.\n\n"
      + "".join(f"{n}: test\n" for n in routines) + "crm-writes: off\n")
    w("context/campaigns.md", "# Campaigns: on, test or off\n\n" + "".join(f"{c}: test\n" for c in team["campaigns"]))
    w("context/owners.md", "# Who writes each system: live (someone else; the team reads and drafts) or bot (the team writes)\n\n"
      "pinnacle-ghl: live\nreferral-site: live\ncold-email-sender: live\nsocial-sender: live\n")
    w("context/standing-approvals.md", "# Message types Justin has approved\n\nOne line per type: `<type>: auto` with the date and his words. Empty means every message is a draft.\n")
    w("context/spend-approvals.md", "# Spend Justin has approved\n\nOne line per plan: `<plan-id>: approved <usd>` with the date and his words. Empty means nothing paid runs.\n")
    w("context/computer.md", f"The team's shared computer. Written by install.py at {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC. id {uuid.uuid4().hex[:12]}\n")
    w("vault/Decisions.md", "# Decisions\n\nOne line per decision: the date, the campaign, what was decided, the number behind it.\n")
    w(".secrets/revenue-os.env", f"BOT_HOME={ws}\nCONVLOG_TZ=America/New_York\n", mode=0o600)
    w("context/team-registry.md", "# Team registry\n\n| Agent | Role | Routines | Set up (UTC) |\n|---|---|---|---|\n")

    for c in team["campaigns"]:
        src, dst = os.path.join(REPO, "campaigns", c), d("context", "revenue-os", c)
        for f in ["campaign.json"] + sorted(os.listdir(os.path.join(src, "settings"))):
            s = os.path.join(src, f if f == "campaign.json" else os.path.join("settings", f))
            t = os.path.join(dst, f)
            if os.path.exists(t):
                kept.append(f"context/revenue-os/{c}/{f}")
            else:
                shutil.copyfile(s, t); made.append(f"context/revenue-os/{c}/{f}")

    # these three are always rewritten: they come from the pack, not from Justin
    for a in team["agents"]:
        w(f"team/{a['role']}.md", T.setup(team, a) + "\n", fresh=True)
    others = team["agents"]
    w("requests/justin/create-the-team.md", "# If the first agent cannot create the other bots\n\nFor each name below that is not a bot yet: create a bot with that name, set its time zone to UTC, paste its line. Nothing else.\n\n"
      + "".join(f"## {a['bot']}\n\n{T.line(team, a)}\n\n" for a in others), fresh=True)
    shutil.copyfile(os.path.join(REPO, "NEEDS-JUSTIN.md"), os.path.join(ws, "requests", "justin", "CHECKLIST.md"))

    def run(*cmd):
        r = subprocess.run([sys.executable, *cmd], cwd=REPO, capture_output=True, text=True, env=dict(os.environ, BOT_HOME=ws))
        last = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or ["(no output)"])[-1]
        return r.returncode, last

    checks = [("pack check", run("tools/check.py")), ("team", run("tools/team.py", "check")), ("self-test", run("tools/selftest.py")),
              *[(f"campaign {c}", run("tools/check_campaign.py", f"campaigns/{c}/campaign.json")) for c in team["campaigns"]],
              ("owner guard", run("guards/scripts/owner_guard.py", "list"))]
    clis = {n: bool(shutil.which(n)) for n in ("claude", "codex")}
    ok = all(rc == 0 for n, (rc, _) in checks if n != "owner guard")
    log = [f"## install.py, {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC", "", f"workspace: {ws}", f"files written: {len(made)}; kept as they were: {len(kept)}", ""]
    log += [f"- {n}: {'ok' if rc == 0 else 'FAILED'} ({last})" for n, (rc, last) in checks]
    log += [f"- Claude Code CLI on this computer: {'yes' if clis['claude'] else 'no'}", f"- Codex CLI on this computer: {'yes' if clis['codex'] else 'no'}", ""]
    with open(os.path.join(ws, "log", "setup.md"), "a", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")

    mains = [a for a in team["agents"] if a["kind"] == "main"]
    print("\n".join(log))
    print("INSTALLED" if ok else "INSTALLED, WITH A FAILED CHECK ABOVE: go on, and put the failed line in your report")
    print(f"""
WHAT YOU DO NOW, in order, without asking Justin anything:

1. You are a main agent. If your name is "{mains[1]['bot']}", your role is {mains[1]['role']}; otherwise it is {mains[0]['role']}
   (rename yourself "{mains[0]['bot']}" if you can). Run: python3 {ws}/repo/tools/team.py setup <your role>
   and do the three things it prints.
2. Create the other {len(team['agents']) - 1} bots, one at a time. For each: python3 {ws}/repo/tools/team.py line <role> prints its name
   and the one line to give it. Set each bot's time zone to UTC. Roles: {', '.join(a['role'] for a in team['agents'])}.
   If you cannot create a bot, or cannot message one, stop trying after the first failure: the same lines are already
   in {ws}/requests/justin/create-the-team.md for Justin.
3. Send Justin ONE message: what is set up (read {ws}/context/team-registry.md), any failed check above, and then the
   whole of {ws}/requests/justin/CHECKLIST.md, starting with the line NEEDS-JUSTIN:
   Then stop. Do not ask the checklist's questions one at a time.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
