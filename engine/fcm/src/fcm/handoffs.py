"""Pairing, the intro and the 7-day clock. The hub holds the ledger; this module acts on it.

    propose_qualified  qualified leads go to the hub as proposals. Justin approves each one on the Handoffs page.
    decide             pure: given a handoff and the time, what's due. Every number is in config/handoff.json.
    watch              runs what's due, once each: partner tasks, the two lead check-ins, flags for Justin, re-pairs.

While a partner has a lead, the contact carries the handling tag: the agent records what comes in and sends only the
intro and the two check-ins (engine.PARTNER_WINDOW_KINDS). The Reply Agent stays out through the hub's quiet list.

Nothing reaches a person while FCM_SEND_HANDOFFS is off: those steps come back as "held" and stay due. Tasks and
flags in our own CRM aren't sends, so they run on --apply. A re-pair only creates a proposal, which Justin approves.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import leads
from .errors import FcmError
from .hubapi import Hub, HubError

ACTIVE = {"sent", "accepted"}
LEFT_PARTNER = {"returned", "declined"}  # they said no: the hub's open list drops these, so `watch` goes looking
FINISHED = {"funded", "paid", "cancelled"}
MOVED = {"application", "submitted", "offer"}  # past first contact: a real sign of work


def send_on() -> bool:
    return os.getenv("FCM_SEND_HANDOFFS") == "1"


def _when(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def milestones(h: dict[str, Any]) -> set[str]:
    return {str(m.get("milestone")) for m in h.get("milestones") or []}


def decide(h: dict[str, Any], now: datetime, cfg: dict[str, Any]) -> list[dict[str, str]]:
    """Which steps are due on this handoff, oldest rule first. Pure, and safe to call on every sweep: `watch` remembers
    what already ran."""
    status = h.get("status")
    intro_steps = [{"step": "intro_partner", "why": "give the partner the lead"},
                   {"step": "intro_lead", "why": "give the lead the partner"}]
    if status == "approved" and h.get("partner", {}).get("delivery") == "ghl_seat":
        return intro_steps
    if status not in ACTIVE:
        return []
    steps = list(intro_steps)
    sent = _when(h.get("sent_at"))
    if not sent:
        return steps
    hours = (now - sent).total_seconds() / 3600
    days = hours / 24
    seen = milestones(h)
    contacted = status == "accepted" or bool(seen)
    moved = bool(seen & MOVED)
    if not contacted and hours >= cfg["contact_within_hours"]:
        steps.append({"step": "nudge_partner", "why": f"{int(hours)} hours, no contact logged"})
    if not contacted and hours >= cfg["flag_after_hours"]:
        steps.append({"step": "flag_no_contact", "why": f"{int(hours)} hours, still no contact logged"})
    first, last = cfg["checkin_days"][0], cfg["checkin_days"][-1]
    if days >= first and not moved:
        steps.append({"step": "checkin_first", "why": f"day {first} check-in"})
    if days >= last:
        steps.append({"step": "checkin_last", "why": f"day {last} check-in"})
    if days >= cfg["status_day"] and not moved:
        steps.append({"step": "status_partner", "why": f"day {cfg['status_day']}, no application or decision"})
        steps.append({"step": "flag_stuck", "why": f"day {cfg['status_day']}, no application or decision"})
    if days >= cfg["repair_day"] and not moved:
        steps.append({"step": "repair", "why": f"day {cfg['repair_day']}, nothing real happening"})
    return steps


class Steps:
    """Which steps already ran for which handoff, so each fires once."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS handoff_steps (handoff_id TEXT, step TEXT, at TEXT, detail TEXT, "
                          "PRIMARY KEY (handoff_id, step))")

    def done(self, handoff_id: str) -> set[str]:
        return {r[0] for r in self.conn.execute("SELECT step FROM handoff_steps WHERE handoff_id=?", (handoff_id,))}

    def mark(self, handoff_id: str, step: str, now: datetime, detail: str = "") -> None:
        self.conn.execute("INSERT OR REPLACE INTO handoff_steps VALUES (?,?,?,?)", (handoff_id, step, now.isoformat(), detail))
        self.conn.commit()


def _steps(engine: Any) -> Steps:
    return Steps(Path(engine.settings.state_dir) / "leads.sqlite3")


