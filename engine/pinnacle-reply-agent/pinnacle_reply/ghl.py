"""GoHighLevel: each lead the Reply Agent answers, and its conversation, in the CRM.

The CRM is the Funding Machine sub-account (REPLY_GHL_TARGET=funding-machine, the default since D1): its "Lead Radar
Leads" pipeline (Facebook leads have their own, below), New Lead until a reply is posted, then Replied, then They
Answered; Talking and later are people's calls. An answer from them also adds the tag radar:answered. The "3. FM
Marketing Pipeline" is the website's (the hub writes it), so no Radar lead goes there. REPLY_GHL_TARGET=pinnacle-funding-group
is the home CRM from spec 36 (location PINNACLE_GHL_LOCATION_ID, set at intake): the same "Lead Radar Leads" and "Facebook Leads" pipelines
and stage maps as the Funding Machine, nothing else. The website and Craigslist belong to the hub, so neither has a path
here. Each contact also carries one "Reply Agent · Contact card" note, kept current (REPLY_GHL_CARD=off hands the card
to the Funding CRM Manager): who they are, what they need, where the conversation stands, and an obsidian:// link to
the lead's note in Justin's vault.

Lead Radar is where leads are found. GHL is where they're tracked. Every lead the agent reads goes in, every tier,
as soon as it is read (REPLY_GHL_FROM=seen, the default since 2026-11-03; `waiting` waits for a checked draft,
`replied` for a posted reply; skipped leads stay out unless REPLY_GHL_SKIPPED=on). For each one the agent makes:
  - a contact named by who asked and what they need ("Jane D.: hard money for a flip"), with the post as its website
    and the tags src:lead-radar, radar:lane-p2, radar:facebook, radar:tier-medium;
  - an opportunity in the target's pipeline at the stage for its state (above). It only moves a stage forward, and
    only to the agent's own stages: people and the Credit Desk own the later ones;
  - the conversation (REPLY_GHL_RECORD): `note` (default) adds one note per message that was said, their post, each
    reply posted and each answer, every one starting "Reply Agent ·" so Justin's own notes stay apart.
    `field:<custom field id>` keeps the whole conversation in one contact custom field instead.
Drafts, holds and skips stay in the ledger and the vault: they weren't said to anyone.

The creators and gig lanes are the one exception (Justin, 2026-11-06). The creators sync (pinnacle-creators crm.py) makes
their contacts and deals in Pinnacle Funding Group, because a commenter has no email or phone for GHL to match on and a
second maker would mean a second contact. This agent never makes either. attach() finds the sync's contact by the tag
the sync puts on it for each comment (ask_tag) and stores the ids; a lead with no contact yet waits. From then on the
agent adds only what the sync can't know: a captured email, phone or partner OK, a note for each reply and answer, its
lane and radar:answered tags, and the stage, forward only. The sync reads those stage moves back. A lead read straight
from radar-db (source creators) gets the capture alone: the sync sees its messages and stage there already.

Every write goes through an outbox in the ledger (prepare, then send), the way the creators sync (W3, pinnacle-creators
crm-sync 4bb7174) does, and every call is checked against ghl_contract.json, copied from it. send() runs only with
REPLY_GHL=on and the target's token and location (the Funding Machine: FM_GHL_API_KEY, else GHL_API_KEY in FM_GHL_ENV,
and FM_GHL_LOCATION_ID; Pinnacle Funding Group: GHL_API_KEY and GHL_LOCATION_ID). A row is marked sending before its call; one found still sending was cut off and may have reached GHL, so it is
failed for a person to check and never retried blindly: these leads have no email or phone for GHL to match on, so a
blind retry would make a second contact. The agent never writes consent:* or fi:* tags. A public post isn't consent.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit

from . import config, ledger, sources, vault

NEVER_LOCATIONS = config.NEVER_LOCATIONS  # set at intake: REPLY_NEVER_LOCATIONS and NEVER_TOUCH
# Every Radar lead that isn't Facebook's (Reddit, TikTok, forums, Skool, Instagram, YouTube, LinkedIn, the web). Made
# once in GHL's screen (its API can't create a pipeline), with these stage names in this order.
LR = ("New Lead", "Replied", "They Answered", "Talking", "Qualified", "Booked", "Not a Fit")
# Where leads go. A lead in any state the map doesn't name (held, unattended) opens at the first stage. The agent moves
# a deal forward only to its own stages; the later ones are people's.
_RADAR_STAGES = {"waiting": "New Lead", "replied": "Replied", "answered": "They Answered"}
TARGETS = {
    "funding-machine": {"location": config.FM_GHL_LOCATION, "pipeline": "Lead Radar Leads", "stages": LR,
                        "stage_for": _RADAR_STAGES},
    # Spec 36 section 6: the home CRM. The same pipelines and stage maps as the Funding Machine; the pipelines are made
    # once in GHL's screen (its API can't create one). Its old "P1 · Funding Leads" target is gone.
    "pinnacle-funding-group": {"location": config.PINNACLE_GHL_LOCATION, "pipeline": "Lead Radar Leads", "stages": LR,
                               "stage_for": _RADAR_STAGES},
}
# Facebook leads are the hired posters' to answer (Justin's ruling, 2026-11-07, in place of MetaMuse) and Justin's to
# work: their own pipeline, filled as soon as the Reply Agent has a checked draft (not only once a reply is posted) so the
# list is in GHL before anyone posts. The agent moves a deal through the first three stages; Talking and later are
# Justin's. The pipeline is made once in GHL's screen (its API can't create one), with these stage names in this order.
FB = ("New Lead", "Poster Replied", "They Answered", "Talking", "Qualified", "Booked", "Not a Fit")
_FACEBOOK = {"facebook": {"pipeline": "Facebook Leads", "stages": FB, "from": "waiting",
                          "stage_for": {"waiting": "New Lead", "replied": "Poster Replied", "answered": "They Answered"}}}
# A stage's old name reads as its new one: in GHL's pipelines, in writes already in the outbox and in a deal's saved stage.
# "MetaMuse Replied" becomes "Poster Replied" on Justin's yes (2026-11-07); the stage id doesn't change, so the agent works
# before and after the rename in GHL's screen.
RENAMED = {"MetaMuse Replied": "Poster Replied"}


def canon(stage: str | None) -> str | None:
    return RENAMED.get(stage, stage) if stage else stage


BY_PLATFORM = {"funding-machine": _FACEBOOK, "pinnacle-funding-group": _FACEBOOK}
ALLOWED_LOCATIONS = {t["location"] for t in TARGETS.values() if t["location"]}  # an unset id allows nothing
CARD = "Reply Agent · Contact card"
SOURCE = "Lead Radar"
SAID = ("post", "reply", "answer")  # what goes to GHL: what was said. Drafts, holds and skips weren't.
CONTRACT = json.loads(Path(__file__).with_name("ghl_contract.json").read_text())["operations"]


class GhlError(RuntimeError):
    pass


class GhlRefused(GhlError):
    """A call the sync won't make: not in the contract, a field missing, a tag it doesn't own, the wrong location."""


class Skip(Exception):
    """The write no longer applies: someone (the Credit Desk, a person) moved the opportunity on."""

    def __init__(self, stage: str | None, have: dict):
        super().__init__(stage or "an unknown stage")
        self.stage, self.have = stage, have


def target() -> dict[str, Any]:
    t = TARGETS.get(config.GHL_TARGET)
    if t is None:
        raise GhlRefused(f"REPLY_GHL_TARGET={config.GHL_TARGET} isn't one of {sorted(TARGETS)}")
    if not t["location"]:
        raise GhlRefused(f"the {config.GHL_TARGET} location id isn't set (FM_GHL_LOCATION_ID or PINNACLE_GHL_LOCATION_ID, intake)")
    return t


# Tags the Reply Agent owns besides src:lead-radar and radar:*: what it learned from a lead's own answer (spec 36).
OWNED_TAGS = {"contact:captured", "consent:partner-ok"}
# Outbox ops that carry what a lead told us. They are queued when the answer arrives (ledger.take_contact), not planned
# from the ledger, so prepare() leaves them alone; the values are blanked once sent (or given up on).
CAPTURE_OPS = ("contact_details",)
CAPTURE_TRIES = 5          # tries before a transient failure is given up on
CAPTURE_KEEP_DAYS = 14     # a capture that never went (REPLY_GHL off, no contact) is dropped, blanked, after this
CAPTURE_WARN_DAYS = 3      # a cycle says so this long before a capture waiting on the creators sync is dropped
LOOK_AGAIN_HOURS = 20      # the sync sends once a night, so a lead with nothing waiting is searched about once a day
# The creators sync (pinnacle-creators crm.py) makes these lanes' contacts and deals: Justin's call, 2026-11-06. They have
# no email or phone for GHL to match on, so a second maker means a second contact. The agent answers them and attaches.
OTHER_WRITER = ("lane-creators", "lane-gig")
SYNC_TARGET = "pinnacle-funding-group"  # the only sub-account the creators sync writes
ASK = "ask:"
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "igsh",
                   "igshid", "si", "ref", "ref_src", "_rdr", "rdt", "share_id", "is_from_webapp", "sender_device", "_t",
                   "_r", "mibextid", "rcm", "__cft__[0]", "__tn__"}  # Lead Radar's normalize.TRACKING_PARAMS


def ask_tag(url: str | None) -> str:
    """The tag for one ask: ask:<12 hex> of its comment link, or "" with no link. GHL's tag search matches a whole tag,
    so this finds exactly the contacts holding it. Lead Radar's desk holds the link in its canonical form and this
    pipeline in its stored one, so the hash is taken over what's left once both forms are the same: host without www,
    m. or old., no trailing slash, no tracking parameters, the rest sorted.

    pinnacle-creators crm.py and lending_hub/work.py hold copies of this function. tests/ask_tags.json holds the same
    vectors in all three repos: change one, change them all, or this agent stops finding the sync's contacts."""
    if not (url or "").strip():
        return ""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.").removeprefix("old.")
    if host in ("twitter.com", "mobile.twitter.com"):
        host = "x.com"
    path = re.sub(r"/+$", "", parts.path) or "/"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if k not in TRACKING_PARAMS))
    return ASK + hashlib.sha1(f"{host}{path}?{query}".encode()).hexdigest()[:12]


