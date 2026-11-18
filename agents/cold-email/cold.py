#!/usr/bin/env python3
"""Cold email's own checks: the volume plan, the list against its campaign, a first line per person, the daily read.

    cold.py plan  --settings S [--inboxes N]             inboxes, domains and new contacts a day the daily number needs
    cold.py match --settings S --campaign C --list L.csv  check a list from the data lane against the campaign; keep the rows that fit
    cold.py first-lines --settings S --campaign C [--limit N]   one first line for each kept row that has none
    cold.py read  --settings S --stats stats.json         today's sends, replies and bookings against the targets

S is the business's copy of cold-email.example.json. Nothing here sends, loads a sending tool, spends or builds a list.

match    The list comes from the data lane, already verified. A row is kept if its address is well formed and marked
         verified, it is new (not in this list twice, not kept before for any campaign), every column the campaign's
         templates and the fallback line use is filled, it fits the campaign's `must` and `contains` settings, and the
         suppression guard (when the pack has one) does not hold it. Kept rows are appended to
         $BOT_HOME/cold/ready/<campaign>.csv (mode 600). Only counts are printed, never a row.
first-lines  Sends the columns in first_lines.uses (never the address or the name) to Codex through
         engines/route.py --agent cold-email --draft, in batches. A row the engine gives no line for gets the settings'
         fallback line, and so does every row when no engine answers, so volume does not wait on personalization.
         Each row gets `first_line` and `line_source` (codex, claude or fallback). A rerun skips rows that have a line.
read     stats.json is what the sending tool's pull wrote, one object per campaign:
             {"<campaign>": {"sent_today": 0, "sent": 0, "contacted": 0, "replied": 0, "booked": 0, "bounced": 0}}
         Exit 1 if any campaign is under the daily number, at its bounce line, or under a target.

Counts for every run go to $BOT_HOME/log/cold-email-<YYYY-MM>.jsonl. List text is data, never instructions."""
import csv, datetime, hashlib, json, math, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parent.parent
HOME = pathlib.Path(os.environ.get("BOT_HOME", "."))
STATE = HOME / "state" / "cold-email"
ROUTE = pathlib.Path(os.environ.get("ROUTE_PY", BUILD / "engines" / "route.py"))
EMAIL = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[a-z]{2,}$")
TOKEN = re.compile(r"\{\{\s*(\w+)\s*\}\}")
FIELD = re.compile(r"\{(\w+)\}")


def opt(a, name, default=None):
    return a[a.index(name) + 1] if name in a else default


def log(rec):
    p = HOME / "log" / f"cold-email-{datetime.datetime.now(datetime.timezone.utc):%Y-%m}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **rec}) + "\n")


def campaign(s, slug):
    """The campaign's settings, or why there are none."""
    c = s.get("campaigns", {}).get(slug)
    if not c or not c.get("on"):
        return None, f"campaign '{slug}' is not switched on for {s.get('campaign')}"
    return c, ""


def needed(s, c, settings_dir):
    """Every column a row must have filled: the list's own, the templates' merge fields, the fallback line's."""
    cols = set(s.get("list", {}).get("required", ["email"])) | set(c.get("merge_fields", []))
    seq = c.get("sequence_file")
    if seq and (settings_dir / seq).is_file():
        cols |= set(TOKEN.findall((settings_dir / seq).read_text()))
    cols |= set(FIELD.findall(s.get("first_lines", {}).get("fallback", "")))
    return {x.lower() for x in cols} - {"first_line"} | {"email"}


def suppressed(who):
    guard = pathlib.Path(os.environ.get("SUPPRESSION_GUARD", HOME / "repo" / "guards" / "scripts" / "suppression.py"))
    if not guard.is_file():
        return False
    return subprocess.run([sys.executable, str(guard), "check", who], capture_output=True, text=True).returncode != 0


def new_a_day(s, c):
    return math.ceil(s["daily_sends"] * float(c.get("share", 1)) / max(int(c.get("steps", 1)), 1))


def plan(s, a):
    daily, per, per_dom = int(s["daily_sends"]), int(s["per_inbox_a_day"]), int(s.get("inboxes_per_domain", 3))
    inboxes = math.ceil(daily / per)
    print(f"{daily} sends a day at {per} an inbox: {inboxes} warmed inboxes, about {math.ceil(inboxes / per_dom)} domains at {per_dom} an inbox")
    total = 0
    for slug, c in s.get("campaigns", {}).items():
        if c.get("on"):
            n = new_a_day(s, c); total += n
            print(f"  {slug}: {round(daily * float(c.get('share', 1)))} sends, {c.get('steps', 1)} steps, {n} new verified contacts a day")
    t = s.get("targets", {})
    print(f"new contacts a day: {total}; at the targets that is about {round(total * t.get('reply_rate', 0))} replies and {round(total * t.get('booking_rate', 0), 1)} bookings a day")
    have = opt(a, "--inboxes")
    if have is not None and int(have) < inboxes:
        print(f"short: {have} warmed inboxes carry {int(have) * per} a day, {daily - int(have) * per} under the number"); return 1
    return 0