def lead_for_hub(card: dict[str, Any], view: dict[str, Any]) -> dict[str, Any]:
    """What the hub gets. Its own gate decides whether this qualifies and strips text consent from the payload."""
    summary = leads.scrub(f"{view['ask']}. Readiness: {view['readiness']} ({view['why']}).")
    return {"contact_id": card["contact_id"], "name": card.get("name") or "", "email": card.get("email") or "",
            "phone": card.get("phone") or "", "business": card.get("company") or "", "state": view["state"],
            "lane": view["lane"], "amount": view["amount"], "summary": summary, "source": view["source"],
            "partner_ok_quote": view["ok_quote"], "readiness": "" if view["readiness"] == "unknown" else view["readiness"],
            "ask": view.get("said", "")}  # only for the hub's word rule: it never reaches the partner's payload


def propose_qualified(engine: Any, apply: bool = False, limit: int = 0, hub: Hub | None = None) -> dict[str, Any]:
    """Send every lead who is ready to propose. Without --apply, the hub previews who each would go to."""
    hub = hub or Hub()
    cfg = leads.config(engine.settings)
    candidates: dict[str, dict[str, Any]] = {}
    for tag in (cfg["tags"]["consent"], "src:website"):
        page = 1
        while True:
            rows = engine.ghl.search_contacts(tags=[tag], limit=100, page=page)
            for r in rows:
                candidates.setdefault(r["id"], r)
            if len(rows) < 100:
                break
            page += 1
    report: dict[str, Any] = {"apply": apply, "looked_at": len(candidates), "proposed": 0, "previewed": [], "unrouted": [],
                              "not_ready": 0, "failed": 0}
    worked = 0
    for cid in candidates:
        if limit and worked >= limit:
            break
        try:
            card = hub.card(cid)
            view = leads.assess(card, cfg)
            if view["next"] != "ready to propose":
                report["not_ready"] += 1
                continue
            worked += 1
            lead = lead_for_hub(card, view)
            if not apply:
                got = hub.preview(lead)
                partner = (got.get("route") or {}).get("partner") or {}
                report["previewed"].append({"contact_id": cid, "qualifies": (got.get("qualify") or {}).get("ok"),
                                            "partner": partner.get("name", ""), "why": (got.get("route") or {}).get("why", "")})
                continue
            got = hub.propose(lead)
            if got.get("already_open"):
                continue
            report["proposed"] += 1
            engine.vault.log("Handoff proposed", f"{cid}: to {got.get('partner_id')}")
        except HubError as exc:
            text = str(exc)
            if "-> 400" in text or "-> 409" in text or "-> 422" in text:  # the hub's own no: no partner fits, or not qualified
                report["unrouted"].append({"contact_id": cid, "why": text[:200]})
            else:
                report["failed"] += 1
    return report


def _fill(template: dict[str, str], values: dict[str, Any]) -> dict[str, str]:
    class Blank(dict):
        def __missing__(self, key: str) -> str:
            return ""
    return {k: v.format_map(Blank(values)) for k, v in template.items()}


def _reach(p: dict[str, Any]) -> str:
    return str(p.get("contact") or "").strip() or "they'll have your details"


def _values(h: dict[str, Any], card: dict[str, Any], view: dict[str, Any], old: dict[str, Any] | None = None) -> dict[str, Any]:
    p = h.get("partner") or {}
    name = str(p.get("name") or "our partner")
    first = str(card.get("name") or "").split(":")[0].split()[0] if card.get("name") else "there"
    if view.get("lead_is_asker") or ":" in str(card.get("name") or ""):
        first = "there"  # "Facebook asker: needs a DSCR loan" isn't a name
    link = str(h.get("status_link") or "")
    consent = f"their words: {view['ok_quote']}" if view["ok_quote"] else "website form"
    return {"first": first, "name": str(card.get("name") or "this lead"),
            "partner_name": name, "partner_first": name.split()[0],
            "at_company": f" at {p['company']}" if p.get("company") else "", "partner_reach": _reach(p),
            "ask": leads.scrub(view["ask"]), "readiness": view["readiness"], "email": card.get("email") or "",
            "phone": card.get("phone") or "", "state": view["state"] or "unknown", "consent": consent,
            "status_line": f"\n\nUpdate us here: {link}" if link else "",
            "old_partner_first": str((old or {}).get("name") or "the last partner").split()[0]}