def sync_owned(row: dict[str, Any]) -> bool:
    """Whether the creators sync makes this lead's contact and deal, however the lead reached this agent."""
    return row.get("source") == "creators" or row.get("campaign") in OTHER_WRITER


def attached(row: dict[str, Any]) -> bool:
    """Whether the lead holds the creators sync's contact in this target. A contact id alone isn't that: a lead the
    agent wrote into the Funding Machine before the one-writer call holds an id of its own."""
    return bool(row.get("ghl_contact_id")) and bool(json.loads(row.get("ghl_have") or "{}").get("attached"))


def ours(tag: str) -> bool:
    return tag == "src:lead-radar" or tag.startswith("radar:") or tag in OWNED_TAGS


def route(row: dict[str, Any]) -> dict[str, Any]:
    """Where a lead's deal goes: its platform's own pipeline when it has one (Facebook), else the target's. The creators
    sync keeps every deal in the target's pipeline, Facebook commenters' too."""
    own = BY_PLATFORM.get(config.GHL_TARGET, {}).get((row.get("platform") or "").lower())
    if sync_owned(row):
        return target()
    return own if own and config.GHL_PLATFORM_PIPELINES else target()


def _stages(pipeline: str | None) -> tuple[str, ...]:
    for p in [target(), *BY_PLATFORM.get(config.GHL_TARGET, {}).values()]:
        if p["pipeline"] == pipeline:
            return p["stages"]
    return target()["stages"]


def _rank(stage: str | None, stages: tuple[str, ...] | None = None) -> int:
    stages, stage = stages or target()["stages"], canon(stage)
    return stages.index(stage) if stage in stages else -1


