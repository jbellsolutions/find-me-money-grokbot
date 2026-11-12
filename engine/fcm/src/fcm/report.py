"""The daily program report: what went out, who replied to what, who came back, deals, follow-ups, compliance.

    fcm daily-report [--day YYYY-MM-DD] [--publish]

Built only from what the agent itself recorded, so every number can be traced:
- **messages out** = outbox rows that reached state `sent` that day. A message marked `simulated` (demo mode, a
  partner without the test tag) is counted apart and never as sent;
- **replies** = triaged inbound replies (`reply.record` in the audit log). STOP, HELP and wrong numbers are compliance,
  not replies;
- **reactivated** = a reply that moved a quiet, dormant or dead partner to `aff:reactivated`;
- **deals** = deals recorded (`deal.record`), plus partners who said they have one (`has_deal`). A deal submitted in
- **follow-ups** = replies in the last 7 days that need a person, with no message from us since.

`--publish` writes it to the Obsidian daily note (one task per day, updated
on rerun). The routine posts `slack_text` in the program's channel.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

NEEDS_PERSON = {"has_deal": "has a deal: call today", "book_call": "wants a call", "question": "asked a question",
                "commission_question": "asked about commission", "identity_question": "asked who they're texting with: "
                "reply personally", "wants_service": "wants help", "will_send_deals": "plans to send deals: ask for "
                "the first one", "help": "texted HELP", "wrong_number": "wrong number: fix it"}
LIKELY_DEAL = {"has_deal", "will_send_deals", "book_call"}
COMPLIANCE = {"unsubscribe": "opted out (DND set)", "help": "texted HELP", "wrong_number": "wrong number",
              "identity_question": "asked if it's a real person"}
NON_REPLY = {"unsubscribe", "help", "wrong_number"}


def _window(engine: Any, day: date) -> tuple[str, str]:
    start = datetime.combine(day, time(0), tzinfo=engine.tz).astimezone(UTC).replace(tzinfo=None)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _audit(engine: Any, actions: tuple[str, ...], since: str, until: str) -> list[dict[str, Any]]:
    with engine.store.connection() as c:
        rows = c.execute(f"SELECT * FROM audit WHERE action IN ({','.join('?' * len(actions))}) AND "
                         "substr(at, 1, 19) >= ? AND substr(at, 1, 19) < ? ORDER BY id",
                         (*actions, since[:19], until[:19])).fetchall()
    return [{**dict(r), "details": json.loads(r["details_json"] or "{}")} for r in rows]


def _sent(engine: Any, since: str, until: str) -> list[dict[str, Any]]:
    with engine.store.connection() as c:
        rows = c.execute("SELECT * FROM outbox WHERE state = 'sent' AND substr(updated_at, 1, 19) >= ? AND "
                         "substr(updated_at, 1, 19) < ? ORDER BY updated_at", (since[:19], until[:19])).fetchall()
    payloads: dict[str, list[dict[str, Any]]] = {}
    out = []
    for r in rows:
        if r["action_id"] not in payloads:
            action = engine.store.get_action(r["action_id"]) or {}
            payloads[r["action_id"]] = json.loads(action.get("payload_json") or "{}").get("messages", [])
        msgs = payloads[r["action_id"]]
        m = msgs[r["n"] - 1] if 0 < r["n"] <= len(msgs) else {}
        out.append({**dict(r), "delivery": m.get("delivery", "real"), "body": m.get("body", "")})
    return out


def _last_outbound(engine: Any, contact_id: str, before: str) -> dict[str, Any] | None:
    with engine.store.connection() as c:
        r = c.execute("SELECT * FROM outbox WHERE contact_id = ? AND state = 'sent' AND substr(updated_at, 1, 19) <= ? "
                      "ORDER BY updated_at DESC LIMIT 1", (contact_id, before[:19])).fetchone()
    if not r:
        return None
    action = engine.store.get_action(r["action_id"]) or {}
    msgs = json.loads(action.get("payload_json") or "{}").get("messages", [])
    m = msgs[r["n"] - 1] if 0 < r["n"] <= len(msgs) else {}
    return {"kind": r["kind"], "channel": r["channel"], "at": r["updated_at"], "body": m.get("body", "")}


def _name(engine: Any, contact_id: str, cache: dict[str, str]) -> str:
    if contact_id not in cache:
        try:
            cache[contact_id] = engine.affiliate(contact_id).name
        except Exception:  # noqa: BLE001 - a deleted or unreachable card still gets a line
            cache[contact_id] = contact_id
    return cache[contact_id]


def daily_report(engine: Any, day: date | None = None) -> dict[str, Any]:
    day = day or engine.today()
    since, until = _window(engine, day)
    names: dict[str, str] = {}
    sent = _sent(engine, since, until)
    real = [s for s in sent if s["delivery"] != "simulated"]
    by_channel: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for s in real:
        by_channel[s["channel"]] = by_channel.get(s["channel"], 0) + 1
        by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + 1

    triaged = _audit(engine, ("reply.record",), since, until)
    replies, compliance, reactivated = [], [], []
    for a in triaged:
        cid, intent = a["resource"], a["details"].get("intent", "")
        taken = a["details"].get("taken", [])
        prior = _last_outbound(engine, cid, a["at"])
        row = {"contact_id": cid, "name": _name(engine, cid, names), "intent": intent, "at": a["at"],
               "replied_to": (f"{prior['kind']} {prior['channel']}: {prior['body'][:90]}" if prior else "")}
        if intent in COMPLIANCE:
            compliance.append({**row, "what": COMPLIANCE[intent]})
        if intent not in NON_REPLY:
            replies.append(row)
        if any("aff:reactivated" in t for t in taken):
            reactivated.append(row)

    deals = [{"contact_id": a["resource"], "name": _name(engine, a["resource"], names),
              "note": a["details"].get("note", "")} for a in _audit(engine, ("deal.record",), since, until)]

    week_since, _ = _window(engine, day - timedelta(days=6))
    recent = _audit(engine, ("reply.record",), week_since, until)
    followups: dict[str, dict[str, Any]] = {}
    likely: dict[str, dict[str, Any]] = {}
    for a in recent:
        cid, intent = a["resource"], a["details"].get("intent", "")
        answered = _last_outbound(engine, cid, until)
        handled = bool(answered and answered["at"][:19] > a["at"][:19])
        if intent in NEEDS_PERSON and not handled:
            followups[cid] = {"contact_id": cid, "name": _name(engine, cid, names), "why": NEEDS_PERSON[intent],
                              "since": a["at"][:10]}
        if intent in LIKELY_DEAL:
            likely[cid] = {"contact_id": cid, "name": _name(engine, cid, names), "signal": NEEDS_PERSON[intent],
                           "since": a["at"][:10]}

    program: dict[str, Any] = {}
    try:
        sc = engine.scorecard()
        program = {"partners": sc["affiliates"], "reactivated_total": sc["cohorts"].get("aff:reactivated", 0),
                   "producing": sc["cohorts"].get("aff:producing", 0), "dnc_total": sc["dnc"],
                   "reply_rate_30d": sc["reply_rate_30d"], "cohorts": sc["cohorts"]}
    except Exception as exc:  # noqa: BLE001 - the day's activity is still worth reporting if GHL is slow
        program = {"error": f"program totals unavailable: {exc}"[:200]}
    with engine.store.connection() as c:
        ever = c.execute("SELECT COUNT(*) FROM outbox WHERE state = 'sent'").fetchone()[0]

    report = {
        "date": day.isoformat(),
        "demo_mode": bool(getattr(engine.settings, "demo_mode", False)),
        "sent": {"real": len(real), "simulated": len(sent) - len(real), "by_channel": by_channel, "by_kind": by_kind,
                 "partners_reached": len({s["contact_id"] for s in real}), "all_time_rows_sent": ever},
        "replies": replies, "reactivated": reactivated, "deals_recorded": deals,
        "likely_deals": sorted(likely.values(), key=lambda r: r["since"]),
        "follow_ups": sorted(followups.values(), key=lambda r: r["since"]),
        "compliance": compliance, "program": program,
    }
    report["slack_text"] = render(report)
    return report


def _names(rows: list[dict[str, Any]], key: str, limit: int = 15) -> list[str]:
    out = [f"• {r['name']}: {r[key]}" for r in rows[:limit]]
    return out + ([f"• …and {len(rows) - limit} more"] if len(rows) > limit else [])


def render(r: dict[str, Any]) -> str:
    s, p = r["sent"], r["program"]
    lines = [f"*Funding CRM: daily report, {r['date']}*" + ("  _(test mode: only test contacts get real "
                                                                     "messages)_" if r["demo_mode"] else "")]
    chan = ", ".join(f"{n} {c}" for c, n in sorted(s["by_channel"].items())) or "none"
    lines.append(f"*Went out:* {s['real']} messages to {s['partners_reached']} partners ({chan})"
                 + (f"; {s['simulated']} simulated (not sent)" if s["simulated"] else ""))
    lines.append(f"*Replied:* {len(r['replies'])}")
    lines += _names([{**x, "what": f"{x['intent']}" + (f", to {x['replied_to']}" if x["replied_to"] else "")}
                     for x in r["replies"]], "what")
    lines.append(f"*Reactivated today:* {len(r['reactivated'])}"
                 + (f"  (program total {p['reactivated_total']})" if "reactivated_total" in p else ""))
    lines += _names([{**x, "what": x["intent"]} for x in r["reactivated"]], "what")
    lines.append(f"*Deals recorded:* {len(r['deals_recorded'])}")
    lines += _names([{**x, "what": x["note"] or "deal submitted"} for x in r["deals_recorded"]], "what")
    lines.append(f"*Deals likely to come in:* {len(r['likely_deals'])}")
    lines += _names(r["likely_deals"], "signal")
    lines.append(f"*Follow up / respond to:* {len(r['follow_ups'])}")
    lines += _names(r["follow_ups"], "why")
    lines.append(f"*Compliance:* {len(r['compliance'])}" + (f"  (DND total {p['dnc_total']})" if "dnc_total" in p else ""))
    lines += _names(r["compliance"], "what")
    if "partners" in p:
        lines.append(f"*Program:* {p['partners']} partners, {p['producing']} producing, {p['reactivated_total']} "
                     f"reactivated, 30-day reply rate {round(p['reply_rate_30d'] * 100)}%")
    elif p.get("error"):
        lines.append(f"_{p['error']}_")
    return "\n".join(lines)


def to_markdown(r: dict[str, Any]) -> str:
    return r["slack_text"].replace("*", "**").replace("• ", "- ")