def _message_lead(engine: Any, contact_id: str, msg: dict[str, str], kind: str, purpose: str) -> dict[str, Any]:
    if not send_on():
        return {"state": "held"}
    action = engine.prepare_messages([{"contact_id": contact_id, "channel": "email", "subject": msg["subject"],
                                       "body": msg["body"], "kind": kind}], purpose)
    got = engine.execute(action["action_id"])
    if got.get("live") or got.get("mock") or got.get("simulated"):
        return {"state": "sent"}
    if got.get("pending") and not got.get("stopped"):
        return {"state": "sent", "waiting": "quiet hours"}  # the batch is frozen; `fcm outbox resume` finishes it
    why = next((str(c.get("skipped") or c.get("error")) for c in got.get("per_contact") or [] if c.get("skipped") or c.get("error")), "")
    raise FcmError(f"not sent: {why or got.get('stopped') or got.get('state')}")  # stays due, and shows up as failed


def _task_partner(engine: Any, h: dict[str, Any], msg: dict[str, str], due: datetime, cfg: dict[str, Any]) -> dict[str, Any]:
    """A seat partner gets a task on the lead's contact. A partner without a seat can't see the CRM, so the same task goes
    to Justin, marked for him to pass on, until the partner's status link answers."""
    p = h.get("partner") or {}
    seat = str(p.get("ghl_user_id") or "") if p.get("delivery") == "ghl_seat" else ""
    title = msg["title"] if seat else f"Tell {p.get('name') or 'the partner'}: {msg['title']}"
    manager = str(engine.settings.ghl_map.get("users", {}).get("manager", ""))
    engine.ghl.create_task(h["contact_id"], title, due.date().isoformat(), msg["body"], assigned_to=seat or manager)
    return {"state": "done", "assigned": "partner" if seat else "justin"}


def _flag(engine: Any, h: dict[str, Any], title: str, why: str, due: datetime) -> dict[str, Any]:
    manager = str(engine.settings.ghl_map.get("users", {}).get("manager", ""))
    engine.ghl.create_task(h["contact_id"], title, due.date().isoformat(), why, assigned_to=manager)
    engine.ghl.add_tags(h["contact_id"], [engine.settings.program_tag("manager")])
    return {"state": "done"}


def intro(engine: Any, handoff_id: str, apply: bool = False, hub: Hub | None = None, now: datetime | None = None) -> dict[str, Any]:
    """See the intro for one handoff, or run what's left of it now. `watch` normally does this."""
    hub = hub or Hub()
    cfg = leads.config(engine.settings)
    now = now or datetime.now(timezone.utc)
    h = next((x for x in hub.open() if x["id"] == handoff_id), None)
    if not h:
        raise FcmError(f"{handoff_id} isn't open")
    if not apply:
        return _intro_preview(engine, h, cfg, hub)
    log = _steps(engine)
    out = {}
    for step in ("intro_partner", "intro_lead"):
        if step not in log.done(h["id"]):
            out[step] = run_step(engine, h, {"step": step, "why": "by hand"}, cfg, hub, now)
            if out[step].get("state") != "held":
                log.mark(h["id"], step, now)
    return out


def _intro_messages(h: dict[str, Any], cfg: dict[str, Any], hub: Hub) -> tuple[dict[str, str], dict[str, str]]:
    if h.get("status") not in ACTIVE | {"approved"}:
        raise FcmError(f"{h['id']} is {h.get('status')}: only an approved or sent handoff gets an intro")
    card = hub.card(h["contact_id"])
    view = leads.assess(card, cfg)
    old = None
    if h.get("previous_id"):
        pid = hub.handoff(h["previous_id"]).get("partner_id")
        old = next((p for p in hub.board().get("partners") or [] if p.get("id") == pid), None)
    values = _values(h, card, view, old)
    t = cfg["templates"]
    return _fill(t["repair_lead" if h.get("previous_id") else "intro_lead"], values), _fill(t["intro_partner"], values)


def _intro_preview(engine: Any, h: dict[str, Any], cfg: dict[str, Any], hub: Hub) -> dict[str, Any]:
    to_lead, to_partner = _intro_messages(h, cfg, hub)
    return {"state": "preview", "to_lead": to_lead, "to_partner": to_partner}