# --------------------------------------------------------------------------------------------------- what GHL should hold
def here(row: dict[str, Any]) -> dict[str, Any]:
    """The lead as the current target sees it. A contact and deal made in another sub-account (the Funding Machine
    before REPLY_GHL_TARGET flips) are not in this one: such a lead has no contact here yet, and its first write is a
    contact_create again. A lead made before locations were recorded was made in the Funding Machine."""
    if not row.get("ghl_contact_id"):
        return row
    made_in = json.loads(row.get("ghl_have") or "{}").get("location") or TARGETS["funding-machine"]["location"]
    if made_in == target()["location"]:
        return row
    return {**row, "ghl_contact_id": None, "ghl_opportunity_id": None, "ghl_have": "{}"}


def eligible(row: dict[str, Any]) -> bool:
    if (row.get("source") or "lead-radar") not in ledger.CRM_SOURCES:
        return False  # website and inbox leads are already in a GHL
    if sync_owned(row):
        return attached(row)  # the creators sync makes these; until attach() finds its contact, a detail waits (CAPTURE_KEEP_DAYS)
    if row.get("ghl_contact_id"):
        return True  # once in GHL, its conversation keeps going there
    if row["state"] in ("replied", "answered"):
        return True
    if config.GHL_FROM == "seen":
        return row["state"] != "skipped" or config.GHL_SKIPPED
    if row["state"] != "waiting":
        return False
    if config.GHL_FROM == "waiting":
        return True
    # a platform's own pipeline (Facebook) takes its leads at a checked draft: high and medium only, like the hub's queue
    return route(row).get("from") == "waiting" and (row.get("tier") or "").lower() in ("high", "medium")


def contact_name(row: dict[str, Any]) -> str:
    """vault.title, except a Facebook post id ("pfbid…") never stands in for a person's name in the CRM."""
    if re.match(r"pfbid", (row.get("author") or "").strip(), re.I):
        row = {**row, "author": ""}
    return vault.title(row)


def desired(row: dict[str, Any]) -> dict[str, Any]:
    name = contact_name(row)[:100]
    tags = {"src:lead-radar", f"radar:{(row.get('platform') or 'unknown').lower()}"}
    if row.get("persona"):
        tags.add(f"radar:lane-{row['persona'].lower()}")
    if row.get("tier"):
        tags.add(f"radar:tier-{row['tier'].lower()}")
    if row["state"] == "answered" or row.get("answer"):
        tags.add("radar:answered")
    # GHL refuses a contact with no first name, last name, email or phone (HTTP 422), and these leads have only a post:
    # "Facebook asker: needs a DSCR loan" goes in as first name "Facebook asker:" and last name "needs a DSCR loan"
    first, _, last = name.partition(": ")
    return {"contact": {"name": name, "firstName": f"{first}:" if last else first, "lastName": last or None,
                        "website": row.get("url") or None, "source": SOURCE},
            "tags": sorted(tags), "deal": name, "pipeline": route(row)["pipeline"],
            "stage": route(row)["stage_for"].get(row["state"]) or route(row)["stages"][0]}


def note_body(row: dict[str, Any], m: dict[str, Any]) -> str:
    where = vault.platform_name(row.get("platform"))
    when = vault._stamp(m["at"])
    if m["kind"] == "post":
        lead = f"Reply Agent · Their post on {where}" + (f" ({m['by']})" if m.get("by") and not m["by"].isdigit() else "") + f", {when}:"
        tail = [f"Need: {row['need']}" if row.get("need") else "", f"Post: {row.get('url')}" if row.get("url") else "",
                f"Lane {row.get('persona') or '?'}, tier {row.get('tier') or '?'}, campaign {row.get('campaign') or '?'}"]
    elif m["kind"] == "reply":
        lead = f"Reply Agent · Reply posted by {m.get('by') or 'someone'} on {where}, {when}:"
        tail = [f"Where: {m['url']}" if m.get("url") else ""]
    else:
        lead = f"Reply Agent · They wrote back on {where}, {when}:"
        tail = []
    return "\n".join([lead, ledger.scrub(m["text"]), *[t for t in tail if t]])[:5000]


def card_body(row: dict[str, Any], msgs: list[dict[str, Any]]) -> str:
    """The contact card: one note per contact, rewritten in place when anything on it changes. No timestamps of its
    own, so an unchanged lead never rewrites it."""
    said = [m for m in msgs if m["kind"] in SAID][-4:]
    kinds = {"post": "Their post", "reply": "Our reply", "answer": "They wrote back"}
    lines = [CARD, f"{contact_name(row)} · {vault.platform_name(row.get('platform'))}",
             f"Needs: {row['need']}" if row.get("need") else "",
             f"Where it stands: {row['state']}" + (f", waiting on {row['poster']}" if row["state"] == "waiting" and row.get("poster") else ""),
             f"Intent {row.get('tier') or '?'} · lane {vault.lane_name(row.get('persona'))} · campaign {row.get('campaign') or '?'}",
             f"Thread: {row['url']}" if row.get("url") else "", "", "The conversation so far:"]
    lines += [f"- {kinds[m['kind']]}, {vault._stamp(m['at'])}" + (f" ({m['by']})" if m['kind'] == 'reply' and m.get('by') else "")
              + f": {ledger.scrub(m['text'])[:280]}" for m in said] or ["- nothing said yet"]
    lines += ["", f"Full card in Obsidian: {vault.obsidian_link(row)}"]
    return "\n".join(x for i, x in enumerate(lines) if x or (i and lines[i - 1]))[:5000]


def transcript(row: dict[str, Any], msgs: list[dict[str, Any]]) -> str:
    """The whole conversation, newest last, for REPLY_GHL_RECORD=field:<id>."""
    parts = [note_body(row, m).removeprefix("Reply Agent · ") for m in msgs if m["kind"] in SAID]
    return "\n\n".join(parts)[-10000:]


