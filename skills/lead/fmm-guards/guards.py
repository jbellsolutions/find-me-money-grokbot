#!/usr/bin/env python3
"""guards: the checks the Find Me Money agent runs in code before it drafts, sends or spends.
Standard library only. State lives in $FMM_HOME (default /workspace/find-me-money/state).

    guards.py preflight [host ...]          STOP file, never-touch list and network. Every cron script starts here
    guards.py target <name>                 ok | refused: may the bot touch this computer, agent or account at all
    guards.py suppress check <who>          clear | held
    guards.py suppress add <who> --why ...  record an opt-out (always allowed)
    guards.py send <type> --to <who> [--text ...]   allowed | queued <id> | held <why>
    guards.py decide <id> approved|edited|rejected  a person's answer on a queued item
    guards.py gates                         each message type: mode, today's count, clean streak
    guards.py spend <pool> <amount>         allowed | refused <why>
    guards.py beat '<line>' found=N drafted=N ...   the heartbeat the health check reads

Exit codes: 0 go ahead, 3 STOP, 4 network down, 10 queued for a person, 11 held, 12 refused.

The guard never sends and never flips a gate. `gates.json` is edited by Justin only:
    {"public_reply": {"mode": "ask", "daily_cap": 20}, "email_first_touch": {"mode": "ask", "daily_cap": 25}}
A type that isn't listed is "ask". `spend.json` likewise: {"radar_credits": {"daily_cap": 3300, "floor": 3300}}.

Private names never ship in the pack; they come from the environment at intake:
    FMM_HOSTS     comma-separated hosts of the live services the jobs reach (the Radar, the Lending Hub). The vendor
                  host services.leadconnectorhq.com is always checked. Unset: preflight refuses (exit 12).
    NEVER_TOUCH   comma-separated never-touch names, else <workspace>/.secrets/never-touch.txt. Missing or empty:
                  preflight and every `target` check refuse (exit 12), so no Orgo or remote write runs without it.
"""
import argparse, json, os, socket, sys, time, uuid

HOME = os.environ.get("FMM_HOME", "/workspace/find-me-money/state")
VENDOR_HOSTS = ["services.leadconnectorhq.com"]
def allowed_hosts():
    """The hosts preflight checks: the vendor's plus FMM_HOSTS. None when FMM_HOSTS isn't set (refuse)."""
    own = [h.strip() for h in os.environ.get("FMM_HOSTS", "").split(",") if h.strip()]
    return VENDOR_HOSTS + own if own else None
PROVE = int(os.environ.get("FMM_PROVE_STREAK", "10"))   # clean approvals before a gate may be proposed for auto

