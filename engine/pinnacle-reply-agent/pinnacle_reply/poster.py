"""The auto-poster: checked drafts go out as replies in the lead's own thread, from the lane's account, and the
conversation goes on from there. Off until Justin turns it on.

Each run (a cycle step, or `reply-agent post`):
  1. Read what was said under our posts. A reply from the person who asked becomes their answer (the same path as
     `reply_answered`), so the next cycle drafts the follow-up for the same thread.
  2. Line up what can go: follow-ups to answers first, then first replies, high tier first and newest first, with
     medium filling what's left of each platform's daily cap. Low tier never goes out on its own. Only Lead Radar's
     leads, only a draft that passes the checker, only a draft no person wrote by hand.
  3. Post each one through its platform's driver (platforms/), with the bot line added when REPLY_POST_BOT_LINE sets
     one (none by default since 2026-10-31) and the whole text checked again. Each post is recorded the one way every reply is: `ops.record_mark` under the lane's account
     ("P2 (auto)"), so it shows on Lead Radar's desk, in the ledger, the vault and GHL like a reply a person posted.
  4. With REPLY_FOLLOW on, follow the person after a first reply.

Its rules (doc 20, "Guardrails on auto-replies"): one kill switch (REPLY_POST) and a list of platforms
(REPLY_POST_PLATFORMS); a daily cap per platform; one reply per thread, and never a second message to someone who
hasn't answered; first replies only to recent posts (REPLY_POST_MAX_AGE_DAYS); the checker on every post; every
send in `post_log`; a platform that says stop (rate limit, captcha, warning, 403) is stopped for the rest of the
day and reported, never retried around. Nothing goes out in a dry run.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import checks, config, ledger, ops, radar
from .platforms import Blocked, PostError, Unconfirmed, same_person
from .platforms import drivers as make_drivers

ET = ZoneInfo("America/New_York")
TIER_RANK = {"high": 0, "medium": 1}  # low tier is never posted on its own
SENT = ("reply", "follow-up")
OUT = ("posted", "unconfirmed")  # unconfirmed: sent but not seen where it should be; counted as out, never resent
READ_DAYS = 14  # answers are looked for under our posts this recent

SCHEMA = """
CREATE TABLE IF NOT EXISTS post_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, platform TEXT NOT NULL, account TEXT DEFAULT '',
  kind TEXT NOT NULL, result TEXT NOT NULL, text TEXT DEFAULT '', ref TEXT DEFAULT '', url TEXT DEFAULT '',
  detail TEXT DEFAULT '', day TEXT NOT NULL, at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS post_log_lead ON post_log (lead_id, id);
