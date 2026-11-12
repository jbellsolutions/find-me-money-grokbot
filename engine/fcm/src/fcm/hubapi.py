"""Client for the Lending Hub, the record for partners, routing and handoffs. This agent keeps no second ledger.

Auth is the hub's bearer token (HUB_PASSWORD). It can read, propose, report a partner's answer and re-pair. It can't
approve a handoff, record a hand delivery, or mark Funded or Paid: a signed-in person does those.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

from .errors import FcmError


class HubError(FcmError):
    pass


class Hub:
    def __init__(self, url: str = "", password: str = "", timeout: float = 30):
        self.url = (url or os.getenv("HUB_URL", "")).rstrip("/")
        self.password = password or os.getenv("HUB_PASSWORD", "")
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        if not self.url:
            raise HubError("HUB_URL isn't set")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method)
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "funding-crm-manager/1.0")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.password:
            req.add_header("Authorization", f"Bearer {self.password}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            raise HubError(f"hub {method} {path} -> {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise HubError(f"hub unreachable at {self.url}: {exc.reason}") from exc

    def card(self, contact_id: str) -> dict[str, Any]:
        return self._call("GET", f"/api/crm/contacts/{quote(contact_id)}?home=1")  # our home CRM, not the hub's default GHL

    def board(self) -> dict[str, Any]:
        return self._call("GET", "/api/distribution")

    def open(self) -> list[dict[str, Any]]:
        return self._call("GET", "/api/distribution/open").get("open") or []

    def handoff(self, handoff_id: str) -> dict[str, Any]:
        return self._call("GET", f"/api/distribution/handoffs/{quote(handoff_id)}")

    def preview(self, lead: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/distribution/preview", {"lead": lead})

    def propose(self, lead: dict[str, Any], partner_id: str = "") -> dict[str, Any]:
        return self._call("POST", "/api/distribution/handoffs", {"lead": lead, "partner_id": partner_id})

    def report(self, handoff_id: str, status: str, note: str = "", milestone: str = "") -> dict[str, Any]:
        body = {"status": status, "note": note, **({"milestone": milestone} if milestone else {})}
        return self._call("POST", f"/api/distribution/handoffs/{quote(handoff_id)}/report", body)

    def repair(self, handoff_id: str, reason: str) -> dict[str, Any]:
        return self._call("POST", f"/api/distribution/handoffs/{quote(handoff_id)}/repair", {"reason": reason})

    def charges(self) -> dict[str, Any]:
        """Read only. This token can never mark a charge Paid: that takes a verified payment or a signed-in person."""
        return self._call("GET", "/api/distribution/charges")

    def dashboard(self) -> dict[str, Any]:
        return self._call("GET", "/api/distribution/dashboard")

    def loops(self) -> dict[str, Any]:
        return self._call("GET", "/api/distribution/loops")

    def save_loops(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/distribution/loops", body)

    def posting_queue(self) -> dict[str, Any]:
        return self._call("GET", "/api/posting/queue")

    def craigslist(self, apply: bool = False) -> dict[str, Any]:
        return self._call("POST" if apply else "GET", "/api/craigslist/route", {} if apply else None)

    def sent_by_seat(self, handoff_id: str) -> dict[str, Any]:
        return self._call("POST", f"/api/distribution/handoffs/{quote(handoff_id)}/sent", {"via": "ghl"})
