#!/usr/bin/env python3
"""Update a bot that already has an older Find Me Money install. One command, no questions, safe to run again.

    python3 /workspace/find-me-money/repo/tools/update.py

Justin, 2026-11-24: "it needs just the instructions to unpack the update because it's already been installed. The
instructions should just tell it to delete and remove the referral partnership stuff, the referral site."

What it does, in order:
1. If the older install lived in another folder (/workspace/revenue-os), brings Justin's answers across: context/,
   .secrets/, vault/, data/, content/, state/, log/, approved/ and his queue. Nothing is brought over twice.
2. Deletes the referral site's things from the workspace: every file and folder with "referral" in its name outside
   repo/, vault/ and log/, the referral lines in the switch files, and the site's two key lines in .secrets/. It also
   deletes the older install's setup pages for bots this pack no longer has. Every deleted path is listed in
   log/update-<date>.md. Nothing on the referral site itself is touched: it has its own agent now.
3. Renames what changed name (the CRM routine's line becomes Sales), puts this pack's settings in place (the older
   settings files are kept in a before-update/ folder) and runs the installer, which adds what is new and
   keeps every answer Justin already gave.
4. Prints what the bot does next: replace its memory, save the skills, delete the old routines, create the new ones.
"""
import os, re, shutil, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import team as T
import install as I

CARRY = ["context", ".secrets", "vault", "data", "content", "state", "log", "approved", "requests/justin"]
SKIP_TOP = {"repo", "vault", "log"}
OLD_BOTS = ["Referral Connection", "Lead Radar", "Content", "AEO and SEO", "Dream 100", "Dream 500", "Cold Email", "SpeakerAgent", "Reply", "Sales and CRM"]


def is_ref(s):
    """The referral site's, not the affiliates-and-referrals work this bot keeps."""
    s = s.lower()
    return bool(re.search(r"referral(?!s)", s)) and "affiliate" not in s and "referral partner" not in s


