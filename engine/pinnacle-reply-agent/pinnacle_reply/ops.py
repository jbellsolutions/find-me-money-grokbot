"""The `pinnacle_replies` operations a person or the Revenue Partner asks for between cycles.

    ledger · queue · chase · check · draft (one lead) · assign · hold · skip · mark (replied/won) · answered

Hold, assign and answered live in the ledger only (Lead Radar has no held or answered status yet: F2).
Skip and mark also go to the desk while REPLY_WRITE is on, for Lead Radar's leads only: the other lanes' leads are
recorded in the ledger and never written back to where they came from. Nothing here posts or sends.
"""

from __future__ import annotations

import json
from typing import Any

from . import checks, config, drafter, ghl, lanes, ledger, radar, sources, vault

STATES = ledger.STATES


def _row(conn, lead_id: str) -> dict[str, Any]:
    row = ledger.lead(conn, lead_id)
    if not row:
        raise KeyError(f"no lead {lead_id} in the ledger; run a cycle first")
    return row


def _on_desk(row: dict[str, Any]) -> bool:
    return (row.get("source") or "lead-radar") == "lead-radar"


def _desk_item(row: dict[str, Any]) -> dict[str, Any]:
    """The lead as the desk has it now, so a write sees the latest reply state and note. A lead from another lane is
    rebuilt from the ledger: its lane is never called from here."""
    if not _on_desk(row):
        with ledger.connect() as conn:
            said = next((m["text"] for m in ledger.messages(conn, row["id"]) if m["kind"] == "post"), "")
        return {"id": row["id"], "source": row["source"], "campaign": row.get("campaign"), "kind": row.get("kind"),
                "platform": row.get("platform"), "need": row.get("need"), "text": said, "reply": {}}
    items = radar.queue_all(status="all", campaign=row.get("campaign") or "", since="").get("items") or []
    item = next((i for i in items if i["id"] == row["id"]), None)
    if item is None:
        raise KeyError(f"lead {row['id']} isn't on Lead Radar's desk any more")
    return item


def queue(state: str = "unattended", persona: str = "", poster: str = "", limit: int = 50) -> list[dict[str, Any]]:
    if state not in (*STATES, "all"):
        raise ValueError(f"state is one of {', '.join(STATES)} or all")
    sql, args = "SELECT * FROM leads WHERE 1=1", []
    if state != "all":
        sql, args = sql + " AND state=?", [state]
    if persona:
        sql, args = sql + " AND persona=?", args + [persona]
    if poster:
        sql, args = sql + " AND poster=?", args + [poster]
    sql += " ORDER BY CASE tier WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, posted_at DESC LIMIT ?"
    keep = ("id", "state", "reason", "campaign", "platform", "kind", "tier", "url", "posted_at", "persona", "poster",
            "draft", "radar_draft", "answer")
    with ledger.connect() as conn:
        return [{k: r[k] for k in keep} for r in conn.execute(sql, (*args, max(1, min(500, limit))))]


