"""The Lending Hub's daily checklist, from the Reply Agent's side (hub docs/DAILY-CHECKLIST-API.md).

Each cycle the agent checks off every checklist line its lanes feed, then itself, then reports the calls booked
today from the Funding Machine's booking calendar (the hub counts interested and closed itself):

    GET  {HUB_URL}/api/daily          today's checklist, Eastern time, with the hub's own run check (`auto`)
    POST {HUB_URL}/api/daily/{id}     {status, leads, handed_off, replied, note, by}
    POST {HUB_URL}/api/quota          {booked, by}

A check-off says two things: the source ran today, and every lead it found went to the Reply Agent. The agent knows
the second; the first comes from what saw the source run: the hub's own check (the Funding Radar's runs, the
website forms that are always on), the creators and gig runs in radar-db, or the agent's own read of the inbox.
A line is `done` only when the source ran today, every lane feeding it was read and none of its leads is
unattended. Otherwise it is `partial`, and the note says which part is missing. A line none of whose lanes the agent
could read isn't posted at all: that's the agent's gap, not the source's, and the `reply-agent` line says so.

Posted only with REPLY_HUB on, and only when the check changed. A line someone else checked off today is left
alone: a person's check-off wins over the agent's, the way a person's work wins on the desk.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import config, ledger, sources

ET = ZoneInfo("America/New_York")
# Which lanes feed each checklist line, and what says the line's source ran today. Startup askers come from both the
# desk and the creators segments.
FEEDS = {
    "funding-radar": ("lead-radar",),
    "real-estate": ("lead-radar",),
    "startup": ("lead-radar", "creators"),
    "creators": ("creators",),
    "direct-sales": ("creators",),
    "gig": ("creators",),
    "website": ("website",),
    "ghl-inbound": ("inbound",),
}
RAN_BY = {
    "funding-radar": "hub:funding-radar", "real-estate": "hub:funding-radar", "startup": "hub:funding-radar",
    "website": "hub:website", "ghl-inbound": "read:inbound",
    "creators": "runs:creators", "direct-sales": "runs:creators", "gig": "runs:gig",
}
NEVER_READABLE = ("craigslist",)
SELF = "reply-agent"


class HubError(RuntimeError):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code  # the HTTP status, when the hub answered


def today() -> str:
    return datetime.now(timezone.utc).astimezone(ET).date().isoformat()


def _on(ts: str | None, day: str) -> bool:
    if not ts:
        return False
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return False
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(ET).date().isoformat() == day


def _call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    if not config.HUB_URL or not config.HUB_PASSWORD:
        raise HubError("HUB_URL and HUB_PASSWORD aren't both set")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(config.HUB_URL + path, data=data, method=method, headers={
        "Accept": "application/json", "Authorization": f"Bearer {config.HUB_PASSWORD}", "User-Agent": sources.UA,
        **({"Content-Type": "application/json"} if data is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        raise HubError(f"hub {method} {path} -> {exc.code}: {exc.read().decode(errors='replace')[:200]}", exc.code) from exc
    except urllib.error.URLError as exc:
        raise HubError(f"hub unreachable at {config.HUB_URL}: {exc.reason}") from exc
    except (OSError, ValueError) as exc:  # a timeout mid-read, or a page that isn't JSON (an old hub's HTML)
        raise HubError(f"hub {method} {path} gave no usable answer: {type(exc).__name__}") from exc


def quiet() -> set[str]:
    """GHL contact ids a funding partner has right now (spec 36): `GET /api/distribution/quiet` ->
    {"contact_ids": [...]}. The Reply Agent drafts nothing for these. An old hub answers 404: nobody is held, so an empty
    set. Anything else that goes wrong raises HubError, and the caller treats the list as unknown."""
    try:
        got = _call("GET", "/api/distribution/quiet")
    except HubError as exc:
        if exc.code == 404:
            return set()
        raise
    ids = got.get("contact_ids") if isinstance(got, dict) else None
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise HubError("hub GET /api/distribution/quiet gave an unexpected shape")
    return set(ids)


def partner_check(conn: sqlite3.Connection) -> dict[str, Any]:
    """Read the quiet list and mark the leads a funding partner has (ledger.set_partner_owned). Never raises. Only with
    REPLY_GHL on and the hub set. When the hub can't be read the answer is `unknown`: the flags from the last good read
    stay, and the callers pause follow-ups to leads already in GHL (a handoff needs an answer first, so first replies are
    safe either way). Quiet ids only match leads when the hub and this agent use the same GHL sub-account."""
    out: dict[str, Any] = {"checked": False, "unknown": False, "ids": 0, "held": 0, "released": 0, "why": ""}
    if not config.GHL:
        return {**out, "why": "REPLY_GHL is off"}
    if not (config.HUB_URL and config.HUB_PASSWORD):
        return {**out, "why": "HUB_URL and HUB_PASSWORD aren't both set, so no handoff can be seen"}
    try:
        ids = quiet()
    except HubError as exc:
        return {**out, "unknown": True, "why": str(exc)[:200]}
    out.update(checked=True, ids=len(ids), **ledger.set_partner_owned(conn, ids))
    out["partner_leads"] = conn.execute("SELECT COUNT(*) FROM leads WHERE partner_hold=1").fetchone()[0]
    return out


def _line(rows: list[dict[str, Any]], day: str) -> dict[str, Any]:
    states = Counter(r["state"] for r in rows)
    why = Counter(r["reason"].split(":")[0] for r in rows if r["state"] == "unattended")
    on = Counter(r["poster"] or "nobody" for r in rows if r["state"] == "waiting")
    return {
        "leads": sum(1 for r in rows if _on(r["first_seen"], day)),
        "replied": sum(1 for r in rows if _on(r.get("replied_at"), day) or _on(r.get("marked_at"), day)),
        "unattended": states["unattended"],
        "note": f"{len(rows)} in the ledger: {states['replied']} replied, {states['waiting']} waiting"
                + (f" ({', '.join(f'on {k} {v}' for k, v in on.most_common(3))})" if on else "")
                + f", {states['held']} held, {states['skipped']} skipped, {states['answered']} answered"
                + (f"; {states['unattended']} unattended: " + "; ".join(f"{k} ({v})" for k, v in why.most_common(3))
                   if states["unattended"] else ""),
    }


def ran_today(line: str, read: dict[str, str], day: str, have: dict[str, dict[str, Any]] | None,
              ran: dict[str, str | None] | None) -> tuple[bool | None, str, int | None]:
    """(ran, note, leads the source itself counted): True ran today, False didn't, None nothing says."""
    kind, _, key = RAN_BY[line].partition(":")
    if kind == "read":
        return (True, "", None) if not read.get(key, "not read") else (None, "", None)
    if kind == "hub":
        row = (have or {}).get(key)
        if row is None or "auto" not in row:
            return None, "the hub's own run check couldn't be read", None
        auto = row["auto"]
        if not auto:
            return False, "the hub saw no run today", None
        return auto.get("status") == "done", auto.get("note") or "", auto.get("leads") if key == line else None
    at = (ran or {}).get(key)
    if not at:
        return None, f"no {key} run on record", None
    return (True, "ran today", None) if _on(at, day) else (False, f"no run today (last {at[:16].replace('T', ' ')} UTC)", None)


