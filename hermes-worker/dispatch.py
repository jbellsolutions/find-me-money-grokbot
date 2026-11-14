#!/usr/bin/env python3
"""Hermes worker dispatcher: runs on the Mac, inside the Find Me Money Hermes profile's cron (no model of its own).

Every 15 minutes it takes GrokBot's work orders from ~/.fmm/grok/inbox/, runs each lane, writes the result to
~/.fmm/grok/outbox/<lane>/<date>-<id>.<ext>, and records a heartbeat. GrokBot pulls the outbox a few times a day.

    python3 dispatch.py run [--max 4]     work the inbox (the cron job)
    python3 dispatch.py selftest          offline checks, no network, no model

Script lanes run a script. Model lanes run ONE bounded Hermes turn on the profile's own cheap model with a fixed
prompt from prompts/<lane>.md; the work order supplies only checked short values, never instructions.
~/.fmm/STOP stops everything (orders stay in the inbox).
"""
import json, os, pathlib, re, shutil, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent
FMM = pathlib.Path(os.environ.get("FMM_DIR", os.path.expanduser("~/.fmm")))
G = FMM / "grok"
PROFILE = os.environ.get("FMM_PROFILE", "find-me-money")
HERMES = os.environ.get("HERMES_BIN", "hermes")
# Which engine runs the model lanes here: "hermes" (the Find Me Money profile on the Mac or a VPS, its own cheap model)
# or "codex" (a Codex CLI signed in to its own subscription, so the spend leaves Grok's allowance; usage-mastery trick 29).
ENGINE = os.environ.get("FMM_ENGINE", "hermes")
CODEX = os.environ.get("CODEX_BIN", "codex")
# Lanes a CLI can do with no browser, no Muse, no Mac sign-ins and no web search: writing only.
# (`codex exec` has no web-search switch as of 2026-11-14, so research lanes stay on Hermes; a CLI asked to
# research without the web invents rows.)
CODEX_OK = {"drafts"}
TIMEOUT = int(os.environ.get("FMM_LANE_TIMEOUT", "900"))

SCRIPT_LANES = {
    "craigslist": lambda a, out: [sys.executable, str(HERE / "lanes" / "scrape.py"), "run", "--cats", a.get("cats", "biz"),
                                  "--sites", a.get("sites", "tampa"), "--max-age-hours", "36", "--out", str(out)],
    "fbgroups": lambda a, out: ["bash", str(HERE / "lanes" / "fbgroups.sh"), a.get("theme", "funding"), str(a.get("max_groups", 100)), str(out)],
}
MODEL_LANES = {"marketplace", "muse", "places", "influencers", "affiliate-houses", "coaches", "wholesalers", "drafts", "group-discovery"}
TURNS = {"drafts": 12, "muse": 20, "marketplace": 25}
SAFE = re.compile(r"^[A-Za-z0-9 ,._'-]{1,80}$")   # no slashes: work orders never carry paths


def ok_args(args):
    for k, v in args.items():
        if not re.fullmatch(r"[a-z_]{1,20}", k):
            return False
        if isinstance(v, int):
            if not 0 < v <= 1000:
                return False
        elif not (isinstance(v, str) and SAFE.match(v)) or ".." in v:
            return False
    return True


def beat(lane, line, n=None):
    f = G / "heartbeat.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        d = {}
    d[lane] = {"at": int(time.time()), "line": line, "n": n}
    tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(d, indent=1)); os.replace(tmp, f)


def prompt_for(lane, args):
    t = (HERE / "prompts" / f"{lane}.md").read_text()
    for k, v in args.items():
        t = t.replace("<" + k + ">", str(v))
    return re.sub(r"<[a-z_]+>", "(not given)", t)


def run_one(order):
    lane, args, oid = order.get("lane"), order.get("args", {}), order.get("id", "x")
    if lane not in SCRIPT_LANES and lane not in MODEL_LANES:
        return "rejected: unknown lane"
    if not ok_args(args):
        return "rejected: bad args"
    day = time.strftime("%Y%m%d")
    od = G / "outbox" / lane; od.mkdir(parents=True, exist_ok=True)
    if lane in SCRIPT_LANES:
        out = od / f"{day}-{oid}.jsonl"
        cmd = SCRIPT_LANES[lane](args, out)
    elif ENGINE == "codex":
        if lane not in CODEX_OK:
            return f"rejected: {lane} needs the Mac (browser, Muse or sign-ins), not a CLI"
        out = od / f"{day}-{oid}.md"
        cmd = [CODEX, "exec", "--approve-for-me", "--skip-git-repo-check", prompt_for(lane, args)]   # tested form, codex-cli 0.167
    else:
        out = od / f"{day}-{oid}.md"
        cmd = [HERMES, "-p", PROFILE, "chat", "-q", prompt_for(lane, args), "-Q", "--source", "tool",
               "--max-turns", str(TURNS.get(lane, 15))]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "failed: timeout"
    if lane in MODEL_LANES:
        out.write_text(p.stdout)
    if p.returncode:
        (od / f"{day}-{oid}.err").write_text(p.stderr[-4000:])
        return f"failed: exit {p.returncode}"
    return f"done: {out.name}"


