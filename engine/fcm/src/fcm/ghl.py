"""Location-scoped GoHighLevel client for affiliate operations.

Ported from funding-director-orgo's narrow GHLClient and widened to the
affiliate-ops surface: contacts, tags, custom fields, notes, tasks,
conversations, workflow enrollment, opportunities, and location setup.

Two backends share one interface:
  * LiveGHL  — the public API v2 with a location Private Integration Token (pit-...).
  * MockGHL  — a JSON-file CRM used by the demo simulation and tests.

The client refuses to run against a location other than the one recorded in
config/ghl-map.json, so a stray call can never hit the agency's real account.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib import error, parse, request

from .errors import FcmError, GHLError

def iso_time(value: Any) -> str:
    """GoHighLevel dates arrive as epoch milliseconds or ISO strings; compare them as UTC ISO strings."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)) or str(value).isdigit():
        return datetime.fromtimestamp(float(value) / 1000, UTC).replace(microsecond=0).isoformat()
    text = str(value).replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return text
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).replace(microsecond=0).isoformat()


BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"
CONVERSATIONS_VERSION = "2021-04-15"


class GHLBackend(Protocol):
    location_id: str

    def search_contacts(self, *, query: str = "", tags: list[str] | None = None, limit: int = 100,
                        page: int = 1) -> list[dict[str, Any]]: ...
    def get_contact(self, contact_id: str) -> dict[str, Any]: ...
    def create_contact(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def update_contact(self, contact_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def add_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]: ...
    def remove_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]: ...
    def list_notes(self, contact_id: str) -> list[dict[str, Any]]: ...
    def add_note(self, contact_id: str, body: str, title: str = "", pinned: bool = False) -> dict[str, Any]: ...
    def update_note(self, contact_id: str, note_id: str, body: str, title: str = "",
                    pinned: bool = False) -> dict[str, Any]: ...
    def list_tasks(self, contact_id: str) -> list[dict[str, Any]]: ...
    def create_task(self, contact_id: str, title: str, due: str, body: str = "",
                    assigned_to: str = "") -> dict[str, Any]: ...
    def complete_task(self, contact_id: str, task_id: str) -> dict[str, Any]: ...
    def list_conversations(self, contact_id: str = "", unread_only: bool = False,
                           limit: int = 20) -> list[dict[str, Any]]: ...
    def list_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]: ...
    def list_recent_conversations(self, since: str, max_pages: int = 50) -> list[dict[str, Any]]: ...
    def send_message(self, contact_id: str, channel: str, body: str, subject: str = "") -> dict[str, Any]: ...
    def enroll_workflow(self, contact_id: str, workflow_id: str) -> dict[str, Any]: ...
    def search_opportunities(self, pipeline_id: str = "", contact_id: str = "",
                             limit: int = 50) -> list[dict[str, Any]]: ...
    def upsert_opportunity(self, *, pipeline_id: str, stage_id: str, contact_id: str, name: str,
                           status: str = "open", monetary_value: float = 0) -> dict[str, Any]: ...
    def list_pipelines(self) -> list[dict[str, Any]]: ...
    def list_custom_fields(self) -> list[dict[str, Any]]: ...
    def create_custom_field(self, name: str, data_type: str, options: list[str] | None = None) -> dict[str, Any]: ...
    def list_tags(self) -> list[dict[str, Any]]: ...
    def create_tag(self, name: str) -> dict[str, Any]: ...
    def list_workflows(self) -> list[dict[str, Any]]: ...
    def list_users(self) -> list[dict[str, Any]]: ...
    def location(self) -> dict[str, Any]: ...


_OUR_EMAIL = re.compile(r"\n\s*On .{5,120} wrote:|\n>|^-{2,}\s*original message|\n(?:Hi|Hey) [^,\n]{1,30},\s+(?:My name is "
                        r"|I've just stepped in|I've been going through)", re.I | re.M)


