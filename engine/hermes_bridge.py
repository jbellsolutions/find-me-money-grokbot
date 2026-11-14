#!/usr/bin/env python3
"""The bridge between the Grok bot (the orchestrator) and the Hermes worker on the Mac (the doer).

GrokBot plans, judges, queues approvals and reports. Hermes on the Mac in $MUSE_COMPUTER mines, scrapes,
drives Muse and the Mac's browser, sweeps inboxes and writes bulk drafts on its own cheap model. They talk
through two folders on the Mac, over the Orgo API (orgo.py bash), never through chat:

    ~/.fmm/grok/inbox/<id>.json     work orders the bot puts       (Hermes's fmm-worker-inbox job reads them)
    ~/.fmm/grok/outbox/<lane>/...   results Hermes writes           (the bot pulls them)
    ~/.fmm/grok/heartbeat.json      Hermes's last run per lane      (the watchdog reads it)

    hermes_bridge.py put <lane> '<json args>' [--routine NAME]   queue one work order (owner hermes-worker must be bot)
    hermes_bridge.py pull [--into DIR]                          copy new results into state/hermes/ (read only)
    hermes_bridge.py status                                     Hermes heartbeats, inbox depth, outbox counts (read only)
    hermes_bridge.py lanes                                      the lanes a work order may name, and who runs each

Executors (context/executors.md, one line per lane, `<lane>: hermes-mac | codex`; default hermes-mac):
- hermes-mac: the Hermes worker on the Mac (owner `hermes-worker` must be bot). Browser, Muse, Marketplace, sign-ins.
- codex: a Codex CLI on this bot's own computer, signed in to its own subscription (owner `codex-cli` must be bot).
  The `drafts` lane only (no web search in `codex exec`); the order runs here at once through the same dispatcher, and Grok
  spends nothing on it but this one call. Usage-mastery trick 29.

A work order names a lane and its arguments, nothing else: no free-text instructions, so a lead's words can
never become a command on the Mac. Each pull is one Orgo call; each put is one. That keeps the bot's usage
to a handful of calls a day however much Hermes does.
"""
import base64, json, os, pathlib, subprocess, sys, time, uuid

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
WS = pathlib.Path(os.environ.get("BOT_HOME") or REPO.parent)
ORGO = REPO / "skills" / "muse" / "orgo-computer-use" / "scripts" / "orgo.py"
OWNER = REPO / "guards" / "scripts" / "owner_guard.py"
REMOTE = "~/.fmm/grok"

# The lanes Hermes runs. Each maps to a script in hermes-worker/lanes/ on the Mac. Args are checked here.
LANES = {
    "fbgroups":      {"args": {"theme": str, "max_groups": int}, "doc": "One API read of the newest posts in one theme's Facebook groups"},
    "marketplace":   {"args": {"category": str, "metro": str, "via": str}, "doc": "Marketplace listings in one category and metro, read on the Mac (Muse or the Mac's browser)"},
    "muse":          {"args": {"niche": str}, "doc": "Ask Muse for today's finds in one niche (only when muse-app: bot)"},
    "craigslist":    {"args": {"sites": str, "cats": str}, "doc": "Craigslist read, rung 0, the business categories"},
    "places":        {"args": {"metro": str, "category": str}, "doc": "Google Maps businesses through Scrapebox places, free rung"},
    "influencers":   {"args": {"niche": str, "platform": str, "limit": int}, "doc": "Research public creators in one niche as partner or affiliate candidates"},
    "affiliate-houses": {"args": {"vertical": str, "limit": int}, "doc": "Research affiliate networks, ISO and broker networks, referral programs"},
    "coaches":       {"args": {"type": str, "limit": int}, "doc": "Coaches and consultants of one type, and their groups, as referral partners"},
    "group-discovery": {"args": {"theme": str, "limit": int}, "doc": "Find and register Facebook groups for one theme (coaching type, trade, niche), with member counts"},
    "wholesalers":   {"args": {"metro": str}, "doc": "Wholesaler rows from the live Craigslist reader, the Radar, groups and Muse, with call cards"},
    "drafts":        {"args": {"kind": str, "source": str, "limit": int}, "doc": "Bulk first drafts for a batch (the bot judges the best and queues them)"},
}