def plan(row: dict[str, Any], have: dict[str, Any], msgs: list[dict[str, Any]]) -> list[tuple[str, str, dict, str]]:
    """The writes that take GHL from `have` (what was last sent) to what the ledger says: (op, key, payload, why)."""
    if not eligible(row):
        return []
    if sync_owned(row):
        return _plan_attached(row, have, msgs)
    want, out = desired(row), []
    if not row.get("ghl_contact_id"):
        out.append(("contact_create", "", {**want["contact"], "tags": want["tags"]}, f"new lead ({row['state']})"))
    else:
        if want["contact"] != have.get("contact"):
            out.append(("contact_update", "", want["contact"], "name or post changed"))
        add = sorted(set(want["tags"]) - set(have.get("tags") or []))
        if add:
            out.append(("tags_add", ",".join(add), {"tags": add}, "lane, platform or tier changed"))
    if want["stage"]:
        if not row.get("ghl_opportunity_id"):
            out.append(("opportunity_create", "", {"name": want["deal"], "stage": want["stage"], "pipeline": want["pipeline"]},
                        f"new lead ({row['state']})"))
        elif not have.get("moved") and _rank(want["stage"], _stages(want["pipeline"])) > _rank(have.get("stage"), _stages(want["pipeline"])):
            out.append(("opportunity_stage", want["stage"], {"stage": want["stage"], "pipeline": want["pipeline"]},
                        f"{have.get('stage') or '?'} → {want['stage']} ({row['state']})"))
    out += _conversation(row, have, msgs)
    card = card_body(row, msgs)
    key = hashlib.sha1(card.encode()).hexdigest()[:12]
    if config.GHL_CARD and have.get("card") != key:  # REPLY_GHL_CARD=off: the Funding CRM Manager owns the card
        out.append(("card", key, {"body": card}, "contact card changed" if have.get("card") else "contact card"))
    return out


def _conversation(row: dict[str, Any], have: dict[str, Any], msgs: list[dict[str, Any]]) -> list[tuple[str, str, dict, str]]:
    """What was said and isn't in GHL yet: one note per message, or the whole transcript in one field."""
    out, said = [], [m for m in msgs if m["kind"] in SAID]
    if config.GHL_RECORD.startswith("field:"):
        last = str(said[-1]["id"]) if said else ""
        if said and have.get("transcript") != last:
            out.append(("transcript", last, {"field": config.GHL_RECORD[6:], "value": transcript(row, msgs)},
                        "the conversation grew"))
        return out
    noted = set(have.get("notes") or [])
    for m in said:
        if str(m["id"]) not in noted:
            out.append(("note", str(m["id"]), {"body": note_body(row, m)},
                        {"post": "their post", "reply": "a reply posted", "answer": "their answer"}[m["kind"]]))
    return out


def _plan_attached(row: dict[str, Any], have: dict[str, Any], msgs: list[dict[str, Any]]) -> list[tuple[str, str, dict, str]]:
    """A lead on the creators sync's contact. Its name, website, source and deal are the sync's, and so is the note of
    their post, so this plans only what the sync can't know. No contact card either: that's one per person, and the
    Funding CRM Manager's (spec 36 section 2). A capture isn't planned here: their answer queues it."""
    if row.get("source") == "creators":
        return []  # read from radar-db, where the sync already sees its messages and stage
    want, out = desired(row), []
    add = sorted(t for t in want["tags"] if (t == "radar:answered" or t.startswith("radar:lane-"))
                 and t not in (have.get("tags") or []))
    if add:
        out.append(("tags_add", ",".join(add), {"tags": add}, "their lane, or their answer"))
    if row.get("ghl_opportunity_id") and not have.get("moved") and _rank(want["stage"]) > _rank(have.get("stage")):
        out.append(("opportunity_stage", want["stage"], {"stage": want["stage"], "pipeline": want["pipeline"]},
                    f"{have.get('stage') or '?'} → {want['stage']} ({row['state']})"))
    return out + _conversation(row, have, [m for m in msgs if m["kind"] != "post"])