"""
# kind: reply, follow-up, follow (what we did); answer (what they said under it); stop (a platform stopped today).
# result: posted, unconfirmed, failed, blocked, seen.


def ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def today() -> str:
    return datetime.now(timezone.utc).astimezone(ET).date().isoformat()


def cap(platform: str) -> int:
    return config.POST_CAPS.get(platform, config.POST_CAP)


def _log(conn: sqlite3.Connection, lead_id: str, platform: str, kind: str, result: str, account: str = "",
         text: str = "", ref: str = "", url: str = "", detail: str = "") -> None:
    conn.execute("INSERT INTO post_log (lead_id, platform, account, kind, result, text, ref, url, detail, day, at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (lead_id, platform, account[:80], kind, result, ledger.scrub(text)[:5000], ref, url, detail[:500],
                  today(), ledger.now()))
    conn.commit()


def stopped(conn: sqlite3.Connection, day: str) -> dict[str, str]:
    return {r["platform"]: r["detail"] for r in conn.execute(
        "SELECT platform, detail FROM post_log WHERE kind='stop' AND day=? ORDER BY id", (day,))}


def sent_today(conn: sqlite3.Connection, day: str) -> Counter:
    return Counter(r["platform"] for r in conn.execute(
        f"SELECT platform FROM post_log WHERE kind IN {SENT} AND result IN {OUT} AND day=?", (day,)))


def _last_sent(conn: sqlite3.Connection, lead_id: str) -> dict[str, Any] | None:
    r = conn.execute(f"SELECT * FROM post_log WHERE lead_id=? AND kind IN {SENT} AND result IN {OUT} "
                     "ORDER BY id DESC LIMIT 1", (lead_id,)).fetchone()
    return dict(r) if r else None


def _last_answer_ref(conn: sqlite3.Connection, lead_id: str) -> str:
    r = conn.execute("SELECT ref FROM post_log WHERE lead_id=? AND kind='answer' ORDER BY id DESC LIMIT 1",
                     (lead_id,)).fetchone()
    return r["ref"] if r else ""


def _threads_replied(conn: sqlite3.Connection) -> set[str]:
    return {r["url"] for r in conn.execute(
        f"SELECT DISTINCT l.url FROM post_log p JOIN leads l ON l.id=p.lead_id "
        f"WHERE p.kind IN {SENT} AND p.result IN {OUT} AND l.url IS NOT NULL")}


def _age_days(posted_at: str | None) -> float | None:
    if not posted_at:
        return None
    try:
        t = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - (t if t.tzinfo else t.replace(tzinfo=timezone.utc))).total_seconds() / 86400


def with_bot_line(text: str) -> str:
    """The post's text with REPLY_POST_BOT_LINE at the end. Empty by default (no bot line, 2026-10-31): unchanged."""
    if not config.POST_BOT_LINE:
        return text
    return f"{text.rstrip()} {config.POST_BOT_LINE}".strip()


# --------------------------------------------------------------------------------------------------- what can go
def _what(conn: sqlite3.Connection, row: dict[str, Any], threads: set[str]) -> tuple[str, str, str]:
    """(kind, draft, "") for a lead that can be posted now, else ("", "", why not)."""
    last = _last_sent(conn, row["id"])
    if row["state"] == "answered":
        if row.get("reason") != "follow-up ready":
            return "", "", "answered: the follow-up isn't drafted yet"
        if last is None:
            return "", "", "answered, but the first reply was posted by a person: theirs to continue"
        if (row.get("answered_at") or "") <= last["at"]:
            return "", "", "no answer since our last post"
        return "follow-up", row["draft"], ""
    if last is not None or (row.get("url") and row["url"] in threads):
        return "", "", "we already replied in this thread"
    if (row.get("radar_status") or "new") == "drafted" and row.get("radar_by") not in radar.MACHINE:
        return "", "", "a person's own draft: theirs to post"
    text = row["draft"] if row.get("draft") and checks.passes(row["draft"]) else \
        row.get("radar_draft") if row.get("radar_draft") and checks.passes(row["radar_draft"]) else ""
    if not text:
        return "", "", "no draft that passes the checker"
    age = _age_days(row.get("posted_at"))
    if config.POST_MAX_AGE_DAYS > 0 and age is not None and age > config.POST_MAX_AGE_DAYS:
        return "", "", f"older than {config.POST_MAX_AGE_DAYS:g} days"
    return "reply", text, ""


def queue(conn: sqlite3.Connection, hold_follow_ups: bool = False) -> tuple[list[dict[str, Any]], Counter]:
    """(what can go, in order; why the rest can't). Follow-ups first, then high, then medium, newest first. A lead a
    funding partner has is state `partner`, so it is never here. `hold_follow_ups`: the hub's quiet list couldn't be
    read, so a follow-up to a lead already in GHL waits (it may have been handed off)."""
    ensure(conn)
    threads, out, why_not = _threads_replied(conn), [], Counter()
    for row in [dict(r) for r in conn.execute(
            "SELECT * FROM leads WHERE source='lead-radar' AND state IN ('waiting', 'answered')")]:
        tier = (row.get("tier") or "low").lower()
        if tier not in TIER_RANK:
            why_not["low tier: never posted on its own"] += 1
            continue
        kind, text, why = _what(conn, row, threads)
        if not kind:
            why_not[why] += 1
            continue
        if hold_follow_ups and kind == "follow-up" and row.get("ghl_contact_id"):
            why_not["the hub's quiet list couldn't be read: follow-ups wait"] += 1
            continue
        out.append({"row": row, "kind": kind, "text": text, "tier": tier,
                    "platform": (row.get("platform") or "unknown").lower()})
    out.sort(key=lambda c: c["row"].get("posted_at") or "", reverse=True)
    out.sort(key=lambda c: (c["kind"] != "follow-up", TIER_RANK[c["tier"]]))
    return out, why_not


