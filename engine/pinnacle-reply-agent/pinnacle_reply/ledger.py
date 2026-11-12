"""The attended ledger: one row per lead, in exactly one state, kept in `$REPLY_STATE/ledger.sqlite`.

    replied   a person posted a reply; we know who and when (Lead Radar replied or won)
    waiting   a draft that passes the checker is assigned to a poster
    held      it can't be answered yet, and the reason is written down
    skipped   not a lead, and the reason is written down
    answered  the person wrote back; the follow-up is the next draft
    unattended  none of the above. The agent's score is unattended = 0

Lead Radar is the source of leads and of what people did (replied, won, skipped). The agent's own work (drafts,
holds, its skips, assignments, chases) lives here, and goes back to the desk only while REPLY_WRITE is on.
No contact details are stored (G5): only whether the lead had a contact card, and emails and phone numbers are
taken out of every text kept.

`messages` is the conversation, append-only: their post, each reply drafted, held or skipped, each reply posted
(by whom, and where), each answer. The vault's Timeline and GHL's notes are both written from it.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import capture, checks, config, lanes
from .sources import DIRECT, LANE_DRAFTS, radar_hub

# partner: a funding partner has the lead (the hub's quiet list); the agent drafts and posts nothing for it
STATES = ("replied", "waiting", "held", "skipped", "answered", "partner", "unattended")
# Every lane Justin asked the agent to cover (charter §3). Each cycle says which ones it could read (sources.py).
LANES = {
    "lead-radar": "Lead Radar funding-web (posts, comment leads, job leads)",
    "real-estate": "Real estate investors (Lead Radar lanes P1 and P2)",
    "creators": "Creators pipeline askers (creators, startup, direct sales)",
    "gig": "Gig-workers askers (in the creators pipeline)",
    "website": "Website and app forms (hosted Lending Hub)",
    "inbound": "Funding Machine GHL inbox (email, texts, calls)",
    "craigslist": "Craigslist replies",
}
RIDES_ON = {"real-estate": "lead-radar", "gig": "creators"}  # lanes that arrive inside another lane's read

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY, source TEXT NOT NULL, campaign TEXT, platform TEXT, kind TEXT, tier TEXT, url TEXT,
  posted_at TEXT, has_contact INTEGER DEFAULT 0, first_seen TEXT NOT NULL, seen_at TEXT NOT NULL,
  radar_status TEXT, radar_by TEXT, replied_at TEXT, radar_draft TEXT,
  persona TEXT, poster TEXT, state TEXT NOT NULL DEFAULT 'unattended', reason TEXT DEFAULT '',
  draft TEXT DEFAULT '', violations TEXT DEFAULT '', drafted_at TEXT, desk_written INTEGER DEFAULT 0,
  local_state TEXT DEFAULT '', answer TEXT DEFAULT '', answered_at TEXT, waiting_since TEXT, last_chased TEXT,
  assigned_to TEXT DEFAULT '', marked_by TEXT DEFAULT '', marked_at TEXT, radar_reason TEXT DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cycles (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL,
  direction TEXT NOT NULL, by TEXT DEFAULT '', text TEXT DEFAULT '', url TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS messages_lead ON messages (lead_id, id);
CREATE TABLE IF NOT EXISTS ghl_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL, op TEXT NOT NULL, key TEXT DEFAULT '',
  payload TEXT NOT NULL, why TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'prepared', receipt TEXT, error TEXT,
  created_at TEXT NOT NULL, sent_at TEXT
);
"""
# What each message kind is. `in` is their words, `out` is a reply that was posted, `internal` is the agent's work.
KINDS = {"post": "in", "answer": "in", "reply": "out", "draft": "internal", "held": "internal", "skipped": "internal",
         "partner": "internal"}

_EMAIL, _PHONE = capture.EMAIL, capture.PHONE  # the same patterns find what capture takes and what scrub removes
CRM_SOURCES = ("lead-radar", "creators")  # the lanes whose leads have a GHL contact (the creators sync makes its own: ghl.attach)