def _intro_partner(engine: Any, h: dict[str, Any], cfg: dict[str, Any], hub: Hub, now: datetime) -> dict[str, Any]:
    """The seat assign (the hub's write), the partner's task, and the tag that quiets everyone else."""
    _, to_partner = _intro_messages(h, cfg, hub)
    if h.get("status") == "approved":
        hub.sent_by_seat(h["id"])
    got = _task_partner(engine, h, to_partner, now + timedelta(hours=cfg["contact_within_hours"]), cfg)
    engine.ghl.add_tags(h["contact_id"], [cfg["tags"]["handling"]])
    return got


def _intro_lead(engine: Any, h: dict[str, Any], cfg: dict[str, Any], hub: Hub) -> dict[str, Any]:
    to_lead, _ = _intro_messages(h, cfg, hub)
    sent = _message_lead(engine, h["contact_id"], to_lead, "handoff_intro", "partner intro")
    engine.vault.log("Handoff intro", f"{h['id']}: {sent['state']}")
    return sent


def _repair(engine: Any, h: dict[str, Any], why: str, cfg: dict[str, Any], hub: Hub, now: datetime) -> dict[str, Any]:
    got = hub.repair(h["id"], why)
    engine.ghl.remove_tags(h["contact_id"], [cfg["tags"]["handling"]])
    state = got.get("status")
    if state != "proposed":
        _flag(engine, h, "Handoff stuck: no other partner fits", got.get("why") or f"re-pair said {state}", now)
    return {"state": "done", "repair": state, "next": (got.get("handoff") or {}).get("id", "")}


def run_step(engine: Any, h: dict[str, Any], step: dict[str, str], cfg: dict[str, Any], hub: Hub, now: datetime) -> dict[str, Any]:
    kind = step["step"]
    if kind == "intro_partner":
        return _intro_partner(engine, h, cfg, hub, now)
    if kind == "intro_lead":
        return _intro_lead(engine, h, cfg, hub)
    if kind == "repair":
        return _repair(engine, h, step["why"], cfg, hub, now)
    if kind in ("flag_no_contact", "flag_stuck"):
        return _flag(engine, h, f"Handoff stuck: {step['why']}", step["why"], now)
    card = hub.card(h["contact_id"])
    view = leads.assess(card, cfg)
    values = _values(h, card, view)
    values["hours"] = int((now - (_when(h.get("sent_at")) or now)).total_seconds() / 3600)
    t = cfg["templates"]
    if kind == "nudge_partner":
        return _task_partner(engine, h, _fill(t["nudge_partner"], values), now + timedelta(days=1), cfg)
    if kind == "status_partner":
        return _task_partner(engine, h, _fill(t["status_partner"], values), now + timedelta(days=2), cfg)
    which = cfg["checkin_days"][0] if kind == "checkin_first" else cfg["checkin_days"][-1]
    return _message_lead(engine, h["contact_id"], _fill(t[f"checkin_lead_{which}"], values), "handoff_checkin", "handoff check-in")


def _closed(engine: Any, cfg: dict[str, Any], hub: Hub, log: Steps, now: datetime, apply: bool, report: dict[str, Any]) -> None:
    """The partner said no, or the deal finished. A "no" that nobody has re-paired gets the next partner at once. Either
    way the lead stops being marked as with that partner."""
    rows = hub.board().get("handoffs") or []
    replaced = {r.get("previous_id") for r in rows if r.get("previous_id")}
    for h in rows:
        status, hid, cid = h.get("status"), h.get("id"), h.get("contact_id")
        if status not in LEFT_PARTNER | FINISHED or not cid or "closed" in log.done(hid):
            continue
        again = status in LEFT_PARTNER and hid not in replaced
        item = {"handoff": hid, "step": "repair" if again else "release", "why": f"{status}: the partner is done"}
        if not apply:
            report["due"].append(item)
            continue
        try:
            if again:
                _repair(engine, h, item["why"], cfg, hub, now)
            else:
                engine.ghl.remove_tags(cid, [cfg["tags"]["handling"]])
        except (FcmError, HubError, KeyError, OSError) as exc:
            report["failed"].append({**item, "error": str(exc)[:200]})
            continue
        log.mark(hid, "closed", now, status)
        report["ran"].append(item)