# --------------------------------------------------------------------------------------------------- the answers
def _z(at: str) -> str:
    """A ledger time as the platforms write theirs: 2026-10-29T21:22:07Z."""
    t = datetime.fromisoformat(at)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_answers(conn: sqlite3.Connection, drivers: dict[str, Any], stops: dict[str, str]) -> dict[str, Any]:
    """What the people we replied to said back. Their reply under ours becomes the lead's answer."""
    ensure(conn)
    since = (datetime.now(timezone.utc) - timedelta(days=READ_DAYS)).isoformat()
    found, errors = 0, []
    posts = [dict(r) for r in conn.execute(
        f"SELECT p.*, l.author FROM post_log p JOIN leads l ON l.id=p.lead_id "
        f"WHERE p.kind IN {SENT} AND p.result='posted' AND p.at >= ? ORDER BY p.id", (since,))]
    for post in posts:
        drv, p = drivers.get(post["platform"]), post["platform"]
        if drv is None or p in stops or not drv.ready()[0]:
            continue
        try:
            got = drv.replies(post["ref"], _z(post["at"]))
        except Blocked as exc:
            stops[p] = str(exc)
            _log(conn, post["lead_id"], p, "stop", "blocked", drv.account, detail=str(exc))
            continue
        except PostError as exc:
            errors.append(f"{post['lead_id']}: reading {p} replies failed: {exc}"[:300])
            continue
        seen = {r["ref"] for r in conn.execute("SELECT ref FROM post_log WHERE lead_id=? AND kind='answer'",
                                               (post["lead_id"],))}
        known = {r["detail"] for r in conn.execute("SELECT detail FROM post_log WHERE lead_id=? AND kind='answer'",
                                                   (post["lead_id"],))}
        for g in sorted(got, key=lambda x: str(x.get("at") or "")):
            if not g.get("id") or g["id"] in seen or not (g.get("text") or "").strip():
                continue
            author = post.get("author") or ""
            author = "" if author.startswith("pfbid") else author  # a post token, not the person: unknown asker
            theirs = same_person(author, g.get("author")) or (g.get("author_id") and g["author_id"] in known) \
                or (not author and not known)  # an unknown asker: the first person to answer us is them
            if not theirs:
                continue
            ledger.take_contact(conn, post["lead_id"], g["text"])  # before anything is scrubbed
            _log(conn, post["lead_id"], p, "answer", "seen", text=g["text"], ref=g["id"],
                 detail=g.get("author_id") or g.get("author") or "")
            ledger.record(conn, post["lead_id"], local_state="answered", answer=ledger.scrub(g["text"])[:2000],
                          answered_at=ledger.now(), **({} if author else {"author": (g.get("author") or "")[:80]}))
            seen.add(g["id"])
            found += 1
    return {"answers": found, "errors": errors}


# --------------------------------------------------------------------------------------------------- posting
def _label(row: dict[str, Any]) -> str:
    """Who the post is recorded under: the lane's account, never the agent (`save_replied` refuses that)."""
    return f"{row.get('persona') or 'lane'} (auto)"