def scrub(text: str | None) -> str:
    """Their words without emails or phone numbers (G5): the vault goes to git and the notes to the CRM."""
    return _PHONE.sub("[phone removed]", _EMAIL.sub("[email removed]", text or "")).strip()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or config.LEDGER_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # An email or number sits in the outbox until it is sent and is then blanked; secure_delete zeroes the old bytes
    # instead of leaving them in the file's free pages.
    conn.execute("PRAGMA secure_delete=ON")
    had_log = conn.execute("SELECT 1 FROM sqlite_master WHERE name='messages'").fetchone() is not None
    conn.executescript(SCHEMA)
    have = {r[1] for r in conn.execute("PRAGMA table_info(leads)")}
    for name, decl in (("assigned_to", "TEXT DEFAULT ''"), ("marked_by", "TEXT DEFAULT ''"), ("marked_at", "TEXT"),
                       ("radar_reason", "TEXT DEFAULT ''"), ("author", "TEXT DEFAULT ''"), ("need", "TEXT DEFAULT ''"),
                       ("ghl_contact_id", "TEXT"), ("ghl_opportunity_id", "TEXT"), ("ghl_have", "TEXT DEFAULT '{}'"),
                       ("hub", "TEXT DEFAULT ''"), ("partner_hold", "INTEGER DEFAULT 0"),
                       ("ghl_looked", "TEXT"), ("ghl_attach_issue", "TEXT DEFAULT ''")):
        if name not in have:  # a ledger made by an older version
            conn.execute(f"ALTER TABLE leads ADD COLUMN {name} {decl}")
    if not had_log:
        _backfill(conn)
    conn.commit()
    return conn


def _backfill(conn: sqlite3.Connection) -> None:
    """A ledger from before the conversation log: write what its columns already say, at the times they say it."""
    for r in [dict(x) for x in conn.execute("SELECT * FROM leads")]:
        if r.get("draft"):
            _insert(conn, r["id"], "draft", r["draft"], r.get("poster") or "", at=r.get("drafted_at") or r["updated_at"])
        if r.get("local_state") in ("held", "skipped") and r.get("reason"):
            _insert(conn, r["id"], r["local_state"], r["reason"], config.WRITER, at=r["updated_at"])
        if r.get("marked_by"):
            _insert(conn, r["id"], "reply", r.get("draft") or r.get("radar_draft") or "", r["marked_by"],
                    at=r.get("marked_at") or r["updated_at"])
        if r.get("answer"):
            _insert(conn, r["id"], "answer", r["answer"], "", at=r.get("answered_at") or r["updated_at"])