def watch(engine: Any, apply: bool = False, hub: Hub | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Run what's due on every handoff. A failed or held step stays due; one handoff failing never stops the rest."""
    hub = hub or Hub()
    cfg = leads.config(engine.settings)
    now = now or datetime.now(timezone.utc)
    log = _steps(engine)
    report: dict[str, Any] = {"apply": apply, "open": 0, "ran": [], "held": [], "due": [], "failed": []}
    _closed(engine, cfg, hub, log, now, apply, report)
    for h in hub.open():
        report["open"] += 1
        done = log.done(h["id"])
        for step in decide(h, now, cfg):
            if step["step"] in done:
                continue
            item = {"handoff": h["id"], **step}
            if not apply:
                report["due"].append(item)
                continue
            try:
                got = run_step(engine, h, step, cfg, hub, now)
            except (FcmError, HubError, KeyError, OSError) as exc:
                report["failed"].append({**item, "error": str(exc)[:200]})
                break  # the next step on this handoff may depend on this one
            if got.get("state") == "held":
                report["held"].append(item)
                continue
            log.mark(h["id"], step["step"], now, str(got.get("repair") or ""))
            report["ran"].append(item)
            if step["step"] == "repair":
                break
    return report


def status(engine: Any, hub: Hub | None = None, now: datetime | None = None) -> dict[str, Any]:
    hub = hub or Hub()
    cfg = leads.config(engine.settings)
    now = now or datetime.now(timezone.utc)
    log = _steps(engine)
    rows = []
    for h in hub.open():
        due = [s["step"] for s in decide(h, now, cfg) if s["step"] not in log.done(h["id"])]
        sent = _when(h.get("sent_at"))
        rows.append({"id": h["id"], "partner": (h.get("partner") or {}).get("name", h.get("partner_id")), "status": h.get("status"),
                     "days": round((now - sent).total_seconds() / 86400, 1) if sent else None,
                     "milestones": sorted(milestones(h)), "due": due})
    return {"open": len(rows), "sends": "on" if send_on() else "held", "handoffs": rows}


def partner_notes(engine: Any, apply: bool = False, hub: Hub | None = None) -> dict[str, Any]:
    """One note per backend partner in Partners/: what they fund, what they won't, and how they've done."""
    hub = hub or Hub()
    board = hub.board()
    handoffs = board.get("handoffs") or []
    written = []
    profiles = {x.get("id"): x for x in board.get("profiles") or []}
    for p in board.get("partners") or []:
        mine = [h for h in handoffs if h.get("partner_id") == p.get("id")]
        count = {s: sum(1 for h in mine if h.get("status") == s) for s in ("proposed", "sent", "accepted", "declined", "returned", "funded", "paid")}
        seat = profiles.get(p.get("id")) or {}
        lines = [f"# {p.get('name')}", "", f"- Status: {p.get('status')}", f"- Company: {p.get('company') or '?'}",
                 f"- Lanes: {', '.join(p.get('lanes') or [])}", f"- Products: {', '.join(p.get('products') or []) or 'any'}",
                 f"- States: {', '.join(p.get('states') or [])}", f"- Takes: {', '.join(p.get('takes') or ['ready'])}",
                 f"- Situations: {p.get('situations') or '?'}", f"- How we take leads to them: {p.get('delivery')}",
                 f"- Won't do: {', '.join((seat.get('doesnt') or {}).get('products') or []) or '?'}",
                 f"- Strong at: {', '.join(seat.get('strong_at') or []) or '?'}",
                 f"- Weak at: {', '.join(seat.get('weak_at') or []) or '?'}",
                 f"- Seat: {(seat.get('seat') or {}).get('delivery') or p.get('delivery')}, "
                 f"{(seat.get('seat') or {}).get('open', 0)} open", "",
                 "## Send history", ""] + [f"- {k}: {v}" for k, v in (seat.get("history") or {}).items()] + [
                 "", "## Scorecard", ""] + [f"- {k}: {v}" for k, v in count.items()]
        path = Path(engine.settings.vault_dir) / "Partners" / f"{leads._slug(str(p.get('name') or p.get('id')))}.md"
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n")
        written.append(path.name)
    return {"apply": apply, "partners": written}
