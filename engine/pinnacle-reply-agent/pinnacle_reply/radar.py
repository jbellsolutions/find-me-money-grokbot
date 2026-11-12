"""Client for Lead Radar's reply desk (funding-web), the queue of every lead it found.

    GET  /api/replies?status=all&limit=1000   every lead with its reply state
    POST /api/replies/{id}                    {status, draft, note, by}: what happened to one lead

Lead Radar never sends. This client never sends either, and it guards the desk: it writes only while
REPLY_WRITE is on, never touches a lead a person replied to, skipped or drafted, and appends to notes
instead of replacing them. Contact cards in the queue stay in memory and never reach the ledger or a log (G5).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from . import config

QUEUE_LIMIT = 1000  # the API's own maximum per page
MACHINE = {"", "draft", config.WRITER}  # `by` values that mean no person has touched the lead
NOTE_MAX = 4000


class RadarError(RuntimeError):
    pass


def _call(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 60) -> Any:
    if not config.RADAR_URL:
        raise RadarError("RADAR_URL isn't set (Lead Radar's funding-web address)")
    if not config.RADAR_PASSWORD:
        raise RadarError("RADAR_PASSWORD isn't set (the funding-web dashboard password)")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(config.RADAR_URL + path, data=data, method=method)
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"Bearer {config.RADAR_PASSWORD}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        raise RadarError(f"radar {method} {path} -> {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RadarError(f"radar unreachable at {config.RADAR_URL}: {exc.reason}") from exc


def queue(status: str = "all", campaign: str = "", min_tier: str = "low", limit: int = QUEUE_LIMIT,
          **page: str) -> dict[str, Any]:
    """One page: {status, total, items, truncated, next?}. `page` takes `since` and `offset` (radar-v2-ingest).
    truncated means the page was full and the count is a floor."""
    q = {"status": status, "min_tier": min_tier, "limit": str(limit), **{k: str(v) for k, v in page.items() if v}}
    if campaign:
        q["campaign"] = campaign
    out = _call("GET", "/api/replies?" + urllib.parse.urlencode(q))
    out["truncated"] = len(out.get("items") or []) >= limit
    return out


def queue_all(status: str = "all", campaign: str = "", min_tier: str = "low", since: str | None = None,
              pages: int | None = None) -> dict[str, Any]:
    """Every page of the desk: {status, total, items, truncated, paged}. A desk with paging answers `next` (the next
    offset, null on the last page) and `total`; one without it (before radar-v2-ingest) answers one page, as before.
    `since` (ISO date; default the last DESK_SINCE_DAYS days) keeps posts dated on or after it, plus undated ones.
    Rows can shift between pages while the queue changes, so items are deduplicated by id."""
    if since is None and config.DESK_SINCE_DAYS > 0:
        since = (datetime.now(timezone.utc) - timedelta(days=config.DESK_SINCE_DAYS)).date().isoformat()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset, out, paged, truncated = 0, {}, False, False
    for _ in range(max(1, pages or config.DESK_PAGES)):
        extra = {k: v for k, v in (("since", since), ("offset", offset)) if v}
        out = queue(status=status, campaign=campaign, min_tier=min_tier, **extra) or {}
        got = out.get("items") or []
        for it in got:
            if it.get("id") not in seen:
                seen.add(it.get("id"))
                items.append(it)
        if "next" not in out:  # a desk without paging: one page, a floor when it's full
            truncated = len(got) >= QUEUE_LIMIT
            break
        paged = True
        if out["next"] is None or not got:
            break
        offset = int(out["next"])
    else:
        truncated = True  # stopped at the page cap with more to read
    return {"status": status, "total": out.get("total", len(items)), "items": items, "truncated": truncated,
            "paged": paged, "since": since}


def health() -> dict[str, Any]:
    try:
        out = queue(status="open", limit=1)
        return {"ok": True, "url": config.RADAR_URL, "open_sample": out.get("total"), "write": config.WRITE}
    except RadarError as exc:
        return {"ok": False, "url": config.RADAR_URL, "error": str(exc), "write": config.WRITE}


def writable(item: dict[str, Any]) -> tuple[bool, str]:
    """Whether the agent may change this lead on the desk. People's work always wins."""
    reply = item.get("reply") or {}
    status, by = reply.get("status", "new"), reply.get("by") or ""
    if status == "new":
        return True, ""
    if status == "drafted" and by in MACHINE:
        return True, ""
    if status == "drafted":
        return False, f"{by} drafted it by hand"
    return False, f"already {status}" + (f" by {by}" if by else "")


def _note(item: dict[str, Any], line: str) -> str:
    old = ((item.get("reply") or {}).get("note") or "").strip()
    return (f"{old}\n{line}" if old else line)[-NOTE_MAX:]


def _save(item: dict[str, Any], body: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    if dry_run or not config.WRITE:
        return {"written": False, "would_send": body, "why": "dry run" if dry_run else "REPLY_WRITE is off"}
    return {"written": True, **_call("POST", f"/api/replies/{urllib.parse.quote(item['id'], safe='')}", body)}


def save_draft(item: dict[str, Any], draft: str, note: str, dry_run: bool = False) -> dict[str, Any]:
    ok, why = writable(item)
    if not ok:
        return {"written": False, "why": why}
    return _save(item, {"status": "drafted", "draft": draft, "note": _note(item, note), "by": config.WRITER}, dry_run)


def save_skip(item: dict[str, Any], reason: str, dry_run: bool = False) -> dict[str, Any]:
    ok, why = writable(item)
    if not ok:
        return {"written": False, "why": why}
    return _save(item, {"status": "skipped", "note": _note(item, f"reply-agent skip: {reason}"), "by": config.WRITER},
                 dry_run)


def save_hold(item: dict[str, Any], reason: str, dry_run: bool = False) -> dict[str, Any]:
    """The desk has no held status (F2). When a held lead still shows a machine draft that breaks the rules, clear
    that draft so nobody posts it, and write the hold reason in the note. A lead with no draft is left alone."""
    reply = item.get("reply") or {}
    ok, why = writable(item)
    if not ok or reply.get("status") != "drafted" or not reply.get("draft"):
        return {"written": False, "why": why or "nothing on the desk to clear"}
    return _save(item, {"draft": "", "note": _note(item, f"reply-agent hold: {reason}"), "by": config.WRITER}, dry_run)


def save_replied(item: dict[str, Any], poster: str, note: str = "", status: str = "replied",
                 dry_run: bool = False) -> dict[str, Any]:
    """Record a reply a person posted, as they reported it. `by` is that person, never the agent."""
    if status not in ("replied", "won"):
        raise ValueError("status is replied or won")
    if not poster or poster == config.WRITER:
        raise ValueError("say who posted it: a reply is only marked when a person posted it")
    current = (item.get("reply") or {}).get("status")
    if current in ("replied", "won") and status == "replied":
        return {"written": False, "why": f"already {current}"}
    line = f"reply-agent: {status} by {poster}" + (f" ({note})" if note else "")
    return _save(item, {"status": status, "note": _note(item, line), "by": poster[:60]}, dry_run)
