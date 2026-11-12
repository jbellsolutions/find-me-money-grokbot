"""Every lead's record: the context card, the Obsidian note, and the copy pinned on the GHL contact.

The hub builds the card (`GET /api/crm/contacts/{id}`), so there is one definition of a context card. This module adds
what a person needs to act on it: what's next, whether they're ready for a closer, and whether we hold their OK. Then
it writes the note and pins the copy:

    Leads/<name> (<id6>).md        ## Where they stand   regenerated
                                   ## Context card       regenerated
                                   ## Game plan          the agent's, kept
                                   ## Manager notes      Justin's, kept
                                   ## Timeline           kept

The vault blanks emails, phone numbers and long digit runs: those stay on the GHL contact. Their words can't become
links. A dry run writes nothing anywhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from . import mirror, social
from .errors import FcmError
from .hubapi import Hub, HubError
from .vault import MANAGER_NOTES, MANAGER_PLACEHOLDER, TIMELINE, _section, _slug, frontmatter

STAND, CARD, PLAN = "## Where they stand", "## Context card", "## Game plan"
PLAN_PLACEHOLDER = "_The agent's plan for this person. Kept across refreshes._"
PARTNER_OK = "Partner OK:"
EMAIL_REPLY = "Email reply:"
THEIR_NOTES = ("Reply Agent · Their post", "Reply Agent · They wrote back", EMAIL_REPLY)  # notes that hold their own words
ANSWER_NOTES = ("Reply Agent · They wrote back", EMAIL_REPLY)
NOT_THEIR_WORDS = ("Post:", "Lane ", "Need:")
SOCIAL_TAG = "social:queue"
SKIP_NOTES = (mirror.HEADER, "Reply Agent · Contact card")
BATCH = 150  # about what a cycle clears at GHL's pace; the rest wait for the next sweep
REFRESH = timedelta(hours=24)

_URL = re.compile(r"(?:https?|obsidian)://\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\w-])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\w-])")
_SSN = re.compile(r"(?<![\w-])\d{3}-\d{2}-\d{4}(?![\w-])")
_LONG = re.compile(r"(?<![A-Za-z0-9])\d{9,}(?![A-Za-z0-9])")
_AMOUNT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(k|m|thousand|million)?\b", re.I)
_STATE = re.compile(r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|"
                    r"ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b")


def config(settings: Any) -> dict[str, Any]:
    path = Path(settings.config_dir) / "handoff.json"
    if not path.exists():
        raise FcmError(f"missing {path}")
    return json.loads(path.read_text())


def scrub(text: str) -> str:
    """Blank contact details and long numbers everywhere except inside links, and keep their words from linking."""
    def plain(s: str) -> str:
        s = _EMAIL.sub("[email]", s)
        s = _SSN.sub("[number]", s)
        s = _PHONE.sub("[phone]", s)
        return _LONG.sub("[number]", s)
    out, at = [], 0
    for m in _URL.finditer(text or ""):
        out += [plain(text[at:m.start()]), m.group(0)]
        at = m.end()
    out.append(plain((text or "")[at:]))
    return "".join(out).replace("[[", "[ [").replace("]]", "] ]")


# How the creators lane labels a need on the desk. It's ours: this text reaches partners, in the intro and the summary.
_INTENT_LABEL = re.compile(r"^(?:high|medium|low) intent under [^:]*:\s*", re.I)


def _their_notes(card: dict[str, Any]) -> list[str]:
    """Their words as the Reply Agent or a campaign reply stored them: the note minus its header and our own labels."""
    out = []
    for n in card.get("notes") or []:
        body = str(n.get("body") or "")
        if body.startswith(THEIR_NOTES):
            out.append(" ".join(line for line in body.split("\n")[1:] if not line.startswith(NOT_THEIR_WORDS)))
    return out


def _note_need(card: dict[str, Any]) -> str:
    """The Need: line on the Reply Agent's post note, for a card whose desk row has aged out."""
    for n in card.get("notes") or []:
        for line in str(n.get("body") or "").split("\n"):
            if str(n.get("body") or "").startswith(THEIR_NOTES) and line.startswith("Need:"):
                return line[len("Need:"):].strip()
    return ""


def _inbound(card: dict[str, Any]) -> str:
    """What they said: their post, their answers, and what they typed on a form."""
    parts = []
    for r in card.get("radar") or []:
        parts += [r.get("need", ""), r.get("quote", ""), r.get("text", "")]
    parts += [m.get("body", "") for m in card.get("messages") or [] if m.get("direction") == "inbound"]
    parts += _their_notes(card)
    for d in card.get("hub_deals") or []:
        parts += [str(v) for v in (d.get("intake") or {}).values()]
    return " ".join(p for p in parts if p)