def checks(conn: sqlite3.Connection, read: dict[str, str], day: str | None = None,
           have: dict[str, dict[str, Any]] | None = None,
           ran: dict[str, str | None] | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """({checklist id: the check-off to post}, {checklist id: why it isn't posted}), from the ledger, which lanes were
    read ({lane: why, "" = read}), the hub's own checks (`have`) and the creators and gig runs (`ran`)."""
    day = day or today()
    rows = [dict(r) for r in conn.execute("SELECT * FROM leads")]
    out: dict[str, dict[str, Any]] = {}
    unposted: dict[str, str] = {}
    for hub_id, lanes_in in FEEDS.items():
        missing = {lane: read.get(lane, "not read") for lane in lanes_in if read.get(lane, "not read")}
        if len(missing) == len(lanes_in):
            unposted[hub_id] = "; ".join(sorted(set(missing.values())))
            continue
        line = _line([r for r in rows if r.get("hub") == hub_id], day)
        did_run, run_note, source_leads = ran_today(hub_id, read, day, have, ran)
        parts = [run_note] if run_note else []
        if did_run is None and not run_note:
            parts.append("no run seen today")
        parts.append("Reply Agent: " + line["note"])
        if missing:
            parts.append("Not read: " + "; ".join(f"{k} ({v})" for k, v in missing.items()))
        status = "done" if did_run and not line["unattended"] and not missing else "partial"
        out[hub_id] = {"status": status, "leads": line["leads"] if source_leads is None else int(source_leads),
                       "handed_off": line["leads"], "replied": line["replied"], "note": ". ".join(parts)[:1000],
                       "by": SELF, "day": day}
    every = _line(rows, day)
    unread = {k: why for k, why in ledger.coverage(read).items() if why and k not in NEVER_READABLE}
    note = every["note"]
    if unread:
        note += ". Lanes not read: " + "; ".join(f"{k} ({v})" for k, v in unread.items())
    if unposted:
        note += ". Not checked off (couldn't read them): " + ", ".join(unposted)
    note += ". Craigslist replies can't be read: they go to whoever posted the ad"
    out[SELF] = {"status": "partial" if every["unattended"] or unread else "done", "leads": every["leads"],
                 "handed_off": every["leads"], "replied": every["replied"], "by": SELF, "day": day,
                 "note": note[:1000]}
    return out, unposted


def _same(a: dict[str, Any] | None, b: dict[str, Any]) -> bool:
    return bool(a) and all(str(a.get(k) or "") == str(b.get(k) or "") for k in ("status", "leads", "handed_off",
                                                                                 "replied", "note"))


def report(conn: sqlite3.Connection, read: dict[str, str], dry_run: bool = False, count_booked: bool | None = None,
           ran: dict[str, str | None] | None = None) -> dict[str, Any]:
    """Work out every check-off and the booked count, and post what changed while REPLY_HUB is on. The booked count
    reads the Funding Machine calendar, so it runs only with the hub on, unless `count_booked` asks for it."""
    day = today()
    on = config.HUB and not dry_run
    out: dict[str, Any] = {"day": day, "on": on, "posted": [], "unchanged": [], "left_alone": {}, "errors": []}
    have: dict[str, dict[str, Any]] | None = None
    quota: dict[str, Any] = {}
    if config.HUB_URL and config.HUB_PASSWORD:
        try:
            got = _call("GET", f"/api/daily?day={day}") or {}
            have, quota = {s["id"]: s for s in got.get("sources") or []}, got.get("quota") or {}
        except HubError as exc:
            out["errors"].append(str(exc))
    want, unposted = checks(conn, read, day, have, ran)
    out["not_posted"] = unposted
    booked: dict[str, Any] = {"booked": None, "why": "counted only with REPLY_HUB on"}
    if on if count_booked is None else count_booked:
        try:
            booked = sources.booked(day, ET)
        except sources.SourceError as exc:
            booked = {"booked": None, "why": str(exc)}
    out["booked"] = booked
    if not on:
        out.update(would_post=want, why="dry run" if dry_run else "REPLY_HUB is off")
        return out
    if have is None:
        return out  # the GET failed: post nothing blind
    for hub_id, body in want.items():
        if hub_id not in have:
            continue  # a line the hub doesn't list
        current = have[hub_id].get("check")
        if current and current.get("at") and current.get("by") != SELF:
            out["left_alone"][hub_id] = f"checked off by {current.get('by') or 'someone'}"
            continue
        if _same(current, body):
            out["unchanged"].append(hub_id)
            continue
        try:
            _call("POST", f"/api/daily/{hub_id}", body)
            out["posted"].append(hub_id)
        except HubError as exc:
            out["errors"].append(str(exc))
    if booked.get("booked") is not None:
        if quota.get("reported_by") not in ("", None, SELF):
            out["left_alone"]["quota"] = f"reported by {quota['reported_by']}"
        elif (quota.get("booked") or {}).get("value") != booked["booked"] or \
                (quota.get("booked") or {}).get("source") != "reported":
            try:
                _call("POST", "/api/quota", {"booked": booked["booked"], "by": SELF, "day": day})
                out["posted"].append("quota")
            except HubError as exc:
                out["errors"].append(str(exc))
    return out
