"""Collections: who owes us what, and a polite draft to each of them.

The hub's ledger is the record. This reads it, drafts one message per partner at each stage, and flags Justin. Drafts wait for a person, and nothing
goes out until FCM_SEND_COLLECTIONS=1. It can't mark anything Paid: its token can't, and it has no reason to.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import sales
from .errors import FcmError
from .hubapi import Hub


def on() -> bool:
    return os.getenv("FCM_SEND_COLLECTIONS") == "1"


def _book(engine: Any) -> sqlite3.Connection:
    path = Path(engine.settings.state_dir) / "leads.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS collection_drafts (id TEXT PRIMARY KEY, partner_id TEXT, stage TEXT, subject TEXT, body TEXT, cents INTEGER, "
                 "state TEXT, at TEXT, sent_by TEXT)")
    return conn


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _items(charges: list[dict[str, Any]]) -> str:
    fees = [c for c in charges if c["kind"] == "lead_fee"]
    deals = [c for c in charges if c["kind"] == "commission"]
    parts = []
    if fees:
        parts.append(f"{len(fees)} lead{'s' if len(fees) != 1 else ''}")
    if deals:
        parts.append(f"{len(deals)} closed deal{'s' if len(deals) != 1 else ''}")
    return "It covers " + " and ".join(parts) + "."


def _stage(cfg: dict[str, Any], days: int) -> dict[str, Any] | None:
    hits = [s for s in cfg["stages"] if days >= s["after_days"]]
    return hits[-1] if hits else None


def run(engine: Any, apply: bool = False, hub: Hub | None = None, now: datetime | None = None) -> dict[str, Any]:
    """One draft per partner per stage. A dry run shows what's late and writes nothing."""
    hub = hub or Hub()
    now = now or datetime.now(timezone.utc)
    cfg = sales.config(engine.settings)["collections"]
    data = hub.charges()
    board = {p.get("id"): p for p in hub.board().get("partners") or []}
    by_partner: dict[str, list[dict[str, Any]]] = {}
    for c in data.get("overdue") or []:
        by_partner.setdefault(c["partner_id"], []).append(c)
    report: dict[str, Any] = {"apply": apply, "partners_late": len(by_partner), "drafted": 0, "held": 0, "flagged": [], "money": data.get("totals") or {},
                              "send_switch": "on" if on() else "off"}
    conn = _book(engine)
    for pid, charges in by_partner.items():
        days = max(c["days_late"] for c in charges)
        stage = _stage(cfg, days)
        if not stage:
            continue
        cents = sum(c["amount_cents"] or 0 for c in charges)
        name = str((board.get(pid) or {}).get("name") or pid)
        values = {"first": name.split()[0], "amount": _money(cents), "days": days, "items": _items(charges)}
        subject, body = stage["subject"].format(**values), stage["body"].format(**values)
        draft_id = "col-" + hashlib.sha256(f"{pid}|{stage['key']}|{cents}".encode()).hexdigest()[:12]
        if conn.execute("SELECT 1 FROM collection_drafts WHERE id=?", (draft_id,)).fetchone():
            report["held"] += 1
            continue
        if days >= cfg["flag_justin_after_days"]:
            report["flagged"].append(f"{name}: {_money(cents)}, {days} days late")
        if apply:
            conn.execute("INSERT INTO collection_drafts VALUES (?,?,?,?,?,?,?,?,?)", (draft_id, pid, stage["key"], subject, body, cents, "held", now.isoformat(), ""))
            conn.commit()
        report["drafted"] += 1
    return report


def drafts(engine: Any, state: str = "held") -> list[dict[str, Any]]:
    return [dict(r) for r in _book(engine).execute("SELECT * FROM collection_drafts WHERE state=? ORDER BY at", (state,))]


def send(engine: Any, draft_id: str, approver: str, hub: Hub | None = None) -> dict[str, Any]:
    """A person's yes on one draft, to the partner's billing contact in the home CRM."""
    if not approver.strip():
        raise FcmError("name the person approving this")
    conn = _book(engine)
    row = conn.execute("SELECT * FROM collection_drafts WHERE id=?", (draft_id,)).fetchone()
    if not row or row["state"] != "held":
        raise FcmError(f"{draft_id} isn't held")
    if not on():
        return {"state": "held", "draft": draft_id, "why": "FCM_SEND_COLLECTIONS is off"}
    hub = hub or Hub()
    partner = next((p for p in hub.board().get("partners") or [] if p.get("id") == row["partner_id"]), {})
    contact = str(partner.get("billing_contact_id") or "")
    if not contact:
        raise FcmError(f"{row['partner_id']} has no billing_contact_id in the hub's table")
    action = engine.prepare_messages([{"contact_id": contact, "channel": "email", "subject": row["subject"], "body": row["body"], "kind": "reply"}],
                                      "collections")  # through the engine, so its checks and the send guard apply
    got = engine.execute(action["action_id"])
    if not (got.get("live") or got.get("mock") or got.get("simulated")):
        raise FcmError(f"not sent: {got.get('stopped') or got.get('state')}")
    conn.execute("UPDATE collection_drafts SET state='sent', sent_by=? WHERE id=?", (approver, draft_id))
    conn.commit()
    engine.store.audit(actor=approver, action="collection.send", resource=row["partner_id"], decision="human", result="ok", details={"draft": draft_id})
    return {"state": "sent", "draft": draft_id}


def old_drafts(engine: Any, now: datetime, days: int = 1) -> list[dict[str, Any]]:
    cutoff = (now - timedelta(days=days)).isoformat()
    return [d for d in drafts(engine) if d["at"] < cutoff]