def _ask(card: dict[str, Any]) -> str:
    for r in card.get("radar") or []:
        if r.get("need"):
            return _INTENT_LABEL.sub("", str(r["need"]).strip()).strip()
    if need := _note_need(card):
        return _INTENT_LABEL.sub("", need).strip()
    name = str(card.get("name") or "")
    if ": " in name:
        return name.split(": ", 1)[1].strip()
    return "funding"


def _amount(text: str) -> float | None:
    best = None
    for m in _AMOUNT.finditer(text):
        n = float(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").lower()
        n *= {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6}.get(unit, 1)
        best = max(best or 0, n)
    return best


def _lane(card: dict[str, Any], cfg: dict[str, Any]) -> str:
    tags = [str(t).lower() for t in card.get("tags") or []]
    campaigns = " ".join(str(r.get("campaign", "")).lower() for r in card.get("radar") or [])
    if "wholesal" in campaigns:
        return "wholesaler"
    if "gig" in campaigns or any(t.startswith("pocket:gig-") for t in tags):  # the creators sync files gig askers by pocket
        return "gig"
    for t in tags:
        if t.startswith("radar:lane-"):
            return cfg["lane_by_persona"].get(t.removeprefix("radar:lane-"), "business")
    return "business"


def _partner_ok(card: dict[str, Any]) -> tuple[str, str]:
    """(quote, source) of their OK for a partner. A website form's OK comes from the privacy policy; anything else must
    be their own words, in a `Partner OK:` note the Reply Agent wrote. Never inferred here."""
    for n in card.get("notes") or []:
        body = str(n.get("body") or "")
        if body.startswith(PARTNER_OK):
            return body[len(PARTNER_OK):].strip()[:300], str(card.get("source") or "")
    for d in card.get("hub_deals") or []:
        if str(d.get("source", "")).startswith("website:"):
            return "", str(d["source"])
    return "", ""


def assess(card: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """What's true about this lead right now, and what happens next."""
    tags = {str(t).lower() for t in card.get("tags") or []}
    words = _inbound(card)
    low = f" {words.lower()} "
    t = cfg["tags"]
    readiness, why = "unknown", "nothing on the card says yet"
    prep = next((w for w in cfg["prep_words"] if w in low), "")
    ready = next((w for w in cfg["ready_words"] if w in low), "")
    if t["prep"] in tags:
        readiness, why = "prep", "set on the contact"
    elif t["ready"] in tags:
        readiness, why = "ready", "set on the contact"
    elif prep:
        readiness, why = "prep", f"they said \"{prep}\""
    elif ready:
        readiness, why = "ready", f"they mentioned \"{ready}\""
    quote_text, source = _partner_ok(card)
    has_email, has_phone = bool(card.get("email")), bool(card.get("phone"))
    website = source.startswith("website:")
    answered = any(m.get("direction") == "inbound" for m in card.get("messages") or []) or "radar:answered" in tags \
        or any(str(n.get("body") or "").startswith(ANSWER_NOTES) for n in card.get("notes") or [])
    replied = bool(answered or any(r.get("reply_status") == "replied" for r in card.get("radar") or []))
    if t["handling"] in tags:
        nxt = "with a partner"
    elif not replied and not website and not (has_email or has_phone):
        nxt = "needs a first reply"
    elif not (has_email and has_phone):
        nxt = "get their email and phone" if not (has_email or has_phone) else \
            ("get their phone" if has_email else "get their email")
    elif not (quote_text or website):
        nxt = "get their OK for a partner"
    else:
        nxt = "ready to propose"
    state = str(card.get("state") or "").upper()
    if len(state) != 2:
        hit = _STATE.search(words)
        state = hit.group(1) if hit else ""
    return {"lane": _lane(card, cfg), "readiness": readiness, "why": why, "email": has_email, "phone": has_phone,
            "ok_quote": scrub(quote_text), "source": source, "website": website, "next": nxt, "ask": _ask(card),
            "amount": _amount(words), "state": state, "said": scrub(words)[:1500], "socials": social.links(card)}


def card_section(card: dict[str, Any]) -> str:
    """The hub's card as text, minus contact details and minus our own earlier card (or it would nest forever)."""
    out = [f"- Added: {card.get('added') or '?'} · source: {card.get('source') or '?'}",
           f"- Came from: {', '.join(card.get('came_from') or []) or 'no source tag'}"]
    if card.get("company"):
        out.append(f"- Company: {card['company']}")
    if card.get("link"):
        out.append(f"- Their post or page: {card['link']}")
    out += ["", "### Pipeline"]
    out += [f"- {p.get('pipeline')} → {p.get('stage')} ({p.get('status')})" for p in card.get("pipelines") or []] \
        or ["- On no pipeline card."]
    for r in card.get("radar") or []:
        out += ["", f"### The post ({r.get('platform')}, {r.get('tier')} intent, {r.get('campaign')})",
                f"- {r.get('url')} · posted {r.get('posted_at') or '?'}", f"- Needs: {r.get('need')}",
                f"> {r.get('quote') or ''}", "", str(r.get("text") or ""), "",
                f"- Reply: {r.get('reply_status')}" + (f" by {r['by']}" if r.get("by") else "")]
    for d in card.get("hub_deals") or []:
        out += ["", f"### Website deal ({d.get('source')}, {d.get('stage')})"]
        out += [f"- {k}: {v}" for k, v in (d.get("intake") or {}).items()]
    if card.get("fields"):
        out += ["", "### CRM fields"] + [f"- {k}: {v}" for k, v in card["fields"].items()]
    out += ["", "### Conversation"]
    out += [f"- {m.get('at') or '?'} · {m.get('channel')} · {m.get('direction')}: {m.get('body')}"
            for m in card.get("messages") or []] or ["- Nothing yet."]
    notes = [n for n in card.get("notes") or [] if not str(n.get("body") or "").startswith(SKIP_NOTES)]
    out += ["", "### Notes"]
    out += [f"- {n.get('at') or '?'}: {n.get('body')}" for n in notes] or ["- None."]
    return scrub("\n".join(out))


def vault_name() -> str:
    return os.getenv("FCM_VAULT_NAME", "Funding CRM Manager")


def obsidian_link(rel: str) -> str:
    return f"obsidian://open?vault={quote(vault_name())}&file={quote(rel.removesuffix('.md'), safe='')}"


def note_path(vault_dir: Path, name: str, contact_id: str) -> Path:
    """The lead's note, found by id, renamed if their name changed."""
    folder = Path(vault_dir) / "Leads"
    folder.mkdir(parents=True, exist_ok=True)
    want = folder / f"{_slug(name)} ({contact_id[-6:]}).md"
    if want.exists():
        return want
    for old in folder.glob(f"* ({contact_id[-6:]}).md"):
        if f"ghl_contact_id: {contact_id}\n" in old.read_text():
            old.rename(want)
            return want
    return want


def render(card: dict[str, Any], view: dict[str, Any], rel: str, old: str = "") -> str:
    plan = _section(old, PLAN) or PLAN_PLACEHOLDER
    manager = _section(old, MANAGER_NOTES) or MANAGER_PLACEHOLDER
    timeline = _section(old, TIMELINE)
    ok = f"yes: “{view['ok_quote']}”" if view["ok_quote"] else ("yes: website form" if view["website"] else "not yet")
    stand = [f"- **Next:** {view['next']}", f"- Wants: {scrub(view['ask'])}",
             f"- Readiness: {view['readiness']} ({view['why']})", f"- Lane: {view['lane']}",
             f"- State: {view['state'] or 'unknown'}",
             f"- Email on file: {'yes' if view['email'] else 'no'} · phone on file: {'yes' if view['phone'] else 'no'}",
             f"- Their OK for a partner: {ok}", f"- CRM: {card.get('crm_url') or ''}", f"- Obsidian: {obsidian_link(rel)}"]
    front = frontmatter({"type": "lead", "ghl_contact_id": card["contact_id"], "readiness": view["readiness"],
                         "lane": view["lane"], "next": view["next"]})
    name = scrub(str(card.get("name") or "Lead")).replace("\n", " ")
    return (f"{front}# {name}\n\n{STAND}\n" + "\n".join(stand) + f"\n\n{CARD}\n{card_section(card)}\n\n{PLAN}\n{plan}\n\n"
            f"{MANAGER_NOTES}\n{manager}\n\n{TIMELINE}\n{timeline}\n")


class Seen:
    """Which contacts were carded when, so a sweep skips the unchanged and works through a large book in batches."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS lead_seen (contact_id TEXT PRIMARY KEY, updated TEXT, at TEXT, "
                          "hash TEXT)")

    def due(self, contact_id: str, updated: str, now: datetime) -> bool:
        row = self.conn.execute("SELECT updated, at FROM lead_seen WHERE contact_id=?", (contact_id,)).fetchone()
        if not row or row[0] != updated:
            return True
        return now - datetime.fromisoformat(row[1]) >= REFRESH

    def mark(self, contact_id: str, updated: str, now: datetime, digest: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO lead_seen VALUES (?,?,?,?)", (contact_id, updated, now.isoformat(), digest))
        self.conn.commit()


def contacts(engine: Any, cfg: dict[str, Any], contact_id: str = "") -> list[dict[str, Any]]:
    """Every contact carrying a lead source tag, once."""
    if contact_id:
        return [engine.ghl.get_contact(contact_id)]
    seen: dict[str, dict[str, Any]] = {}
    for tag in cfg["lead_tags"]:
        page = 1
        while True:
            rows = engine.ghl.search_contacts(tags=[tag], limit=100, page=page)
            for r in rows:
                seen.setdefault(r["id"], r)
            if len(rows) < 100:
                break
            page += 1
    return list(seen.values())


def card_one(engine: Any, contact_id: str, apply: bool = False, hub: Hub | None = None,
             cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    if not contact_id:
        raise FcmError("which contact?")
    hub = hub or Hub()
    cfg = cfg or config(engine.settings)
    card = hub.card(contact_id)
    view = assess(card, cfg)
    vault_dir = Path(engine.settings.vault_dir)
    path = note_path(vault_dir, str(card.get("name") or "Lead"), contact_id) if apply else \
        vault_dir / "Leads" / f"{_slug(str(card.get('name') or 'Lead'))} ({contact_id[-6:]}).md"
    rel = str(path.relative_to(vault_dir))
    old = path.read_text() if path.exists() else ""
    text = render(card, view, rel, old)
    changed = text != old
    if apply:
        if changed:
            path.write_text(text)
        mirror.mirror_one(engine.settings, engine.ghl, contact_id, rel)
        if view["socials"] and social.queue(engine).add(contact_id, view["socials"], engine.now()):
            engine.ghl.add_tags(contact_id, [SOCIAL_TAG])
    return {"contact_id": contact_id, "note": rel, "changed": changed, "created": not old, **view,
            "digest": hashlib.sha256(text.encode()).hexdigest()[:16]}


def set_readiness(engine: Any, contact_id: str, readiness: str, why: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """The agent's or Justin's read, which overrides the word rules. Lands as a tag on the contact."""
    cfg = cfg or config(engine.settings)
    tags = cfg["tags"]
    if readiness not in {"ready", "prep"}:
        raise FcmError("readiness is ready or prep")
    engine.ghl.remove_tags(contact_id, [tags["ready"], tags["prep"]])
    engine.ghl.add_tags(contact_id, [tags[readiness]])
    engine.add_note(contact_id, f"Readiness: {readiness}. {why}")
    return {"ok": True, "contact_id": contact_id, "readiness": readiness}


def sync(engine: Any, apply: bool = False, limit: int = 0, contact_id: str = "", hub: Hub | None = None,
         log: Callable[[str], None] = lambda _l: None, now: datetime | None = None) -> dict[str, Any]:
    """Card the leads that are new or changed. One failure never stops the rest."""
    hub = hub or Hub()
    cfg = config(engine.settings)
    now = now or datetime.now(timezone.utc)
    seen = Seen(Path(engine.settings.state_dir) / "leads.sqlite3")
    rows = contacts(engine, cfg, contact_id)
    due = [r for r in rows if contact_id or seen.due(r["id"], str(r.get("dateUpdated") or ""), now)]
    batch = due[:limit or BATCH]
    report: dict[str, Any] = {"apply": apply, "leads": len(rows), "due": len(due), "worked": len(batch), "created": 0,
                              "updated": 0, "unchanged": 0, "failed": 0, "next": {}, "readiness": {}, "ready_to_propose": []}
    for r in batch:
        cid = r["id"]
        try:
            got = card_one(engine, cid, apply=apply, hub=hub, cfg=cfg)
        except (FcmError, HubError, KeyError, OSError) as exc:
            report["failed"] += 1
            log(f"failed {cid}: {str(exc)[:200]}")
            continue
        report["created" if got["created"] else "updated" if got["changed"] else "unchanged"] += 1
        report["next"][got["next"]] = report["next"].get(got["next"], 0) + 1
        report["readiness"][got["readiness"]] = report["readiness"].get(got["readiness"], 0) + 1
        if got["next"] == "ready to propose":
            report["ready_to_propose"].append(cid)
        if apply:
            seen.mark(cid, str(r.get("dateUpdated") or ""), now, got["digest"])
    return report