def die(msg, code=1):
    print(msg, file=sys.stderr); sys.exit(code)


def computer():
    c = os.environ.get("MUSE_COMPUTER", "").strip()
    if not c:
        die("blocked: MUSE_COMPUTER not set (intake)", 2)
    return c


def orgo_bash(cmd, timeout=120):
    """One Orgo call. orgo.py itself refuses anything on the never-touch list, and refuses when there is no list."""
    r = subprocess.run([sys.executable, str(ORGO), "bash", computer(), cmd, "--timeout", str(timeout)],
                       capture_output=True, text=True, timeout=timeout + 90)
    if r.returncode:
        die(f"orgo bash failed ({r.returncode}): {r.stderr.strip()[-300:]}", r.returncode)
    return r.stdout


def owns(routine):
    a = [sys.executable, str(OWNER), "check", "hermes-worker"] + (["--routine", routine] if routine else [])
    return subprocess.run(a, capture_output=True, text=True).returncode == 0


def check_args(lane, args):
    spec = LANES.get(lane)
    if not spec:
        die(f"unknown lane {lane}; one of {', '.join(LANES)}", 2)
    out = {}
    for k, v in args.items():
        t = spec["args"].get(k)
        if not t:
            die(f"lane {lane} takes no '{k}' (takes {', '.join(spec['args'])})", 2)
        if t is int:
            v = int(v)
            if not 0 < v <= 1000:
                die(f"{k} must be 1..1000", 2)
        else:
            v = str(v)
            if len(v) > 80 or any(c in v for c in "\n`$;|&<>/\\") or ".." in v:
                die(f"{k} must be a short plain value", 2)
        out[k] = v
    return out


def executor(lane):
    f = WS / "context" / "executors.md"
    if f.exists():
        for l in f.read_text(errors="ignore").splitlines():
            k, _, v = l.partition(":")
            if k.strip().strip("-* `") == lane and v.strip().split():
                return v.strip().split()[0].strip("`").lower()
    return "hermes-mac"


def run_local_codex(lane, args, routine):
    a = [sys.executable, str(OWNER), "check", "codex-cli"] + (["--routine", routine] if routine else [])
    if subprocess.run(a, capture_output=True, text=True).returncode:
        print("held: codex-cli is not moved to bot yet (Codex not installed and signed in)"); return 1
    base = WS / "state" / "worker"
    inbox = base / "grok" / "inbox"; inbox.mkdir(parents=True, exist_ok=True)
    order = {"id": uuid.uuid4().hex[:10], "lane": lane, "args": args, "at": int(time.time()), "from": "grokbot"}
    (inbox / f"{order['id']}.json").write_text(json.dumps(order))
    env = dict(os.environ, FMM_DIR=str(base), FMM_ENGINE="codex")
    r = subprocess.run([sys.executable, str(REPO / "hermes-worker" / "dispatch.py"), "run", "--max", "1"], env=env,
                       capture_output=True, text=True, timeout=1200)
    src = base / "grok" / "outbox" / lane
    dst = WS / "state" / "hermes" / lane; dst.mkdir(parents=True, exist_ok=True)
    for f in (src.glob("*") if src.exists() else []):
        f.replace(dst / f.name)   # the Pull routine routes state/hermes/ for every executor
    print(r.stdout.strip() or r.stderr.strip()[-300:]); return r.returncode


def muse_allowed(routine):
    a = [sys.executable, str(OWNER), "check", "muse-app"] + (["--routine", routine] if routine else [])
    return subprocess.run(a, capture_output=True, text=True).returncode == 0


