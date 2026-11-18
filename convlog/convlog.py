#!/usr/bin/env python3
"""The conversation log: one append-only record of every message every agent drafts, sends or receives.

    convlog.py add --agent sales-crm --channel email --direction in --person jo@example.com --text-file msg.txt
                   [--thread ID] [--status received] [--engine codex] [--approval REF] [--subject S] [--url U] [--test]
    convlog.py thread <person>            the whole conversation with one person, across agents and channels
    convlog.py pending-crm                lines the CRM sales agent has not recorded yet
    convlog.py mark-crm <id> <crm-ref>    the CRM sales agent records a line (appends a crm event; never rewrites)
    convlog.py has-draft <sha256>         exit 0 if a drafted or approved line carries this hash (the send gate asks)
    convlog.py daily [YYYY-MM-DD] [--mark]  write conversations/daily/<date>.md for a business whose CRM belongs to another system:
                                          that day's lines by person, plus every earlier received or sent line not yet handed
                                          over (a reply after last night's wrap, the weekend). --mark records each as handed over.
                                          The day is the business's own (CONVLOG_TZ, or "timezone" in context/config.json), not UTC
    convlog.py audit                      exit 1 on: a sent line with no earlier draft of the same text; an inbound
                                          line older than AUDIT_HOURS (default 26) the CRM agent has not recorded
    convlog.py vault                      rewrite vault/People/<person>.md from the log (Obsidian reads these)

Files, under $BOT_HOME (default: the current folder): conversations/<YYYY-MM>.jsonl (mode 600), vault/People/.
Rules the roles follow: log the inbound message before judging it; log the draft before asking for approval;
log the send after the sending tool confirms it. Only the CRM sales agent runs mark-crm. Nothing is ever edited
or deleted: a correction is a new line with direction "note". A line added with --test is marked as a test and treated like any other line."""
import datetime, hashlib, json, os, pathlib, re, sys, zoneinfo

HOME = pathlib.Path(os.environ.get("BOT_HOME", "."))
DIR = HOME / "conversations"
CHANNELS = {"email", "linkedin", "x", "instagram", "youtube", "facebook", "reddit", "tiktok", "skool", "sms", "phone", "forms", "newsletter", "crm", "site", "medium", "other"}
DIRECTIONS = {"in", "out", "note"}
STATUSES = {"received", "drafted", "approved", "sent", "skipped", "failed", "note"}


def now():
    if os.environ.get("CONVLOG_NOW"):  # tests set the clock
        return datetime.datetime.fromisoformat(os.environ["CONVLOG_NOW"]).astimezone(datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)


def zone():
    """The business's own day: CONVLOG_TZ, else "timezone" in context/config.json, else UTC. Timestamps stay UTC."""
    name = os.environ.get("CONVLOG_TZ")
    if not name:
        try:
            name = json.loads((HOME / "context" / "config.json").read_text()).get("timezone")
        except (OSError, ValueError):
            name = None
    try:
        return zoneinfo.ZoneInfo(name) if name else datetime.timezone.utc
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return datetime.timezone.utc


def local_day(ts):
    return f"{datetime.datetime.fromisoformat(ts).astimezone(zone()):%Y-%m-%d}"


def person_key(p):
    p = p.strip().lower()
    return p if "@" in p and " " not in p else re.sub(r"[^a-z0-9@._-]+", "-", p).strip("-")