def _post_one(conn: sqlite3.Connection, c: dict[str, Any], drv: Any, desk_item, out: dict[str, Any],
              fresh=None) -> bool:
    row, p, text = c["row"], c["platform"], with_bot_line(c["text"])
    bad = checks.violations(text, checks.FOLLOW_UP if c["kind"] == "follow-up" else checks.FIRST)
    if bad:
        out["not_posted"][f"with the bot line it breaks: {', '.join(bad)}"] += 1
        return False
    if c["kind"] == "reply" and fresh is not None:  # the desk, read again just now: a person's work wins
        item = fresh(row)
        if item is not None and not radar.writable(item)[0]:
            out["not_posted"][f"a person took it on the desk just now ({radar.writable(item)[1]})"] += 1
            return False
    parent = _last_answer_ref(conn, row["id"]) if c["kind"] == "follow-up" else ""
    try:
        posted = drv.reply(row, text, parent)
    except Blocked as exc:
        out["stopped"][p] = str(exc)
        _log(conn, row["id"], p, "stop", "blocked", drv.account, detail=str(exc))
        return False
    except Unconfirmed as exc:  # it may be out: never sent again, and the platform stops so a person can look
        _log(conn, row["id"], p, c["kind"], "unconfirmed", drv.account, text, url=row.get("url") or "",
             detail=str(exc))
        _log(conn, row["id"], p, "stop", "blocked", drv.account, detail=str(exc))
        out["stopped"][p] = str(exc)
        out["errors"].append(f"{row['id']} on {p}: {exc}"[:300])
        return False
    except PostError as exc:
        _log(conn, row["id"], p, c["kind"], "failed", drv.account, text, detail=str(exc))
        out["errors"].append(f"{row['id']} on {p}: {exc}"[:300])
        return False
    _log(conn, row["id"], p, c["kind"], "posted", drv.account, text, posted.ref, posted.url)
    note = f"auto-posted on {p} as {drv.account}"
    try:
        ops.record_mark(conn, row, desk_item(row["id"]), _label(row), note=note, dry_run=False, text=text,
                        url=posted.url)
    except radar.RadarError as exc:  # it went out: the ledger must say so even when the desk can't be told
        ops.record_mark(conn, row, None, _label(row), note=note, dry_run=True, text=text, url=posted.url)
        out["errors"].append(f"{row['id']}: posted, but the desk mark failed: {exc}"[:300])
    out["posted"].append({"lead": row["id"], "platform": p, "tier": c["tier"], "kind": c["kind"], "url": posted.url})
    if config.FOLLOW and c["kind"] == "reply":
        try:
            who = drv.follow(row)
            if who:
                _log(conn, row["id"], p, "follow", "posted", drv.account, ref=who)
                out["followed"].append({"lead": row["id"], "platform": p, "who": who})
        except Blocked as exc:
            out["stopped"][p] = str(exc)
            _log(conn, row["id"], p, "stop", "blocked", drv.account, detail=str(exc))
        except PostError as exc:
            _log(conn, row["id"], p, "follow", "failed", drv.account, detail=str(exc))
    return True


