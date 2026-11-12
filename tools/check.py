#!/usr/bin/env python3
"""Completeness and safety check for a GrokBot pack built from the factory template.

    python3 tools/check.py            print the report; exit 1 on any failure
    python3 tools/check.py --ready    also fail on any placeholder left ({{...}} or FILL:)
    python3 tools/check.py --write    also rewrite SKILLS-MAP.md from skills.json

Checks:
1. Secrets: no key-shaped value anywhere in the pack.
2. Skills: every skill in skills.json exists with a SKILL.md that has a name and description.
3. Accounts: every account a role charter names is in skills.json -> accounts; its path exists; its keys
   are in .env.example and NEEDS-JUSTIN.md, or (SIGNIN) the account is on NEEDS-JUSTIN.md.
4. Routines: every role section in TRIGGER-MAP.md has a charter in roles/, and schedules total 50 or fewer.
5. Placeholders: {{...}} and FILL: left, reported as TODO (a failure only with --ready).
6. Adaptation: skills that still mention Mac paths or Hermes commands (reported, not failed).
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ROUTINE_CAP = 50

SECRET = re.compile(r"(agt_[A-Za-z0-9_-]{20,}|sk-(?:ant-|or-|proj-)?[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|pit-[0-9a-f-]{30,}|eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----\s*[A-Za-z0-9+/=]{40})")
ASSIGN = re.compile(r"""(?i)\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*["']?([A-Za-z0-9_\-]{24,})""")
PLACEHOLDER = re.compile(r"\{\{[a-z_]+\}\}|FILL:")
ADAPT = {"Hermes command": re.compile(r"\bhermes (?:-p|chat|kanban|cron)|kanban_create|\bHERMES_"),
         "Mac path": re.compile(r"~/\.claude|/Users/home"),
         "old box path": re.compile(r"/root/")}


def files():
    for d, ds, fs in os.walk("."):
        ds[:] = [x for x in ds if x not in (".git", "__pycache__")]
        for f in fs:
            p = os.path.join(d, f)[2:]
            try:
                yield p, open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                pass


def frontmatter(p):
    t = open(p, encoding="utf-8", errors="ignore").read()
    m = re.match(r"---\n(.*?)\n---", t, re.S)
    if not m:
        return None, None
    name = re.search(r"^name:\s*(.+)$", m.group(1), re.M)
    desc = re.search(r"^description:\s*(.+)$", m.group(1), re.M)
    return (name.group(1).strip() if name else None), (desc.group(1).strip().strip('"') if desc else None)


def roles():
    return sorted(f[:-3] for f in os.listdir("roles") if f.endswith(".md") and not f.startswith("_"))