def prepare(conn: sqlite3.Connection) -> dict[str, int]:
    """Work out every write GHL needs and put it in the outbox. Free: it calls nothing."""
    made = updated = dropped = 0
    rows = [here(dict(r)) for r in conn.execute("SELECT * FROM leads")]
    for row in rows:
        have = json.loads(row.get("ghl_have") or "{}")
        wanted = plan(row, have, ledger.messages(conn, row["id"]))
        keys = {(op, key) for op, key, _p, _w in wanted}
        for op, key, payload, why in wanted:
            prior = conn.execute("SELECT id, status FROM ghl_outbox WHERE lead_id=? AND op=? AND key=? "
                                 "ORDER BY id DESC LIMIT 1", (row["id"], op, key)).fetchone()
            if prior and prior["status"] == "prepared":
                conn.execute("UPDATE ghl_outbox SET payload=?, why=? WHERE id=?", (json.dumps(payload), why, prior["id"]))
                updated += 1
            elif prior and prior["status"] in ("sending", "failed"):
                continue  # a person checks GHL first (see the module note); never prepared twice
            else:
                conn.execute("INSERT INTO ghl_outbox (lead_id, op, key, payload, why, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (row["id"], op, key, json.dumps(payload), why, ledger.now()))
                made += 1
        for r in conn.execute("SELECT id, op, key FROM ghl_outbox WHERE lead_id=? AND status='prepared'", (row["id"],)).fetchall():
            if r["op"] in CAPTURE_OPS:
                continue  # queued by their answer, not planned from the ledger
            if (r["op"], r["key"]) not in keys:
                conn.execute("UPDATE ghl_outbox SET status='skipped', error='no longer needed' WHERE id=?", (r["id"],))
                dropped += 1
    stale = (datetime.now(timezone.utc) - timedelta(days=CAPTURE_KEEP_DAYS)).isoformat(timespec="microseconds")
    for r in conn.execute(f"SELECT id, payload FROM ghl_outbox WHERE status='prepared' AND created_at < ? "
                          f"AND op IN ({','.join('?' * len(CAPTURE_OPS))})", (stale, *CAPTURE_OPS)).fetchall():
        conn.execute("UPDATE ghl_outbox SET status='skipped', error=?, payload=? WHERE id=?",
                     (f"never sent in {CAPTURE_KEEP_DAYS} days: dropped", json.dumps(_blank(json.loads(r["payload"]))), r["id"]))
        dropped += 1
    conn.commit()
    return {"prepared": made, "updated": updated, "dropped": dropped}


def _blank(body: dict[str, Any]) -> dict[str, Any]:
    """A capture payload with its values gone: only which kinds it held stay, for the record."""
    return {"email": bool(body.get("email")), "phone": bool(body.get("phone")), "consent": bool(body.get("consent")),
            "blanked": True}


# --------------------------------------------------------------------------------------------------- the client
Transport = Callable[[str, str, dict, bytes | None], tuple[int, str]]


def _urllib(method: str, url: str, headers: dict, data: bytes | None) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except urllib.error.URLError as exc:
        raise GhlError(f"GHL unreachable: {exc.reason}") from exc


class Ghl:
    BASE = "https://services.leadconnectorhq.com"

    def __init__(self, token: str, location_id: str, *, transport: Transport | None = None, sleep=time.sleep):
        if location_id != target()["location"]:
            raise GhlRefused(f"location {location_id} isn't the {config.GHL_TARGET} sub-account the Reply Agent writes to")
        self.loc, self.sleep, self.transport = location_id, sleep, transport or _urllib
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
                        "User-Agent": "pinnacle-reply-agent"}
        self._pipes: dict[str, dict] = {}

    @classmethod
    def from_config(cls, **kw) -> "Ghl":
        if config.GHL_TARGET == "funding-machine":
            try:
                return cls(sources._fm_token(), config.FM_GHL_LOCATION, **kw)
            except sources.SourceError as exc:
                raise GhlRefused(str(exc)) from exc
        if not config.GHL_TOKEN or not config.GHL_LOCATION:
            raise GhlRefused("GHL_API_KEY and GHL_LOCATION_ID aren't both set")
        return cls(config.GHL_TOKEN, config.GHL_LOCATION, **kw)

    def call(self, method: str, path: str, *, op: str | None = None, params: dict | None = None,
             body: dict | None = None) -> dict:
        key = f"{method} {op or path}"
        spec = CONTRACT.get(key)
        if spec is None:
            raise GhlRefused(f"{key} isn't in ghl_contract.json")
        missing = [f for f in spec["required_body"] if f not in (body or {})] + \
                  [f for f in spec["required_query"] if f not in (params or {})]
        if missing:
            raise GhlRefused(f"{key} needs {missing}")
        unknown = sorted(set(body or {}) - set(spec["body"])) + sorted(set(params or {}) - set(spec["query"]))
        if unknown:
            raise GhlRefused(f"{key} has no field {unknown}")
        if key == "PUT /contacts/{contactId}" and "tags" in (body or {}):
            raise GhlRefused("PUT /contacts replaces every tag on the contact: tags go through /tags")
        foreign = [t for t in (body or {}).get("tags") or [] if not ours(t)]
        if foreign:
            raise GhlRefused(f"won't write tags the Reply Agent doesn't own: {foreign}")
        url = self.BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {**self.headers, "Version": spec["version"], **({"Content-Type": "application/json"} if body is not None else {})}
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            code, text = self.transport(method, url, headers, data)
            if code == 429 and attempt < 3:
                self.sleep(2 ** attempt)
                continue
            if code >= 400:
                raise GhlError(f"{key}: HTTP {code} {text[:200]}")
            try:
                return json.loads(text) if text.strip() else {}
            except ValueError as exc:
                raise GhlError(f"{key}: not JSON: {text[:120]}") from exc
        raise GhlError(f"{key}: still rate limited")

    def check_location(self) -> str:
        name = ((self.call("GET", f"/locations/{self.loc}", op="/locations/{locationId}").get("location") or {})
                .get("name") or "")
        if name.lower() in NEVER_LOCATIONS:
            raise GhlRefused(f"location {self.loc} is {name}")
        return name

    def pipeline(self, name: str | None = None) -> dict:
        name = name or target()["pipeline"]
        if name not in self._pipes:
            data = self.call("GET", "/opportunities/pipelines", params={"locationId": self.loc})
            p = next((x for x in data.get("pipelines") or [] if x.get("name") == name), None)
            if p is None:
                raise GhlError(f"no pipeline named {name}: make it in GHL (Opportunities > Pipelines) with the stages "
                               f"{', '.join(_stages(name))}")
            ids = {canon(s["name"]): s["id"] for s in p.get("stages") or []}
            own = next((p["stage_for"] for p in [target(), *BY_PLATFORM.get(config.GHL_TARGET, {}).values()]
                        if p["pipeline"] == name), {})
            missing = sorted({s for s in own.values() if s not in ids})
            if missing:  # the stages the agent moves deals to must be there, spelled the same
                raise GhlError(f"pipeline {name} has no stage {missing}")
            self._pipes[name] = {"id": p["id"], "ids": ids, "names": {s["id"]: canon(s["name"]) for s in p.get("stages") or []},
                                 "others": {x.get("id"): x.get("name") for x in data.get("pipelines") or []}}
        return self._pipes[name]

    def contacts_tagged(self, tag: str) -> list[dict]:
        """The contacts holding this exact tag, each with its deals. Two are enough to know it isn't one."""
        return self.call("POST", "/contacts/search", body={
            "locationId": self.loc, "pageLimit": 2,
            "filters": [{"field": "tags", "operator": "eq", "value": tag}]}).get("contacts") or []


def _contact_details(ghl: Ghl, cid: str, r: dict, body: dict, have: dict) -> tuple[dict, dict, dict]:
    """Their email and phone onto the contact, the tags, and the Partner OK note. Only values they gave: an empty one
    is never sent, so it can't blank what the contact already has. Every step is a PUT or an add, safe to repeat, except
    the note, which comes last; steps already done are remembered in the row (names only), so a retry skips them."""
    done = set(body.get("done") or [])

    def step(name: str) -> None:
        done.add(name)
        r["payload"] = json.dumps({**body, "done": sorted(done)})  # progress, kept if a later step fails

    fields = {k: body[k] for k in ("email", "phone") if body.get(k)}
    tags = (["contact:captured"] if fields else []) + (["consent:partner-ok"] if body.get("consent") else [])
    if fields and "fields" not in done:
        ghl.call("PUT", f"/contacts/{cid}", op="/contacts/{contactId}", body=fields)
        step("fields")
    if tags and "tags" not in done:
        ghl.call("POST", f"/contacts/{cid}/tags", op="/contacts/{contactId}/tags", body={"tags": tags})
        step("tags")
    if body.get("consent") and "note" not in done:
        ghl.call("POST", f"/contacts/{cid}/notes", op="/contacts/{contactId}/notes",
                 body={"body": f"Partner OK: {body.get('quote') or ''}"[:5000]})
        step("note")
    have["tags"] = sorted(set(have.get("tags") or []) | set(tags))
    return {"fields": sorted(fields), "tags": tags, "partner_ok": bool(body.get("consent"))}, have, {}