def put(lane, raw, routine):
    args = check_args(lane, json.loads(raw or "{}"))
    # Typing into Muse is gated here, on this computer, where context/owners.md lives. The Mac never decides it.
    if lane == "muse" and not muse_allowed(routine):
        print("held: muse-app is live (typing into Muse needs Justin's yes)"); return 1
    if lane == "marketplace":
        args["via"] = "muse" if muse_allowed(routine) else "browser"
    if executor(lane) == "codex":
        return run_local_codex(lane, args, routine)
    if not owns(routine):
        # Hermes worker jobs aren't installed and on yet (Justin's yes): keep the order locally for the record.
        q = WS / "requests" / "hermes" / f"{time.strftime('%Y%m%d')}-{lane}-{uuid.uuid4().hex[:6]}.json"
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps({"lane": lane, "args": args, "at": int(time.time()), "state": "held: hermes-worker is live"}))
        print(f"held {q.name} (hermes-worker not moved to bot yet)"); return 1
    order = {"id": uuid.uuid4().hex[:10], "lane": lane, "args": args, "at": int(time.time()), "from": "grokbot"}
    b64 = base64.b64encode(json.dumps(order).encode()).decode()
    orgo_bash(f"mkdir -p {REMOTE}/inbox && echo {b64} | base64 -d > {REMOTE}/inbox/{order['id']}.json && echo ok")
    print(f"queued {order['id']} {lane}"); return 0


def pull(into):
    dest = pathlib.Path(into) if into else WS / "state" / "hermes"
    dest.mkdir(parents=True, exist_ok=True)
    seen = dest / ".pulled"
    since = int(seen.read_text()) if seen.exists() else 0
    # One call: tar the outbox files newer than the last pull, base64 them back.
    py = ("import io,os,sys,tarfile,base64,time\n"
          "r=os.path.expanduser('~/.fmm/grok/outbox'); s=float(sys.argv[1]); b=io.BytesIO(); n=0\n"
          "t=tarfile.open(fileobj=b,mode='w:gz')\n"
          "for d,_,fs in (os.walk(r) if os.path.isdir(r) else []):\n"
          " for f in fs:\n"
          "  p=os.path.join(d,f)\n"
          "  if n<500 and os.path.getmtime(p)>s and os.path.getsize(p)<2000000: t.add(p,arcname=os.path.relpath(p,r)); n+=1\n"
          "t.close(); print(base64.b64encode(b.getvalue()).decode() if n else '')\n")
    b64 = base64.b64encode(py.encode()).decode()
    out = orgo_bash(f"echo {b64} | base64 -d > /tmp/fmm-pull.py && python3 /tmp/fmm-pull.py {since}; rm -f /tmp/fmm-pull.py", timeout=180)
    data = "".join(out.split())
    if not data:
        print("pulled 0"); return 0
    import io, tarfile
    tf = tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode="r:gz")
    n = 0
    for m in tf.getmembers():
        if not m.isfile() or m.name.startswith("/") or ".." in m.name:
            continue
        tf.extract(m, dest); n += 1
    seen.write_text(str(int(time.time())))
    print(f"pulled {n} into {dest}"); return 0


def status():
    print(orgo_bash(f"cat {REMOTE}/heartbeat.json 2>/dev/null || echo '{{}}'; "
                    f"echo inbox $(ls {REMOTE}/inbox 2>/dev/null | wc -l); "
                    f"for d in {REMOTE}/outbox/*/; do [ -d \"$d\" ] && echo outbox $(basename $d) $(ls $d | wc -l); done; true").strip())
    return 0


def main(a):
    if a[:1] == ["lanes"]:
        for k, v in LANES.items():
            print(f"{k} [{executor(k)}]: {v['doc']} (args: {', '.join(v['args'])})")
        return 0
    if a[:1] == ["status"]:
        return status()
    if a[:1] == ["pull"]:
        return pull(a[a.index("--into") + 1] if "--into" in a else None)
    if len(a) >= 2 and a[0] == "put":
        routine = a[a.index("--routine") + 1] if "--routine" in a else None
        raw = a[2] if len(a) > 2 and not a[2].startswith("--") else "{}"
        return put(a[1], raw, routine)
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