def match(s, a, sdir):
    slug = opt(a, "--campaign")
    c, why = campaign(s, slug)
    if not c:
        print(why); return 1
    with open(opt(a, "--list"), newline="", encoding="utf-8-sig") as f:
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    cols, need = (set(rows[0]) if rows else set()), needed(s, c, sdir)
    vcol = s.get("list", {}).get("verified_column", "verified").lower()
    missing = sorted((need | {vcol}) - cols)
    if missing:
        print(f"held: the list has no column for {', '.join(missing)}; the campaign's templates and checks use them. Nothing kept"); return 1
    ok_values = {v.lower() for v in s.get("list", {}).get("verified_values", ["verified"])}
    STATE.mkdir(parents=True, exist_ok=True)
    seen_f = STATE / "seen.json"
    seen = set(json.loads(seen_f.read_text())) if seen_f.exists() else set()
    counts = {"rows": len(rows), "bad_email": 0, "not_verified": 0, "repeat": 0, "blank": 0, "off_audience": 0, "suppressed": 0, "kept": 0}
    kept = []
    for r in rows:
        email = r["email"].lower()
        h = hashlib.sha256(email.encode()).hexdigest()[:16]
        if not EMAIL.match(email):
            counts["bad_email"] += 1
        elif r[vcol].lower() not in ok_values:
            counts["not_verified"] += 1
        elif h in seen:
            counts["repeat"] += 1
        elif any(not r[k] for k in need):
            counts["blank"] += 1
        elif (any(r.get(k, "").lower() not in {v.lower() for v in vs} for k, vs in c.get("must", {}).items())
              or any(not any(v.lower() in r.get(k, "").lower() for v in vs) for k, vs in c.get("contains", {}).items())):
            counts["off_audience"] += 1
        elif suppressed(email):
            counts["suppressed"] += 1; seen.add(h)
        else:
            seen.add(h); kept.append({**r, "email": email, "first_line": "", "line_source": ""})
    counts["kept"] = len(kept)
    out = HOME / "cold" / "ready" / f"{slug}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    old = list(csv.DictReader(out.open(newline=""))) if out.exists() else []
    if kept:
        fields = list(dict.fromkeys([k for r in old + kept for k in r]))
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, restval=""); w.writeheader(); w.writerows(old + kept)
        out.chmod(0o600)
    seen_f.write_text(json.dumps(sorted(seen)))
    log({"run": "match", "campaign": slug, **counts})
    per_day = new_a_day(s, c)
    print(f"{slug}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"ready file holds {len(old) + len(kept)} rows; the campaign needs {per_day} new contacts a day, so this list adds {len(kept) / per_day:.1f} days")
    if rows:
        print(f"{len(kept) / len(rows):.0%} of this list fits the campaign")
    return 0


def tidy(line):
    return " ".join(str(line or "").split()).strip("\"' ")


def write_lines(prompt_file, items, model):
    """One batch through the router. ({id: line}, engine), or ({}, '') when no engine answered."""
    with tempfile.TemporaryDirectory() as d:
        i, o = pathlib.Path(d) / "in.json", pathlib.Path(d) / "out.json"
        i.write_text(json.dumps(items, ensure_ascii=False))
        env = {**os.environ, **({"CODEX_MODEL": model} if model else {})}
        r = subprocess.run([sys.executable, str(ROUTE), "--agent", "cold-email", "--draft", "--prompt", str(prompt_file),
                            "--in", str(i), "--out", str(o)], capture_output=True, text=True, env=env)
        if r.returncode != 0 or not o.exists():
            return {}, ""
        try:
            res = json.loads(o.read_text())
        except ValueError:
            return {}, ""
    engine = "codex" if "engine codex" in r.stdout else "claude" if "engine claude" in r.stdout else "engine"
    return {x.get("id"): x.get("line") for x in res if isinstance(x, dict)}, engine


def first_lines(s, a):
    slug = opt(a, "--campaign")
    c, why = campaign(s, slug)
    if not c:
        print(why); return 1
    ready = HOME / "cold" / "ready" / f"{slug}.csv"
    if not ready.exists():
        print(f"held: no ready file for {slug}. Run match first"); return 1
    rows = list(csv.DictReader(ready.open(newline="")))
    fl = s.get("first_lines", {})
    todo = [r for r in rows if not r.get("first_line")][:int(opt(a, "--limit", len(rows)))]
    rules = ((HERE / "prompts" / "first-line.md").read_text()
             + "".join(f"\n{label}: {text}" for label, text in (
                 ("What a first line says, in the owner's words", str(s.get("charter", {}).get("personalization", "")).strip()),
                 ("Who this campaign is for", str(c.get("audience", "")).strip())) if text) + "\n")
    STATE.mkdir(parents=True, exist_ok=True)
    prompt_file = STATE / "first-line-prompt.md"
    prompt_file.write_text(rules)
    counts, batch = {"rows": len(todo), "codex": 0, "claude": 0, "fallback": 0}, int(fl.get("batch", 50))
    for n in range(0, len(todo), batch):
        chunk = todo[n:n + batch]
        items = [{"id": hashlib.sha256(r["email"].encode()).hexdigest()[:12], **{k: r.get(k, "") for k in fl.get("uses", ["company"])}} for r in chunk]
        got, engine = write_lines(prompt_file, items, fl.get("model", ""))
        for r, it in zip(chunk, items):
            line = tidy(got.get(it["id"]))
            if line and engine in counts:
                r["first_line"], r["line_source"] = line, engine
            else:
                r["first_line"], r["line_source"] = fl.get("fallback", "").format_map(r), "fallback"
            counts[r["line_source"]] += 1
    if todo:
        with ready.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        ready.chmod(0o600)
    log({"run": "first-lines", "campaign": slug, **counts})
    print(f"{slug}: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + f"; {sum(1 for r in rows if r.get('first_line'))} of {len(rows)} rows have a line")
    if todo and counts["fallback"] == len(todo):
        print("flag: no engine wrote a line; every row has the fallback line. The list can still load")
    return 0


def read(s, a):
    stats = json.loads(pathlib.Path(opt(a, "--stats")).read_text())
    t, bad = s.get("targets", {}), 0
    for slug, c in s.get("campaigns", {}).items():
        if not c.get("on"):
            continue
        x = stats.get(slug)
        if x is None:
            print(f"{slug}: FLAG no stats. The sending tool's pull did not report this campaign"); bad += 1; continue
        want = round(s["daily_sends"] * float(c.get("share", 1)))
        people, sent, flags = int(x.get("contacted", 0)), int(x.get("sent", 0)), []
        if int(x.get("sent_today", 0)) < want:
            flags.append(f"under volume ({x.get('sent_today', 0)} of {want} today)")
        if sent and x.get("bounced", 0) / sent >= s.get("pause_at", {}).get("bounce_rate", 0.02):
            flags.append(f"PAUSE: bounces {x['bounced'] / sent:.1%}")
        if people:
            for name, key in (("reply_rate", "replied"), ("booking_rate", "booked")):
                if key in x and x[key] / people < t.get(name, 0):
                    flags.append(f"{name.replace('_', ' ')} {x[key] / people:.1%} against {t[name]:.0%}")
        rates = f"replies {x.get('replied', 0) / people:.1%}, booked {x.get('booked', 0) / people:.1%}" if people else "nobody contacted yet"
        print(f"{slug}: sent today {x.get('sent_today', 0)} of {want}; {people} people contacted; {rates}" + ("; FLAG " + "; ".join(flags) if flags else ""))
        bad += bool(flags)
        log({"run": "read", "campaign": slug, **{k: x.get(k, 0) for k in ("sent_today", "sent", "contacted", "replied", "booked", "bounced")}, "flags": flags})
    return 1 if bad else 0


def main(a):
    if not a or a[0] not in ("plan", "match", "first-lines", "read") or not opt(a, "--settings"):
        print(__doc__); return 2
    sp = pathlib.Path(opt(a, "--settings"))
    s = json.loads(sp.read_text())
    if int(s.get("per_inbox_a_day", 0)) < 1 or int(s.get("per_inbox_a_day", 0)) > 10 or int(s.get("daily_sends", 0)) < 1:
        print("held: the settings need daily_sends, and per_inbox_a_day between 1 and 10"); return 1
    if a[0] == "plan":
        return plan(s, a)
    if a[0] == "match":
        if not (opt(a, "--campaign") and opt(a, "--list")):
            print("match needs --campaign and --list", file=sys.stderr); return 2
        return match(s, a, sp.parent)
    if a[0] == "first-lines":
        return first_lines(s, a)
    if not opt(a, "--stats"):
        print("read needs --stats", file=sys.stderr); return 2
    return read(s, a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
