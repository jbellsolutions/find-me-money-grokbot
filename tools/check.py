#!/usr/bin/env python3
"""Completeness and safety check for this pack. Exit 1 on any failure.

    python3 tools/check.py [--ready]

1. Secrets: no key-shaped value anywhere in the pack.
2. Bot: team.json, roles/ and jobs/ agree (tools/team.py check): every routine hands a job to the CLI through tools/job.py.
3. Files: every file the memory, INSTALL.md, a job or the CLI skill points to in repo/ is in the pack.
4. Keys: every key name in .env.example is on NEEDS-JUSTIN.md.
5. Size: the bot's whole install reading (INSTALL.md and its setup page) stays under 2,000 words.
6. Placeholders: {{...}} or FILL: left (a failure only with --ready).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import team as T

SECRET = re.compile(r"(agt_[A-Za-z0-9_-]{20,}|sk-(?:ant-|or-|proj-)?[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|pit-[0-9a-f-]{30,}|eyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----\s*[A-Za-z0-9+/=]{40})")
ASSIGN = re.compile(r"""(?i)\b[A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*["']?([A-Za-z0-9_\-]{24,})""")
PLACEHOLDER = re.compile(r"\{\{[a-z_]+\}\}|FILL:")
WORDS = 2000


def files():
    for d, ds, fs in os.walk("."):
        ds[:] = [x for x in ds if x not in (".git", "__pycache__")]
        for f in fs:
            p = os.path.join(d, f)[2:]
            try:
                yield p, open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                pass


def main():
    ready, fails, out = "--ready" in sys.argv, [], []
    allf = dict(files())

    hits = [p for p, t in allf.items() if not p.startswith("tools/check.py") and (SECRET.search(t) or ASSIGN.search(t))]
    out.append(f"1. Secrets: {len(hits)} key-shaped values in {len(allf)} files")
    out += [f"   FAIL {p}" for p in hits]
    if hits: fails.append("secrets")

    bad, team = T.problems()
    n = sum(len(a["routines"]) for a in team["agents"])
    out.append(f"2. Bot: {n} routines; {len(bad)} problems")
    out += [f"   FAIL {b}" for b in bad]
    if bad: fails.append("team")

    missing = []
    texts = {"INSTALL.md": allf.get("INSTALL.md", ""), "MASTER-PROMPT.md": allf.get("MASTER-PROMPT.md", "")}
    texts.update({p: t for p, t in allf.items() if p.startswith(("roles/", "jobs/", "skills/claude-code-cli/", "skills/content-tools/"))})
    texts["team.json"] = allf.get("team.json", "")
    for src, t in texts.items():
        for ref in set(re.findall(r"repo/([A-Za-z0-9_./-]+\.(?:py|md|json))", t)):
            if "<" in ref:
                continue
            if not os.path.exists(ref):
                missing.append(f"{src} points to repo/{ref}")
    out.append(f"3. Files: {len(missing)} missing")
    out += [f"   FAIL {m}" for m in sorted(missing)]
    if missing: fails.append("files")

    env, nj = allf.get(".env.example", ""), allf.get("NEEDS-JUSTIN.md", "")
    keys = re.findall(r"^([A-Z][A-Z0-9_]+)=\s*$", env, re.M)  # the empty ones are the secrets Justin gives
    off = [k for k in keys if k not in nj]
    out.append(f"4. Keys: {len(keys)} names in .env.example; {len(off)} not on NEEDS-JUSTIN.md")
    out += [f"   FAIL {k}" for k in off]
    if off: fails.append("keys")

    first = team["agents"][0]
    words = len(allf.get("INSTALL.md", "").split()) + len(T.setup(team, first).split())
    out.append(f"5. Size: the bot reads {words} words to install (limit {WORDS})")
    if words > WORDS:
        out.append("   FAIL the install reading is too long"); fails.append("size")

    todo = {p: len(PLACEHOLDER.findall(t)) for p, t in allf.items() if not p.startswith("tools/") and not (p.startswith("agents/") and "/prompts/" in p) and PLACEHOLDER.search(t)}
    out.append(f"6. Placeholders: {sum(todo.values())} left in {len(todo)} files")
    out += [f"   {'FAIL' if ready else 'TODO'} {p}: {c}" for p, c in sorted(todo.items())]
    if ready and todo: fails.append("placeholders")

    print("\n".join(out))
    print("RESULT:", "PASS" if not fails else "FAIL (" + ", ".join(fails) + ")")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
