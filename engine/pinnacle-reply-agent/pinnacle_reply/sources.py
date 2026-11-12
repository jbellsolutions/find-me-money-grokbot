"""Every lane the Reply Agent reads, each turned into items in Lead Radar's desk shape so one ledger holds them all.

    lead-radar   Lead Radar's reply desk (radar.py). Real estate rides in it: lanes P1 and P2.
    creators     radar-db: askers under tracked creators, the startup and direct-sales segments, and gig workers.
                 The creators lane drafts its own replies (ic_replies) and is the only writer of those tables.
    website      the Lending Hub's website and app leads: deals whose source starts website: or web-.
    inbound      the Funding Machine GHL inbox: every conversation, waiting on a person when they wrote last.
    craigslist   not readable: a reply to an ad goes to whoever posted it.

Each item carries `source` (its lane), `policy` and `hub` (its line on the hub's daily checklist). Policy says who
writes the reply: `desk`, the agent drafts and Lead Radar's desk takes its writes; `lane`, the lane drafts and the
agent drafts only what the lane hasn't; `direct`, a private conversation with someone who gave us their details,
answered by a person in GHL and never drafted here.

Nothing here writes anywhere. No contact detail leaves this module (G5): an item says only whether one exists, names
are cut to a first name and an initial, and only public words (a post, a comment) or a form's stated purpose are
kept as text. A private message from the inbox never is: the ledger and the vault keep only who waits and why.
"""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from . import config, lanes, radar

DIRECT = ("website", "inbound")
LANE_DRAFTS = ("creators",)
REAL_ESTATE = ("P1", "P2")
STARTUP = re.compile(r"startup|new-founder|buying-a-business|acquisition|franchise|laid-off|vending|laundromat|atm-claw",
                     re.I)
UA = "pinnacle-reply-agent"


class SourceError(RuntimeError):
    pass


def _read(lane: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """{lane, ok, items, why, truncated}. A lane that fails or isn't set up is reported, never fatal to the cycle."""
    if config.LANES_ON and lane not in config.LANES_ON:
        return {"lane": lane, "ok": False, "items": [], "why": "off (REPLY_SOURCES)", "truncated": False}
    try:
        out = fn()
    except (SourceError, radar.RadarError, OSError, ValueError, KeyError) as exc:
        return {"lane": lane, "ok": False, "items": [], "why": str(exc)[:300], "truncated": False}
    return {"lane": lane, "ok": True, "why": "", "truncated": False, **out}


def url_key(url: str | None) -> str:
    """One post however it's linked: no scheme or www, lower-case host, no trailing slash, no tracking parameters."""
    if not url:
        return ""
    p = urllib.parse.urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.").removeprefix("m.")
    keep = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith(("utm_", "fbclid", "mibextid"))]
    return f"{host}{p.path.rstrip('/')}" + (f"?{urllib.parse.urlencode(sorted(keep))}" if keep else "")


