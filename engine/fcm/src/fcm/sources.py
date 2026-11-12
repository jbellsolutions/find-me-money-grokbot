"""Build each partner's profile before the first message, from wherever their history lives.

Sources share one shape (`SourceRecord`: the partner, their record fields, and dated history items):
  * csv          any export: one partners file, plus an optional history file (date, kind, text).
  * ghl_history  partners already in GoHighLevel: their notes and past messages.

`import_records()` upserts each partner into GoHighLevel (tier, plan, dates, deals, source, niche), tags
the quiet ones `fcm:kickoff-pending`, and builds the profile: plain fields go in without any model; one
extraction pass reads the history (only when there is history); every history item lands in the
partner's timeline with its date and source.
"""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator

from . import cadence
from .cadence import KICKOFF_DONE, KICKOFF_PENDING, KICKOFF_SENT
from .errors import FcmError

RECORD_FIELDS = ("tier", "plan", "join_date", "source", "niche", "deals_submitted", "last_deal_date",
                 "assigned_manager", "affiliate_id", "audience_size", "preferred_channel")


@dataclass
class SourceRecord:
    source: str
    external_id: str
    first_name: str
    last_name: str = ""
    email: str = ""
    phone: str = ""
    fields: dict[str, Any] = field(default_factory=dict)  # RECORD_FIELDS plus last_contact_date
    history: list[dict[str, str]] = field(default_factory=list)  # id, date, kind, text
    dnc: bool = False  # do not contact at all
    no_email: bool = False  # opted out of email only (the old CRM Email_Opt_Out); texting is still allowed


def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")[-10:]


def _tier(value: Any) -> str:
    text = str(value or "").strip()
    return next((t for t in cadence.TIERS if t.lower() == text.lower()), text)


# ── CSV ──────────────────────────────────────────────────────────────────────
class CsvSource:
    """partners.csv: external_id, first_name, last_name, email, phone, tier, plan, join_date, source, niche,
    deals_submitted, last_deal_date, last_contact_date, assigned_manager, dnc, no_email.
    history.csv (optional): external_id or email, date, kind, text."""

    name = "csv"

    def __init__(self, partners: Path, history: Path | None = None):
        self.partners, self.history = partners, history

    def records(self) -> Iterator[SourceRecord]:
        events: dict[str, list[dict[str, str]]] = {}
        if self.history and self.history.exists():
            with self.history.open(newline="") as handle:
                for i, row in enumerate(csv.DictReader(handle)):
                    key = (row.get("external_id") or row.get("email") or "").strip().lower()
                    events.setdefault(key, []).append({"id": f"h{i}", "date": (row.get("date") or "")[:10],
                                                       "kind": row.get("kind") or "note", "text": row.get("text") or ""})
        with self.partners.open(newline="") as handle:
            for row in csv.DictReader(handle):
                ext = (row.get("external_id") or row.get("email") or "").strip()
                fields = {k: row[k].strip() for k in (*RECORD_FIELDS, "last_contact_date") if (row.get(k) or "").strip()}
                yield SourceRecord("csv", ext, (row.get("first_name") or "").strip(), (row.get("last_name") or "").strip(),
                                   (row.get("email") or "").strip(), (row.get("phone") or "").strip(), fields,
                                   events.get(ext.lower(), []) + events.get((row.get("email") or "").strip().lower(), []),
                                   str(row.get("dnc") or "").strip().lower() in {"1", "true", "yes"},
                                   str(row.get("no_email") or "").strip().lower() in {"1", "true", "yes"})


# ── GoHighLevel history ──────────────────────────────────────────────────────
class GhlHistorySource:
    """Partners already in GoHighLevel: build their profile from notes and past messages."""

    name = "ghl_history"

    def __init__(self, engine: Any, contact_ids: list[str] | None = None):
        self.engine, self.contact_ids = engine, contact_ids

    def records(self) -> Iterator[SourceRecord]:
        affs = ([self.engine.affiliate(c) for c in self.contact_ids] if self.contact_ids
                else self.engine.affiliates())
        for aff in affs:
            history = [{"id": n.get("id", ""), "date": str(n.get("dateAdded") or "")[:10], "kind": "ghl_note",
                        "text": n.get("body", "")} for n in self.engine.ghl.list_notes(aff.id)
                       if not str(n.get("body", "")).startswith(("[SIMULATED", "Reply (", "Follow-up scheduled",
                                                                  "Task for the manager"))]
            for conv in self.engine.ghl.list_conversations(contact_id=aff.id, limit=3):
                for m in self.engine.ghl.list_messages(conv["id"], limit=20):
                    if m.get("direction") == "inbound" and (m.get("body") or "").strip():
                        history.append({"id": str(m.get("id", "")), "date": str(m.get("dateAdded") or "")[:10],
                                        "kind": "ghl_message", "text": m["body"]})
            yield SourceRecord("ghl_history", aff.id, aff.first_name, "", aff.email, aff.phone, {}, history,
                               aff.is_dnc)



