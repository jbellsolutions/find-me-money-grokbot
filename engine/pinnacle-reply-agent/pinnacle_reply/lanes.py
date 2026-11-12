"""Lanes: which persona a lead belongs to, who posts it today, and the holds that come from Justin's rules."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import config


def personas_file() -> Path:
    """The private persona names: REPLY_PERSONAS, else <workspace>/.secrets/personas.json (workspace = BOT_HOME, else
    the folder above REPLY_HOME). {"P1": {"name": "..."}, ...}. Set at intake; the pack ships placeholders only."""
    import os
    explicit = os.environ.get("REPLY_PERSONAS", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    ws = os.environ.get("BOT_HOME", "").strip()
    return (Path(ws) if ws else config.REPLY_HOME.parent) / ".secrets" / "personas.json"


def _private_names() -> dict[str, str]:
    try:
        raw = json.loads(personas_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v.get("name") if isinstance(v, dict) else v).strip() for k, v in raw.items()
            if (v.get("name") if isinstance(v, dict) else v)}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    names = _private_names()
    data["_personas_ready"] = bool(names) and all(k in names for k in data.get("personas", {}))
    for pid, name in names.items():
        if pid in data.get("personas", {}):
            data["personas"][pid]["name"] = name
    data["_rules"] = [(re.compile(r["match"], re.I), r["persona"]) for r in data.get("campaign_lanes", [])]
    data["_text_rules"] = [(re.compile(r["match"], re.I), r["persona"]) for r in data.get("text_lanes", [])]
    data["_holds"] = [(re.compile(h["match"], re.I), h["reason"]) for h in data.get("hold_patterns", [])]
    return data


def settings(path: Path | None = None) -> dict[str, Any]:
    return _load(str(path or config.LANES_FILE))


def personas_ready(path: Path | None = None) -> bool:
    """True only when the private persona file names every persona. Drafting refuses until then (fail closed)."""
    return bool(settings(path).get("_personas_ready"))


def persona_for(campaign: str, text: str = "", path: Path | None = None) -> str | None:
    """The lane persona: from the campaign, else from the post's own words, else the default lane."""
    s = settings(path)
    for rx, persona in s["_rules"]:
        if rx.search(campaign or ""):
            return persona
    for rx, persona in s["_text_rules"]:
        if text and rx.search(text):
            return persona
    return s.get("persona_default")


def post_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(k) or "") for k in ("need", "quote", "text"))


def persona(pid: str | None, path: Path | None = None) -> dict[str, Any]:
    return settings(path)["personas"].get(pid or "", {})


def poster_for(pid: str | None, path: Path | None = None, campaign: str = "") -> str:
    """Who posts: the poster a campaign names (a lane another agent posts for, such as MetaMuse), else the persona
    when its employee is live on that lane, else the stand-in poster (R1: Justin)."""
    s = settings(path)
    named = (s.get("campaign_posters") or {}).get(campaign or "")
    if named:
        return named
    return pid if pid and pid in s.get("personas_live", []) else s.get("poster_default", "justin")


def _age_days(posted_at: str | None, now: datetime) -> float | None:
    if not posted_at:
        return None
    try:
        ts = datetime.fromisoformat(str(posted_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 86400


def rule_hold(item: dict[str, Any], now: datetime | None = None, path: Path | None = None) -> str | None:
    """A hold reason from Justin's switches (age limit, routing patterns), or None to go ahead and draft."""
    s = settings(path)
    now = now or datetime.now(timezone.utc)
    limit = s.get("hold_older_than_days")
    age = _age_days(item.get("posted_at"), now)
    if limit is not None and age is not None and age > float(limit):
        return f"past the age limit ({age:.0f} days old, limit {limit})"
    text = post_text(item)
    for rx, reason in s["_holds"]:
        if rx.search(text):
            return reason
    return None
