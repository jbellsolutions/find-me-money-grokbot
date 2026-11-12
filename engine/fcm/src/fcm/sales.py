"""The sales side: read a campaign reply, sort it, move the person, draft the answer.

    classify    pure: what kind of reply this is. An opt-out wins over everything else.
    check       pure: the lines a message to a lead can't cross. Campaign copy is tested against the same list.
    triage      one reply: the note, the tags, the stage, the draft. Dry unless apply=True.
    move_stage  forward only, and never past Appointment Booked. Funded and Paid are Justin's.
    mark_ok     records their OK for a partner, only in words they actually wrote.
    send_draft  a person's yes on one draft. Off until FCM_SEND_REPLIES=1.

A reply's text is untrusted data: it's sorted by rules and stored, never followed. Details someone gives go on the GHL
contact; the note and the vault get them blanked. Only people who answer get written to the home CRM, so the campaign needs
no bulk move between CRMs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import instantly, leads
from .engine import BANNED_PHRASES
from .errors import FcmError

EMAIL_REPLY = leads.EMAIL_REPLY
_WORDS = re.compile(r"[a-z0-9']+")

_BOUNCE = re.compile(r"mail delivery (?:failed|subsystem)|undeliverable|delivery has failed|address not found|mailer-daemon|"
                     r"delivery status notification", re.I)
_AUTO = re.compile(r"out of (?:the )?office|automatic reply|auto-?reply|autoreply|on vacation|on leave|maternity leave|"
                   r"away from (?:my|the) (?:desk|office|email)|limited access to (?:my )?email", re.I)
_COMPLAINT = re.compile(r"\bspam\b|my (?:lawyer|attorney)|\bsue\b|report you|cease and desist|\bftc\b|\battorney general\b", re.I)
_OPT_OUT = re.compile(r"unsubscribe|remove me|take me off|stop (?:emailing|contacting|sending|messaging|writing)|no thanks|no,? thank you|"
                      r"do not (?:contact|email)|don'?t (?:contact|email)|opt[ -]?out|not for me|not my thing|please stop|leave me alone|"
                      r"^\s*(?:stop|no|nope|nah|pass|remove)\W*$", re.I)  # the T3 note promises one word stops it
_IDENTITY = re.compile(r"\bbots?\b|\bai\b|automated|real person|are you (?:a )?(?:real|human)|is this really|chatgpt|who is this|"
                       r"who are you|is this justin", re.I)
_SOURCE = re.compile(r"(?:how|where) (?:did|'?d) you (?:get|find)|how do you have my|who gave you", re.I)
_SEND_IT = re.compile(r"^\s*send it\W*$", re.I)
_BARE_AMOUNT = re.compile(r"\$\s?\d|\b\d[\d,.]*\s?(?:k|m|thousand|million)\b", re.I)
_WRONG = re.compile(r"wrong (?:person|email|address)|not the right person|no longer (?:with|at|work)|left the company|"
                    r"(?:doesn'?t|does not) work here|\bretired\b|not my department", re.I)
_NEED = re.compile(r"\bneed\b|\bneeding\b|looking (?:for|to)|\bwant(?:ing)? to\b|would like|tell me more|sounds good|"
                   r"let'?s talk|call me|send (?:me )?(?:the )?(?:info|details)|\binterested\b|\byes\b|\bsure\b|how much can|"
                   r"line of credit|credit line|working capital|payroll|\btrucks?\b|equipment|expansion|inventory|\bloan\b", re.I)
_NO = re.compile(r"not interested|no need|all set|(?:don'?t|do not) need|not looking|pass on this|we'?re good|we are good|no interest", re.I)
_LATER = re.compile(r"not (?:right )?now|maybe later|next (?:year|quarter|month|spring|summer|fall|winter)|in a few months|check back|"
                    r"reach (?:back )?out (?:again )?(?:in|next|later)|later this year|circle back|too early|down the road", re.I)
_OK_HINT = re.compile(r"have (?:your|the|them|him|her)\b.*(?:call|email|reach)|(?:ok|okay|fine|happy|yes)\b.*(?:share|partner|introduce|connect)|"
                      r"connect me|introduce me|send me to", re.I)

# The lines no message to a lead can cross. Each is a law line or Justin's rule; see knowledge/lending/03-campaign-rules.md.
NEVER_SAY = (
    "saw you", "seen you", "your search", "you searched", "you were searching", "you've been searching", "searching for",
    "you were looking", "your recent inquiry", "your inquiry", "as we discussed", "as discussed", "when we spoke", "we spoke",
    "last time we", "our conversation", "following up on our", "you reached out", "you signed up", "you requested", "your request",
    "pre-approved", "preapproved", "pre approved", "you qualify", "you're approved", "you are approved", "approved for",
    "direct lender", "we lend", "our own money", "our money",
    "funding machine", "llc",
    "business credit card", "business credit cards",
    "social security", "ssn", "date of birth", "bank login", "routing number", "account number please",
    "send your bank statements", "send me your bank statements", "credit report",
) + tuple(  # private names a message never says (the legal entity, the broker of record): set at intake, comma-separated
    x.strip().lower() for x in os.environ.get("FCM_NEVER_SAY", "").split(",") if x.strip())
_RATE = re.compile(r"\b\d{1,2}(\.\d+)?\s?%\s*(apr|interest|rate)", re.I)


def config(settings: Any) -> dict[str, Any]:
    path = Path(settings.config_dir) / "sales.json"
    if not path.exists():
        raise FcmError(f"missing {path}")
    from .config import resolve_env
    return resolve_env(json.loads(path.read_text()))


def classify(text: str, subject: str = "") -> dict[str, str]:
    """Rules, in order. An opt-out or a complaint beats any sign of interest, so nobody who said stop gets another word."""
    body = text or ""
    if _BOUNCE.search(f"{subject} {body}"):
        return {"intent": "bounce", "why": "a delivery failure"}
    if _OPT_OUT.search(body):
        return {"intent": "opt_out", "why": "they asked to stop"}
    if _COMPLAINT.search(body):
        return {"intent": "complaint", "why": "reads as a complaint"}
    if _AUTO.search(f"{subject} {body}"):
        return {"intent": "auto_reply", "why": "an automatic reply"}
    if _IDENTITY.search(body):
        return {"intent": "identity", "why": "they asked who or what is writing"}
    if _SOURCE.search(body):
        return {"intent": "source", "why": "they asked how we got their address"}
    if _SEND_IT.search(body):
        return {"intent": "newsletter_yes", "why": "they said yes to the monthly note"}
    if _WRONG.search(body):
        return {"intent": "wrong_person", "why": "not the right person"}
    need = _NEED.search(body) or _BARE_AMOUNT.search(body)
    if _NO.search(body):
        if re.search(r"\bbut\b", body, re.I) and need:
            return {"intent": "interested", "why": "said no to one thing and asked for another"}
        return {"intent": "not_interested", "why": "said no"}
    if _BARE_AMOUNT.search(body):  # "Truck, $80k, next month" is the reply we asked for, not a brush-off
        return {"intent": "interested", "why": "they gave an amount"}
    if _LATER.search(body):
        return {"intent": "not_now", "why": "not yet"}
    if need:
        return {"intent": "interested", "why": f"they said \"{need.group(0).strip()}\""}
    if "?" in body:
        return {"intent": "question", "why": "they asked a question"}
    return {"intent": "unclear", "why": "a person should read this one"}


def details(text: str) -> dict[str, Any]:
    """What they gave us. Their phone and email go on the contact, nowhere else."""
    email = leads._EMAIL.search(text or "")
    phone = leads._PHONE.search(text or "")
    state = leads._STATE.search(text or "")
    return {"email": email.group(0).lower() if email else "", "phone": phone.group(0) if phone else "",
            "amount": leads._amount(text or "") or _bare_amount(text or ""), "state": state.group(1) if state else "",
            "ok_hint": bool(_OK_HINT.search(text or ""))}


def _bare_amount(text: str) -> float | None:
    hit = re.search(r"\b(\d[\d,]*(?:\.\d+)?)\s?(k|m|thousand|million)\b", text, re.I)
    if not hit:
        return None
    return float(hit.group(1).replace(",", "")) * {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}[hit.group(2).lower()]


def map_row(cfg: dict[str, Any], text: str) -> dict[str, str] | None:
    """The row of the funding map that fits what they said, first match wins. The hub's words pick a partner; these pick what
    we'd tell an owner to look at first, so the two can differ."""
    low = (text or "").lower()
    for row in cfg["map_rows"]:
        if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", low) for w in row["words"]):
            return row
    return None


