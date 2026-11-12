"""Every loop closed, every day. One check that runs each job, lists what's still open, and says what it did about each.

"Closed" here means nothing sits without an owner. A loop the agent can finish, it finishes. One it can't, it hands to a named person with a task, and it
says so in the day's report. Sends stay behind their own switches, so a dry run and an applied run differ only in what they write.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import collections_agent, handoffs, instantly, leads, sales, social
from .errors import FcmError
from .hubapi import Hub, HubError

BLOCKER = "replies not posted"


def _safe(step: Any, default: Any) -> tuple[Any, str]:
    try:
        return step(), ""
    except (FcmError, HubError, KeyError, OSError) as exc:
        return default, str(exc)[:200]


def daily(engine: Any, apply: bool = False, hub: Hub | None = None, now: datetime | None = None) -> dict[str, Any]:
    """The whole day, in order. One failing step never stops the rest, and a failure is a loop too."""
    hub = hub or Hub()
    now = now or datetime.now(timezone.utc)
    loops: list[dict[str, Any]] = []
    failures: list[str] = []

    def step(name: str, fn: Any, default: Any) -> Any:
        got, error = _safe(fn, default)
        if error:
            failures.append(f"{name}: {error}")
        return got

    replies = step("reply triage", lambda: sales.triage_inbox(engine, apply=apply, now=now), {})
    synced = step("opt-out sync", lambda: sales.sync_suppressions(engine) if instantly.configured() else {"state": "held", "waiting": 0}, {})
    cards = step("lead sweep", lambda: leads.sync(engine, apply=apply, hub=hub, now=now), {})
    proposed = step("proposals", lambda: handoffs.propose_qualified(engine, apply=apply, hub=hub), {})
    clock = step("handoff watch", lambda: handoffs.watch(engine, apply=apply, hub=hub, now=now), {})
    money = step("collections", lambda: collections_agent.run(engine, apply=apply, hub=hub, now=now), {})
    posting = step("posting queue", hub.posting_queue, {})
    row = step("dashboard", hub.dashboard, {})
    hub_side = step("hub loops", hub.loops, {}).get("open") or []

    waiting = row.get("replies_waiting")
    if waiting:
        people = posting.get("people_named", 0)
        card = posting.get("scorecard") or {}
        did = f"queued {posting.get('assigned', 0)} for today, {posting.get('left_for_tomorrow', 0)} left" + \
              (f", {card.get('posted_today', 0)} posted today" if card else "") + \
              (f", {people} people posting" if people else ". No person is named: Justin's first step on the go-live list")
        loops.append({"loop": BLOCKER, "count": waiting, "did": did, "owner": "posters" if people else "Justin"})
    if cards.get("due"):
        loops.append({"loop": "leads with no fresh card", "count": cards["due"] - cards.get("worked", 0),
                      "did": f"carded {cards.get('worked', 0)} this pass", "owner": "agent"})
    held = sales.book(engine).drafts("held")
    stale = [d for d in held if d["at"] < (now - timedelta(days=1)).isoformat()]
    if held:
        loops.append({"loop": "reply drafts waiting for a person", "count": len(held), "oldest_days": 1 if stale else 0,
                      "did": f"{len(stale)} older than a day" if stale else "all from today", "owner": "person who sends drafts"})
    if synced.get("waiting"):
        loops.append({"loop": "opt-outs not at the sender", "count": synced["waiting"], "did": "held by FCM_SYNC_OPT_OUTS. Turn it on", "owner": "Justin"})
    if clock.get("held"):
        loops.append({"loop": "messages held by the send switch", "count": len(clock["held"]), "did": "listed for Justin", "owner": "Justin"})
    if clock.get("failed"):
        failures += [f"handoff {f.get('handoff')}: {f.get('error')}" for f in clock["failed"]]
    drafts_held = collections_agent.drafts(engine)
    if money.get("drafted") or drafts_held:
        loops.append({"loop": "collection drafts waiting", "count": len(drafts_held) + (money.get("drafted", 0) if not apply else 0),
                      "did": f"{money.get('partners_late', 0)} partners late", "owner": "Justin"})
    for item in hub_side:
        if item.get("count"):
            loops.append({**item, "did": _hub_action(item["loop"], clock, money), "owner": _hub_owner(item["loop"])})
    queue = social.queue(engine).counts()
    if queue:
        loops.append({"loop": "social queue waiting", "count": sum(queue.values()), "did": "listed by platform", "owner": "person with OutFlo"})
    for failure in failures:
        loops.append({"loop": "a job failed", "count": 1, "did": failure, "owner": "Justin"})
    report = {"day": now.date().isoformat(), "apply": apply, "open": len(loops), "loops": loops,
              "ran": {"replies": replies.get("read", 0), "cards": cards.get("worked", 0), "proposed": proposed.get("proposed", 0),
                      "nudges": len(clock.get("ran") or []), "collections": money.get("drafted", 0)},
              "row": {k: v for k, v in row.items() if k != "close_rates"}, "scorecard": posting.get("scorecard") or {}}
    if apply:
        _safe(lambda: hub.save_loops(report), {})
        engine.daily_note(f"Loop check {report['day']}", "\n".join(f"- {x['loop']}: {x.get('count', '')}. {x['did']}. Owner: {x['owner']}" for x in loops) or "- Nothing open.")
        if report["scorecard"]:
            engine.daily_note(f"Posting scorecard {report['day']}", scorecard_page(report["scorecard"]))
    return report


def scorecard_page(card: dict[str, Any]) -> str:
    """The posters' day on one page, from the hub's own marks: who posted what, against their ceiling, and what needs a person."""
    people = card.get("people") or []
    lines = [f"# Posting scorecard, {card.get('day', '')}", "",
             "| Poster | Posted | Skipped | Ceiling | By platform | Still on their list |", "|---|---|---|---|---|---|"]
    for p in people:
        who = f"{p['name']} ({p['id']})" if p.get("name") else f"{p['id']} (no person yet)"
        platforms = ", ".join(f"{k} {v}" for k, v in sorted((p.get("by_platform") or {}).items())) or "none"
        lines.append(f"| {who} | {p.get('posted', 0)} | {p.get('skipped', 0)} | {p.get('ceiling', 0)} | {platforms} | {p.get('still_queued', 0)} |")
    lines += ["", f"Posted today: {card.get('posted_today', 0)}, of which {card.get('posted_by_others', 0)} by someone without a poster link. "
                  f"New asks today: {card.get('new_asks_today', 0)}. Waiting: {card.get('waiting', 0)}. Left for tomorrow: {card.get('left_for_tomorrow', 0)}.", ""]
    flags = []
    if not any(p.get("name") for p in people):
        flags.append("No poster is named. Lane 1 on the go-live list is Justin's.")
    for p in people:
        if p.get("name") and p.get("status") == "active" and p.get("still_queued") and p.get("posted", 0) < p.get("ceiling", 0) / 2:
            flags.append(f"{p['name']} posted {p.get('posted', 0)} of {p.get('ceiling', 0)} with {p['still_queued']} still on their list: ask why.")
        if p.get("posted") and p.get("skipped", 0) > p["posted"]:
            flags.append(f"{p.get('name') or p['id']} skipped more than they posted: read the skip notes.")
    if card.get("skip_platforms"):
        flags.append(f"Not queued for posters: {', '.join(card['skip_platforms'])}. Someone else answers these.")
    lines += ["What needs a person:", *(f"- {f}" for f in flags)] if flags else ["Nothing needs a person."]
    return "\n".join(lines)


def _hub_action(loop: str, clock: dict[str, Any], money: dict[str, Any]) -> str:
    if loop.startswith("handoff stale"):
        steps = len(clock.get("ran") or []) + len(clock.get("due") or [])
        return f"ran the 7-day clock: {steps} steps" if clock.get("ran") else f"the 7-day clock has {steps} steps due"
    if loop == "money overdue":
        return f"drafted {money.get('drafted', 0)} collection messages"
    if loop.startswith("commission with no amount"):
        return "a person enters the partner's fee on the hub"
    if loop.startswith("lead no partner"):
        return "listed on the Handoffs page"
    if loop == "payment needs a person":
        return "money arrived that matched no charge: a person matches it, then resolves it on the hub"
    return "waiting on the Handoffs page"


def _hub_owner(loop: str) -> str:
    return "agent" if loop.startswith("handoff stale") else "Justin"
