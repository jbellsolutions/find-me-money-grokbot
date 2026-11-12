"""The browser lane on Justin's Mac: the Reply Agent's Facebook replies, posted from a Chrome window signed in as
his own account (platforms/facebook.py). The Reply Agent itself runs on the Orgo computer and can't reach this
window, so the lane works from what both can reach, Lead Radar's desk:

  1. Read the desk's Facebook leads into this Mac's own ledger (/workspace/find-me-money/pinnacle-reply).
  2. Post through the same poster as every platform (poster.py): checked drafts the agent wrote, high tier first,
     the bot line, the daily cap, one reply per thread, the desk read again just before each post, a block stops
     Facebook for the day. Each post is marked replied on the desk under the lane's account, so the Orgo cycle
     records it, puts it in GHL and the vault, and never queues it again.
  3. Read what people said under our comments into this ledger. Until those answers reach the Orgo agent (not built
     yet), every `status` and `run` lists the ones nobody has followed up: a person answers them by hand.

    reply-agent-mac open                      # the Facebook window, for Justin to sign in and join groups
    reply-agent-mac status                    # window, account, switches, queue, today's posts
    reply-agent-mac check [--limit N]         # open the next posts and say what a reply would meet; types nothing
    reply-agent-mac groups [--check [--limit N]]  # the groups the leads are in; --check opens the top N (25)
    reply-agent-mac run [--dry-run] [--limit N] [--any-hour]

Its switches are in /workspace/find-me-money/pinnacle-reply/reply.env, apart from the Orgo computer's: REPLY_POST (the kill switch),
REPLY_POST_PLATFORMS=facebook, REPLY_POST_CAP_FACEBOOK, REPLY_POST_PER_RUN, REPLY_POST_HOURS, REPLY_POST_MAX_AGE_DAYS,
REPLY_FOLLOW, and REPLY_WRITE (the desk marks). The launchd job runs `run` every hour; outside the hours it does
nothing, and with REPLY_POST off it never opens the window.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("REPLY_HOME", str(Path.home() / ".pinnacle-reply-mac"))
os.environ.setdefault("REPLY_VAULT", "off")  # the vault is the Orgo agent's; this lane keeps only its ledger
os.environ["REPLY_FACEBOOK_BROWSER"] = "on"

from . import config, ledger, poster, radar  # noqa: E402  (after the settings above)
from .platforms import Blocked, PostError  # noqa: E402
from .platforms.facebook import JOIN, Facebook, group  # noqa: E402

LANE = ("facebook",)


def _shots() -> Path:
    path = config.STATE_DIR / "shots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def in_hours(now: datetime | None = None) -> bool:
    hour = (now or datetime.now(timezone.utc)).astimezone(poster.ET).hour
    start, end = config.POST_HOURS
    return start <= hour < end


def pull(conn) -> dict[str, dict[str, Any]]:
    """The desk's leads on this lane's platforms, into this Mac's ledger. Returns them by id."""
    got = radar.queue_all(status="all")
    items = [i for i in got.get("items") or [] if (i.get("platform") or "").lower() in LANE]
    ledger.sync(conn, items)
    return {i["id"]: i for i in items}


def answers_waiting(conn) -> list[dict[str, Any]]:
    """What people wrote back under our comments that no follow-up has gone out for: a person answers these."""
    poster.ensure(conn)
    return [dict(r) for r in conn.execute(
        f"SELECT p.lead_id AS lead, p.platform, l.url, p.text, p.at FROM post_log p JOIN leads l ON l.id = p.lead_id "
        f"WHERE p.kind = 'answer' AND NOT EXISTS (SELECT 1 FROM post_log q WHERE q.lead_id = p.lead_id "
        f"AND q.kind = 'follow-up' AND q.result IN {poster.OUT} AND q.id > p.id) ORDER BY p.id")]


def run(dry_run: bool = False, limit: int | None = None, any_hour: bool = False, fb: Facebook | None = None) -> dict:
    if not dry_run and not config.POST:
        return {"ran": False, "why": "REPLY_POST is off on this Mac (/workspace/find-me-money/pinnacle-reply/reply.env)"}
    if not dry_run and not any_hour and not in_hours():
        return {"ran": False, "why": f"outside posting hours {config.POST_HOURS[0]}-{config.POST_HOURS[1]} ET"}
    fb = fb or Facebook.from_config()
    try:
        with ledger.connect() as conn:
            by_id = pull(conn)
            out = poster.run(conn, dry_run, limit if limit is not None else config.POST_PER_RUN, by_id=by_id,
                             drivers={"facebook": fb})
            waiting = answers_waiting(conn)
    finally:
        fb.close()
    return {"ran": True, **out, "answers_waiting": waiting}


def status(fb: Facebook | None = None) -> dict[str, Any]:
    fb = fb or Facebook.from_config()
    fb.launch_ok = False  # status only looks; it never opens the window
    with ledger.connect() as conn:
        pull(conn)
        waiting = answers_waiting(conn)
    try:
        st = poster.status(drivers={"facebook": fb})
    finally:
        fb.close()
    st.update(lane=list(LANE), hours=f"{config.POST_HOURS[0]}-{config.POST_HOURS[1]} ET", in_hours=in_hours(),
              per_run=config.POST_PER_RUN, desk_writes=config.WRITE, profile=str(config.FACEBOOK_PROFILE_DIR),
              ledger=str(config.LEDGER_DB), answers_waiting=waiting)
    return st