# ── import ───────────────────────────────────────────────────────────────────
def _find_contact(engine: Any, rec: SourceRecord) -> dict[str, Any] | None:
    if rec.source == "ghl_history":
        return {"id": rec.external_id}
    for key in ("email", "phone"):
        value = getattr(rec, key)
        if not value:
            continue
        for c in engine.ghl.search_contacts(query=value, limit=5):
            if (key == "email" and (c.get("email") or "").lower() == value.lower()) or \
                    (key == "phone" and _digits(c.get("phone", "")) == _digits(value)):
                return c
    return None


def import_records(engine: Any, records: Any, *, mark_kickoff: bool = True, limit: int = 0) -> dict[str, Any]:
    """Upsert partners into GoHighLevel and build each profile. Returns counts and the kickoff queue size."""
    settings, today = engine.settings, engine.today()
    field_ids = settings.field_ids()
    taxonomy = json.loads((settings.config_dir / "tag-taxonomy.json").read_text())
    known_sources = {t[4:] for t in taxonomy.get("source", [])}
    report = {"records": 0, "created": 0, "updated": 0, "kickoff_pending": 0, "with_history": 0, "facts": 0}
    kicked_off = engine.kicked_off_ids()
    for rec in records:
        if limit and report["records"] >= limit:
            break
        report["records"] += 1
        fields = {k: v for k, v in rec.fields.items() if k in RECORD_FIELDS}
        if fields.get("tier"):
            fields["tier"] = _tier(fields["tier"])
        if rec.fields.get("last_contact_date"):
            fields["last_reply_date"] = str(rec.fields["last_contact_date"])[:10]
        tags = []
        if fields.get("source") in known_sources:
            tags.append(f"src:{fields['source']}")
        if fields.get("tier"):
            tags.append(f"tier:{str(fields['tier']).lower()}")
        payload_fields = [{"id": field_ids[k], "field_value": v} for k, v in fields.items() if k in field_ids]
        found = _find_contact(engine, rec)
        if found:
            if payload_fields:
                engine.ghl.update_contact(found["id"], {"customFields": payload_fields})
            if tags:
                engine.ghl.add_tags(found["id"], tags)
            contact_id = found["id"]
            report["updated"] += 1
        else:
            contact_id = engine.ghl.create_contact({"firstName": rec.first_name, "lastName": rec.last_name,
                                                    "email": rec.email, "phone": rec.phone, "tags": tags,
                                                    "customFields": payload_fields})["id"]
            report["created"] += 1
        if rec.dnc:
            engine.ghl.add_tags(contact_id, [cadence.DNC_TAG])
            engine.ghl.update_contact(contact_id, {"dnd": True})
        elif rec.no_email:  # an email opt-out blocks email only; it never sets DND, which would also stop texts
            engine.ghl.add_tags(contact_id, [cadence.NO_EMAIL_TAG])
        aff = engine.affiliate(contact_id)
        lifecycle, silent = cadence.target_lifecycle(aff, today, settings.cadence)
        quiet = silent is None or silent >= int(settings.cadence["quiet_after_days"])
        if (mark_kickoff and quiet and not aff.is_dnc and not aff.is_test_contact and aff.id not in kicked_off
                and not {KICKOFF_PENDING, KICKOFF_SENT, KICKOFF_DONE} & set(aff.tags)):
            engine.ghl.add_tags(contact_id, [KICKOFF_PENDING])
            aff = engine.affiliate(contact_id)
            report["kickoff_pending"] += 1
        facts: list[dict[str, str]] = [{"slot": k, "value": str(fields[k]), "source_type": rec.source,
                                        "observed_on": today.isoformat()} for k in ("tier", "niche") if fields.get(k)]
        history = sorted((h for h in rec.history if (h.get("text") or "").strip()), key=lambda h: h.get("date") or "")
        if history:
            report["with_history"] += 1
            text = "\n".join(f"{h.get('date', '')} ({h.get('kind', 'note')}): {h['text']}" for h in history)
            found_facts = engine.extractor.extract_text(text[:12000], {"name": aff.name})["facts"]
            last = history[-1].get("date") or today.isoformat()
            facts += [{**f, "source_type": f"{rec.source}_history" if rec.source != "ghl_history" else "ghl_note",
                       "source_ref": rec.external_id, "observed_on": last} for f in found_facts]
        interactions = [{"kind": "history", "at": h.get("date") or today.isoformat(),
                         "ref": f"{rec.source}:{rec.external_id}:{h.get('id') or i}",
                         "summary": f"{h.get('kind', 'note').replace('_', ' ')}: {h['text'][:240]}"}
                        for i, h in enumerate(history)]
        interactions.append({"kind": "profile_built", "ref": f"{rec.source}:{rec.external_id}:built:{today.isoformat()}",
                             "summary": f"profile built from {rec.source} ({len(history)} history items)"})
        out = engine.remember(aff, facts=facts, source_type=rec.source, source_ref=rec.external_id,
                              interaction=interactions)
        report["facts"] += len(out["facts_added"])
        engine.vault.affiliate(aff.name, aff.id, f"profile built from {rec.source}: {len(history)} history items, "
                               f"{len(out['facts_added'])} facts, {out['profile']['completeness']}% complete",
                               day=today.isoformat())
    engine.vault.log("Profiles built", f"- {report}", day=today.isoformat())
    engine.store.audit(actor=engine.actor, action="profiles.import", resource="partners", decision="autonomous",
                       result="ok", details=report)
    return report