def _apply(ghl: Ghl, row: dict[str, Any], have: dict, r: dict) -> tuple[dict, dict, dict]:
    """One write. Returns (receipt, new `have`, lead columns to set)."""
    op, body, cid, oid = r["op"], json.loads(r["payload"]), row.get("ghl_contact_id"), row.get("ghl_opportunity_id")
    have = {**have}
    if op in ("contact_create", "contact_update", "opportunity_create") and sync_owned(row):
        raise GhlRefused(f"{op}: the creators sync makes this lead's contact and deal")
    if op == "contact_create":
        contact = {k: v for k, v in body.items() if v is not None}
        data = ghl.call("POST", "/contacts/", body={"locationId": ghl.loc, **contact})
        cid = (data.get("contact") or {}).get("id")
        if not cid:
            raise GhlError("POST /contacts/ returned no contact id")
        # a fresh start in this sub-account: nothing recorded from another one carries over
        have = {"location": ghl.loc, "contact": {k: v for k, v in body.items() if k != "tags"}, "tags": body["tags"]}
        return {"contact_id": cid}, have, {"ghl_contact_id": cid, "ghl_opportunity_id": None}
    if not cid:
        raise GhlError("no contact yet: its create hasn't been sent")
    if op == "contact_update":
        ghl.call("PUT", f"/contacts/{cid}", op="/contacts/{contactId}", body={k: v for k, v in body.items() if v is not None})
        have["contact"] = body
        return {"contact_id": cid}, have, {}
    if op == "contact_details":
        return _contact_details(ghl, cid, r, body, have)
    if op == "tags_add":
        ghl.call("POST", f"/contacts/{cid}/tags", op="/contacts/{contactId}/tags", body={"tags": body["tags"]})
        have["tags"] = sorted(set(have.get("tags") or []) | set(body["tags"]))
        return {"tags": body["tags"]}, have, {}
    if op == "note":
        data = ghl.call("POST", f"/contacts/{cid}/notes", op="/contacts/{contactId}/notes", body={"body": body["body"]})
        have["notes"] = [*(have.get("notes") or []), r["key"]]
        return {"note_id": (data.get("note") or {}).get("id")}, have, {}
    if op == "card":
        if have.get("card_note"):
            ghl.call("PUT", f"/contacts/{cid}/notes/{have['card_note']}", op="/contacts/{contactId}/notes/{id}",
                     body={"body": body["body"]})
        else:
            data = ghl.call("POST", f"/contacts/{cid}/notes", op="/contacts/{contactId}/notes", body={"body": body["body"]})
            have["card_note"] = (data.get("note") or {}).get("id")
        have["card"] = r["key"]
        return {"note_id": have.get("card_note")}, have, {}
    if op == "transcript":
        ghl.call("PUT", f"/contacts/{cid}", op="/contacts/{contactId}",
                 body={"customFields": [{"id": body["field"], "field_value": body["value"]}]})
        have["transcript"] = r["key"]
        return {"contact_id": cid, "field": body["field"]}, have, {}
    p1 = ghl.pipeline(body.get("pipeline"))  # writes prepared before platform pipelines name none: the target's
    stage = canon(body.get("stage"))  # a write queued under a stage's old name goes to the same stage
    if op == "opportunity_create":
        data = ghl.call("POST", "/opportunities/", body={
            "pipelineId": p1["id"], "locationId": ghl.loc, "name": body["name"], "status": "open", "contactId": cid,
            "pipelineStageId": p1["ids"][stage]})
        oid = (data.get("opportunity") or {}).get("id")
        if not oid:
            raise GhlError("POST /opportunities/ returned no opportunity id")
        have.update(stage=stage, status="open")
        return {"opportunity_id": oid}, have, {"ghl_opportunity_id": oid}
    if op == "opportunity_stage":
        current = ghl.call("GET", f"/opportunities/{oid}", op="/opportunities/{id}").get("opportunity") or {}
        if current.get("pipelineId") and current["pipelineId"] != p1["id"]:  # a person took the card on: theirs, at any stage
            moved = p1["others"].get(current["pipelineId"]) or current["pipelineId"]
            raise Skip(moved, {**have, "moved": moved})
        if current.get("status") == "lost":
            raise Skip("lost", {**have, "moved": "lost", "status": "lost"})
        now_at = p1["names"].get(current.get("pipelineStageId"))
        stages = _stages(body.get("pipeline"))
        if _rank(now_at, stages) >= _rank(stage, stages):  # someone moved it on: theirs
            raise Skip(now_at, {**have, "stage": now_at})
        ghl.call("PUT", f"/opportunities/{oid}", op="/opportunities/{id}", body={"pipelineStageId": p1["ids"][stage]})
        have["stage"] = stage
        return {"opportunity_id": oid, "stage": stage}, have, {}
    raise GhlRefused(f"unknown op {op}")