def sha(text):
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def rows():
    out = []
    for f in sorted(DIR.glob("*.jsonl")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                print(f"bad line skipped: {f.name}:{n}", file=sys.stderr)
    return out


def append(rec):
    DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(DIR, 0o700)
    p = DIR / f"{now():%Y-%m}.jsonl"
    with p.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    os.chmod(p, 0o600)


def opt(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def add(a):
    need = {k: opt(a, "--" + k) for k in ("agent", "channel", "direction", "person")}
    if not all(need.values()) or ("--text-file" not in a and "--text" not in a):
        print("add needs --agent --channel --direction --person and --text-file (or --text)", file=sys.stderr); return 2
    if need["channel"] not in CHANNELS or need["direction"] not in DIRECTIONS:
        print(f"channel must be one of {sorted(CHANNELS)}; direction one of {sorted(DIRECTIONS)}", file=sys.stderr); return 2
    text = pathlib.Path(opt(a, "--text-file")).read_text() if "--text-file" in a else opt(a, "--text")
    status = opt(a, "--status", {"in": "received", "out": "drafted", "note": "note"}[need["direction"]])
    if status not in STATUSES:
        print(f"status must be one of {sorted(STATUSES)}", file=sys.stderr); return 2
    ts, h = now(), sha(text)
    rec = {"id": f"{ts:%Y%m%dT%H%M%S}-{h[:8]}", "ts": ts.isoformat(timespec="seconds"), "campaign": os.environ.get("CAMPAIGN", ""),
           "agent": need["agent"], "engine": opt(a, "--engine", ""), "channel": need["channel"], "direction": need["direction"],
           "status": status, "person": person_key(need["person"]), "thread": opt(a, "--thread", ""), "subject": opt(a, "--subject", ""),
           "url": opt(a, "--url", ""), "approval": opt(a, "--approval", ""), "sha256": h, "text": text}
    if "--test" in a:
        rec["test"] = True
    append(rec)
    print(rec["id"]); return 0


def crm_done(rs):
    return {r["ref"] for r in rs if r.get("event") == "crm"}


def messages(rs, tests=False):
    return [r for r in rs if "event" not in r]


def main(a):
    if not a:
        print(__doc__); return 2
    cmd, rs = a[0], rows()
    if cmd == "add":
        return add(a[1:])
    if cmd == "thread":
        key = person_key(a[1])
        for r in messages(rs, tests=True):
            if r["person"] == key:
                print(f"{r['ts']} {r['direction']:4} {r['status']:9} {r['channel']:10} {r['agent']:10} {r['text'][:200]!r}")
        return 0
    if cmd == "pending-crm":
        done = crm_done(rs)
        for r in messages(rs):
            if r["id"] not in done and r["status"] in ("received", "sent"):
                print(json.dumps({k: r[k] for k in ("id", "ts", "agent", "channel", "direction", "person", "thread")}))
        return 0
    if cmd == "mark-crm":
        if len(a) < 3 or a[1] not in {r["id"] for r in messages(rs)}:
            print("mark-crm <id> <crm-ref>: no such line", file=sys.stderr); return 2
        append({"event": "crm", "ref": a[1], "crm_ref": a[2], "ts": now().isoformat(timespec="seconds"), "agent": "sales-crm"})
        return 0
    if cmd == "has-draft":
        ok = any(r["sha256"] == a[1] and r["status"] in ("drafted", "approved") for r in messages(rs))
        print("logged" if ok else "NOT LOGGED: log the draft before it can be sent"); return 0 if ok else 1
    if cmd == "audit":
        done, bad, drafted = crm_done(rs), [], set()
        limit = now() - datetime.timedelta(hours=float(os.environ.get("AUDIT_HOURS", "26")))
        for r in messages(rs):
            if r["status"] in ("drafted", "approved"):
                drafted.add(r["sha256"])
            if r["status"] == "sent" and r["sha256"] not in drafted:
                bad.append(f"sent with no logged draft: {r['id']} {r['agent']} {r['channel']} {r['person']}")
            if r["direction"] == "in" and r["id"] not in done and datetime.datetime.fromisoformat(r["ts"]) < limit:
                bad.append(f"inbound not in the CRM after {os.environ.get('AUDIT_HOURS', '26')}h: {r['id']} {r['channel']} {r['person']}")
        print("\n".join(bad) if bad else f"audit ok: {len(messages(rs))} lines"); return 1 if bad else 0
    if cmd == "daily":
        day = next((x for x in a[1:] if not x.startswith("--")), f"{now().astimezone(zone()):%Y-%m-%d}")
        done = crm_done(rs)
        todays = [r for r in messages(rs) if local_day(r["ts"]) == day]
        carried = [r for r in messages(rs) if local_day(r["ts"]) < day and r["id"] not in done and r["status"] in ("received", "sent")]

        def section(title, ms):
            people, body = {}, []
            for r in ms:
                people.setdefault(r["person"], []).append(r)
            if ms:
                body += [f"## {title}", ""]
            for key, lines in sorted(people.items()):
                body += [f"### {key}", ""]
                for r in lines:
                    when = datetime.datetime.fromisoformat(r["ts"]).astimezone(zone())
                    body += [f"- {when:%Y-%m-%d %H:%M} {r['channel']} {r['direction']} {r['status']} ({r['agent']}): " + " ".join(r["text"].split())[:600]]
                body.append("")
            return body
        body = [f"# Conversations, {day}", "", f"{len(todays)} lines today, {len(carried)} carried over from earlier. Written by `convlog.py daily`; the log is the source.", ""]
        body += section("Carried over (not yet handed over)", carried) + section("Today", todays)
        if not todays and not carried:
            print(f"nothing to hand over for {day}: no file written; day taken in {getattr(zone(), 'key', 'UTC')}"); return 0
        out = DIR / "daily"; out.mkdir(parents=True, exist_ok=True)
        (out / f"{day}.md").write_text("\n".join(body))
        if "--mark" in a:
            for r in carried + todays:
                if r["id"] not in done and r["status"] in ("received", "sent"):
                    append({"event": "crm", "ref": r["id"], "crm_ref": f"daily-file:{day}", "ts": now().isoformat(timespec="seconds"), "agent": "daily-file"})
        print(out / f"{day}.md")
        print(f"{len(todays)} today, {len(carried)} carried over; day taken in {getattr(zone(), 'key', 'UTC')}")
        return 0
    if cmd == "vault":
        people, done = {}, {r["ref"]: r["crm_ref"] for r in rs if r.get("event") == "crm"}
        for r in messages(rs):
            if not r["person"].startswith(("wave-", "list-")):  # a wave's approval line names the list, not a person
                people.setdefault(r["person"], []).append(r)
        out = HOME / "vault" / "People"
        out.mkdir(parents=True, exist_ok=True)
        for key, ms in people.items():
            body = [f"# {key}", "", f"Conversation log, written by `convlog.py vault`. {len(ms)} lines. Do not edit: the log is the source.", ""]
            for r in ms:
                body += [f"## {r['ts']} · {r['channel']} · {r['direction']} · {r['status']} · [[{r['agent']}]]",
                         (f"CRM: {done[r['id']]}" if r["id"] in done else "CRM: not recorded yet"), "", "> " + r["text"].strip().replace("\n", "\n> "), ""]
            (out / (re.sub(r"[^a-z0-9@._-]", "-", key) + ".md")).write_text("\n".join(body))
        print(f"{len(people)} people written to {out}"); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