def dedupe(reads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """No double contact (spec 32 Y9): Radar V2 imports the creators and gig lanes into the desk too, so the same asker
    can arrive twice. The lane's own read (radar-db, with the person and their answers) wins; the desk copy is
    dropped and counted."""
    owned = {url_key(i.get("url")) for r in reads if r["lane"] != "lead-radar" for i in r.get("items") or []}
    owned.discard("")
    for r in reads:
        if r["lane"] == "lead-radar" and owned:
            keep = [i for i in r.get("items") or [] if url_key(i.get("url")) not in owned]
            r["deduped"], r["items"] = len(r.get("items") or []) - len(keep), keep
    return reads


def read_all() -> list[dict[str, Any]]:
    return dedupe([_read("lead-radar", lead_radar), _read("creators", creators), _read("website", website),
                   _read("inbound", inbound), _read("craigslist", craigslist)])


def _short_name(name: str | None) -> str:
    """'Jane Doe' -> 'Jane D.': enough to tell people apart in the vault, not enough to find them."""
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if not parts:
        return ""
    first = parts[0].capitalize()[:30]
    return f"{first} {parts[-1][0].upper()}." if len(parts) > 1 else first


def _iso(value: Any) -> str | None:
    """GHL gives milliseconds or ISO strings; radar-db gives datetimes. Always an ISO string in UTC, or None."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(int(value) / 1000, timezone.utc).isoformat()
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat()


def _get(url: str, headers: dict[str, str], timeout: float = 40) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA, **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        raise SourceError(f"GET {url.split('?')[0]} -> {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SourceError(f"{url.split('/')[2]} unreachable: {exc.reason}") from exc


# ------------------------------------------------------------------------------------------------ Lead Radar's desk
def radar_hub(item: dict[str, Any]) -> str:
    """Which checklist line a desk lead counts toward."""
    if lanes.persona_for(item.get("campaign") or "", lanes.post_text(item)) in REAL_ESTATE:
        return "real-estate"
    return "startup" if STARTUP.search(item.get("campaign") or "") else "funding-radar"


def lead_radar() -> dict[str, Any]:
    pulled = radar.queue_all(status="all")
    items = [{**i, "source": "lead-radar", "policy": "desk", "hub": radar_hub(i)} for i in pulled.get("items") or []]
    return {"items": items, "truncated": bool(pulled.get("truncated"))}


# ------------------------------------------------------------------------------------------------ creators (radar-db)
PEOPLE_SQL = """
select p.id, p.platform, p.handle, p.name, p.need, p.quote, p.fit, p.stage, p.held_reason, p.creators,
       p.first_ask_at, p.last_inbound_at, p.funded_at, p.account,
       c.id as comment_id, c.url, c.text, c.posted_at, c.creator_id,
       r.status as reply_status, r.draft, r.sent_at, r.sent_as,
       a.text as answer, a.at as answered_at,
       to_jsonb(k) ->> 'campaign' as campaign, to_jsonb(k) ->> 'segment' as segment
from radar.ic_people p
left join lateral (select * from radar.ic_comments x where x.person_id = p.id and x.is_lead
                   order by x.found_at desc limit 1) c on true
left join radar.ic_replies r on r.comment_id = c.id
left join lateral (select m.text, m.at from radar.ic_messages m where m.person_id = p.id and m.direction = 'in'
                   and m.channel in ('reply', 'dm', 'email') order by m.at desc limit 1) a on true
left join radar.ic_creators k on k.id = c.creator_id
order by p.last_ask_at desc nulls last
limit %s
"""
PEOPLE_LIMIT = 5000
LANE_BY = "creators-lane"
RUNS = (("creators", "ic_runs"), ("gig", "gig_runs"))  # when radar-creators and radar-gig last ran


def _people(url: str) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    try:
        import psycopg
    except ImportError as exc:
        raise SourceError("psycopg isn't installed in this Python (pip install 'psycopg[binary]')") from exc
    try:
        with psycopg.connect(url, connect_timeout=20) as conn:
            conn.read_only = True  # the creators lane is the only writer of its tables
            with conn.cursor() as cur:
                cur.execute("set statement_timeout = '60s'")
                cur.execute(PEOPLE_SQL, (PEOPLE_LIMIT,))
                cols = [d.name for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                ran: dict[str, str | None] = {}
                for lane, table in RUNS:
                    cur.execute("select to_regclass(%s) is not null", (f"radar.{table}",))
                    if (cur.fetchone() or [False])[0]:
                        cur.execute(f"select max(started_at) from radar.{table}")
                        ran[lane] = _iso((cur.fetchone() or [None])[0])
                return rows, ran
    except psycopg.Error as exc:
        raise SourceError(f"radar-db: {type(exc).__name__}: {str(exc).splitlines()[0][:200]}") from exc


def person_item(p: dict[str, Any]) -> dict[str, Any]:
    """One asker in the creators pipeline, as a desk item. The lane's stage says where the reply stands."""
    asked_under = list(p.get("creators") or []) + [p.get("creator_id") or ""]
    gig = any(str(c).startswith("gig:") for c in asked_under)
    segment = (p.get("segment") or "").lower()
    hub = "gig" if gig else "startup" if "startup" in segment else "direct-sales" if "direct" in segment else "creators"
    stage = p.get("stage") or "found"
    draft = p.get("draft") or ""
    reply: dict[str, Any] = {"status": "new", "by": "", "draft": "", "note": ""}
    if p.get("funded_at"):
        reply.update(status="won", by=p.get("sent_as") or p.get("account") or LANE_BY, replied_at=_iso(p.get("sent_at")))
    elif stage in ("sent", "answered", "conversation", "plan_offered", "prequal_submitted"):
        reply.update(status="replied", by=p.get("sent_as") or p.get("account") or LANE_BY,
                     replied_at=_iso(p.get("sent_at")), draft=draft)
    elif stage == "held":
        reply.update(status="held", reason=f"held by the creators lane: {p.get('held_reason') or 'no reason given'}")
    elif stage == "suppressed":
        reply.update(status="skipped", reason="suppressed by the creators lane")
    elif draft and p.get("reply_status") in ("drafted", "flagged", None):
        reply.update(status="drafted", draft=draft)  # the lane's own draft, judged on G3 (ledger.judge)
    campaign = p.get("campaign") or (f"gig-{str(p.get('creator_id'))[4:]}" if gig else f"creators-{segment or 'tracked'}")
    item = {"id": f"creators:{p['id']}", "source": "creators", "policy": "lane", "hub": hub, "kind": "comment",
            "campaign": campaign, "platform": p.get("platform"), "tier": p.get("fit") or "medium",
            "url": p.get("url"), "author": _short_name(p.get("name") or p.get("handle")), "need": p.get("need") or "",
            "quote": p.get("quote") or "", "text": p.get("text") or "", "contact": None,
            "posted_at": _iso(p.get("posted_at") or p.get("first_ask_at")), "reply": reply}
    if stage == "answered" and p.get("answer"):
        item.update(answer=p["answer"], answered_at=_iso(p.get("answered_at")))
    return item


def creators() -> dict[str, Any]:
    if not config.CREATORS_DB_URL:
        raise SourceError("CREATORS_DB_URL isn't set: the agent needs a read-only radar-db URL to read this lane")
    rows, ran = _people(config.CREATORS_DB_URL)
    return {"items": [person_item(p) for p in rows], "truncated": len(rows) >= PEOPLE_LIMIT, "ran": ran}


# ------------------------------------------------------------------------------------------------ website (the hub)
WEBSITE = ("website:", "web-")
TEST = re.compile(r"\btest\b", re.I)


def deal_item(d: dict[str, Any]) -> dict[str, Any]:
    intake = d.get("intake") or {}
    purpose = " ".join(str(intake.get("purpose") or "").split())
    amount = intake.get("requested_amount")
    need = (f"${float(amount):,.0f} " if isinstance(amount, (int, float)) and amount else "") + purpose[:200]
    stage = d.get("stage") or "received"
    consent = "consent to contact on file" if d.get("consent_to_contact") else "no consent to contact recorded"
    if TEST.search(d.get("contact_name") or "") or TEST.search(d.get("notes") or ""):
        reply = {"status": "skipped", "reason": "a test submission"}
    elif stage != "received":
        reply = {"status": "replied", "by": d.get("owner") or "the team", "replied_at": _iso(d.get("updated_at"))}
    else:
        reply = {"status": "new", "reason": f"a form lead, {consent}: call, text or email them from GHL"}
    return {"id": f"website:{d['id']}", "source": "website", "policy": "direct", "hub": "website", "kind": "form",
            "campaign": d.get("source") or "website", "platform": "website", "tier": "high",
            "url": f"{config.HUB_URL}/#deals/{d['id']}", "author": _short_name(d.get("contact_name")), "need": need,
            "quote": "", "text": purpose, "contact": bool(d.get("contact_email") or d.get("contact_phone")) or None,
            "posted_at": _iso(d.get("created_at")), "reply": {"by": "", "draft": "", "note": "", **reply}}


def website() -> dict[str, Any]:
    if not config.HUB_URL or not config.HUB_PASSWORD:
        raise SourceError("HUB_URL and HUB_PASSWORD aren't both set (the hosted Lending Hub)")
    deals = (_get(config.HUB_URL + "/api/deals", {"Authorization": f"Bearer {config.HUB_PASSWORD}"}) or {}).get("deals")
    return {"items": [deal_item(d) for d in deals or [] if str(d.get("source") or "").startswith(WEBSITE)]}


# ------------------------------------------------------------------------------------------------ the Funding Machine inbox
GHL = "https://services.leadconnectorhq.com"
CHANNEL = {"TYPE_EMAIL": "email", "TYPE_SMS": "sms", "TYPE_CALL": "call", "TYPE_NO_SHOW": "calendar",
           "TYPE_FACEBOOK": "facebook", "TYPE_INSTAGRAM": "instagram", "TYPE_WEBCHAT": "webchat"}


def _fm_token() -> str:
    if config.FM_GHL_TOKEN:
        return config.FM_GHL_TOKEN
    path = config.FM_ENV_FILE
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.strip().partition("=")
            if key.strip() == "GHL_API_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
    raise SourceError("no Funding Machine token: set FM_GHL_API_KEY (or GHL_API_KEY in FM_GHL_ENV)")


def fm_get(path: str, params: dict[str, Any], version: str = "2021-04-15") -> Any:
    """A read from the Funding Machine sub-account. GET only; this client has no way to write."""
    url = GHL + path + "?" + urllib.parse.urlencode({"locationId": config.FM_GHL_LOCATION, **params})
    return _get(url, {"Authorization": f"Bearer {_fm_token()}", "Version": version})


SELF_MADE = "not a lead: the empty conversation GHL opens when the Reply Agent adds a contact"


def our_contacts() -> set[str]:
    """The GHL contacts the Reply Agent made itself (ghl.py). GHL opens an empty conversation for each one, typed as a
    no-show, which is nobody writing in. Read straight from the ledger file: ledger.py imports this module."""
    try:
        with sqlite3.connect(config.LEDGER_DB) as conn:
            return {r[0] for r in conn.execute("SELECT ghl_contact_id FROM leads WHERE ghl_contact_id IS NOT NULL")}
    except sqlite3.Error:
        return set()


def conversation_item(c: dict[str, Any], ours: set[str] | frozenset[str] = frozenset()) -> dict[str, Any]:
    kind = c.get("lastMessageType") or ""
    direction = c.get("lastMessageDirection")
    at = _iso(c.get("lastMessageDate") or c.get("dateUpdated"))
    if c.get("contactId") in ours and not direction and not c.get("lastMessageBody"):
        # Found 2026-11-02: 459 of these, made 50 at a time by the agent's own GHL sync, were counted as missed calls
        reply = {"status": "skipped", "note": f"reply-agent skip: {SELF_MADE}"}
    elif kind == "TYPE_NO_SHOW":
        reply = {"status": "new", "reason": "they missed their booked call: rebook them"}
    elif direction == "inbound" or (c.get("unreadCount") or 0) > 0:
        reply = {"status": "new", "reason": f"they wrote last ({CHANNEL.get(kind, 'message')}), no reply yet"}
    elif direction == "outbound":
        by = "a GHL workflow" if c.get("lastOutboundMessageAction") == "automated" else "a person in GHL"
        reply = {"status": "replied", "by": by, "replied_at": at}
    else:
        reply = {"status": "new", "reason": "nothing in the conversation says who wrote last: open it"}
    return {"id": f"fm-inbox:{c['id']}", "source": "inbound", "policy": "direct", "hub": "ghl-inbound",
            "kind": "conversation", "campaign": "fm-inbox", "platform": CHANNEL.get(kind, "ghl"),
            "tier": "high" if reply["status"] == "new" else "medium",
            "url": f"https://app.myfundingmachine.com/v2/location/{config.FM_GHL_LOCATION}/conversations/conversations/{c['id']}",
            "author": _short_name(c.get("contactName") or c.get("fullName")), "need": "",
            "quote": "", "text": "",  # a private message: never kept
            "contact": bool(c.get("email") or c.get("phone")) or None,
            "posted_at": _iso(c.get("dateAdded")) or at, "reply": {"by": "", "draft": "", "note": "", **reply}}


def inbound(limit: int = 100, pages: int = 20) -> dict[str, Any]:
    items, cursor, ours = [], None, our_contacts()
    for _ in range(pages):
        params: dict[str, Any] = {"limit": limit, "sortBy": "last_message_date", "sort": "desc"}
        if cursor:
            params["startAfterDate"] = cursor
        got = (fm_get("/conversations/search", params) or {}).get("conversations") or []
        items += [conversation_item(c, ours) for c in got]
        if len(got) < limit:
            return {"items": items}
        cursor = (got[-1].get("sort") or [got[-1].get("lastMessageDate")])[0]
    return {"items": items, "truncated": True}


def booked(day: str, tz) -> dict[str, Any]:
    """Calls booked on `day` (Eastern): events on the booking calendars added that day, not cancelled."""
    start = datetime.fromisoformat(day).replace(tzinfo=tz)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    seen: dict[str, dict[str, Any]] = {}
    for cal in config.FM_CALENDARS:
        got = fm_get("/calendars/events", {"calendarId": cal, "startTime": int(start.timestamp() * 1000),
                                           "endTime": now_ms + 120 * 86_400_000})
        for e in (got or {}).get("events") or []:
            seen[e.get("id") or str(len(seen))] = e
    count = 0
    for e in seen.values():
        added = _iso(e.get("dateAdded"))
        if not added or (e.get("appointmentStatus") or "").lower() in ("cancelled", "invalid"):
            continue
        if datetime.fromisoformat(added).astimezone(tz).date().isoformat() == day:
            count += 1
    return {"booked": count, "calendars": len(config.FM_CALENDARS), "events_seen": len(seen)}


# ------------------------------------------------------------------------------------------------ Craigslist
def craigslist() -> dict[str, Any]:
    raise SourceError("not readable: a reply to a Craigslist ad goes to the poster's email or phone. Put the "
                      "Funding Machine number or inbox on the ads and those replies arrive in the inbound lane")