def _lock():
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    f = open(config.STATE_DIR / "ghl.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close()
        raise GhlError("another GHL send is running")
    return f


def send(conn: sqlite3.Connection, ghl: Ghl, limit: int | None = None, only: str = "") -> dict[str, Any]:
    """Send prepared writes, lead by lead. `limit` caps the leads touched (1 for a canary); `only` picks one lead."""
    lock = _lock()
    try:
        # a capture is safe to repeat (its steps are remembered), so a cut-off one goes back to prepared
        conn.execute("UPDATE ghl_outbox SET status='prepared' WHERE status='sending' AND op IN ('contact_details')")
        cut = conn.execute("UPDATE ghl_outbox SET status='failed', error='cut off mid-call: it may have reached GHL. "
                           "Check the contact there before preparing it again' WHERE status='sending'").rowcount
        conn.commit()
        sql = "SELECT * FROM ghl_outbox WHERE status='prepared'" + (" AND lead_id=?" if only else "") + " ORDER BY id"
        pending = [dict(r) for r in conn.execute(sql, (only,) if only else ())]
        order: list[str] = []
        for r in pending:
            if r["lead_id"] not in order:
                order.append(r["lead_id"])
        # high tier first, then medium, then low; within a tier, the order they were prepared
        tier = dict(conn.execute("SELECT id, lower(coalesce(tier, '')) FROM leads").fetchall())
        order.sort(key=lambda i: {"high": 0, "medium": 1}.get(tier.get(i), 2))
        if limit is not None:
            order = order[:limit]
        done = {"sent": 0, "failed": 0, "skipped": 0, "leads": 0, "cut_off": cut, "errors": []}
        for lead_id in order:
            done["leads"] += 1
            # its contact first: a create prepared again (after a refused one) sits behind its own later writes
            for r in sorted([x for x in pending if x["lead_id"] == lead_id], key=lambda x: (x["op"] != "contact_create", x["id"])):
                row = here(ledger.lead(conn, lead_id))
                if r["op"] != "contact_create" and not row.get("ghl_contact_id"):
                    break  # its contact isn't made yet (or its create failed): these wait, prepared
                have = json.loads(row.get("ghl_have") or "{}")
                conn.execute("UPDATE ghl_outbox SET status='sending' WHERE id=?", (r["id"],))
                conn.commit()
                try:
                    receipt, have, cols = _apply(ghl, row, have, r)
                except Skip as s:
                    conn.execute("UPDATE ghl_outbox SET status='skipped', error=? WHERE id=?",
                                 (f"already at {s.stage}: theirs", r["id"]))
                    conn.execute("UPDATE leads SET ghl_have=? WHERE id=?", (json.dumps(s.have), lead_id))
                    conn.commit()
                    done["skipped"] += 1
                    continue
                except GhlError as exc:
                    why = ledger.scrub(str(exc))[:500]  # GHL can echo the email back in an error body
                    if r["op"] in CAPTURE_OPS:
                        body = json.loads(r["payload"])
                        tries = body.get("tries", 0) + 1
                        permanent = bool(re.search(r"HTTP 4(?!01|03|29)\d\d", str(exc))) or tries >= CAPTURE_TRIES
                        body["tries"] = tries
                        # transient (unreachable, 5xx, rate limit): back to prepared for the next cycle, values kept
                        # until it goes or the tries run out; a 4xx (GHL refused the value) is final
                        conn.execute("UPDATE ghl_outbox SET status=?, error=?, payload=? WHERE id=?",
                                     ("failed" if permanent else "prepared", why,
                                      json.dumps(_blank(body) if permanent else body), r["id"]))
                    else:
                        conn.execute("UPDATE ghl_outbox SET status='failed', error=? WHERE id=?", (why, r["id"]))
                    conn.commit()
                    done["failed"] += 1
                    done["errors"].append(f"{lead_id} {r['op']}: {why}"[:300])
                    break  # this lead's later writes depend on this one
                sets = {**cols, "ghl_have": json.dumps(have)}
                conn.execute(f"UPDATE leads SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), lead_id))
                conn.execute("UPDATE ghl_outbox SET status='sent', receipt=?, sent_at=? WHERE id=?",
                             (json.dumps(receipt), ledger.now(), r["id"]))
                if r["op"] in CAPTURE_OPS:  # sent: the values have done their job
                    conn.execute("UPDATE ghl_outbox SET payload=? WHERE id=?", (json.dumps(_blank(json.loads(r["payload"]))), r["id"]))
                conn.commit()
                done["sent"] += 1
        return done
    finally:
        lock.close()


def _sync_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    marks = ",".join("?" * len(OTHER_WRITER))
    return [here(dict(r)) for r in conn.execute(f"SELECT * FROM leads WHERE source='creators' OR campaign IN ({marks})",
                                                OTHER_WRITER)]


def _join(conn: sqlite3.Connection, ghl: Ghl, row: dict[str, Any], contact: dict[str, Any]) -> bool:
    """Put the lead on the sync's contact, and on its deal when it has one (a contact's search result carries its deals).
    A deal in another pipeline means a person took the card on, so its stage is never written. Returns whether the deal
    is known. The location goes in `have`: here() blanks an id it can't place in this sub-account."""
    p1, deals = ghl.pipeline(target()["pipeline"]), contact.get("opportunities") or []
    deal = next((d for d in deals if d.get("pipelineId") == p1["id"]), None) or \
        next((d for d in deals if d.get("status") != "lost"), None)
    have = {**(json.loads(row.get("ghl_have") or "{}") if attached(row) else {}), "location": ghl.loc, "attached": True}
    if deal:
        have.update(status=deal.get("status"))
        if deal.get("pipelineId") == p1["id"]:
            have.update(stage=p1["names"].get(deal.get("pipelineStageId")))
        else:
            have.update(moved=p1["others"].get(deal.get("pipelineId")) or deal.get("pipelineId"))
        if deal.get("status") == "lost":
            have.update(moved="lost")
    conn.execute("UPDATE leads SET ghl_contact_id=?, ghl_opportunity_id=?, ghl_have=?, ghl_attach_issue='' WHERE id=?",
                 (contact["id"], deal["id"] if deal else None, json.dumps(have), row["id"]))
    conn.commit()
    if contact.get("dnd") and row.get("local_state") != "held":  # they asked to stop on the sync's side
        ledger.record(conn, row["id"], local_state="held", reason="do not disturb on their GHL contact")
    return bool(deal)


def attach(conn: sqlite3.Connection, ghl: Ghl, only: str = "") -> dict[str, Any]:
    """Find the creators sync's contact for its leads that have none yet, by each lead's ask tag. One search a lead, up
    to REPLY_GHL_ATTACH_MAX a cycle: leads holding a captured detail first, then those who answered, then those we
    replied to, each cycle; then whoever was looked up longest ago, at most every LOOK_AGAIN_HOURS. No contact yet: the
    lead waits. It never makes one. Two contacts with the tag: a person looks, because guessing could put someone's
    email on someone else. Never raises."""
    if config.GHL_TARGET != SYNC_TARGET:
        return {"skipped": f"the creators sync writes {SYNC_TARGET}, not {config.GHL_TARGET}"}
    rows = _sync_rows(conn)
    capture = {r[0] for r in conn.execute("SELECT DISTINCT lead_id FROM ghl_outbox WHERE status='prepared' AND op='contact_details'")}
    todo = [r for r in rows if r.get("url") and r.get("state") != "skipped" and (not only or r["id"] == only)
            and not (attached(r) and r.get("ghl_opportunity_id"))]

    def need(r: dict[str, Any]) -> int:
        return 0 if r["id"] in capture else {"answered": 1, "replied": 2}.get(r["state"], 3)

    recent = (datetime.now(timezone.utc) - timedelta(hours=LOOK_AGAIN_HOURS)).isoformat(timespec="microseconds")
    todo = [r for r in todo if need(r) < 3 or (r.get("ghl_looked") or "") < recent]
    todo.sort(key=lambda r: (need(r), r.get("ghl_looked") or ""))
    out: Counter = Counter()
    error = ""
    for r in todo[:config.GHL_ATTACH_MAX]:
        tag = ask_tag(r["url"])
        try:
            found = ghl.contacts_tagged(tag)
            conn.execute("UPDATE leads SET ghl_looked=? WHERE id=?", (ledger.now(), r["id"]))
            if not found:
                out["waiting"] += 1
            elif len(found) > 1:
                conn.execute("UPDATE leads SET ghl_attach_issue=? WHERE id=?",
                             (f"more than one contact holds {tag}: a person picks", r["id"]))
                out["ambiguous"] += 1
            else:
                out["attached" if _join(conn, ghl, r, found[0]) else "contact_only"] += 1
            conn.commit()
        except GhlError as exc:  # the next cycle looks again; what's already attached still sends
            error = f"{type(exc).__name__}: {exc}"[:300]
            break
    return {**out, "looked_up": len(todo[:config.GHL_ATTACH_MAX]), "left": max(0, len(todo) - config.GHL_ATTACH_MAX),
            **_captures_waiting(conn, _sync_rows(conn)), **({"error": error} if error else {})}


def _captures_waiting(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Details people gave that have no contact to go to yet, and the days before the oldest is dropped."""
    no_contact = {r["id"] for r in rows if not attached(r)}
    held = [r["created_at"] for r in conn.execute("SELECT lead_id, created_at FROM ghl_outbox WHERE status='prepared' AND "
                                                  "op='contact_details'") if r["lead_id"] in no_contact]
    if not held:
        return {"captures_waiting": 0}
    age = datetime.now(timezone.utc) - datetime.fromisoformat(min(held))
    return {"captures_waiting": len(held), "capture_days_left": round(CAPTURE_KEEP_DAYS - age.total_seconds() / 86400, 1)}


def sync_status(conn: sqlite3.Connection) -> dict[str, Any]:
    """The creators and gig lanes: which leads are on the sync's contact, which wait, and what a person must look at."""
    rows = _sync_rows(conn)
    on = [r for r in rows if attached(r)]
    return {"leads": len(rows), "attached": len(on), "no_deal_yet": sum(1 for r in on if not r.get("ghl_opportunity_id")),
            "waiting_for_contact": sum(1 for r in rows if not attached(r) and r.get("state") != "skipped"),
            "problems": [{"lead": r["id"], "why": r["ghl_attach_issue"]} for r in rows if r.get("ghl_attach_issue")][:12],
            **_captures_waiting(conn, rows)}


def status(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = dict(conn.execute("SELECT status, COUNT(*) FROM ghl_outbox GROUP BY status").fetchall())
    waiting = [dict(r) for r in conn.execute(
        "SELECT o.lead_id, o.op, o.why, l.author, l.need, l.platform FROM ghl_outbox o JOIN leads l ON l.id=o.lead_id "
        "WHERE o.status IN ('prepared', 'failed') ORDER BY o.id LIMIT 12")]
    failed = [dict(r) for r in conn.execute("SELECT lead_id, op, error FROM ghl_outbox WHERE status='failed' LIMIT 12")]
    in_ghl = conn.execute("SELECT COUNT(*) FROM leads WHERE ghl_contact_id IS NOT NULL").fetchone()[0]
    fm = config.GHL_TARGET == "funding-machine"
    try:
        token = bool(sources._fm_token()) if fm else bool(config.GHL_TOKEN)
    except sources.SourceError:
        token = False
    location = config.FM_GHL_LOCATION if fm else config.GHL_LOCATION
    by_platform = {k: v["pipeline"] for k, v in BY_PLATFORM.get(config.GHL_TARGET, {}).items()} if config.GHL_PLATFORM_PIPELINES else {}
    return {"enabled": config.GHL, "target": config.GHL_TARGET, "pipeline": TARGETS.get(config.GHL_TARGET, {}).get("pipeline"),
            "platform_pipelines": by_platform, "creators_sync": sync_status(conn),
            "token": token, "location_allowed": location == TARGETS.get(config.GHL_TARGET, {}).get("location"),
            "from_state": config.GHL_FROM, "record": config.GHL_RECORD, "leads_in_ghl": in_ghl, "outbox": counts,
            "next": [{"lead": w["lead_id"], "op": w["op"], "why": w["why"],
                      "who": contact_name(w)} for w in waiting], "failed": failed}


def run(conn: sqlite3.Connection, limit: int | None = None, only: str = "", ghl: Ghl | None = None) -> dict[str, Any]:
    """Prepare always; attach and send only when REPLY_GHL is on, attach first so a lead that finds its contact sends
    in the same cycle. Never raises: a GHL problem is reported, it doesn't stop a cycle."""
    if not config.GHL and ghl is None:
        return {"prepare": prepare(conn), "sent": False, "why": "REPLY_GHL is off: the writes wait in the outbox"}
    out: dict[str, Any] = {}
    try:
        ghl = ghl or Ghl.from_config()
        out["location"] = ghl.check_location()
        out["attach"] = attach(conn, ghl, only)
        out["prepare"] = prepare(conn)
        out["send"] = send(conn, ghl, config.GHL_MAX if limit is None else limit, only)
    except GhlError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:400]
    if "prepare" not in out:
        out["prepare"] = prepare(conn)
    return out