def run(conn: sqlite3.Connection, dry_run: bool = False, limit: int | None = None,
        by_id: dict[str, dict[str, Any]] | None = None, drivers: dict[str, Any] | None = None,
        hold_follow_ups: bool = False) -> dict[str, Any]:
    """One posting run. Posts only with REPLY_POST on, outside a dry run, on the platforms REPLY_POST_PLATFORMS
    names, within each platform's cap. `limit` caps the posts (1 for a canary). Never raises."""
    ensure(conn)
    day, drivers = today(), make_drivers() if drivers is None else drivers
    stops = stopped(conn, day)
    out: dict[str, Any] = {"on": config.POST, "dry_run": dry_run, "platforms": sorted(config.POST_PLATFORMS),
                           "day": day, "posted": [], "followed": [], "would_post": [], "queued": {},
                           "platform_off": Counter(), "waiting_on_account": {}, "capped": Counter(),
                           "stopped": stops, "not_posted": Counter(), "errors": []}
    try:
        out.update(read_answers(conn, drivers, stops))
        cands, why_not = queue(conn, hold_follow_ups)
    except (radar.RadarError, sqlite3.Error, KeyError, ValueError) as exc:
        out["errors"].append(f"posting run failed: {exc}"[:300])
        return _plain(out)
    out["not_posted"].update(why_not)
    sent, posts, threads = sent_today(conn, day), 0, set()
    cache: dict[str, dict[str, Any]] = dict(by_id or {})

    def desk_item(lead_id: str) -> dict[str, Any] | None:
        if lead_id not in cache:  # outside a cycle: one read of the desk for the whole run
            cache.update({i["id"]: i for i in radar.queue_all(status="all").get("items") or []})
        return cache.get(lead_id)

    def fresh(row: dict[str, Any]) -> dict[str, Any] | None:
        """The lead's desk item read again right before posting (its campaign only); None when it can't be read."""
        try:
            items = radar.queue_all(status="all", campaign=row.get("campaign") or "", since="").get("items") or []
        except radar.RadarError:
            return None
        cache.update({i["id"]: i for i in items})
        return next((i for i in items if i["id"] == row["id"]), None)

    for c in cands:
        p, drv = c["platform"], drivers.get(c["platform"])
        out["queued"].setdefault(p, Counter())[c["tier"]] += 1
        ok, why = drv.ready() if drv is not None else (False, f"no driver for {p}")
        if not ok:
            out["waiting_on_account"].setdefault(p, {"why": why, "leads": 0})["leads"] += 1
            continue
        if p not in config.POST_PLATFORMS:
            out["platform_off"][p] += 1
            continue
        if p in out["stopped"]:
            continue
        url = c["row"].get("url") or c["row"]["id"]
        if c["kind"] == "reply" and url in threads:
            out["not_posted"]["we already replied in this thread"] += 1
            continue
        if sent[p] >= cap(p) or (limit is not None and posts >= limit):
            out["capped"][p] += 1
            continue
        if not config.POST or dry_run:
            out["would_post"].append({"lead": c["row"]["id"], "platform": p, "tier": c["tier"], "kind": c["kind"]})
            sent[p] += 1
            threads.add(url)
            continue
        if _post_one(conn, c, drv, desk_item, out, fresh):
            sent[p] += 1
            posts += 1
            threads.add(url)
    if not config.POST:
        out["why"] = "REPLY_POST is off: nothing was posted (would_post is what would go)"
    return _plain(out)


def _plain(out: dict[str, Any]) -> dict[str, Any]:
    return {k: ({kk: dict(vv) if isinstance(vv, Counter) else vv for kk, vv in v.items()} if isinstance(v, dict) else v)
            for k, v in out.items()}


def run_now(dry_run: bool = True, limit: int | None = None) -> dict[str, Any]:
    with ledger.connect() as conn:
        from . import hub  # the quiet list: a funding partner's lead is never posted to
        return run(conn, dry_run, limit, hold_follow_ups=hub.partner_check(conn)["unknown"])


def status(drivers: dict[str, Any] | None = None) -> dict[str, Any]:
    """The switches, each platform's account and today's count against its cap, the queue, the last posts."""
    drivers = make_drivers() if drivers is None else drivers
    with ledger.connect() as conn:
        ensure(conn)
        day = today()
        stops, sent = stopped(conn, day), sent_today(conn, day)
        cands, why_not = queue(conn)
        line: dict[str, Counter] = {}
        for c in cands:
            line.setdefault(c["platform"], Counter())[c["tier"]] += 1
        accounts = {}
        for p, drv in sorted(drivers.items()):
            ok, why = drv.ready()
            accounts[p] = {"ready": ok, "why": why, "account": drv.account if ok else "", "on": p in config.POST_PLATFORMS,
                           "cap": cap(p), "posted_today": sent[p], "stopped_today": stops.get(p, "")}
        last = [dict(r) for r in conn.execute(
            "SELECT lead_id, platform, account, kind, result, url, detail, at FROM post_log "
            "WHERE kind != 'stop' ORDER BY id DESC LIMIT 10")]
        return {"on": config.POST, "platforms": sorted(config.POST_PLATFORMS), "follow": config.FOLLOW,
                "max_age_days": config.POST_MAX_AGE_DAYS, "bot_line": config.POST_BOT_LINE, "day": day,
                "accounts": accounts, "queue": {p: dict(c) for p, c in line.items()}, "not_posted": dict(why_not),
                "last": last}