def email_plain(html_body: str) -> str:
    """An email's HTML as the plain text the partner typed: tags and entities out, our quoted email cut off (GHL
    often quotes it with no "wrote:" line, starting at our own greeting)."""
    import html as _html
    text = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", html_body, flags=re.I)
    text = _html.unescape(re.sub(r"<style.*?</style>|<script.*?</script>|<[^>]+>", " ", text, flags=re.S | re.I))
    text = re.sub(r"[ \t ]+", " ", text)
    m = _OUR_EMAIL.search(text)
    text = text[: m.start()] if m and m.start() > 0 else text
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Live backend
# ─────────────────────────────────────────────────────────────────────────────
class LiveGHL:
    """Public API v2 client bound to exactly one location."""

    MIN_INTERVAL_SECONDS = 0.12  # stays under GHL's ~100 requests / 10s burst limit

    def __init__(self, token: str | None = None, location_id: str | None = None,
                 expected_location_id: str = ""):
        self.token = (token or os.getenv("GHL_API_KEY", "")).strip()
        self.location_id = (location_id or os.getenv("GHL_LOCATION_ID", "")).strip()
        if not self.token.startswith("pit-"):
            raise FcmError("GHL_API_KEY must be a location-scoped Private Integration Token (pit-...)")
        if not self.location_id:
            raise FcmError("GHL_LOCATION_ID is required")
        if expected_location_id and expected_location_id != self.location_id:
            raise FcmError(
                "GHL_LOCATION_ID does not match config/ghl-map.json location_id — refusing to touch "
                "a location this agent was not configured for"
            )
        self._last_call = 0.0

    def _call(self, method: str, path: str, *, query: dict[str, Any] | None = None,
              body: dict[str, Any] | None = None, version: str = API_VERSION) -> dict[str, Any]:
        wait = self.MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        url = BASE_URL + path
        if query:
            url += "?" + parse.urlencode({k: v for k, v in query.items() if v not in (None, "")}, doseq=True)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Version": version,
            "User-Agent": "FundingAffiliateManager/1.0",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, separators=(",", ":")).encode()
        outbound = request.Request(url, data=data, headers=headers, method=method)
        for attempt in range(4):
            try:
                with request.urlopen(outbound, timeout=30) as response:
                    raw = response.read(2_000_000)
                    self._last_call = time.monotonic()
                    break
            except error.HTTPError as exc:
                self._last_call = time.monotonic()
                if exc.code == 429 and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                detail = ""
                try:
                    detail = exc.read(400).decode(errors="replace")
                except Exception:  # pragma: no cover - best effort
                    pass
                raise GHLError(f"GoHighLevel {method} {path} returned HTTP {exc.code} {detail}".strip(),
                               status=exc.code) from exc
            except error.URLError as exc:
                raise GHLError(f"GoHighLevel could not be reached ({method} {path})") from exc
            except (TimeoutError, OSError) as exc:  # a read timeout escapes urllib as a bare TimeoutError
                raise GHLError(f"GoHighLevel {method} {path} timed out or dropped: {exc}") from exc
        try:
            value = json.loads(raw or b"{}")
        except json.JSONDecodeError as exc:
            raise GHLError("GoHighLevel returned invalid JSON") from exc
        return value if isinstance(value, dict) else {"data": value}

    # contacts
    def search_contacts(self, *, query: str = "", tags: list[str] | None = None, limit: int = 100,
                        page: int = 1) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"locationId": self.location_id, "pageLimit": min(max(limit, 1), 500),
                                "page": max(page, 1)}
        if query.strip():
            body["query"] = query.strip()[:75]
        if tags:
            body["filters"] = [{"field": "tags", "operator": "contains", "value": tag} for tag in tags]
        return self._call("POST", "/contacts/search", body=body).get("contacts", [])

    def all_contacts(self, progress: Any = None, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """Every contact in the location (with all of `tags`), paged with searchAfter (page numbers stop at 10,000)."""
        out: list[dict[str, Any]] = []
        after: list[Any] | None = None
        while True:
            body: dict[str, Any] = {"locationId": self.location_id, "pageLimit": 500}
            if tags:
                body["filters"] = [{"field": "tags", "operator": "contains", "value": tag} for tag in tags]
            if after:
                body["searchAfter"] = after
            else:
                body["page"] = 1
            batch = self._call("POST", "/contacts/search", body=body).get("contacts", [])
            out += batch
            if progress:
                progress(len(out))
            nxt = batch[-1].get("searchAfter") if batch else None
            if len(batch) < 500 or not nxt or nxt == after:
                return out
            after = nxt

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        return self._call("GET", f"/contacts/{parse.quote(contact_id)}").get("contact", {})

    def create_contact(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = dict(payload)
        body["locationId"] = self.location_id
        return self._call("POST", "/contacts/upsert", body=body).get("contact", {})

    def update_contact(self, contact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("PUT", f"/contacts/{parse.quote(contact_id)}", body=payload).get("contact", {})

    def add_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        return self._call("POST", f"/contacts/{parse.quote(contact_id)}/tags", body={"tags": tags})

    def remove_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        return self._call("DELETE", f"/contacts/{parse.quote(contact_id)}/tags", body={"tags": tags})

    def list_notes(self, contact_id: str) -> list[dict[str, Any]]:
        return self._call("GET", f"/contacts/{parse.quote(contact_id)}/notes").get("notes", [])

    def add_note(self, contact_id: str, body: str, title: str = "", pinned: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {"body": body, **({"title": title} if title else {}), **({"pinned": True} if pinned else {})}
        return self._call("POST", f"/contacts/{parse.quote(contact_id)}/notes", body=payload).get("note", {})

    def update_note(self, contact_id: str, note_id: str, body: str, title: str = "",
                    pinned: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {"body": body, **({"title": title} if title else {}), **({"pinned": True} if pinned else {})}
        return self._call("PUT", f"/contacts/{parse.quote(contact_id)}/notes/{parse.quote(note_id)}",
                          body=payload).get("note", {})

    def list_tasks(self, contact_id: str) -> list[dict[str, Any]]:
        return self._call("GET", f"/contacts/{parse.quote(contact_id)}/tasks").get("tasks", [])

    def create_task(self, contact_id: str, title: str, due: str, body: str = "",
                    assigned_to: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "dueDate": due, "completed": False}
        if body:
            payload["body"] = body
        if assigned_to:
            payload["assignedTo"] = assigned_to
        return self._call("POST", f"/contacts/{parse.quote(contact_id)}/tasks", body=payload).get("task", {})

    def complete_task(self, contact_id: str, task_id: str) -> dict[str, Any]:
        return self._call("PUT", f"/contacts/{parse.quote(contact_id)}/tasks/{parse.quote(task_id)}/completed",
                          body={"completed": True})

    # conversations
    def list_conversations(self, contact_id: str = "", unread_only: bool = False,
                           limit: int = 20) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"locationId": self.location_id, "limit": min(max(limit, 1), 100),
                                 "sort": "desc", "sortBy": "last_message_date"}
        if contact_id:
            query["contactId"] = contact_id
        if unread_only:
            query["status"] = "unread"
        return self._call("GET", "/conversations/search", query=query,
                          version=CONVERSATIONS_VERSION).get("conversations", [])

    def list_recent_conversations(self, since: str, max_pages: int = 50) -> list[dict[str, Any]]:
        """Every conversation with a message since `since` (ISO), read or unread: a thread someone already
        opened in the GoHighLevel app still has to be triaged. Pages newest-first with the startAfterDate cursor."""
        cutoff = iso_time(since)
        rows: list[dict[str, Any]] = []
        cursor: Any = None
        for _ in range(max_pages):
            query: dict[str, Any] = {"locationId": self.location_id, "limit": 100, "sort": "desc",
                                     "sortBy": "last_message_date", "startAfterDate": cursor}
            page = self._call("GET", "/conversations/search", query=query,
                              version=CONVERSATIONS_VERSION).get("conversations", [])
            for conv in page:
                if iso_time(conv.get("lastMessageDate")) < cutoff:
                    return rows
                rows.append(conv)
            if len(page) < 100:
                break
            cursor = page[-1].get("lastMessageDate")
            if cursor in (None, ""):
                break
        return rows

    def list_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        value = self._call("GET", f"/conversations/{parse.quote(conversation_id)}/messages",
                           query={"limit": min(max(limit, 1), 100)}, version=CONVERSATIONS_VERSION)
        messages = value.get("messages", {})
        rows = messages.get("messages", []) if isinstance(messages, dict) else messages
        return [self._with_email_text(m) for m in rows]

    def _with_email_text(self, m: dict[str, Any]) -> dict[str, Any]:
        """An inbound email's `body` holds the thread it answered (our own email, unsubscribe footer and all); the
        partner's words are only in the email message itself. Without them the body becomes a placeholder, never our
        email, so our footer can't be read as their opt-out (Nov 3: seven warm email replies were)."""
        if m.get("messageType") != "TYPE_EMAIL" or m.get("direction") != "inbound":
            return m
        text, subject = "", ""
        for eid in reversed(((m.get("meta") or {}).get("email") or {}).get("messageIds") or []):
            try:
                e = self._call("GET", f"/conversations/messages/email/{parse.quote(str(eid))}",
                               version=CONVERSATIONS_VERSION)
            except GHLError:
                continue
            e = e.get("emailMessage", e) if isinstance(e, dict) else {}
            if e.get("direction") == "inbound":
                text, subject = email_plain(str(e.get("body") or "")), str(e.get("subject") or "")
                break
        return {**m, "body": text or "[an email reply whose text couldn't be read: open it in GoHighLevel]",
                "channel": "email", "subject": subject}

    def mark_read(self, contact_id: str) -> None:
        """Clear the unread count on the partner's conversations once a reply has been triaged."""
        for conv in self.list_conversations(contact_id=contact_id, limit=5):
            if conv.get("unreadCount"):
                self._call("PUT", f"/conversations/{parse.quote(conv['id'])}",
                           body={"locationId": self.location_id, "unreadCount": 0}, version=CONVERSATIONS_VERSION)

    # calls (recorded and transcribed by GoHighLevel's phone system)
    def list_call_messages(self, contact_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        calls = []
        for conv in self.list_conversations(contact_id=contact_id, limit=min(limit, 100)):
            for m in self.list_messages(conv["id"], limit=50):
                if "CALL" in str(m.get("messageType", "")).upper():
                    calls.append({**m, "contactId": m.get("contactId") or conv.get("contactId", "")})
        return calls[:limit]

    def get_transcription(self, message_id: str) -> list[dict[str, Any]]:
        """Sentences with mediaChannel, startTime, endTime, transcript, confidence. Needs call transcription
        switched on for the sub-account (a Twilio feature in GoHighLevel)."""
        value = self._call("GET", f"/conversations/locations/{self.location_id}/messages/"
                                  f"{parse.quote(message_id)}/transcription", version=CONVERSATIONS_VERSION)
        return value.get("data") if isinstance(value.get("data"), list) else value.get("transcription", [])

    def recording_ref(self, message_id: str) -> str:
        """Where the audio lives (fetched on demand, never copied into the vault)."""
        return f"ghl:/conversations/messages/{message_id}/locations/{self.location_id}/recording"

    def send_message(self, contact_id: str, channel: str, body: str, subject: str = "") -> dict[str, Any]:
        kind = {"sms": "SMS", "email": "Email"}.get(channel.lower())
        if not kind:
            raise FcmError("channel must be sms or email")
        payload: dict[str, Any] = {"type": kind, "contactId": contact_id}
        if kind == "Email":
            payload["subject"] = subject or "Checking in"
            payload["html"] = "<p>" + "</p><p>".join(
                part.replace("\n", "<br>") for part in body.strip().split("\n\n")) + "</p>"
        else:
            payload["message"] = body
        return self._call("POST", "/conversations/messages", body=payload, version=CONVERSATIONS_VERSION)

    # workflows
    def enroll_workflow(self, contact_id: str, workflow_id: str) -> dict[str, Any]:
        return self._call("POST", f"/contacts/{parse.quote(contact_id)}/workflow/{parse.quote(workflow_id)}",
                          body={"eventStartTime": _now_iso()})

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._call("GET", "/workflows/", query={"locationId": self.location_id}).get("workflows", [])

    # opportunities
    def search_opportunities(self, pipeline_id: str = "", contact_id: str = "",
                             limit: int = 50) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"location_id": self.location_id, "limit": min(max(limit, 1), 100)}
        if pipeline_id:
            query["pipeline_id"] = pipeline_id
        if contact_id:
            query["contact_id"] = contact_id
        return self._call("GET", "/opportunities/search", query=query).get("opportunities", [])

    def upsert_opportunity(self, *, pipeline_id: str, stage_id: str, contact_id: str, name: str,
                           status: str = "open", monetary_value: float = 0) -> dict[str, Any]:
        body = {
            "locationId": self.location_id,
            "pipelineId": pipeline_id,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "name": name,
            "status": status,
            "monetaryValue": monetary_value,
        }
        return self._call("POST", "/opportunities/upsert", body=body).get("opportunity", {})

    def list_pipelines(self) -> list[dict[str, Any]]:
        return self._call("GET", "/opportunities/pipelines", query={"locationId": self.location_id}).get(
            "pipelines", [])

    # location setup
    def list_custom_fields(self) -> list[dict[str, Any]]:
        return self._call("GET", f"/locations/{self.location_id}/customFields",
                          query={"model": "contact"}).get("customFields", [])

    def create_custom_field(self, name: str, data_type: str, options: list[str] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name, "dataType": data_type, "model": "contact"}
        if options:
            body["options"] = options
        return self._call("POST", f"/locations/{self.location_id}/customFields", body=body).get("customField", {})

    def list_tags(self) -> list[dict[str, Any]]:
        return self._call("GET", f"/locations/{self.location_id}/tags").get("tags", [])

    def create_tag(self, name: str) -> dict[str, Any]:
        return self._call("POST", f"/locations/{self.location_id}/tags", body={"name": name}).get("tag", {})

    def list_users(self) -> list[dict[str, Any]]:
        return self._call("GET", "/users/", query={"locationId": self.location_id}).get("users", [])

    def list_custom_values(self) -> list[dict[str, Any]]:
        return self._call("GET", f"/locations/{self.location_id}/customValues").get("customValues", [])

    def update_custom_value_by_name(self, name: str, value: str) -> dict[str, Any]:
        """Newsletter / event / offer copy lives in custom values the workflows reference."""
        for item in self.list_custom_values():
            if item.get("name") == name:
                return self._call("PUT", f"/locations/{self.location_id}/customValues/{item['id']}",
                                  body={"name": name, "value": value}).get("customValue", {})
        return self._call("POST", f"/locations/{self.location_id}/customValues",
                          body={"name": name, "value": value}).get("customValue", {})

    def location(self) -> dict[str, Any]:
        return self._call("GET", f"/locations/{self.location_id}").get("location", {})


# ─────────────────────────────────────────────────────────────────────────────
# Mock backend (demo simulation + tests)
# ─────────────────────────────────────────────────────────────────────────────
class MockGHL:
    """A small JSON-file CRM with the same interface as LiveGHL.

    Contacts store customFields as [{"id": key, "value": v}] exactly like the live API,
    so the engine code path is identical in both modes.
    """

    location_id = "mock-location"

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.db = json.loads(self.path.read_text())
        else:
            self.db = {"contacts": {}, "notes": {}, "tasks": {}, "messages": [], "enrollments": [],
                       "opportunities": {}, "custom_fields": [], "tags": [], "outbox": []}
        self.now_override: str = ""
        self._tick_base, self._tick = "", 0
        self.autosave = True

    def _save(self) -> None:
        if self.autosave:
            self.flush()

    def flush(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.db, indent=1, sort_keys=True))
        tmp.replace(self.path)

    def _now(self) -> str:
        """The simulated clock ticks one second per write, so messages on one simulated day keep their order."""
        if not self.now_override:
            return _now_iso()
        if self.now_override != self._tick_base:
            self._tick_base, self._tick = self.now_override, 0
        self._tick += 1
        return (datetime.fromisoformat(self.now_override) + timedelta(seconds=self._tick)).isoformat()

    def _id(self, prefix: str) -> str:
        # Deterministic ids (a counter kept in the file), so the same seed gives the same simulation.
        seq = int(self.db.get("_seq", 0)) + 1
        self.db["_seq"] = seq
        return f"{prefix}_{hashlib.sha256(f'{prefix}:{seq}'.encode()).hexdigest()[:12]}"

    def reset(self) -> None:
        self.db = {"contacts": {}, "notes": {}, "tasks": {}, "messages": [], "enrollments": [],
                   "opportunities": {}, "custom_fields": [], "tags": [], "outbox": []}
        self._save()

    # contacts
    def search_contacts(self, *, query: str = "", tags: list[str] | None = None, limit: int = 100,
                        page: int = 1) -> list[dict[str, Any]]:
        rows = list(self.db["contacts"].values())
        if query.strip():
            q = query.strip().lower()
            rows = [c for c in rows if q in json.dumps(
                [c.get("firstName"), c.get("lastName"), c.get("email"), c.get("phone")]).lower()]
        for tag in tags or []:
            rows = [c for c in rows if tag in c.get("tags", [])]
        rows.sort(key=lambda c: c["id"])
        start = (max(page, 1) - 1) * limit
        return [json.loads(json.dumps(c)) for c in rows[start:start + limit]]

    def all_contacts(self, progress: Any = None, tags: list[str] | None = None) -> list[dict[str, Any]]:
        return [json.loads(json.dumps(c)) for c in self.db["contacts"].values()
                if all(t in c.get("tags", []) for t in tags or [])]

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        contact = self.db["contacts"].get(contact_id)
        if not contact:
            raise FcmError(f"contact {contact_id} not found")
        return json.loads(json.dumps(contact))

    def create_contact(self, payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("id") or self._id("c")
        contact = {"id": contact_id, "tags": [], "customFields": [], "dateAdded": self._now()}
        contact.update({k: v for k, v in payload.items() if k != "id"})
        contact["tags"] = list(dict.fromkeys(contact.get("tags", [])))
        self.db["contacts"][contact_id] = contact
        self._save()
        return contact

    def update_contact(self, contact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        contact = self.db["contacts"].get(contact_id)
        if not contact:
            raise FcmError(f"contact {contact_id} not found")
        for key, value in payload.items():
            if key == "customFields":
                existing = {f["id"]: f for f in contact.get("customFields", [])}
                for item in value:
                    existing[item["id"]] = {"id": item["id"], "value": item.get("field_value", item.get("value"))}
                contact["customFields"] = list(existing.values())
            else:
                contact[key] = value
        self._save()
        return contact

    def add_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        contact = self.db["contacts"][contact_id]
        contact["tags"] = list(dict.fromkeys(contact.get("tags", []) + tags))
        self._save()
        return {"tags": contact["tags"]}

    def remove_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        contact = self.db["contacts"][contact_id]
        contact["tags"] = [t for t in contact.get("tags", []) if t not in tags]
        self._save()
        return {"tags": contact["tags"]}

    def list_notes(self, contact_id: str) -> list[dict[str, Any]]:
        return list(self.db["notes"].get(contact_id, []))

    def add_note(self, contact_id: str, body: str, title: str = "", pinned: bool = False) -> dict[str, Any]:
        note = {"id": self._id("n"), "body": body, "dateAdded": self._now()}
        if title:
            note["title"] = title
        if pinned:
            note["pinned"] = True
        self.db["notes"].setdefault(contact_id, []).append(note)
        self._save()
        return note

    def update_note(self, contact_id: str, note_id: str, body: str, title: str = "",
                    pinned: bool = False) -> dict[str, Any]:
        for note in self.db["notes"].get(contact_id, []):
            if note["id"] == note_id:
                note.update({"body": body, **({"title": title} if title else {}), **({"pinned": True} if pinned else {})})
                self._save()
                return note
        raise GHLError(f"note {note_id} not found", status=404)

    def list_tasks(self, contact_id: str) -> list[dict[str, Any]]:
        return list(self.db["tasks"].get(contact_id, []))

    def create_task(self, contact_id: str, title: str, due: str, body: str = "",
                    assigned_to: str = "") -> dict[str, Any]:
        task = {"id": self._id("t"), "title": title, "body": body, "dueDate": due,
                "assignedTo": assigned_to, "completed": False, "contactId": contact_id}
        self.db["tasks"].setdefault(contact_id, []).append(task)
        self._save()
        return task

    def complete_task(self, contact_id: str, task_id: str) -> dict[str, Any]:
        for task in self.db["tasks"].get(contact_id, []):
            if task["id"] == task_id:
                task["completed"] = True
                task["completedAt"] = self._now()
        self._save()
        return {"succeded": True}

    # conversations
    def record_inbound(self, contact_id: str, channel: str, body: str) -> dict[str, Any]:
        message = {"id": self._id("m"), "contactId": contact_id, "direction": "inbound",
                   "messageType": channel.upper(), "body": body, "dateAdded": self._now(), "unread": True}
        self.db["messages"].append(message)
        self._save()
        return message

    def list_conversations(self, contact_id: str = "", unread_only: bool = False,
                           limit: int = 20) -> list[dict[str, Any]]:
        by_contact: dict[str, dict[str, Any]] = {}
        for m in self.db["messages"]:
            if contact_id and m["contactId"] != contact_id:
                continue
            conv = by_contact.setdefault(m["contactId"], {
                "id": f"conv_{m['contactId']}", "contactId": m["contactId"], "unreadCount": 0,
                "lastMessageBody": "", "lastMessageDate": "", "lastMessageDirection": ""})
            if m.get("unread") and m["direction"] == "inbound":
                conv["unreadCount"] += 1
            if m["dateAdded"] >= conv["lastMessageDate"]:
                conv.update(lastMessageBody=m["body"], lastMessageDate=m["dateAdded"],
                            lastMessageDirection=m["direction"])
        rows = list(by_contact.values())
        if unread_only:
            rows = [c for c in rows if c["unreadCount"] > 0]
        rows.sort(key=lambda c: c["lastMessageDate"], reverse=True)
        return rows[:limit]

    def list_recent_conversations(self, since: str, max_pages: int = 50) -> list[dict[str, Any]]:
        cutoff = iso_time(since)
        return [c for c in self.list_conversations(limit=10**6) if iso_time(c["lastMessageDate"]) >= cutoff]

    def list_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        contact_id = conversation_id.removeprefix("conv_")
        rows = [m for m in self.db["messages"] if m["contactId"] == contact_id]
        return sorted(rows, key=lambda m: m["dateAdded"], reverse=True)[:limit]

    def mark_read(self, contact_id: str) -> None:
        for m in self.db["messages"]:
            if m["contactId"] == contact_id:
                m["unread"] = False
        self._save()

    def record_call(self, contact_id: str, direction: str, duration_s: int,
                    sentences: list[dict[str, Any]]) -> dict[str, Any]:
        """Play a recorded, transcribed phone call (the simulation and tests)."""
        message = {"id": self._id("m"), "contactId": contact_id, "direction": direction, "messageType": "TYPE_CALL",
                   "body": "", "dateAdded": self._now(), "unread": False, "meta": {"call": {"duration": duration_s}}}
        self.db["messages"].append(message)
        self.db.setdefault("transcriptions", {})[message["id"]] = sentences
        self._save()
        return message

    def list_call_messages(self, contact_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        rows = [m for m in self.db["messages"] if m.get("messageType") == "TYPE_CALL"
                and (not contact_id or m["contactId"] == contact_id)]
        return sorted(rows, key=lambda m: m["dateAdded"], reverse=True)[:limit]

    def get_transcription(self, message_id: str) -> list[dict[str, Any]]:
        return list(self.db.get("transcriptions", {}).get(message_id, []))

    def recording_ref(self, message_id: str) -> str:
        return f"mock:recording/{message_id}"

    def send_message(self, contact_id: str, channel: str, body: str, subject: str = "") -> dict[str, Any]:
        message = {"id": self._id("m"), "contactId": contact_id, "direction": "outbound",
                   "messageType": channel.upper(), "subject": subject, "body": body,
                   "dateAdded": self._now(), "unread": False}
        self.db["messages"].append(message)
        self.db["outbox"].append(message)
        self._save()
        return {"messageId": message["id"], "conversationId": f"conv_{contact_id}"}

    def enroll_workflow(self, contact_id: str, workflow_id: str) -> dict[str, Any]:
        self.db["enrollments"].append({"contactId": contact_id, "workflowId": workflow_id, "at": self._now()})
        self._save()
        return {"succeded": True}

    def list_workflows(self) -> list[dict[str, Any]]:
        seen = sorted({e["workflowId"] for e in self.db["enrollments"]})
        return [{"id": w, "name": w, "status": "published"} for w in seen]

    def search_opportunities(self, pipeline_id: str = "", contact_id: str = "",
                             limit: int = 50) -> list[dict[str, Any]]:
        rows = list(self.db["opportunities"].values())
        if pipeline_id:
            rows = [o for o in rows if o["pipelineId"] == pipeline_id]
        if contact_id:
            rows = [o for o in rows if o["contactId"] == contact_id]
        return rows[:limit]

    def upsert_opportunity(self, *, pipeline_id: str, stage_id: str, contact_id: str, name: str,
                           status: str = "open", monetary_value: float = 0) -> dict[str, Any]:
        key = f"{pipeline_id}:{contact_id}"
        opp = self.db["opportunities"].get(key) or {"id": self._id("o"), "createdAt": self._now()}
        opp.update(pipelineId=pipeline_id, pipelineStageId=stage_id, contactId=contact_id, name=name,
                   status=status, monetaryValue=monetary_value, updatedAt=self._now())
        self.db["opportunities"][key] = opp
        self._save()
        return opp

    def list_pipelines(self) -> list[dict[str, Any]]:
        return []

    def list_custom_fields(self) -> list[dict[str, Any]]:
        return list(self.db["custom_fields"])

    def create_custom_field(self, name: str, data_type: str, options: list[str] | None = None) -> dict[str, Any]:
        item = {"id": name, "name": name, "dataType": data_type, "options": options or []}
        self.db["custom_fields"].append(item)
        self._save()
        return item

    def list_tags(self) -> list[dict[str, Any]]:
        return [{"id": t, "name": t} for t in self.db["tags"]]

    def create_tag(self, name: str) -> dict[str, Any]:
        if name not in self.db["tags"]:
            self.db["tags"].append(name)
            self._save()
        return {"id": name, "name": name}

    def list_users(self) -> list[dict[str, Any]]:
        return [{"id": "user_manager", "name": "Funding Relationship Manager"}]

    def list_custom_values(self) -> list[dict[str, Any]]:
        return [{"id": k, "name": k, "value": v} for k, v in self.db.setdefault("custom_values", {}).items()]

    def update_custom_value_by_name(self, name: str, value: str) -> dict[str, Any]:
        self.db.setdefault("custom_values", {})[name] = value
        self._save()
        return {"id": name, "name": name, "value": value}

    def location(self) -> dict[str, Any]:
        return {"id": self.location_id, "name": "Mock Affiliate Demo"}


def open_backend(settings: Any) -> GHLBackend:
    """Open the configured backend. Live mode is pinned to the mapped location."""
    if settings.ghl_mode == "mock":
        return MockGHL(settings.state_dir / "mock-ghl.json")
    synthetic = synthetic_demo()
    if synthetic and not getattr(settings, "demo_mode", False):
        raise FcmError("FCM_SYNTHETIC_DEMO=1 needs FCM_DEMO_MODE=1: only the test contact may get real messages")
    backend = LiveGHL(expected_location_id=str(settings.ghl_map.get("location_id", "")))
    if synthetic:
        require_demo_location(backend)
    return backend


def synthetic_demo() -> bool:
    """A sub-account that holds only made-up partners (the sales demo; Justin approved this exception 2026-10-20).
    Demo mode stays forced on, and the location's own name must say demo or synthetic."""
    return os.getenv("FCM_SYNTHETIC_DEMO", "").strip().lower() in {"1", "yes", "true"}


def require_demo_location(backend: Any) -> None:
    name = str((backend.location() or {}).get("name", ""))
    if not re.search(r"\b(demo|synthetic)\b", name, re.I):
        raise FcmError(f"FCM_SYNTHETIC_DEMO=1 is only for a demo sub-account (its name says Demo or synthetic); "
                       f"this location is named {name!r}")