def open_window() -> dict[str, Any]:
    fb = Facebook.from_config()
    started = fb.open_window()
    ok, why = fb.ready()
    fb.close()
    return {"window": "started" if started else "already open", "signed_in": ok, "account": fb.account, "why": why,
            "next": "" if ok else "Sign in to Facebook in that window yourself, then run: reply-agent-mac status"}


def check(limit: int = 5, fb: Facebook | None = None) -> dict[str, Any]:
    """The next posts in line, opened one by one: what a reply would meet there, with a screenshot. Types nothing."""
    fb = fb or Facebook.from_config()
    out: dict[str, Any] = {"checked": [], "states": Counter()}
    try:
        with ledger.connect() as conn:
            pull(conn)
            cands, why_not = poster.queue(conn)
        out["not_in_line"] = dict(why_not)
        ok, why = fb.ready()
        if not ok:
            return {**out, "states": {}, "why": why}
        for c in [c for c in cands if c["platform"] in LANE][:limit]:
            row = c["row"]
            try:
                seen = fb.inspect(row["url"], keep=True)
            except Blocked as exc:
                out["stopped"] = str(exc)
                break
            except PostError as exc:
                seen = {"state": "error", "detail": str(exc), "group": group(row["url"])}
            page = seen.pop("page", None)
            if page is not None:
                shot = _shots() / f"{row['id'][:12]}.png"
                page.screenshot(path=str(shot))
                page.close()
                seen["shot"] = str(shot)
            out["states"][seen["state"]] += 1
            out["checked"].append({"lead": row["id"], "tier": c["tier"], "kind": c["kind"], "url": row["url"], **seen})
    finally:
        fb.close()
    out["states"] = dict(out["states"])
    return out


def groups(check_membership: bool = False, fb: Facebook | None = None, limit: int = 25) -> dict[str, Any]:
    """The groups the queue's Facebook posts are in, most high-intent leads first. With check_membership, the top
    `limit` groups' pages are opened to see whether the account is in each (it never clicks Join)."""
    with ledger.connect() as conn:
        pull(conn)
        rows = [dict(r) for r in conn.execute(
            "SELECT url, tier FROM leads WHERE lower(platform)='facebook' AND state IN ('waiting', 'answered')")]
    count: dict[str, Counter] = {}
    for r in rows:
        count.setdefault(group(r["url"]), Counter())[(r["tier"] or "low").lower()] += 1
    out = [{"group": g, "url": f"https://www.facebook.com/groups/{g}/", "high": c["high"], "medium": c["medium"],
            "low": c["low"]} for g, c in count.items() if g]
    out.sort(key=lambda x: (-x["high"], -x["medium"], -x["low"]))
    if check_membership:
        fb = fb or Facebook.from_config()
        try:
            ok, why = fb.ready()
            if not ok:
                return {"groups": out, "why": why}
            for g in [g for g in out if g["high"] or g["medium"]][:limit]:
                try:
                    g["member"] = member(fb, g["url"])
                except Blocked as exc:
                    return {"groups": out, "stopped": str(exc)}
        finally:
            fb.close()
    return {"groups": out, "total": len(out)}


def member(fb: Facebook, url: str) -> str:
    """yes, no, pending or unknown, from the group's own page."""
    import re
    page = fb._page(url)
    try:
        fb._stop_check(page)
        if page.get_by_role("button", name=re.compile(r"^(cancel request|pending)", re.I)).count():
            return "pending"
        if page.get_by_role("button", name=JOIN).count():
            return "no"
        if page.get_by_role("button", name=re.compile(r"^joined", re.I)).count() or \
                page.get_by_role("button", name=re.compile(r"^write something", re.I)).count():
            return "yes"
        return "unknown"
    finally:
        page.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reply-agent-mac", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open")
    sub.add_parser("status")
    ch = sub.add_parser("check")
    ch.add_argument("--limit", type=int, default=5)
    gr = sub.add_parser("groups")
    gr.add_argument("--check", action="store_true", help="open each group's page to see if the account is in it")
    gr.add_argument("--limit", type=int, default=25, help="how many groups --check opens, top first")
    ru = sub.add_parser("run")
    ru.add_argument("--dry-run", action="store_true", help="say what would go; post nothing")
    ru.add_argument("--limit", type=int, default=None, help="posts at most (default REPLY_POST_PER_RUN)")
    ru.add_argument("--any-hour", action="store_true", help="ignore the posting hours")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "open":
            out = open_window()
        elif a.cmd == "status":
            out = status()
        elif a.cmd == "check":
            out = check(a.limit)
        elif a.cmd == "groups":
            out = groups(a.check, limit=a.limit)
        else:
            out = run(a.dry_run, a.limit, a.any_hour)
    except (radar.RadarError, PostError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    out["at"] = ledger.now()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
