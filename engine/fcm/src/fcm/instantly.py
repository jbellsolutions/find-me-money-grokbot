"""Read and answer campaign replies in Instantly (API v2).

That account also holds other businesses' campaigns, so this client reads only the campaign ids in FCM_INSTANTLY_CAMPAIGNS
and refuses to run without them. Reading is safe. A reply or a block goes out only when the caller says so, and the caller
in sales.py holds both behind Justin's switches.

Field names come from Instantly's docs. They're unproven against a real reply until the go-live canary.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .errors import FcmError

BASE = "https://api.instantly.ai/api/v2"
Opener = Callable[[urllib.request.Request], Any]


def _campaigns() -> list[str]:
    return [c.strip() for c in os.getenv("FCM_INSTANTLY_CAMPAIGNS", "").split(",") if c.strip()]


def configured() -> bool:
    return bool(os.getenv("INSTANTLY_API_KEY", "").strip() and _campaigns())


class Instantly:
    def __init__(self, key: str = "", campaigns: list[str] | None = None, opener: Opener | None = None):
        self.key = key or os.getenv("INSTANTLY_API_KEY", "").strip()
        self.campaigns = _campaigns() if campaigns is None else campaigns
        self.opener = opener or (lambda req: urllib.request.urlopen(req, timeout=30))
        if not self.key:
            raise FcmError("INSTANTLY_API_KEY isn't set")
        if not self.campaigns:
            raise FcmError("name this campaign in FCM_INSTANTLY_CAMPAIGNS: the account holds other businesses' campaigns")

    def _call(self, method: str, path: str, query: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> Any:
        url = BASE + path + (f"?{urllib.parse.urlencode(query)}" if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "funding-crm-manager/1.0"})
        try:
            with self.opener(req) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise FcmError(f"Instantly answered {exc.code} on {path}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FcmError("Instantly could not be reached") from exc
        return json.loads(raw) if raw else {}

    @staticmethod
    def _reply(item: dict[str, Any]) -> dict[str, Any]:
        body = item.get("body") or {}
        return {"id": str(item.get("id") or ""), "email": str(item.get("from_address_email") or item.get("lead") or "").strip().lower(),
                "subject": str(item.get("subject") or ""), "text": str(body.get("text") or item.get("content_preview") or ""),
                "eaccount": str(item.get("eaccount") or ""), "campaign": str(item.get("campaign_id") or ""),
                "at": str(item.get("timestamp_email") or item.get("timestamp_created") or ""), "source": "instantly"}

    def replies(self, limit: int = 50) -> list[dict[str, Any]]:
        """Replies on our campaigns only. Anything from another campaign is dropped, even if the API returns it."""
        out = []
        for campaign in self.campaigns:
            got = self._call("GET", "/emails", {"campaign_id": campaign, "email_type": "received", "limit": min(limit, 100)})
            items = got.get("items") if isinstance(got, dict) else got
            out += [self._reply(i) for i in items or [] if str(i.get("campaign_id") or campaign) in self.campaigns]
        return out

    def send_reply(self, reply_to: str, eaccount: str, subject: str, text: str) -> dict[str, Any]:
        return self._call("POST", "/emails/reply", body={"reply_to_uuid": reply_to, "eaccount": eaccount, "subject": subject,
                                                         "body": {"text": text}})

    def block(self, email: str) -> dict[str, Any]:
        return self._call("POST", "/block-lists-entries", body={"bl_value": email})
