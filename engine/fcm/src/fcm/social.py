"""The social queue: anyone with a profile we can see waits here for a person, or an approved profile, to reach out.

Nothing here posts or messages. It keeps the list, one row per person and platform, and tags the contact.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PLATFORMS = {"linkedin.com": "linkedin", "facebook.com": "facebook", "fb.com": "facebook", "instagram.com": "instagram",
             "tiktok.com": "tiktok", "x.com": "x", "twitter.com": "x", "youtube.com": "youtube", "skool.com": "skool",
             "reddit.com": "reddit"}


def platform(url: str) -> str:
    host = urlparse(str(url or "").strip()).netloc.lower().removeprefix("www.").removeprefix("m.")
    return next((name for domain, name in PLATFORMS.items() if host == domain or host.endswith(f".{domain}")), "")


def links(card: dict[str, Any]) -> list[dict[str, str]]:
    """Profile or post links on a card, once each. Their own words never become links here."""
    found = [card.get("link")] + [v for v in (card.get("fields") or {}).values() if isinstance(v, str)]
    found += [r.get("url") for r in card.get("radar") or []]
    out, seen = [], set()
    for url in found:
        name = platform(str(url or ""))
        if name and url not in seen:
            seen.add(url)
            out.append({"platform": name, "url": str(url)})
    return out


class Queue:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE IF NOT EXISTS social_queue (contact_id TEXT, platform TEXT, url TEXT, added TEXT, "
                          "status TEXT DEFAULT 'waiting', PRIMARY KEY (contact_id, platform))")

    def add(self, contact_id: str, rows: list[dict[str, str]], now: datetime) -> int:
        added = 0
        for row in rows:
            cur = self.conn.execute("INSERT OR IGNORE INTO social_queue (contact_id, platform, url, added) VALUES (?,?,?,?)",
                                    (contact_id, row["platform"], row["url"], now.isoformat()))
            added += cur.rowcount
        self.conn.commit()
        return added

    def waiting(self, limit: int = 50) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM social_queue WHERE status='waiting' ORDER BY added LIMIT ?", (limit,))]

    def counts(self) -> dict[str, int]:
        return {r["platform"]: r["n"] for r in self.conn.execute(
            "SELECT platform, count(*) n FROM social_queue WHERE status='waiting' GROUP BY platform")}


def queue(engine: Any) -> Queue:
    return Queue(Path(engine.settings.state_dir) / "leads.sqlite3")
