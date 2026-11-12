"""Recorded calls feed the relationship graph, whatever recorded them.

Every recorder's output becomes one `CallTranscript`. Adapters all poll; the agent's server has no
open HTTP port:
  * ghl_phone  calls through our GoHighLevel number. Transcripts come from GoHighLevel's transcription
               endpoint (switch transcription on for the sub-account first); the audio stays in GHL.
  * drop       any transcript file in the call inbox (FCM_CALL_INBOX, default ~/fcm-inbox/calls):
               normalized JSON, a Read.ai-style or Fathom-style JSON export, WebVTT, or "Name: text" lines.
               Whatever records video calls can land here (an export, a sync, a person
               dragging the file), and a vendor API adapter can replace it later without touching
               anything downstream.

Ingest: match the call to a partner (email, then phone, then exact name), pull facts and commitments
(fcm.extract), write a call note linked from the partner note, turn commitments into open loops and
manager tasks, and mark the call as a touch. A call that matches nobody waits in unmatched/ with a
line in the daily note, so a person can link it: `fcm calls ingest --file F --contact ID`.

Recording notice: every recorded call is announced (GoHighLevel's call-recording announcement on the
number; video recorders announce themselves). Florida and other all-party-consent states require it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .errors import FcmError


def _clip(text: str, limit: int) -> str:
    """Shorten at a word boundary so a task title never ends mid-word."""
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0].rstrip(",;") + "…"


@dataclass
class CallTranscript:
    source: str
    external_id: str
    started_at: str
    duration_min: float = 0.0
    participants: list[dict[str, str]] = field(default_factory=list)  # name, email, phone
    segments: list[dict[str, Any]] = field(default_factory=list)  # speaker, start (seconds), text
    summary: str = ""
    action_items: list[str] = field(default_factory=list)
    recording: str = ""
    title: str = ""

    @property
    def day(self) -> str:
        return (self.started_at or date.today().isoformat())[:10]

    def text(self) -> str:
        return "\n".join(f"{s.get('speaker') or 'Speaker'}: {s.get('text', '').strip()}" for s in self.segments)

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ("source", "external_id", "started_at", "duration_min", "participants",
                                              "segments", "summary", "action_items", "recording", "title")}


# ── parsers ──────────────────────────────────────────────────────────────────
def _seconds(stamp: str) -> float:
    parts = [float(x) for x in re.split(r"[:]", stamp.replace(",", "."))]
    total = 0.0
    for part in parts:
        total = total * 60 + part
    return total


def from_json(data: dict[str, Any], source: str = "drop", external_id: str = "") -> CallTranscript:
    """Our normalized shape, or a vendor export with participants and speaker blocks / sentences."""
    parts = data.get("participants") or data.get("attendees") or data.get("invitees") or []
    participants = []
    for p in parts:
        if isinstance(p, str):
            participants.append({"name": p, "email": "", "phone": ""})
        elif isinstance(p, dict):
            participants.append({"name": str(p.get("name") or p.get("display_name") or ""),
                                 "email": str(p.get("email") or ""), "phone": str(p.get("phone") or "")})
    raw = data.get("segments")
    if raw is None:
        tr = data.get("transcript")
        if isinstance(tr, dict):
            raw = tr.get("speaker_blocks") or tr.get("blocks") or tr.get("segments") or []
        elif isinstance(tr, list):
            raw = tr
        elif isinstance(tr, str):
            raw = [{"speaker": m.group(1), "text": m.group(2)}
                   for m in re.finditer(r"^([^:\n]{2,40}):\s*(.+)$", tr, re.M)]
        else:
            raw = []
    segments = []
    for s in raw:
        speaker = s.get("speaker")
        if isinstance(speaker, dict):
            speaker = speaker.get("name", "")
        segments.append({"speaker": str(speaker or s.get("speaker_name") or ""),
                         "start": float(s.get("start") or s.get("start_time") or s.get("startTime") or 0),
                         "text": str(s.get("text") or s.get("words") or s.get("transcript") or "").strip()})
    started = str(data.get("started_at") or data.get("start_time") or data.get("date") or data.get("created_at") or "")
    if started.isdigit():  # epoch millis
        started = datetime.fromtimestamp(int(started) / 1000).isoformat()
    duration = (data.get("duration_min") or data.get("duration_minutes")
                or float(data.get("duration_s") or data.get("duration") or 0) / 60)
    summary = data.get("summary")
    if isinstance(summary, dict):
        summary = summary.get("text") or summary.get("overview") or ""
    items = data.get("action_items") or []
    return CallTranscript(source=str(data.get("source") or source),
                          external_id=str(data.get("external_id") or data.get("id") or data.get("session_id")
                                          or external_id),
                          started_at=started, duration_min=round(float(duration or 0), 1),
                          participants=participants, segments=[s for s in segments if s["text"]],
                          summary=str(summary or ""), recording=str(data.get("recording") or data.get("recording_url")
                                                                    or ""),
                          action_items=[str(i.get("text") if isinstance(i, dict) else i) for i in items],
                          title=str(data.get("title") or ""))


def from_vtt(text: str, external_id: str, started_at: str = "") -> CallTranscript:
    segments, start = [], 0.0
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        stamp = next((ln for ln in lines if "-->" in ln), "")
        if stamp:
            start = _seconds(stamp.split("-->")[0].strip())
        for ln in lines:
            if "-->" in ln or ln.strip().upper() == "WEBVTT" or ln.strip().isdigit():
                continue
            m = re.match(r"<v\s+([^>]+)>(.*?)(?:</v>)?$", ln) or re.match(r"([^:]{2,40}):\s*(.+)$", ln)
            speaker, said = (m.group(1).strip(), m.group(2).strip()) if m else ("", ln.strip())
            if said:
                segments.append({"speaker": speaker, "start": start, "text": said})
    duration = round((segments[-1]["start"] / 60) if segments else 0, 1)
    speakers = sorted({s["speaker"] for s in segments if s["speaker"]})
    return CallTranscript("drop", external_id, started_at, duration,
                          [{"name": n, "email": "", "phone": ""} for n in speakers], segments)


def from_txt(text: str, external_id: str, started_at: str = "") -> CallTranscript:
    head = dict(re.findall(r"^(Date|With|Participants|Email|Phone):\s*(.+)$", text, re.M | re.I))
    head = {k.lower(): v.strip() for k, v in head.items()}
    segments = [{"speaker": m.group(1).strip(), "start": 0.0, "text": m.group(2).strip()}
                for m in re.finditer(r"^(?!Date:|With:|Participants:|Email:|Phone:)([^:\n]{2,40}):\s*(.+)$", text, re.M)]
    names = [n.strip() for n in re.split(r",|;", head.get("participants") or head.get("with") or "") if n.strip()]
    names = names or sorted({s["speaker"] for s in segments})
    participants = [{"name": n, "email": "", "phone": ""} for n in names]
    if participants and (head.get("email") or head.get("phone")):
        participants[-1].update(email=head.get("email", ""), phone=head.get("phone", ""))
    return CallTranscript("drop", external_id, head.get("date", started_at), 0.0, participants, segments)


def parse_file(path: Path) -> CallTranscript:
    text = path.read_text(errors="replace")
    stem = re.sub(r"\W+", "-", path.stem).strip("-")
    stamp = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    if path.suffix.lower() == ".json":
        return from_json(json.loads(text), "drop", external_id=f"file:{stem}")
    if path.suffix.lower() == ".vtt" or text.lstrip().startswith("WEBVTT"):
        return from_vtt(text, f"file:{stem}", stamp)
    return from_txt(text, f"file:{stem}", stamp)


# ── ingest ───────────────────────────────────────────────────────────────────
def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")[-10:]


def match(engine: Any, transcript: CallTranscript, ours: set[str]) -> str:
    """The partner on the call: email, then phone, then an exact name match in the graph."""
    others = [p for p in transcript.participants if p.get("name", "").lower() not in ours]
    for p in others:
        for key in ("email", "phone"):
            value = p.get(key, "")
            if not value:
                continue
            for c in engine.ghl.search_contacts(query=value, limit=5):
                if (key == "email" and (c.get("email") or "").lower() == value.lower()) or \
                        (key == "phone" and _digits(c.get("phone", "")) == _digits(value)):
                    return c["id"]
    for p in others:
        name = p.get("name", "").strip().lower()
        if name:
            hits = [r for r in engine.graph.query(limit=5000) if r["name"].lower() == name]
            if len(hits) == 1:
                return hits[0]["contact_id"]
    return ""


def ingest(engine: Any, transcript: CallTranscript, contact_id: str = "") -> dict[str, Any]:
    kick = engine.settings.kickoff
    managers = {str(kick.get("default_sender", "")).lower()}
    ref = f"{transcript.source}:{transcript.external_id}"
    if engine.graph.has_interaction("call", ref):
        return {"ok": True, "duplicate": True, "ref": ref}
    if not contact_id:
        managers |= {m.lower() for m in _manager_names(engine)}
        contact_id = match(engine, transcript, managers)
    if not contact_id:
        engine.vault.log("Call needs a partner", f"- {transcript.title or ref} ({transcript.day}): no participant "
                         "matched a partner. Link it with `fcm calls ingest --file … --contact …`.",
                         day=engine.today().isoformat())
        return {"ok": False, "unmatched": True, "ref": ref,
                "participants": [p.get("name") for p in transcript.participants]}
    aff = engine.affiliate(contact_id)
    profile = engine.profile_get(contact_id, aff=aff)
    us = sorted({profile["manager"], *(p["name"] for p in transcript.participants
                                        if p.get("name", "").lower() in managers)} - {""})
    found = engine.extractor.extract_call(transcript, profile, us, today=engine.today())
    summary = found.get("summary") or transcript.summary or f"Call with {aff.first_name}"
    day = transcript.day
    loops, tasks = [], []
    for c in found.get("commitments", []):
        who = "We" if c["owner"] == "us" else aff.first_name
        loops.append({"slot": "open_loop", "value": f"{who}: {c['what']} (by {c['due']})"})
        if c["owner"] == "us":
            due = max(c["due"], engine.today().isoformat())
            engine.schedule_followup(contact_id, due, f"From the call on {day}: {c['what']}",
                                     title=f"Follow through for {aff.first_name}: {_clip(c['what'], 90)}",
                                     customer_touch=False)
            tasks.append(c["what"])
    lines = [f"- **{engine.graph.slots.get(slot, {}).get('label', slot)}:** {value}"
             for slot, value in engine.graph.normalize(found.get("facts", []))]
    note = engine.vault.call_note(day, aff.name, {
        "partner": engine.vault.partner_link(aff.name, aff.id), "ghl_contact_id": aff.id, "source": transcript.source,
        "external_id": transcript.external_id, "duration_min": transcript.duration_min,
        "recording": transcript.recording, "participants": ", ".join(p.get("name", "") for p in transcript.participants),
    }, [("Summary", summary), ("What we learned", "\n".join(lines)),
        ("Commitments", "\n".join(f"- [ ] {loop['value']}" for loop in loops)),
        ("Transcript", "\n".join(f"**{s.get('speaker') or 'Speaker'}:** {s['text']}" for s in transcript.segments))])
    link = f"[[Calls/{note.stem}|{transcript.title or 'Call'}]]"
    engine._set_fields(contact_id, {"last_touch_date": day, "last_touch_channel": "call", "last_reply_date": day})
    out = engine.remember(engine.affiliate(contact_id), facts=list(found.get("facts", [])) + loops,
                          source_type="call", source_ref=ref,
                          interaction={"kind": "call", "ref": ref, "summary": f"{link} — {summary[:300]}"})
    engine.ghl.add_note(contact_id, f"Call ({transcript.duration_min} min, {transcript.source}): {summary[:600]}")
    engine.vault.affiliate(aff.name, aff.id, f"call: {link}", day=engine.today().isoformat())
    engine.vault.log("Call ingested", f"- {engine.vault.partner_link(aff.name, aff.id)} — {link}: "
                     f"{len(out['facts_added'])} facts, {len(loops)} commitments", day=engine.today().isoformat())
    engine.store.audit(actor=engine.actor, action="call.ingest", resource=contact_id, decision="autonomous",
                       result="ok", details={"ref": ref, "facts": len(out["facts_added"]), "commitments": len(loops)})
    return {"ok": True, "contact_id": contact_id, "call_note": str(note.relative_to(engine.vault.root)), "summary": summary,
            "facts_added": out["facts_added"], "commitments": found.get("commitments", []), "manager_tasks": tasks,
            "completeness": out["profile"]["completeness"]}


def _manager_names(engine: Any) -> set[str]:
    names = {str(engine.settings.kickoff.get("default_sender", ""))}
    with engine.store.connection() as conn:
        names |= {r["manager"] for r in conn.execute("SELECT DISTINCT manager FROM partners")}
    return {n for n in names if n}


# ── adapters ─────────────────────────────────────────────────────────────────
def inbox_dir() -> Path:
    return Path(os.getenv("FCM_CALL_INBOX", "") or Path.home() / "fcm-inbox" / "calls").expanduser()


def poll_drop(engine: Any, folder: Path | None = None) -> dict[str, Any]:
    folder = folder or inbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".vtt", ".txt"}):
        try:
            out = ingest(engine, parse_file(path))
        except (FcmError, ValueError, KeyError, json.JSONDecodeError) as exc:
            out = {"ok": False, "error": str(exc)}
        dest = folder / ("processed" if out.get("ok") else "unmatched" if out.get("unmatched") else "failed")
        dest.mkdir(exist_ok=True)
        shutil.move(str(path), dest / path.name)
        results.append({"file": path.name, **{k: v for k, v in out.items() if k != "facts_added"}})
    return {"source": "drop", "folder": str(folder), "files": len(results), "results": results}


def poll_ghl(engine: Any, contact_id: str = "", limit: int = 50) -> dict[str, Any]:
    list_calls = getattr(engine.ghl, "list_call_messages", None)
    if list_calls is None:
        raise FcmError("this GoHighLevel backend can't list calls")
    results = []
    for m in list_calls(contact_id=contact_id, limit=limit):
        ref = f"ghl_phone:{m['id']}"
        if engine.graph.has_interaction("call", ref):
            continue
        sentences = engine.ghl.get_transcription(m["id"])
        if not sentences:
            results.append({"message_id": m["id"], "ok": False, "error": "no transcript (is transcription on?)"})
            continue
        aff = engine.affiliate(m["contactId"])
        manager = engine.profile_get(aff.id, aff=aff)["manager"] or "Manager"
        # GoHighLevel splits the audio by channel; channel 1 is the side that placed the call
        ours = 1 if m.get("direction") == "outbound" else 2
        segments = [{"speaker": manager if int(s.get("mediaChannel") or 1) == ours else aff.name,
                     "start": float(s.get("startTime") or 0), "text": str(s.get("transcript") or "")}
                    for s in sorted(sentences, key=lambda s: int(s.get("sentenceIndex") or 0))]
        duration = float((m.get("meta") or {}).get("call", {}).get("duration") or 0) / 60
        transcript = CallTranscript("ghl_phone", m["id"], str(m.get("dateAdded") or ""), round(duration, 1),
                                    [{"name": manager, "email": "", "phone": ""},
                                     {"name": aff.name, "email": aff.email, "phone": aff.phone}],
                                    segments, recording=engine.ghl.recording_ref(m["id"]), title="Phone call")
        out = ingest(engine, transcript, contact_id=aff.id)
        results.append({"message_id": m["id"], **{k: v for k, v in out.items() if k != "facts_added"}})
    return {"source": "ghl_phone", "calls": len(results), "results": results}