def main():
    ready, write = "--ready" in sys.argv, "--write" in sys.argv
    fails, out = [], []
    allf = dict(files())
    cfg = json.load(open("skills.json"))

    # 1 secrets
    hits = []
    for p, t in allf.items():
        if p.endswith(".env.example"):
            continue
        for m in SECRET.finditer(t):
            hits.append((p, m.group(0)[:6] + "…"))
        for m in ASSIGN.finditer(t):
            v = m.group(1)
            if not re.fullmatch(r"[A-Z_]+|x+|X+|\.+|your[A-Za-z_-]*|<[^>]+>", v) and not v.isupper():
                hits.append((p, m.group(0)[:18] + "…"))
    out.append(f"1. Secrets: {len(hits)} key-shaped values in {len(allf)} files")
    out += [f"   FAIL {p}: {h}" for p, h in hits]
    if hits:
        fails.append("secrets")

    # 2 skills
    missing, bad, rows = [], [], []
    for role, need in cfg.get("skills", {}).items():
        for s in need:
            d = "guards" if s == "bot-guards" else f"skills/{role}/{s}"
            sk = os.path.join(d, "SKILL.md")
            if not os.path.exists(sk):
                missing.append(f"{role}/{s}")
                continue
            n, desc = frontmatter(sk)
            if not (n and desc):
                bad.append(sk)
            rows.append((role, s, d, desc or ""))
    total = sum(len(v) for v in cfg.get("skills", {}).values())
    out.append(f"2. Skills: {len(rows)} of {total} listed skills present; {len(missing)} missing; {len(bad)} without name+description")
    out += [f"   FAIL missing {m}" for m in missing] + [f"   FAIL no frontmatter {b}" for b in bad]
    if missing or bad:
        fails.append("skills")

    # 3 accounts
    env = open(".env.example").read() if os.path.exists(".env.example") else ""
    nj = open("NEEDS-JUSTIN.md").read() if os.path.exists("NEEDS-JUSTIN.md") else ""
    accounts = cfg.get("accounts", {})
    n_acc, problems = 0, []
    for r in roles():
        t = open(f"roles/{r}.md").read()
        sec = re.search(r"## Accounts it needs.*?\n(.*?)\n## ", t, re.S)
        for line in re.findall(r"^- (.+)$", sec.group(1) if sec else "", re.M):
            n_acc += 1
            key = next((k for k in accounts if line.startswith(k) or k in line), None)
            if not key:
                problems.append(f"roles/{r}.md: '{line}' is not in skills.json accounts")
                continue
            a = accounts[key]
            if a.get("path") and not os.path.exists(a["path"]):
                problems.append(f"roles/{r}.md: '{key}' -> {a['path']} not in the pack")
            for k in a.get("keys", []):
                if k == "SIGNIN":
                    if key not in nj:
                        problems.append(f"'{key}' sign-in is not on NEEDS-JUSTIN.md")
                elif not re.search(rf"^{k}=", env, re.M) or k not in nj:
                    problems.append(f"key {k} ({key}) is not in both .env.example and NEEDS-JUSTIN.md")
    out.append(f"3. Accounts: {n_acc} named in role charters; {len(problems)} problems")
    out += [f"   FAIL {p}" for p in problems]
    if problems:
        fails.append("accounts")

    # 4 routines
    tm = open("TRIGGER-MAP.md").read() if os.path.exists("TRIGGER-MAP.md") else ""
    sections = re.findall(r"^### (\S+)", tm, re.M)
    schedules = len(re.findall(r"^\| Schedule \| `[^`]+`", tm, re.M))
    orphan = [s for s in sections if s not in roles()]
    out.append(f"4. Routines: {schedules} schedules of {ROUTINE_CAP} allowed, across {len(sections)} role sections; {len(roles())} role charters")
    out += [f"   FAIL TRIGGER-MAP section '{s}' has no roles/{s}.md" for s in orphan]
    if schedules > ROUTINE_CAP:
        out.append(f"   FAIL {schedules} schedules is over the {ROUTINE_CAP} a bot allows")
    if orphan or schedules > ROUTINE_CAP:
        fails.append("routines")

    # 5 placeholders
    todo = {}
    for p, t in allf.items():
        if p.startswith(("tools/", "roles/_")) or p == "skills/README.md":
            continue
        c = len(PLACEHOLDER.findall(t))
        if c:
            todo[p] = c
    out.append(f"5. Placeholders: {sum(todo.values())} left in {len(todo)} files" + (" (TODO)" if todo and not ready else ""))
    out += [f"   {'FAIL' if ready else 'TODO'} {p}: {c}" for p, c in sorted(todo.items())]
    if ready and todo:
        fails.append("placeholders")

    # 6 adaptation (report only)
    flagged = []
    for role, s, d, _ in rows:
        text = "".join(t for p, t in allf.items() if p.startswith(d + "/"))
        flags = [k for k, rx in ADAPT.items() if rx.search(text)]
        if flags:
            flagged.append(f"{role}/{s}: {', '.join(flags)}")
    out.append(f"6. Adaptation: {len(rows)} skills; {len(flagged)} still mention Mac or Hermes things")
    out += [f"   NOTE {f}" for f in flagged]

    if write:
        with open("SKILLS-MAP.md", "w") as f:
            f.write("# Which role uses which skill, and why\n\nGenerated by `python3 tools/check.py --write` from skills.json. \"Why\" is the skill's own description: it is when the bot loads it.\n\n| Role | Skill | Where | Why |\n|---|---|---|---|\n")
            for role, s, d, desc in rows:
                f.write(f"| {role} | `{s}` | `{d}/` | {desc[:220].replace('|', '/')}{'…' if len(desc) > 220 else ''} |\n")

    print("\n".join(out))
    print("RESULT:", "PASS" if not fails else "FAIL (" + ", ".join(fails) + ")")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