def main():
    team = T.load()
    ws = T.where(team)
    olds = [p for p in os.environ.get("OLD_HOMES", "/workspace/revenue-os").split(":") if p and os.path.isdir(p) and os.path.realpath(p) != os.path.realpath(ws)]
    notes, gone = [], []

    # 1. bring Justin's answers across from an older folder
    for old in olds:
        for rel in CARRY:
            src, dst = os.path.join(old, rel), os.path.join(ws, rel)
            if not os.path.isdir(src):
                continue
            n = 0
            for d, _, fs in os.walk(src):
                for f in fs:
                    s = os.path.join(d, f); t = os.path.join(dst, os.path.relpath(s, src))
                    if not os.path.exists(t):
                        os.makedirs(os.path.dirname(t), exist_ok=True); shutil.copy2(s, t); n += 1
            if n:
                notes.append(f"brought {n} files from {old}/{rel}")
        sec = os.path.join(ws, ".secrets")
        if os.path.isdir(sec):
            os.chmod(sec, 0o700)

    # the secrets file's name and its BOT_HOME line
    sec = os.path.join(ws, ".secrets")
    new_env = os.path.join(sec, team["secrets"])
    if os.path.isdir(sec):
        for f in sorted(os.listdir(sec)):
            p = os.path.join(sec, f)
            if f.endswith(".env") and p != new_env:
                lines = open(p).read().splitlines()
                have = open(new_env).read().splitlines() if os.path.exists(new_env) else []
                keys = {l.split("=", 1)[0] for l in have}
                add = [l for l in lines if "=" in l and l.split("=", 1)[0] not in keys]
                with open(new_env, "a") as h:
                    h.write("".join(l + "\n" for l in add))
                os.chmod(new_env, 0o600); os.remove(p); notes.append(f"keys from .secrets/{f} moved into .secrets/{team['secrets']}")
        if os.path.exists(new_env):
            lines = [l for l in open(new_env).read().splitlines() if not re.match(r"(RC_SITE|RC_ADMIN_KEY)=", l)]
            lines = [f"BOT_HOME={ws}" if l.startswith("BOT_HOME=") else l for l in lines]
            open(new_env, "w").write("\n".join(lines) + "\n"); os.chmod(new_env, 0o600)

    # 2. delete the referral site's things, and the older install's pages for bots that no longer exist
    for top in sorted(os.listdir(ws)) if os.path.isdir(ws) else []:
        if top in SKIP_TOP:
            continue
        base = os.path.join(ws, top)
        if is_ref(top):
            (shutil.rmtree if os.path.isdir(base) else os.remove)(base); gone.append(top); continue
        for d, ds, fs in os.walk(base):
            for x in list(ds):
                if is_ref(x):
                    shutil.rmtree(os.path.join(d, x)); ds.remove(x); gone.append(os.path.relpath(os.path.join(d, x), ws) + "/")
            for f in fs:
                if is_ref(f):
                    os.remove(os.path.join(d, f)); gone.append(os.path.relpath(os.path.join(d, f), ws))
    for rel in ("team", "sites", "requests/justin/create-the-team.md", "context/team-registry.md", "context/launch-area.md"):
        p = os.path.join(ws, rel)
        if os.path.isdir(p):
            shutil.rmtree(p); gone.append(rel + "/")
        elif os.path.exists(p):
            os.remove(p); gone.append(rel)
    old_routines = []
    for name in ("routines-on.md", "campaigns.md", "owners.md", "standing-approvals.md"):
        p = os.path.join(ws, "context", name)
        if not os.path.exists(p):
            continue
        keep = []
        for l in open(p).read().splitlines():
            if is_ref(l) or re.match(r"\s*rc_", l):
                gone.append(f"context/{name}: the line \"{l.strip()}\""); continue
            if name == "owners.md":
                l = re.sub(r"^pinnacle-ghl\s*:", "gohighlevel:", l)
            if name == "routines-on.md":
                l = re.sub(r"^CRM\s*:", "Sales:", l)
                l = re.sub(r"^Partnerships\s*:", "Affiliates and referrals:", l)
            keep.append(l)
        if name == "routines-on.md":
            now = {n for n, _, _ in team["agents"][0]["routines"]} | {s.split(":")[0] for s in team.get("switches", [])}
            old_routines = [l.split(":")[0].strip() for l in keep if re.match(r"[A-Za-z][^:#]*:\s*(on|test|off)\b", l) and l.split(":")[0].strip() not in now]
            keep = [l for l in keep if l.split(":")[0].strip() not in old_routines]
        open(p, "w").write("\n".join(keep) + "\n")

    # the campaign's settings come fresh from this pack; the older ones are kept beside them
    for c in team["campaigns"]:
        sd = os.path.join(ws, "context", "revenue-os", c)
        olds_ = [f for f in os.listdir(sd) if f.endswith(".json")] if os.path.isdir(sd) else []
        changed = [f for f in olds_ if not os.path.exists(os.path.join(REPO, "campaigns", c, "settings", f)) and f != "campaign.json"
                   or open(os.path.join(sd, f)).read() != open(os.path.join(REPO, "campaigns", c, f if f == "campaign.json" else os.path.join("settings", f))).read()]
        if changed:
            bk = os.path.join(sd, "before-update"); os.makedirs(bk, exist_ok=True)
            for f in changed:
                os.replace(os.path.join(sd, f), os.path.join(bk, f))
            notes.append(f"{len(changed)} settings files for {c} replaced by this pack's; the older ones are in context/revenue-os/{c}/before-update/")

    os.makedirs(os.path.join(ws, "log"), exist_ok=True)
    with open(os.path.join(ws, "log", f"update-{time.strftime('%Y-%m-%d', time.gmtime())}.md"), "a") as h:
        h.write(f"## update.py, {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC\n\n" + "".join(f"- {n}\n" for n in notes)
                + f"\nDeleted ({len(gone)}):\n" + "".join(f"- {g}\n" for g in gone) + "\n")

    print(f"UPDATE: {len(notes)} things brought across, {len(gone)} referral and old-install items deleted (the list is in {ws}/log/update-<date>.md)\n")
    # 3. the installer adds what is new and keeps the rest
    sys.argv = [sys.argv[0], "--update"]
    I.main()
    print(f"""BECAUSE THIS IS AN UPDATE, also do these before step 4 above:

A. Your memory: delete everything an older Find Me Money, Disruptor Revenue OS or Referral Connection install saved there,
   then save the new memory from step 1. Delete any skill of yours that is about the referral site.
B. Your routines: delete every routine of yours that is not one of the {len(team['agents'][0]['routines'])} in step 1's list"""
          + (f" (the old switch file named: {', '.join(old_routines)})" if old_routines else "") + f""".
   That includes anything named Referral, SpeakerAgent, Cold Email, Dream 100, Dream 500, Reply, CRM, or "... plan" and "... report".
C. Other bots from the older install ({', '.join(OLD_BOTS)}): if any exists, switch its routines off if you can and
   name it in your one message so Justin can delete it. Do not delete a bot yourself.
D. In your one message, before the checklist, say: what was deleted (the count and the file), which old routines you
   deleted, and which old bots still exist.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