def check(text: str) -> list[str]:
    """What's wrong with a message to a lead, or [] when it's clean."""
    low = (text or "").lower()
    words = set(_WORDS.findall(low))
    hits = [p for p in (*BANNED_PHRASES, *NEVER_SAY) if (p in words if " " not in p and "-" not in p and "'" not in p else p in low)]
    if _RATE.search(low):
        hits.append("a specific rate")
    return sorted(set(hits))


class Book:
    """What's been handled, the drafts, and who must never hear from us again. In leads.sqlite3 on the agent's box."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sales_replies (reply_id TEXT PRIMARY KEY, contact_id TEXT, intent TEXT, at TEXT, source TEXT,
                eaccount TEXT, subject TEXT);
            CREATE TABLE IF NOT EXISTS sales_drafts (id TEXT PRIMARY KEY, contact_id TEXT, reply_id TEXT, source TEXT, eaccount TEXT,
                subject TEXT, body TEXT, state TEXT, at TEXT, sent_by TEXT, kind TEXT);
            CREATE TABLE IF NOT EXISTS suppressions (email TEXT PRIMARY KEY, why TEXT, at TEXT, synced INTEGER DEFAULT 0);""")

    def seen(self, reply_id: str) -> bool:
        return bool(self.conn.execute("SELECT 1 FROM sales_replies WHERE reply_id=?", (reply_id,)).fetchone())

    def mark(self, reply_id: str, contact_id: str, intent: str, now: datetime, reply: dict[str, Any] | None = None) -> None:
        reply = reply or {}
        self.conn.execute("INSERT OR REPLACE INTO sales_replies VALUES (?,?,?,?,?,?,?)",
                          (reply_id, contact_id, intent, now.isoformat(), str(reply.get("source") or ""),
                           str(reply.get("eaccount") or ""), str(reply.get("subject") or "")))
        self.conn.commit()

    def last_reply(self, contact_id: str) -> dict[str, Any]:
        """Their latest reply, so an answer stays in the thread it answers."""
        row = self.conn.execute("SELECT * FROM sales_replies WHERE contact_id=? ORDER BY at DESC, rowid DESC LIMIT 1", (contact_id,)).fetchone()
        return dict(row) if row else {}

    def suppress(self, email: str, why: str, now: datetime) -> None:
        self.conn.execute("INSERT OR IGNORE INTO suppressions (email, why, at) VALUES (?,?,?)", (email.lower(), why, now.isoformat()))
        self.conn.commit()

    def suppressed(self, email: str) -> bool:
        return bool(self.conn.execute("SELECT 1 FROM suppressions WHERE email=?", (email.lower(),)).fetchone())

    def unsynced(self) -> list[str]:
        return [r["email"] for r in self.conn.execute("SELECT email FROM suppressions WHERE synced=0")]

    def synced(self, email: str) -> None:
        self.conn.execute("UPDATE suppressions SET synced=1 WHERE email=?", (email.lower(),))
        self.conn.commit()

    def add_draft(self, contact_id: str, reply: dict[str, Any], subject: str, body: str, now: datetime, kind: str = "") -> str:
        draft_id = "dr-" + hashlib.sha256(f"{contact_id}|{reply.get('id')}|{body}".encode()).hexdigest()[:12]
        self.conn.execute("INSERT OR REPLACE INTO sales_drafts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (draft_id, contact_id, str(reply.get("id") or ""), str(reply.get("source") or ""),
                           str(reply.get("eaccount") or ""), subject, body, "held", now.isoformat(), "", kind))
        self.conn.commit()
        return draft_id

    def draft(self, draft_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM sales_drafts WHERE id=?", (draft_id,)).fetchone()
        if not row:
            raise FcmError(f"no draft {draft_id}")
        return dict(row)

    def drafts(self, state: str = "held") -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM sales_drafts WHERE state=? ORDER BY at", (state,))]

    def set_draft(self, draft_id: str, state: str, by: str = "") -> None:
        self.conn.execute("UPDATE sales_drafts SET state=?, sent_by=? WHERE id=?", (state, by, draft_id))
        self.conn.commit()


def book(engine: Any) -> Book:
    return Book(Path(engine.settings.state_dir) / "leads.sqlite3")


def _home_only(engine: Any, cfg: dict[str, Any]) -> None:
    from .config import unresolved
    from .ghl import LiveGHL
    location = str(getattr(engine.ghl, "location_id", "") or "")
    if location == cfg["never_location"]:
        raise FcmError("this agent never writes to that account; point GHL_LOCATION_ID at the home CRM")
    if isinstance(engine.ghl, LiveGHL):
        # Fail closed on a live CRM: both ids must be set at intake, and the location must be the home one.
        if unresolved(cfg.get("never_location")) or unresolved(cfg.get("home_location")) or not cfg.get("home_location"):
            raise FcmError("PINNACLE_GHL_LOCATION_ID and FM_GHL_LOCATION_ID must be set (intake) before a live write")
        if location != cfg["home_location"]:
            raise FcmError("this agent writes only to the home CRM; point GHL_LOCATION_ID at it")


def find_contact(engine: Any, email: str) -> dict[str, Any] | None:
    for row in engine.ghl.search_contacts(query=email, limit=10):
        if str(row.get("email") or "").strip().lower() == email.lower():
            return row
    return None


def _first(reply: dict[str, Any], contact: dict[str, Any] | None) -> str:
    name = str((contact or {}).get("firstName") or reply.get("first_name") or "").strip()
    return name.split()[0].title() if name else "there"


def plan_stage(cfg: dict[str, Any], pipeline: str, current: str, target: str) -> dict[str, Any]:
    """Pure. {move: bool, why}. Refuses anything past the agent's line; forward only."""
    stages = cfg["pipelines"].get(pipeline)
    if not stages:
        raise FcmError(f"{pipeline!r} isn't a lead pipeline this agent moves")
    if target in cfg["never_stages"]:
        raise FcmError(f"{target} isn't the agent's to set")
    if target not in stages:
        raise FcmError(f"{pipeline} has no stage {target!r}")
    stop = cfg["agent_stops_at"].get(pipeline)
    if stop and stages.index(target) > stages.index(stop):
        raise FcmError(f"the agent stops at {stop} on {pipeline}")
    if current and current in stages and stages.index(target) <= stages.index(current):
        return {"move": False, "why": f"already at {current}: stages only go forward"}
    return {"move": True, "why": f"{current or 'not on this pipeline'} to {target}"}


def move_stage(engine: Any, contact_id: str, pipeline: str, target: str, why: str, apply: bool = False,
               cfg: dict[str, Any] | None = None, name: str = "") -> dict[str, Any]:
    cfg = cfg or config(engine.settings)
    _home_only(engine, cfg)
    if not why.strip():
        raise FcmError("give one line of why")
    pipe = next((p for p in engine.ghl.list_pipelines() if p.get("name") == pipeline), None)
    if not pipe:
        raise FcmError(f"{pipeline} isn't built in this account")
    renamed = cfg.get("stage_renames") or {}  # a stage GHL still shows under its old name is the same stage
    stage_ids = {renamed.get(s["name"], s["name"]): s["id"] for s in pipe.get("stages") or []}
    if target not in stage_ids:
        plan_stage(cfg, pipeline, "", target)
        raise FcmError(f"{target} isn't built on {pipeline} in this account")
    rows = engine.ghl.search_opportunities(pipeline_id=pipe["id"], contact_id=contact_id)
    names = {v: k for k, v in stage_ids.items()}
    current = names.get(rows[0].get("pipelineStageId"), "") if rows else ""
    plan = plan_stage(cfg, pipeline, current, target)
    out = {"contact_id": contact_id, "pipeline": pipeline, "from": current, "to": target, "apply": apply, **plan}
    if not plan["move"] or not apply:
        return out
    engine.ghl.upsert_opportunity(pipeline_id=pipe["id"], stage_id=stage_ids[target], contact_id=contact_id,
                                  name=(rows[0].get("name") if rows else "") or name or contact_id)
    engine.ghl.add_note(contact_id, f"Stage: {plan['why']}. {why.strip()}")
    if tag := cfg["tag_on_stage"].get(target):
        engine.ghl.add_tags(contact_id, [tag])
    return out


def _ensure_contact(engine: Any, reply: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    found = find_contact(engine, reply["email"])
    if found:
        return found
    return engine.ghl.create_contact({"email": reply["email"], "firstName": reply.get("first_name") or "",
                                      "lastName": reply.get("last_name") or "", "companyName": reply.get("company") or "",
                                      "source": "Intent email campaign", "tags": [cfg["lead_tag"], "intent-lead"]})


def _draft(engine: Any, cfg: dict[str, Any], key: str, reply: dict[str, Any], contact_id: str, first: str, now: datetime,
           log: Book, row: dict[str, str] | None = None) -> str:
    template = cfg["drafts"][key]
    subject = re.sub(r"^(?:re:\s*)+", "", str(reply.get("subject") or "your note"), flags=re.I)
    follow = (now + timedelta(days=cfg["not_now_days"])).strftime("%B")
    row = row or {}
    second = f"Second look: {row['second']}\n" if row.get("second") else ""
    values = {"name": "" if first == "there" else f", {first}", "subject": subject, "follow_up": follow,
              "first_look": row.get("first", ""), "second_look": second, "skip": row.get("skip", "")}
    body = template["body"].format(**values) + cfg["signature"]
    if problems := check(body):
        raise FcmError(f"a draft crossed a line: {problems}")
    return log.add_draft(contact_id, reply, template["subject"].format(**values), body, now, kind=key)


def triage(engine: Any, reply: dict[str, Any], apply: bool = False, now: datetime | None = None,
           cfg: dict[str, Any] | None = None, log: Book | None = None) -> dict[str, Any]:
    """Sort one reply and do what it calls for. A reply handled once is never handled twice."""
    cfg = cfg or config(engine.settings)
    _home_only(engine, cfg)
    log = log or book(engine)
    now = now or datetime.now(timezone.utc)
    email = str(reply.get("email") or "").strip().lower()
    if not email:
        raise FcmError("a reply with no sender address")
    reply_id = str(reply.get("id") or hashlib.sha256(f"{email}|{reply.get('at')}|{reply.get('text')}".encode()).hexdigest()[:24])
    sorted_as = classify(str(reply.get("text") or ""), str(reply.get("subject") or ""))
    intent = sorted_as["intent"]
    out: dict[str, Any] = {"reply": reply_id, "intent": intent, "why": sorted_as["why"], "apply": apply, "stage": "", "draft": "",
                           "flag": ""}
    if log.seen(reply_id):
        return {**out, "skipped": "already handled"}
    t = cfg["tags"]
    if intent in {"opt_out", "complaint", "bounce"}:
        out["stage"] = "suppressed"
        if not apply:
            return out
        log.suppress(email, intent, now)
        contact = find_contact(engine, email)  # someone who said stop is never added to a CRM just to record it
        if contact:
            engine.ghl.add_tags(contact["id"], [t["bounced"] if intent == "bounce" else t["opted_out"], t["dnc"]])
            engine.ghl.add_note(contact["id"], f"Suppressed: {sorted_as['why']}.")
        if intent == "complaint":
            out["flag"] = "complaint: Justin should read it"
            if contact:
                _task(engine, contact["id"], "Complaint on the campaign: read this one", now)
        log.mark(reply_id, (contact or {}).get("id", ""), intent, now, reply)
        return out
    if intent == "auto_reply":
        if apply:
            log.mark(reply_id, "", intent, now, reply)
        return out
    if not apply:
        out["stage"] = cfg["stage_by_intent"].get(intent, "")
        return out
    contact = _ensure_contact(engine, reply, cfg)
    cid = contact["id"]
    first = _first(reply, contact)
    text = str(reply.get("text") or "")
    engine.ghl.add_note(cid, f"{EMAIL_REPLY} {str(reply.get('subject') or '')[:120]}\n{leads.scrub(text)[:4000]}")
    tags = [t["replied"], cfg["lead_tag"]]
    if t["replied"] in (contact.get("tags") or []):
        tags.append(t["replied_again"])  # stops a running workflow: they're talking to us now
    if intent == "not_now":
        tags.append(t["not_now"])
    elif intent == "wrong_person":
        tags.append(t["wrong_person"])
    elif intent == "identity":
        tags.append(t["needs_justin"])
    elif intent == "newsletter_yes":
        tags.append(t["newsletter"])
    if sequence := cfg["sequence_by_intent"].get(intent):
        tags.append(sequence)  # a Draft workflow does nothing with it; once Justin publishes, this is what starts it
    engine.ghl.add_tags(cid, tags)
    got = details(text)
    fields = {k: v for k, v in (("phone", got["phone"]),) if v and not contact.get(k)}
    if fields:
        engine.ghl.update_contact(cid, fields)
    if intent in {"not_interested", "wrong_person"}:
        log.suppress(email, intent, now)  # they told us. No later campaign writes to this address again
    target = cfg["stage_by_intent"].get(intent)
    if target:
        out["stage"] = move_stage(engine, cid, cfg["campaign_pipeline"], target, f"Campaign reply: {sorted_as['why']}.", apply=True,
                                  cfg=cfg, name=str(contact.get("contactName") or first))["to"]
    if intent in {"interested", "not_now", "source"}:
        row = map_row(cfg, text) if intent == "interested" else None
        key = "map" if row else intent
        out["draft"] = _draft(engine, cfg, key, reply, cid, first, now, log, row=row)
        out["draft_kind"] = key
        _task(engine, cid, "Read the draft reply and send it the same day, or edit it", now, f"Draft {out['draft']}. Nothing has gone out.")
    elif intent == "question":
        out["flag"] = "answer what they asked, with fcm_reply_draft"
        _task(engine, cid, "Campaign reply: answer their question, then ask one thing", now)
    elif intent in {"identity", "unclear"}:
        out["flag"] = "a person should answer this one"
        _task(engine, cid, f"Campaign reply needs a person: {sorted_as['why']}", now)
    log.mark(reply_id, cid, intent, now, reply)
    engine.vault.log("Campaign reply", f"{cid}: {intent}")
    out["contact_id"] = cid
    out["ok_hint"] = got["ok_hint"]
    return out


def _task(engine: Any, contact_id: str, title: str, now: datetime, body: str = "") -> None:
    manager = str(engine.settings.ghl_map.get("users", {}).get("manager", ""))
    engine.ghl.create_task(contact_id, title, (now + timedelta(days=1)).date().isoformat(), body or title, assigned_to=manager)


def ghl_replies(engine: Any, cfg: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    """Replies to the CRM's own emails, from people who came through a campaign. A stop sent to a nurture email counts too."""
    out = []
    for row in engine.reply_inbox(limit):
        contact_id = str((row.get("contact") or {}).get("id") or "")
        try:
            contact = engine.ghl.get_contact(contact_id)
        except FcmError:
            continue
        if cfg["lead_tag"] not in (contact.get("tags") or []) or row.get("channel") != "email" or not contact.get("email"):
            continue
        out.append({"id": (row.get("message_ids") or [""])[0], "email": str(contact["email"]).lower(), "subject": row.get("subject") or "",
                    "text": row.get("last_message") or "", "source": "ghl", "first_name": contact.get("firstName") or ""})
    return out


def triage_inbox(engine: Any, apply: bool = False, limit: int = 50, source: Any = None, now: datetime | None = None) -> dict[str, Any]:
    """Every new reply on our campaigns and on the CRM's emails to those people. One failure never stops the rest."""
    cfg = config(engine.settings)
    log = book(engine)
    if source is None and instantly.configured():
        source = instantly.Instantly()
    replies = source.replies(limit) if source else []
    try:
        replies += ghl_replies(engine, cfg, limit)
    except (FcmError, KeyError, OSError):
        pass  # the sender's replies still get worked
    report: dict[str, Any] = {"apply": apply, "read": 0, "by_intent": {}, "drafts": 0, "flags": 0, "failed": 0, "skipped": 0}
    if not source:
        report["sender"] = "off: INSTANTLY_API_KEY and FCM_INSTANTLY_CAMPAIGNS aren't set"
    for reply in replies:
        report["read"] += 1
        try:
            got = triage(engine, reply, apply=apply, now=now, cfg=cfg, log=log)
        except (FcmError, KeyError, OSError):
            report["failed"] += 1
            continue
        if got.get("skipped"):
            report["skipped"] += 1
            continue
        report["by_intent"][got["intent"]] = report["by_intent"].get(got["intent"], 0) + 1
        report["drafts"] += bool(got["draft"])
        report["flags"] += bool(got["flag"])
    report["suppressions_to_sync"] = len(log.unsynced())
    return report


def inbound_text(engine: Any, contact_id: str) -> str:
    notes = [str(n.get("body") or "") for n in engine.ghl.list_notes(contact_id)]
    return " ".join(n.split("\n", 1)[-1] for n in notes if n.startswith(EMAIL_REPLY))


def mark_ok(engine: Any, contact_id: str, quote: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Their OK for a partner. The quote must be words they wrote in a reply we hold, so it can't be made up."""
    cfg = cfg or config(engine.settings)
    _home_only(engine, cfg)
    said = " ".join(inbound_text(engine, contact_id).lower().split())
    words = " ".join((quote or "").lower().split())
    if len(words) < 3 or words not in said:
        raise FcmError("that quote isn't in anything they wrote; their OK has to be their own words")
    consent = leads.config(engine.settings)["tags"]["consent"]
    engine.ghl.add_note(contact_id, f"{leads.PARTNER_OK} {leads.scrub(quote.strip())[:300]}")
    engine.ghl.add_tags(contact_id, [consent])
    return {"ok": True, "contact_id": contact_id, "tag": consent}


def save_draft(engine: Any, contact_id: str, subject: str, body: str, kind: str = "", now: datetime | None = None) -> dict[str, Any]:
    """The agent's own wording for an answer, in the thread they wrote in. Held like any other draft. kind="map" when it's the
    funding map, so sending it starts nurture."""
    if problems := check(f"{subject}\n{body}"):
        raise FcmError(f"this crosses a line: {problems}")
    if not body.strip():
        raise FcmError("an empty draft")
    log = book(engine)
    last = log.last_reply(contact_id)
    thread = {"id": last.get("reply_id", ""), "source": last.get("source") or "ghl", "eaccount": last.get("eaccount", "")}
    draft_id = log.add_draft(contact_id, thread, subject, body.strip(), now or datetime.now(timezone.utc), kind=kind)
    return {"ok": True, "draft": draft_id, "state": "held"}


def replies_on() -> bool:
    return os.getenv("FCM_SEND_REPLIES") == "1"


def send_draft(engine: Any, draft_id: str, approver: str, source: Any = None) -> dict[str, Any]:
    """A person's yes on one draft. Refuses while the switch is off, and refuses anyone suppressed."""
    if not approver.strip():
        raise FcmError("name the person approving this")
    log = book(engine)
    d = log.draft(draft_id)
    if d["state"] != "held":
        raise FcmError(f"{draft_id} is {d['state']}")
    if not replies_on():
        return {"state": "held", "draft": draft_id, "why": "FCM_SEND_REPLIES is off"}
    if problems := check(f"{d['subject']}\n{d['body']}"):
        raise FcmError(f"this crosses a line: {problems}")
    contact = engine.ghl.get_contact(d["contact_id"])
    email = str(contact.get("email") or "")
    tags = {str(t).lower() for t in contact.get("tags") or []}
    if log.suppressed(email) or config(engine.settings)["tags"]["dnc"] in tags:
        log.set_draft(draft_id, "cancelled", approver)
        raise FcmError("this person asked us to stop")
    if d["source"] == "instantly":
        (source or instantly.Instantly()).send_reply(d["reply_id"], d["eaccount"], d["subject"], d["body"])
    else:  # through the engine, so its checks and the send guard apply
        action = engine.prepare_messages([{"contact_id": d["contact_id"], "channel": "email", "subject": d["subject"],
                                           "body": d["body"], "kind": "reply"}], "campaign reply")
        got = engine.execute(action["action_id"])
        if not (got.get("live") or got.get("mock") or got.get("simulated")):
            raise FcmError(f"not sent: {got.get('stopped') or got.get('state')}")
    engine.store.audit(actor=approver, action="reply.send", resource=d["contact_id"], decision="human", result="ok",
                       details={"draft": draft_id, "source": d["source"]})
    log.set_draft(draft_id, "sent", approver)
    if tag := config(engine.settings)["sequence_on_send"].get(d.get("kind") or ""):
        engine.ghl.add_tags(d["contact_id"], [tag])  # nurture starts after they have their answer, never before it
    return {"state": "sent", "draft": draft_id}


def sync_on() -> bool:
    return os.getenv("FCM_SYNC_OPT_OUTS") == "1"


def sync_suppressions(engine: Any, source: Any = None) -> dict[str, Any]:
    """Tell the sender who must never hear from us. It has its own switch, on before the first cold send, so an opt-out never
    waits on the switch for answers."""
    log = book(engine)
    waiting = log.unsynced()
    if not sync_on():
        return {"state": "held", "waiting": len(waiting)}
    source = source or instantly.Instantly()
    for email in waiting:
        source.block(email)
        log.synced(email)
    return {"state": "synced", "synced": len(waiting)}
