"""The loop-close audit (doc 33): is every lead we found answered, and checked off?

Every lead found opens a loop. Justin, 2026-11-02: "If it was open, meaning we found it, it needs to have been replied
to, responded to, and checked off somehow." So a loop is

    open      unattended (nothing done yet), waiting (a checked draft nobody has posted), held (a person decides),
              answered (they wrote back and the follow-up is ours to post)
    closed    replied (posted, and the next word is theirs), skipped (not a lead, with the reason), partner (a funding
              partner has the lead and owns the conversation, so the agent drafts nothing)

`unattended` = 0 only says the agent did its part. A draft waiting for a poster is still an open loop, so this audit
counts it as one, says how long it has been open and who it waits on, and lists the oldest. It reads the ledger only:
no model call, no network, nothing written outside the agent's own folders. The 6 pm cron (`pra-loop-close`) runs it.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import config, ledger

OPEN = ("unattended", "waiting", "held", "answered")
CLOSED = ("replied", "skipped", "partner")
EASTERN = ZoneInfo("America/New_York")
AGES = (("under 24h", 1), ("1-3 days", 3), ("over 3 days", None))
TIER_RANK = {"high": 0, "medium": 1, "low": 2}


def _when(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def opened_at(r: dict[str, Any]) -> datetime | None:
    """When this loop's current wait began: the draft for waiting, their answer for answered, else when found."""
    if r["state"] == "waiting":
        return _when(r.get("waiting_since")) or _when(r.get("first_seen"))
    if r["state"] == "answered":
        return _when(r.get("answered_at")) or _when(r.get("first_seen"))
    return _when(r.get("first_seen"))


def _age(r: dict[str, Any], now: datetime) -> str:
    t = opened_at(r)
    days = (now - t).total_seconds() / 86400 if t else 0
    for name, limit in AGES:
        if limit is None or days < limit:
            return name
    return AGES[-1][0]


def audit(conn: sqlite3.Connection, now: datetime | None = None, oldest: int = 15) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    day = now.astimezone(EASTERN).date()
    start = datetime.combine(day, datetime.min.time(), EASTERN).astimezone(timezone.utc)
    rows = [dict(r) for r in conn.execute("SELECT * FROM leads")]
    opened = [r for r in rows if r["state"] in OPEN]
    said_today = Counter(m["kind"] for m in conn.execute(
        "SELECT kind FROM messages WHERE kind IN ('reply', 'skipped', 'answer') AND at >= ?", (start.isoformat(),)))
    found_today = sum(1 for r in rows if (_when(r.get("first_seen")) or start) >= start)
    by_stage = {s: dict(Counter(_age(r, now) for r in opened if r["state"] == s)) for s in OPEN}
    late = sorted(opened, key=lambda r: (TIER_RANK.get(r.get("tier") or "low", 3), opened_at(r) or now))
    late = [r for r in late if r.get("tier") in ("high", "medium")][:oldest] or late[:oldest]
    return {
        "day": day.isoformat(),
        "found": len(rows),
        "open": len(opened),
        "closed": sum(1 for r in rows if r["state"] in CLOSED),
        "closed_all": not opened,
        "by_stage": {s: {"count": sum(v.values()), "age": v} for s, v in by_stage.items() if v},
        "open_over_24h": sum(1 for r in opened if _age(r, now) != AGES[0][0]),
        "today": {"found": found_today, "replies_posted": said_today["reply"], "answers_in": said_today["answer"],
                  "skipped": said_today["skipped"]},
        "waiting_on": dict(Counter(r.get("poster") or "nobody" for r in opened if r["state"] == "waiting").most_common()),
        "open_by_platform": dict(Counter(r.get("platform") or "?" for r in opened).most_common()),
        "open_by_source": dict(Counter(r.get("source") or "?" for r in opened).most_common()),
        "open_by_tier": dict(Counter(r.get("tier") or "?" for r in opened).most_common()),
        "oldest_open": [{"id": r["id"], "state": r["state"], "tier": r.get("tier"), "platform": r.get("platform"),
                         "poster": r.get("poster"), "since": (opened_at(r) or now).isoformat(timespec="minutes"),
                         "reason": r.get("reason"), "url": r.get("url")} for r in late],
    }


def markdown(a: dict[str, Any]) -> str:
    verdict = "**Every loop is closed.**" if a["closed_all"] else \
        f"**{a['open']} loops are open** ({a['open_over_24h']} for over 24 hours). {a['closed']} closed."
    t = a["today"]
    lines = [f"# Loop close {a['day']} (6 pm Eastern)", "", verdict, "",
             f"Today: {t['found']} found, **{t['replies_posted']} replies posted**, {t['answers_in']} answers in, "
             f"{t['skipped']} skipped.", "", "## Open, by stage", ""]
    names = {"unattended": "Nothing done yet", "waiting": "Draft ready, nobody has posted it",
             "held": "Held for a person to decide", "answered": "They wrote back, our follow-up is owed"}
    for s, v in a["by_stage"].items():
        ages = ", ".join(f"{k} {n}" for k, n in v["age"].items())
        lines.append(f"- {names[s]}: **{v['count']}** ({ages})")
    if a["waiting_on"]:
        lines += ["", "Waiting on: " + ", ".join(f"{k} {v}" for k, v in a["waiting_on"].items())]
    lines += ["", "Open by platform: " + ", ".join(f"{k} {v}" for k, v in a["open_by_platform"].items()),
              "Open by source: " + ", ".join(f"{k} {v}" for k, v in a["open_by_source"].items()),
              "", "## Oldest open (high and medium first)", ""]
    for r in a["oldest_open"]:
        why = f"{r['state']} on {r['poster'] or 'nobody'}" if r["state"] == "waiting" else f"{r['state']}: {r['reason'] or ''}"
        lines.append(f"- {r['since'][:16].replace('T', ' ')} · {r['tier']} · {r['platform']} · {why} · {r['url'] or r['id']}")
    return "\n".join(lines) + "\n"


def write(a: dict[str, Any]) -> list[str]:
    """The audit as a daily note, next to the daily ledger (and in the vault's Ledgers folder)."""
    out = []
    for folder in [config.STATE_DIR / "ledgers"] + ([config.VAULT_DIR / "Ledgers"] if config.VAULT_DIR else []):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"Loop close {a['day']}.md"
        path.write_text(markdown(a), encoding="utf-8")
        out.append(str(path))
    return out


def run(now: datetime | None = None) -> dict[str, Any]:
    with ledger.connect() as conn:
        a = audit(conn, now)
    return {**a, "notes": write(a)}