def p(*parts):
    path = os.path.join(HOME, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def load(name, default):
    try: return json.load(open(p(name)))
    except (OSError, ValueError): return default

def save(name, data):
    tmp = p(name) + ".tmp"
    with open(tmp, "w") as f: json.dump(data, f, indent=1)
    os.replace(tmp, p(name))

def today(): return time.strftime("%Y-%m-%d", time.gmtime())
WS = os.environ.get("BOT_HOME") or os.path.dirname(HOME.rstrip("/"))   # the workspace: one STOP and one suppression list for every guard
def stopped(): return os.path.exists(os.path.join(HOME, "STOP")) or os.path.exists(os.path.join(WS, "context", "STOP"))

def never_touch():
    raw = os.environ.get("NEVER_TOUCH", "")
    names = raw.split(",")
    if not raw.strip():
        try: names = [l.split("#", 1)[0] for l in open(os.path.join(WS, ".secrets", "never-touch.txt"), errors="ignore").read().splitlines()]
        except OSError: names = []
    out = {n.strip().lower() for n in names if n.strip()}
    return out or None

def target(name):
    nt = never_touch()
    if nt is None: return 12, "refused: no never-touch list (set NEVER_TOUCH or .secrets/never-touch.txt at intake)"
    t = (name or "").strip().lower()
    if t and any(n == t or n in t for n in nt): return 12, "refused: target is on the never-touch list"
    return 0, "ok"

def preflight(hosts, tries=3, wait=10, resolve=socket.gethostbyname):
    if stopped(): return 3, "STOP"
    if never_touch() is None: return 12, "refused: no never-touch list (set NEVER_TOUCH or .secrets/never-touch.txt at intake)"
    hosts = hosts or allowed_hosts()
    if not hosts: return 12, "refused: FMM_HOSTS is not set (intake)"
    for h in hosts:
        for i in range(tries):
            try: resolve(h); break
            except OSError:
                if i == tries - 1: return 4, f"network: {h} doesn't resolve"
                time.sleep(wait)
    return 0, "ok"

def norm(s): return " ".join(str(s).lower().split())

def suppressed(who):
    who = norm(who)
    if not os.path.exists(os.path.join(WS, "context", "suppression.csv")): return True   # no list yet: hold, as suppression.py does
    lines = []
    for f in (p("suppression.txt"), os.path.join(WS, "context", "suppression.csv")):
        try: lines += [l.replace(",", "\t", 1) for l in open(f).read().splitlines() if l.strip() and not l.startswith("#")]
        except OSError: pass
    for line in lines:
        entry = norm(line.split("\t")[0])
        if entry and (entry == who or entry in who.split() or (entry.startswith("@") and who.endswith(entry))): return True
    return False

def suppress_add(who, why):
    with open(p("suppression.txt"), "a") as f: f.write(f"{norm(who)}\t{today()}\t{why}\n")
    shared = os.path.join(WS, "context", "suppression.csv")
    os.makedirs(os.path.dirname(shared), exist_ok=True)
    with open(shared, "a") as f: f.write(f"{who.replace(',', ' ')},{why.replace(',', ' ') or 'said no'},{today()}\n")

def queue(): return load("approvals.json", {})

def send(kind, to, text=""):
    if stopped(): return 3, "held STOP"
    if suppressed(to): return 11, "held suppressed"
    gate = dict(load("gates.json", {}).get(kind, {"mode": "ask"}))
    # One switch governs every guard: a type is auto only when context/standing-approvals.md marks it auto too (PLAYBOOK §4)
    try: sa = open(os.path.join(WS, "context", "standing-approvals.md")).read().splitlines()
    except OSError: sa = []
    if not any(l.strip().lower().startswith(kind.lower() + ":") and " auto" in " " + l.lower().split(":", 1)[1] for l in sa): gate["mode"] = "ask"
    counts = load("sent-counts.json", {})
    n = counts.get(today(), {}).get(kind, 0)
    if gate.get("mode") != "auto":
        q = queue(); qid = uuid.uuid4().hex[:10]
        q[qid] = {"type": kind, "to": to, "text": text, "at": time.time(), "state": "waiting"}
        save("approvals.json", q)
        return 10, f"queued {qid}"
    if n >= int(gate.get("daily_cap", 0)): return 11, f"held daily cap {gate.get('daily_cap', 0)}"
    counts.setdefault(today(), {})[kind] = n + 1
    save("sent-counts.json", counts)
    return 0, "allowed"

def decide(qid, verdict):
    q = queue()
    if qid not in q: return 12, "unknown id"
    q[qid].update(state=verdict, decided_at=time.time()); save("approvals.json", q)
    return 0, verdict

def gates():
    cfg, out = load("gates.json", {}), {}
    items = sorted(queue().values(), key=lambda x: x.get("decided_at") or 0)
    for kind in sorted(set(cfg) | {i["type"] for i in items}):
        streak = 0
        for i in items:
            if i["type"] != kind or i["state"] == "waiting": continue
            streak = streak + 1 if i["state"] == "approved" else 0     # an edit or a rejection resets it
        mode = cfg.get(kind, {}).get("mode", "ask")
        out[kind] = {"mode": mode, "waiting": sum(1 for i in items if i["type"] == kind and i["state"] == "waiting"),
                     "clean_streak": streak, "proven": streak >= PROVE,
                     "sent_today": load("sent-counts.json", {}).get(today(), {}).get(kind, 0)}
    return out

def spend(pool, amount, balance=None):
    if stopped(): return 3, "refused STOP"
    cap = load("spend.json", {}).get(pool)
    if not cap: return 12, f"refused: no cap set for {pool}; new spend is Justin's yes"
    used = load("spend-used.json", {})
    n = used.get(today(), {}).get(pool, 0)
    if n + amount > cap.get("daily_cap", 0): return 12, f"refused: {pool} daily cap {cap.get('daily_cap', 0)}, used {n}"
    if balance is not None and balance - amount < cap.get("floor", 0): return 12, f"refused: {pool} balance would fall under the floor {cap.get('floor', 0)}"
    used.setdefault(today(), {})[pool] = n + amount; save("spend-used.json", used)
    return 0, "allowed"

def beat(line, pairs, job=""):
    counts = {}
    for kv in pairs:
        k, _, v = kv.partition("=")
        try: counts[k] = int(v)
        except ValueError: counts[k] = v
    save(os.path.join("heartbeat", "find-me-money.json"), {"at": time.time(), "job": job, "line": line, "counts": counts})
    return 0, "ok"

def main(argv=None):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("preflight"); s.add_argument("hosts", nargs="*")
    s = sub.add_parser("target"); s.add_argument("name")
    s = sub.add_parser("suppress"); s.add_argument("op", choices=["check", "add"]); s.add_argument("who"); s.add_argument("--why", default="")
    s = sub.add_parser("send"); s.add_argument("kind"); s.add_argument("--to", required=True); s.add_argument("--text", default="")
    s = sub.add_parser("decide"); s.add_argument("qid"); s.add_argument("verdict", choices=["approved", "edited", "rejected"])
    sub.add_parser("gates")
    s = sub.add_parser("spend"); s.add_argument("pool"); s.add_argument("amount", type=int); s.add_argument("--balance", type=int)
    s = sub.add_parser("beat"); s.add_argument("line"); s.add_argument("pairs", nargs="*"); s.add_argument("--job", default="")
    a = ap.parse_args(argv)
    if a.cmd == "preflight": code, msg = preflight(a.hosts)
    elif a.cmd == "target": code, msg = target(a.name)
    elif a.cmd == "suppress":
        if a.op == "add": suppress_add(a.who, a.why); code, msg = 0, "added"
        else: code, msg = (11, "held") if suppressed(a.who) else (0, "clear")
    elif a.cmd == "send": code, msg = send(a.kind, a.to, a.text)
    elif a.cmd == "decide": code, msg = decide(a.qid, a.verdict)
    elif a.cmd == "gates": code, msg = 0, json.dumps(gates(), indent=1)
    elif a.cmd == "spend": code, msg = spend(a.pool, a.amount, a.balance)
    else: code, msg = beat(a.line, a.pairs, a.job)
    print(msg); return code

if __name__ == "__main__":
    sys.exit(main())