def run(max_n):
    if (FMM / "STOP").exists():
        print("STOP"); return 3
    G.mkdir(parents=True, exist_ok=True)
    lock = G / "dispatch.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 4 * TIMEOUT + 300:
            print("busy: another dispatch is running"); return 0
        lock.unlink(); return run(max_n)   # a stale lock from a killed run
    try:
        return _run(max_n)
    finally:
        lock.unlink(missing_ok=True)


def _run(max_n):
    inbox, done = G / "inbox", G / "done"
    inbox.mkdir(parents=True, exist_ok=True); done.mkdir(parents=True, exist_ok=True)
    orders = sorted(inbox.glob("*.json"))[:max_n]
    for f in orders:
        try:
            order = json.loads(f.read_text())
        except ValueError:
            order = {"lane": "?", "id": f.stem}
        res = run_one(order)
        order["result"], order["finished"] = res, int(time.time())
        (done / f.name).write_text(json.dumps(order))
        f.unlink()
        beat(order.get("lane", "?"), res)
        print(f"{f.stem} {order.get('lane')}: {res}")
    export_profile()
    beat("dispatch", f"worked {len(orders)}", len(orders))
    return 0


def export_profile():
    """Copy what the Hermes profile's own jobs produced (its approval queue of drafts waiting on Justin, its
    heartbeats, today's loop list) into the outbox, so GrokBot's Sales desk reads it in the same pull."""
    od = G / "outbox" / "profile"; od.mkdir(parents=True, exist_ok=True)
    for src, name in ((FMM / "approvals.json", "approvals.json"), (FMM / "gates.json", "gates.json")):
        if src.exists():
            shutil.copyfile(src, od / name)
    hb = FMM / "heartbeat"
    if hb.is_dir():
        for f in hb.glob("*.json"):
            shutil.copyfile(f, od / f"heartbeat-{f.name}")
    loops = sorted(pathlib.Path(os.path.expanduser("~/.pinnacle-reply/vault")).glob("**/*loop*.md"))[-1:]
    for f in loops:
        shutil.copyfile(f, od / "loops-latest.md")


def selftest():
    global G, FMM
    import tempfile
    t = pathlib.Path(tempfile.mkdtemp()); FMM = t; G = t / "grok"
    assert ok_args({"metro": "Tampa", "limit": 5}) and not ok_args({"metro": "a; rm -rf /"}) and not ok_args({"limit": 0})
    assert not ok_args({"theme": "../x"}) and not ok_args({"theme": "a/b"})
    assert "Tampa" in prompt_for("places", {"metro": "Tampa", "category": "roofing"})
    for lane in MODEL_LANES:
        assert (HERE / "prompts" / f"{lane}.md").exists(), f"no prompt for {lane}"
    (G / "inbox").mkdir(parents=True)
    (G / "inbox" / "a.json").write_text(json.dumps({"id": "a", "lane": "nope", "args": {}}))
    (G / "inbox" / "b.json").write_text(json.dumps({"id": "b", "lane": "places", "args": {"metro": "x`y"}}))
    run(4)
    assert json.loads((G / "done" / "a.json").read_text())["result"] == "rejected: unknown lane"
    assert json.loads((G / "done" / "b.json").read_text())["result"] == "rejected: bad args"
    (t / "STOP").write_text(""); (G / "inbox" / "c.json").write_text("{}")
    assert run(4) == 3 and (G / "inbox" / "c.json").exists()
    global ENGINE
    ENGINE = "codex"
    assert run_one({"id": "d", "lane": "marketplace", "args": {"category": "cars", "metro": "Tampa"}}).startswith("rejected: marketplace needs the Mac")
    ENGINE = "hermes"
    shutil.rmtree(t)
    print("selftest OK"); return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]:
        sys.exit(selftest())
    if a[:1] == ["run"]:
        sys.exit(run(int(a[a.index("--max") + 1]) if "--max" in a else 4))
    print(__doc__); sys.exit(2)