def report() -> dict[str, Any]:
    with ledger.connect() as conn:
        last = conn.execute("SELECT summary FROM cycles WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        summary = json.loads(last[0]) if last else {}
        read = {k: "" if v.get("read") else v.get("why") or "not read" for k, v in (summary.get("lanes") or {}).items()}
        return ledger.report(conn, bool((summary.get("ledger") or {}).get("truncated")), read or None)


def chase() -> dict[str, Any]:
    with ledger.connect() as conn:
        return ledger.chase(conn)


def check(text: str, kind: str = checks.FIRST) -> dict[str, Any]:
    """The checker on any text. `kind` is "first" (a first reply: asks for nothing) or "follow_up" (may ask once for
    their best email or number and their OK for a funding partner to reach them)."""
    if kind not in (checks.FIRST, checks.FOLLOW_UP):
        raise ValueError("kind is first or follow_up")
    bad = checks.violations(text, kind)
    return {"passes": not bad, "kind": kind, "violations": bad, "g3": checks.g3_violations(text),
            "words": len(text.split())}


def draft_one(lead_id: str, guidance: str = "", dry_run: bool = True, client=None) -> dict[str, Any]:
    """Draft or redraft one lead now. Shown, recorded in the ledger, written to the desk only if dry_run is off."""
    with ledger.connect() as conn:
        row = _row(conn, lead_id)
        if row["source"] in sources.DIRECT:
            raise ValueError(f"{lead_id} is a private conversation: a person answers it in GHL, the agent doesn't draft it")
        if row["state"] == "partner":
            raise ValueError(f"{lead_id}: {ledger.PARTNER_REASON}")
        item = _desk_item(row)
        if guidance:
            item = {**item, "need": f"{item.get('need') or ''} (guidance from the team: {guidance[:300]})"}
        if row.get("local_state") == "answered" and row.get("answer"):  # redrafting the follow-up to their answer
            item = ledger.with_answer(conn, row, item)
        out = drafter.draft(item, row["persona"], client)
        if out["action"] == "reply":
            ledger.record(conn, lead_id, draft=out["reply"], drafted_at=ledger.now(), violations="", desk_written=0)
            out["desk"] = radar.save_draft(item, out["reply"], "reply-agent: redraft", dry_run) if _on_desk(row) \
                else {"written": False, "why": f"{row['source']} leads stay in the ledger"}
            if out["desk"].get("written"):
                ledger.record(conn, lead_id, desk_written=1)
        return {"id": lead_id, "persona": row["persona"], "poster": row["poster"], **out}


def assign(lead_id: str, poster: str) -> dict[str, Any]:
    poster = poster.strip()
    if not poster:
        raise ValueError("say who posts it: a persona id (P1-P5) or a person's name")
    with ledger.connect() as conn:
        _row(conn, lead_id)
        return ledger.record(conn, lead_id, assigned_to=poster[:60], poster=poster[:60])


def hold(lead_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("a hold needs its reason")
    with ledger.connect() as conn:
        _row(conn, lead_id)
        return ledger.record(conn, lead_id, local_state="held", reason=reason.strip()[:300])


def skip(lead_id: str, reason: str, dry_run: bool = True) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("a skip needs its reason")
    with ledger.connect() as conn:
        row = _row(conn, lead_id)
        out = ledger.record(conn, lead_id, local_state="skipped", reason=reason.strip()[:300], desk_written=0)
        desk = radar.save_skip(_desk_item(row), reason.strip(), dry_run) if _on_desk(row) \
            else {"written": False, "why": f"{row['source']} leads stay in the ledger"}
        if desk.get("written"):
            ledger.record(conn, lead_id, desk_written=1)
        return {"id": lead_id, "state": out["state"], "reason": out["reason"], "desk": desk}


def mark(lead_id: str, poster: str, status: str = "replied", note: str = "", dry_run: bool = True,
         text: str = "", url: str = "") -> dict[str, Any]:
    """Record a reply that was posted. The one path for every channel: a person posting by hand today, a lane's
    auto-poster later. `text` is what was posted (default: the draft it was posted from) and `url` where."""
    _poster_named(poster)
    with ledger.connect() as conn:
        row = _row(conn, lead_id)
        return record_mark(conn, row, _desk_item(row) if _on_desk(row) else None, poster, status, note, dry_run,
                           text, url)


def _poster_named(poster: str) -> None:
    if not poster.strip() or poster.strip() == config.WRITER:
        raise ValueError("say who posted it: a reply is only marked when a person posted it")


def record_mark(conn, row: dict[str, Any], item: dict[str, Any] | None, poster: str, status: str = "replied",
                note: str = "", dry_run: bool = True, text: str = "", url: str = "") -> dict[str, Any]:
    """mark() on an open ledger with the desk's item in hand. The auto-poster records each post through here, under
    its lane's account ("P2 (auto)"), never as the agent itself."""
    _poster_named(poster)
    lead_id = row["id"]
    if not _on_desk(row):
        desk = {"written": False, "why": f"{row['source']} leads stay in the ledger"}
    elif item is None:
        desk = {"written": False, "why": "the lead wasn't on the desk's queue just now"}
    else:
        desk = radar.save_replied(item, poster.strip(), note, status, dry_run)
    kind = checks.FOLLOW_UP if row.get("local_state") == "answered" else checks.FIRST
    posted = text.strip() or (row.get("draft") if row.get("draft") and checks.passes(row["draft"], kind) else "") \
        or row.get("radar_draft") or ""
    ledger.log(conn, lead_id, "reply", posted, poster.strip(), url.strip() or row.get("url") or "")
    out = ledger.record(conn, lead_id, marked_by=poster.strip()[:60], marked_at=ledger.now(),
                        desk_written=1 if desk.get("written") else 0,
                        # a posted follow-up ends the answered turn: the lead waits on their next answer
                        **({"local_state": ""} if row.get("local_state") == "answered" else {}))
    return {"id": lead_id, "state": out["state"], "reason": out["reason"], "desk": desk}


def answered(lead_id: str, answer: str) -> dict[str, Any]:
    """The person wrote back. The next cycle drafts the follow-up for the same poster."""
    if not answer.strip():
        raise ValueError("paste what they wrote back")
    with ledger.connect() as conn:
        _row(conn, lead_id)
        ledger.take_contact(conn, lead_id, answer)  # their email, number and OK go to the GHL contact, before the scrub
        out = ledger.record(conn, lead_id, local_state="answered", answer=answer.strip(), answered_at=ledger.now())
        return {"id": lead_id, "state": out["state"], "reason": out["reason"]}


def conversation(lead_id: str) -> dict[str, Any]:
    """One lead's whole conversation, oldest first: their post, drafts, holds, replies posted, answers."""
    with ledger.connect() as conn:
        row = _row(conn, lead_id)
        return {"id": lead_id, "who": vault.title(row), "state": row["state"], "reason": row["reason"],
                "url": row.get("url"), "ghl_contact_id": row.get("ghl_contact_id"),
                "messages": [{k: m[k] for k in ("at", "kind", "direction", "by", "text", "url")}
                             for m in ledger.messages(conn, lead_id)]}


def crm(action: str = "status", limit: int | None = None, only: str = "") -> dict[str, Any]:
    """GHL: status (what's in the outbox), prepare (work it out, free), send (only with REPLY_GHL on)."""
    with ledger.connect() as conn:
        if action == "status":
            return ghl.status(conn)
        if action == "prepare":
            return {**ghl.prepare(conn), **ghl.status(conn)}
        if action == "send":
            return ghl.run(conn, limit, only)
        raise ValueError("action is status, prepare or send")


def memory() -> dict[str, Any]:
    """Write every lead and its conversation into the Obsidian vault, then commit and push it."""
    with ledger.connect() as conn:
        return vault.publish(conn)


def personas() -> dict[str, Any]:
    s = lanes.settings()
    return {"personas": {k: {"name": v["name"], "lane": v["lane"]} for k, v in s["personas"].items()},
            "personas_live": s.get("personas_live", []), "poster_default": s.get("poster_default"),
            "hold_older_than_days": s.get("hold_older_than_days")}


def lanes_now() -> dict[str, Any]:
    """Read every lane now and count what each holds, without touching the ledger: what a cycle would pull."""
    from collections import Counter
    out = {}
    for r in sources.read_all():
        items = r.get("items") or []
        out[r["lane"]] = {"read": r["ok"], "why": r.get("why") or "", "leads": len(items),
                          "truncated": bool(r.get("truncated")),
                          "by_checklist_line": dict(Counter(i.get("hub") or "" for i in items)),
                          "reply_status": dict(Counter((i.get("reply") or {}).get("status") or "new" for i in items))}
    return out


def checklist(send: bool = False) -> dict[str, Any]:
    """The hub check-offs from the last cycle's reads and today's booked calls. Posted only with send and REPLY_HUB."""
    from . import hub
    with ledger.connect() as conn:
        last = conn.execute("SELECT summary FROM cycles WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        lanes_read = (json.loads(last[0]) if last else {}).get("lanes") or {}
        read = {k: "" if v.get("read") else v.get("why") or "not read" for k, v in lanes_read.items()} or \
            {"lead-radar": "no cycle has run yet"}
        ran = (lanes_read.get("creators") or {}).get("ran")
        return hub.report(conn, read, dry_run=not send, count_booked=True, ran=ran)