def _insert(conn: sqlite3.Connection, lead_id: str, kind: str, text: str, by: str = "", url: str = "",
            at: str | None = None) -> None:
    conn.execute("INSERT INTO messages (lead_id, at, kind, direction, by, text, url) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (lead_id, at or now(), kind, KINDS[kind], (by or "")[:60], scrub(text)[:5000], url or ""))


def log(conn: sqlite3.Connection, lead_id: str, kind: str, text: str, by: str = "", url: str = "") -> bool:
    """Append one message, unless it repeats the lead's last message of the same kind. Returns whether it did."""
    last = conn.execute("SELECT text, by FROM messages WHERE lead_id=? AND kind=? ORDER BY id DESC LIMIT 1",
                        (lead_id, kind)).fetchone()
    if last and last["text"] == scrub(text)[:5000] and (kind != "reply" or last["by"] == (by or "")[:60]):
        return False
    _insert(conn, lead_id, kind, text, by, url)
    return True


def _when(at: str | None) -> datetime:
    try:
        t = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.max.replace(tzinfo=timezone.utc)


def messages(conn: sqlite3.Connection, lead_id: str) -> list[dict[str, Any]]:
    """In the order things happened (a backfilled draft can be logged before the post it answers)."""
    rows = [dict(r) for r in conn.execute("SELECT * FROM messages WHERE lead_id=? ORDER BY id", (lead_id,))]
    return sorted(rows, key=lambda m: _when(m["at"]))


def _desk_reason(note: str) -> str:
    """The reason the agent wrote on the desk for a skip ("reply-agent skip: ..."), so any ledger can show it."""
    found = [l.split("reply-agent skip:", 1)[1].strip() for l in (note or "").splitlines() if "reply-agent skip:" in l]
    return found[-1][:200] if found else ""


def lead(conn: sqlite3.Connection, lead_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    return dict(row) if row else None


def judge(row: dict[str, Any], text: str | None) -> list[str]:
    """The rules a lane's own draft must pass. The creators lane writes to its own guardrail (G3); everything the
    agent writes, and every desk draft, passes the full persona rules."""
    if row.get("source") in LANE_DRAFTS:
        return checks.g3_violations(text)
    return checks.violations(text, checks.FOLLOW_UP if row.get("local_state") == "answered" else checks.FIRST)


PARTNER_REASON = "a funding partner has this lead (the hub's quiet list): the agent drafts and posts nothing"


def set_partner_owned(conn: sqlite3.Connection, contact_ids: set[str]) -> dict[str, int]:
    """Mark the leads whose GHL contact is on the hub's quiet list as a funding partner's, and release the ones that
    left it. The change is logged once in each direction (kind `partner`), so the vault and the audit say why."""
    held = released = 0
    for r in [dict(x) for x in conn.execute(
            "SELECT id, ghl_contact_id, partner_hold FROM leads WHERE ghl_contact_id IS NOT NULL OR partner_hold=1")]:
        owned = bool(r["ghl_contact_id"]) and r["ghl_contact_id"] in contact_ids
        if owned == bool(r["partner_hold"]):
            continue
        conn.execute("UPDATE leads SET partner_hold=?, updated_at=? WHERE id=?", (1 if owned else 0, now(), r["id"]))
        _insert(conn, r["id"], "partner", PARTNER_REASON if owned else "the funding partner no longer has this lead",
                config.WRITER)
        rederive(conn, r["id"])
        held, released = held + owned, released + (not owned)
    conn.commit()
    return {"held": held, "released": released}


def contact_ask_state(conn: sqlite3.Connection, lead_id: str) -> str:
    """"allowed" while a follow-up may still ask this lead for their details; "done" once it has (spec 36: once), when a
    posted reply already asked or their details are already on their way to the GHL contact; "off" while REPLY_GHL is
    off, because there is nowhere to send what they'd tell us (the new behaviour waits for the same switch as the CRM)."""
    for m in conn.execute("SELECT text FROM messages WHERE lead_id=? AND kind='reply'", (lead_id,)):
        if checks.asks_contact(m["text"]):
            return "done"
    if conn.execute("SELECT 1 FROM ghl_outbox WHERE lead_id=? AND op='contact_details'", (lead_id,)).fetchone():
        return "done"
    return "allowed" if config.GHL else "off"


def with_answer(conn: sqlite3.Connection, row: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    """The desk item as the drafter needs it to write a follow-up: their answer, our first reply, and whether this
    follow-up may still ask for their details."""
    return {**item, "answer": row["answer"], "first_reply": row.get("radar_draft") or row.get("draft") or "",
            "contact_ask": contact_ask_state(conn, row["id"])}


def derive(row: dict[str, Any]) -> tuple[str, str]:
    """(state, reason) from what people did on the desk and what the agent recorded here. People win."""
    status = row.get("radar_status") or "new"
    if row.get("partner_hold"):  # a funding partner owns the conversation; this is closed on our side, with the reason
        return "partner", PARTNER_REASON
    if row.get("local_state") == "answered":
        follow_up = row.get("draft") if (row.get("drafted_at") or "") > (row.get("answered_at") or "") else ""
        return "answered", ("follow-up ready" if follow_up and checks.passes(follow_up, checks.FOLLOW_UP)
                            else "follow-up to draft")
    if status in ("replied", "won"):
        return "replied", f"{status} by {row.get('radar_by') or 'someone'}"
    if row.get("marked_by"):
        return "replied", f"replied by {row['marked_by']} (in the ledger; not yet on the desk)"
    if status == "skipped":
        return "skipped", (row.get("reason") if row.get("local_state") == "skipped" else "") or row.get("radar_reason") \
            or f"skipped by {row.get('radar_by') or 'someone'}"
    if row.get("local_state") in ("held", "skipped"):
        return row["local_state"], row.get("reason") or "no reason recorded"
    if status == "held":
        return "held", row.get("radar_reason") or "held by its lane"
    if row.get("source") in DIRECT:  # a private conversation: a person answers it in GHL, the agent never drafts
        return "waiting", f"on {row.get('poster') or 'justin'}: {row.get('radar_reason') or 'a person answers this one'}"
    if row.get("draft") and checks.passes(row["draft"]):
        return "waiting", f"on {row.get('poster') or 'nobody'}"
    if status == "drafted" and row.get("radar_by") not in ("", "draft", config.WRITER, None):
        bad = checks.violations(row.get("radar_draft"))
        return ("waiting", f"on {row.get('radar_by')} (their own draft)") if not bad else \
            ("unattended", f"{row.get('radar_by')}'s draft breaks: {', '.join(bad)}")
    if row.get("radar_draft") and not judge(row, row["radar_draft"]):
        return "waiting", f"on {row.get('poster') or 'nobody'}"
    if row.get("radar_draft"):
        return "unattended", ("lane" if row.get("source") in LANE_DRAFTS else "desk") + " draft breaks: " \
            + ", ".join(judge(row, row["radar_draft"]))
    return "unattended", "no draft yet"


def sync(conn: sqlite3.Connection, items: Iterable[dict[str, Any]], source: str = "lead-radar") -> dict[str, int]:
    """Upsert every queue item, then re-derive each lead's state. Returns {new, seen}."""
    t, new, seen = now(), 0, 0
    for it in items:
        reply = it.get("reply") or {}
        src = it.get("source") or source
        pid = lanes.persona_for(it.get("campaign") or "", lanes.post_text(it))
        cur = lead(conn, it["id"])
        poster = (cur or {}).get("assigned_to") or \
            (lanes.settings().get("poster_default", "justin") if src in DIRECT
             else lanes.poster_for(pid, campaign=it.get("campaign") or ""))
        fields = dict(source=src, campaign=it.get("campaign"), platform=it.get("platform"), kind=it.get("kind"),
                      tier=it.get("tier"), url=it.get("url"), posted_at=it.get("posted_at"),
                      has_contact=1 if it.get("contact") else 0, seen_at=t,
                      radar_status=reply.get("status") or "new", radar_by=reply.get("by") or "",
                      replied_at=reply.get("replied_at"), radar_draft=reply.get("draft") or "",
                      radar_reason=(reply.get("reason") or _desk_reason(reply.get("note") or ""))[:300],
                      persona=pid, poster=poster, hub=it.get("hub") or (radar_hub(it) if src == "lead-radar" else ""),
                      author=(it.get("author") or "")[:80], need=scrub(it.get("need"))[:300])
        fresh_answer = None  # their raw words, only when the answer is new: details are captured once
        if src in LANE_DRAFTS:  # the lane says when they answered; the agent's follow-up comes next
            answer = scrub(it.get("answer"))[:2000]
            if answer and answer != (cur or {}).get("answer"):
                fields.update(local_state="answered", answer=answer, answered_at=it.get("answered_at") or t)
                fresh_answer = it.get("answer")
            elif not answer and (cur or {}).get("local_state") == "answered":
                fields.update(local_state="")
        if cur is None:
            new += 1
            conn.execute(f"INSERT INTO leads (id, first_seen, updated_at, {', '.join(fields)}) "
                         f"VALUES (?, ?, ?, {', '.join('?' * len(fields))})", (it["id"], t, t, *fields.values()))
        else:
            seen += 1
            conn.execute(f"UPDATE leads SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), it["id"]))
        if fresh_answer:
            take_contact(conn, it["id"], fresh_answer)
        said = it.get("text") or it.get("quote") or it.get("need") or ""
        if said and not conn.execute("SELECT 1 FROM messages WHERE lead_id=? AND kind='post'", (it["id"],)).fetchone():
            _insert(conn, it["id"], "post", said, (it.get("author") or "")[:60], it.get("url") or "",
                    at=it.get("posted_at") or t)
        if fields["radar_status"] in ("replied", "won") and not conn.execute(
                "SELECT 1 FROM messages WHERE lead_id=? AND kind='reply'", (it["id"],)).fetchone():
            # A person marked it on the dashboard: the reply they posted is the desk's draft
            _insert(conn, it["id"], "reply", fields["radar_draft"] or "(the reply itself isn't in the ledger)",
                    fields["radar_by"] or "someone", it.get("url") or "", at=fields["replied_at"] or t)
        if fields.get("local_state") == "answered":
            log(conn, it["id"], "answer", fields["answer"], fields["author"])
        rederive(conn, it["id"])
    conn.commit()
    return {"new": new, "seen": seen}


def rederive(conn: sqlite3.Connection, lead_id: str) -> dict[str, Any]:
    row = lead(conn, lead_id)
    state, reason = derive(row)
    waiting_since = row.get("waiting_since") if state == "waiting" else None
    if state == "waiting" and not waiting_since:
        waiting_since = now()
    conn.execute("UPDATE leads SET state=?, reason=?, waiting_since=?, updated_at=? WHERE id=?",
                 (state, reason, waiting_since, now(), lead_id))
    return {**row, "state": state, "reason": reason}


def take_contact(conn: sqlite3.Connection, lead_id: str, raw: str | None) -> dict[str, bool]:
    """Call this with what a lead wrote, BEFORE it is scrubbed. An email or phone in it, and a clear yes to being
    contacted, are queued for the lead's GHL contact as one `contact_details` write in the outbox. Nothing else keeps
    them: not `leads`, not `messages`, not the vault, the notes or the logs. Returns which kinds were found (no
    values). A lead that gets no GHL contact (website, inbox) takes nothing."""
    row = lead(conn, lead_id)
    if not row or row.get("source") not in CRM_SOURCES:
        return {}
    raw = (raw or "")[:5000]
    found, consent = capture.extract(raw), capture.partner_ok(raw)
    if not (found["email"] or found["phone"] or consent):
        return {}
    said = scrub(raw)
    key = hashlib.sha1(f"{lead_id}|{said}".encode()).hexdigest()[:12]
    if conn.execute("SELECT 1 FROM ghl_outbox WHERE lead_id=? AND op='contact_details' AND key=?", (lead_id, key)).fetchone():
        return {}  # this very answer, already queued or sent
    got = {"email": bool(found["email"]), "phone": bool(found["phone"]), "partner_ok": consent}
    conn.execute("INSERT INTO ghl_outbox (lead_id, op, key, payload, why, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (lead_id, "contact_details", key,
                  json.dumps({**found, "consent": consent, "quote": said[:500] if consent else "", "tries": 0}),
                  "from their answer: " + ", ".join(k.replace("_", " ") for k, v in got.items() if v), now()))
    conn.commit()
    return got


def record(conn: sqlite3.Connection, lead_id: str, **fields: Any) -> dict[str, Any]:
    before = lead(conn, lead_id)
    if not before:
        raise KeyError(f"no lead {lead_id} in the ledger; run a cycle first")
    if "answer" in fields:  # whoever recorded it, the stored answer never holds an email or phone (G5)
        fields["answer"] = scrub(fields["answer"])[:2000]
    fields["updated_at"] = now()
    conn.execute(f"UPDATE leads SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), lead_id))
    # The conversation log: every new draft, hold, skip and answer (a posted reply is logged by whoever reports it)
    if fields.get("draft") and fields["draft"] != before.get("draft"):
        log(conn, lead_id, "draft", fields["draft"], fields.get("poster") or before.get("poster") or "")
    if fields.get("local_state") in ("held", "skipped"):
        log(conn, lead_id, fields["local_state"], fields.get("reason") or before.get("reason") or "", config.WRITER)
    if fields.get("answer") and fields["answer"] != before.get("answer"):
        log(conn, lead_id, "answer", fields["answer"], before.get("author") or "")
    out = rederive(conn, lead_id)
    conn.commit()
    return out


def coverage(read: dict[str, str] | None) -> dict[str, str]:
    """{lane: "" when read this cycle, else why not}, from each lane's read ({lane: why}, "" = read)."""
    read = dict(read if read is not None else {"lead-radar": ""})
    out = {}
    for lane in LANES:
        why = read.get(RIDES_ON.get(lane, lane), "not read")
        out[lane] = why if lane not in RIDES_ON or not why else f"rides on {RIDES_ON[lane]}, which isn't read: {why}"
    return out


def report(conn: sqlite3.Connection, truncated: bool = False, read: dict[str, str] | None = None) -> dict[str, Any]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM leads")]
    cover = coverage(read)
    covered = [k for k, why in cover.items() if not why]
    by_state = Counter(r["state"] for r in rows)
    hours = []
    for r in rows:
        if r["state"] == "replied" and r.get("replied_at"):
            try:
                a = datetime.fromisoformat(r["first_seen"])
                b = datetime.fromisoformat(str(r["replied_at"]).replace("Z", "+00:00"))
                b = b if b.tzinfo else b.replace(tzinfo=timezone.utc)
                hours.append(max(0.0, (b - a).total_seconds() / 3600))
            except ValueError:
                pass
    replied = by_state["replied"] + by_state["answered"]
    return {
        "unattended": by_state["unattended"],
        "found": len(rows),
        "replied": by_state["replied"],
        "waiting": by_state["waiting"],
        "waiting_on": dict(Counter(r["poster"] or "nobody" for r in rows if r["state"] == "waiting")),
        "held": by_state["held"],
        "held_by_reason": dict(Counter(r["reason"] for r in rows if r["state"] == "held").most_common(12)),
        "skipped": by_state["skipped"],
        "skipped_by_reason": dict(Counter(r["reason"] for r in rows if r["state"] == "skipped").most_common(12)),
        "answered": by_state["answered"],
        "partner": by_state["partner"],
        "unattended_why": dict(Counter(r["reason"].split(":")[0] for r in rows if r["state"] == "unattended")),
        "by_lane": {pid or "no lane": dict(Counter(r["state"] for r in rows if r["persona"] == pid))
                    for pid in sorted({r["persona"] for r in rows}, key=lambda p: p or "~")},
        "median_hours_found_to_replied": round(statistics.median(hours), 1) if hours else None,
        "answer_share": round(by_state["answered"] / replied, 2) if replied else None,
        "by_source": {src: dict(Counter(r["state"] for r in rows if r["source"] == src))
                      for src in sorted({r["source"] for r in rows})},
        "covers": f"{len(covered)} of {len(LANES)} lanes: " + ", ".join(LANES[k] for k in covered),
        "not_covered_yet": [f"{LANES[k]} ({why})" for k, why in cover.items() if why],
        "truncated": truncated,
        "write_to_desk": config.WRITE,
    }


def chase(conn: sqlite3.Connection, since: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """What has been waiting since the last cycle (or `since`), grouped by poster, oldest first."""
    since = since or (conn.execute("SELECT MAX(started_at) FROM cycles WHERE finished_at IS NOT NULL").fetchone()[0] or now())
    out: dict[str, list[dict[str, Any]]] = {}
    for r in conn.execute("SELECT id, poster, campaign, platform, tier, url, waiting_since FROM leads "
                          "WHERE state='waiting' AND waiting_since <= ? ORDER BY waiting_since", (since,)):
        out.setdefault(r["poster"] or "nobody", []).append(dict(r))
    return out


def markdown(rep: dict[str, Any], day: str) -> str:
    lines = [f"# Reply ledger {day}", "", f"**Unattended: {rep['unattended']}** of {rep['found']} leads found.", "",
             f"- Replied: {rep['replied']}", f"- Waiting: {rep['waiting']} "
             + (f"({', '.join(f'{k} {v}' for k, v in rep['waiting_on'].items())})" if rep["waiting_on"] else ""),
             f"- Held: {rep['held']}", *[f"  - {k}: {v}" for k, v in rep["held_by_reason"].items()],
             f"- Skipped: {rep['skipped']}", *[f"  - {k}: {v}" for k, v in rep["skipped_by_reason"].items()],
             f"- Answered: {rep['answered']}", f"- With a funding partner: {rep['partner']}", "",
             f"Covers {rep['covers']}.", "Not covered yet: " + "; ".join(rep["not_covered_yet"]) + "."]
    if rep["unattended_why"]:
        lines += ["", "Why leads are unattended: " + "; ".join(f"{k} ({v})" for k, v in rep["unattended_why"].items())]
    if rep["truncated"]:
        lines += ["", "Lead Radar's queue hit its 1000-item cap, so these counts are a floor."]
    if not rep["write_to_desk"]:
        lines += ["", "REPLY_WRITE is off: drafts and holds are in this ledger only, not on Lead Radar's desk."]
    return "\n".join(lines) + "\n"
