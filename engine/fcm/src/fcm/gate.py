"""The send gate: the only thing that holds a GoHighLevel token able to send, and it runs off the agent's computer.

Why it exists (Justin, 2026-10-20): the agent drives its own Orgo computer, desktop and terminal included. Anything
on that computer, our approval records too, is within its reach, so "a person approves every message" can't rest
on code there. The computer gets a GHL token WITHOUT `conversations/message.write`, and a GHL user without
Conversations or Automation access. Sending happens here. A batch nobody approved is sent as approver "auto", unless
GATE_REQUIRE_APPROVAL=1, which refuses it until an approver
posts the approve line. When Slack is configured, Justin can act on a batch from his own Slack account:

    approve act_1a2b3c 9f8e7d6c5b4a3210 except 4, 17   # hold messages back (the id and digest from the card)
    revoke act_1a2b3c                                  # stops whatever hasn't gone out yet

The gate reads those messages itself through Slack's API and accepts them only from the approver user ids it is
configured with, posted by a person (never a bot). The gate recomputes the batch digest from the frozen payload it
is handed, so a changed text, recipient or channel is refused. Each message goes out at most once (its own
ledger), demo mode only reaches contacts tagged fcm:test-contact, and only to its one location.

    fcm gate serve --port 8080       # env: GATE_TOKEN, GATE_GHL_API_KEY, GATE_GHL_LOCATION_ID,
                                     #      GATE_SLACK_BOT_TOKEN, GATE_SLACK_CHANNEL, GATE_APPROVER_SLACK_IDS (optional),
                                     #      GATE_DEMO_ONLY (default 1), GATE_DB (default ./gate.sqlite3),
                                     #      GATE_REQUIRE_APPROVAL (default 0), GATE_SENT_TAG (e.g. crm:sent:
                                     #      added to the contact after its message really went out: attribution)
                                     #      Reply webhook (optional): GATE_REPLY_HOOK_SECRET, GATE_ORGO_API_KEY,
                                     #      GATE_ORGO_COMPUTER_ID, GATE_TRIAGE_JOB_ID, GATE_REPLY_DELAY (default 20)

A GoHighLevel workflow posts each partner reply to /hook/reply?k=<GATE_REPLY_HOOK_SECRET>. The gate waits
GATE_REPLY_DELAY seconds (replies that land meanwhile ride the same run), then asks the agent's Orgo computer to run
its reply-triage cron job now, so a reply is answered in under a minute instead of at the next scheduled check.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib import parse, request

from .errors import FcmError, GHLError
from .store import digest

TEST_TAG = "fcm:test-contact"
_APPROVE = re.compile(r"^\s*approve\s+(act_[A-Za-z0-9]+)\s+([0-9a-f]{16})(?:\s+except\s+([\d,\s]+))?\s*$", re.I)
_REVOKE = re.compile(r"^\s*revoke\s+(act_[A-Za-z0-9]+)\s*$", re.I)


class SlackApprovals:
    """Reads approvals from one Slack channel. `fetch(method, params) -> dict` is the Slack Web API call."""

    def __init__(self, token: str, channel: str, approvers: set[str],
                 fetch: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None):
        if not (token and channel and approvers):
            raise FcmError("the gate needs GATE_SLACK_BOT_TOKEN, GATE_SLACK_CHANNEL and GATE_APPROVER_SLACK_IDS")
        self.token, self.channel, self.approvers = token, channel, approvers
        self.fetch = fetch or self._fetch

    def _fetch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"https://slack.com/api/{method}?" + parse.urlencode(params)
        req = request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        with request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read(5_000_000))
        if not body.get("ok"):
            raise FcmError(f"Slack {method} failed: {body.get('error')}")
        return body

    def _messages(self) -> list[dict[str, Any]]:
        out, cursor = [], ""
        for _ in range(10):  # the last ~2,000 messages are plenty for an approval that lasts hours
            params: dict[str, Any] = {"channel": self.channel, "limit": 200}
            if cursor:
                params["cursor"] = cursor
            body = self.fetch("conversations.history", params)
            out += body.get("messages", [])
            cursor = (body.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        return out

    def _by_a_person(self, m: dict[str, Any]) -> bool:
        return (m.get("user") in self.approvers and not m.get("bot_id") and not m.get("app_id")
                and m.get("subtype") in (None, "", "thread_broadcast"))

    def find(self, action_id: str, action_digest: str) -> dict[str, Any] | None:
        """The approver's newest approval of exactly this batch, unless revoked after it. None if there isn't one."""
        approval, revoked_at = self.scan(action_id, action_digest)
        if approval and revoked_at > approval["ts"]:
            return None
        return approval

    def scan(self, action_id: str, action_digest: str) -> tuple[dict[str, Any] | None, float]:
        """The approver's newest approval of exactly this batch (or None), and when it was last revoked (0 if never)."""
        approval, revoked_at = None, 0.0
        for m in self._messages():
            if not self._by_a_person(m):
                continue
            text, ts = str(m.get("text", "")), float(m.get("ts", 0))
            if (r := _REVOKE.match(text)) and r.group(1) == action_id:
                revoked_at = max(revoked_at, ts)
            elif (a := _APPROVE.match(text)) and a.group(1) == action_id and a.group(2).lower() == action_digest:
                if approval is None or ts > approval["ts"]:
                    exclude = sorted({int(x) for x in re.findall(r"\d+", a.group(3) or "")})
                    approval = {"approver": m["user"], "ts": ts, "exclude": exclude}
        return approval, revoked_at


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS sent (action_id TEXT, n INTEGER, state TEXT, ref TEXT, at TEXT, "
                      "PRIMARY KEY (action_id, n))")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def claim(self, action_id: str, n: int) -> dict[str, Any] | None:
        """Mark (action, n) as sending. Returns the earlier record if it was already claimed."""
        with self.lock, self._conn() as c:
            row = c.execute("SELECT state, ref FROM sent WHERE action_id=? AND n=?", (action_id, n)).fetchone()
            if row:
                return {"state": row[0], "ref": row[1]}
            c.execute("INSERT INTO sent VALUES (?,?,?,?,?)",
                      (action_id, n, "sending", "", datetime.now(UTC).isoformat()))
            return None

    def finish(self, action_id: str, n: int, state: str, ref: str = "") -> None:
        with self.lock, self._conn() as c:
            c.execute("UPDATE sent SET state=?, ref=? WHERE action_id=? AND n=?", (state, ref, action_id, n))


class Gate:
    def __init__(self, ghl: Any, slack: SlackApprovals | None, ledger: Ledger, demo_only: bool = True,
                 require_approval: bool = False, sent_tag: str = ""):
        self.ghl, self.slack, self.ledger, self.demo_only = ghl, slack, ledger, demo_only
        self.require_approval, self.sent_tag = require_approval, sent_tag.strip()
        if require_approval and not slack:
            raise FcmError("GATE_REQUIRE_APPROVAL=1 needs Slack (GATE_SLACK_BOT_TOKEN, GATE_SLACK_CHANNEL, "
                           "GATE_APPROVER_SLACK_IDS): approvals are read there")

    def _check(self, req: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        action_id, kind = str(req.get("action_id", "")), str(req.get("kind", ""))
        payload, claimed = req.get("payload"), str(req.get("digest", ""))
        if not isinstance(payload, dict) or not action_id:
            raise FcmError("action_id and payload are required")
        if digest({"kind": kind, "payload": payload}) != claimed:
            raise FcmError("the payload doesn't match its digest: this isn't the batch that was approved")
        if payload.get("location_id") != self.ghl.location_id:
            raise FcmError("this batch was prepared for another GoHighLevel location")
        approval, revoked_at = self.slack.scan(action_id, claimed) if self.slack else (None, 0.0)
        if revoked_at and (not approval or revoked_at > approval["ts"]):
            raise FcmError(f"{action_id} was revoked in Slack")
        if not approval and self.require_approval:
            raise FcmError(f"{action_id} isn't approved yet: an approver posts `approve {action_id} {claimed}` in Slack")
        return payload, approval or {"approver": "auto", "exclude": []}

    def approval(self, req: dict[str, Any]) -> dict[str, Any]:
        found = self.slack.find(str(req.get("action_id", "")), str(req.get("digest", ""))) if self.slack else None
        return {"approved": bool(found), **(found or {})}

    def _demo_ok(self, contact_id: str) -> bool:
        return not self.demo_only or TEST_TAG in (self.ghl.get_contact(contact_id).get("tags") or [])

    def send(self, req: dict[str, Any]) -> dict[str, Any]:
        payload, approval = self._check(req)
        if req.get("kind") != "send_messages":
            raise FcmError("send takes a send_messages batch")
        n = int(req.get("n", 0))
        messages = payload.get("messages") or []
        if not 1 <= n <= len(messages):
            raise FcmError(f"message {n} isn't in this batch")
        if n in approval["exclude"]:
            raise FcmError(f"message {n} was held back in the approval")
        m = messages[n - 1]
        if m.get("delivery") == "simulated":
            raise FcmError("simulated messages are notes, written by the agent; they never reach the gate")
        if not self._demo_ok(m["contact_id"]):
            raise FcmError("demo mode: only contacts tagged fcm:test-contact get real messages")
        if (earlier := self.ledger.claim(req["action_id"], n)) is not None:
            if earlier["state"] == "sent":
                return {"ok": True, "messageId": earlier["ref"], "duplicate": True}
            raise FcmError(f"message {n} was already attempted ({earlier['state']}); settle it, never resend")
        try:
            sent = self.ghl.send_message(m["contact_id"], m["channel"], m["body"], m.get("subject", ""))
        except Exception as exc:
            definite = isinstance(exc, GHLError) and exc.rejected
            self.ledger.finish(req["action_id"], n, "failed" if definite else "unknown")
            raise
        ref = str((sent or {}).get("messageId") or (sent or {}).get("id") or "")
        self.ledger.finish(req["action_id"], n, "sent", ref)
        if self.sent_tag:
            try:
                self.ghl.add_tags(m["contact_id"], [self.sent_tag])
            except Exception:  # noqa: BLE001 - the message is out; a missing tag never turns that into a failure
                pass
        return {"ok": True, "messageId": ref, "approver": approval["approver"]}

    def enroll(self, req: dict[str, Any]) -> dict[str, Any]:
        payload, _approval = self._check(req)
        if req.get("kind") != "enroll_workflow":
            raise FcmError("enroll takes an enroll_workflow batch")
        cid = str(req.get("contact_id", ""))
        if cid not in payload.get("contact_ids", []):
            raise FcmError("that contact isn't in this batch")
        if not self._demo_ok(cid):
            raise FcmError("demo mode: only contacts tagged fcm:test-contact are enrolled")
        n = payload["contact_ids"].index(cid) + 1
        if (earlier := self.ledger.claim(req["action_id"], n)) is not None:
            if earlier["state"] == "sent":
                return {"ok": True, "duplicate": True}
            raise FcmError(f"enrollment {n} was already attempted ({earlier['state']})")
        self.ghl.enroll_workflow(cid, payload["workflow_id"])
        self.ledger.finish(req["action_id"], n, "sent", payload["workflow_id"])
        return {"ok": True}


class ReplyKicker:
    """Runs the agent's reply triage soon after a reply arrives: one run per burst, `delay` seconds after the first."""

    def __init__(self, run: Callable[[], Any], delay: float = 20.0):
        self.run, self.delay = run, delay
        self.lock, self.pending = threading.Lock(), False
        self.kicks = 0

    def hit(self) -> dict[str, Any]:
        with self.lock:
            if self.pending:
                return {"ok": True, "queued": False}  # a run is already coming; it reads every new reply
            self.pending = True
        threading.Timer(self.delay, self._fire).start()
        return {"ok": True, "queued": True, "in_seconds": self.delay}

    def _fire(self) -> None:
        with self.lock:
            self.pending = False  # a reply landing during the run queues the next one
        try:
            self.run()
            self.kicks += 1
        except Exception as exc:  # noqa: BLE001 - the scheduled check still runs every few minutes
            print(f"gate reply kick failed: {type(exc).__name__}: {str(exc)[:200]}", flush=True)


def orgo_triage(api_key: str, computer: str, job_id: str) -> Callable[[], Any]:
    """Ask the Orgo computer to run the reply-triage cron job now (Orgo's bash API; the agent is never exposed)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", job_id or "") or not re.fullmatch(r"[A-Za-z0-9-]{8,64}", computer or ""):
        raise FcmError("GATE_TRIAGE_JOB_ID and GATE_ORGO_COMPUTER_ID must be plain ids")
    command = f"hermes cron run {job_id} >/dev/null 2>&1; timeout -k 10 600 hermes cron tick >/dev/null 2>&1; echo done"

    def run() -> Any:
        req = request.Request(f"https://www.orgo.ai/api/computers/{computer}/bash",
                              data=json.dumps({"command": command}).encode(),
                              headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        with request.urlopen(req, timeout=660) as resp:
            out = json.load(resp)
        if out.get("error"):
            raise FcmError(f"Orgo: {str(out['error'])[:200]}")
        return out
    return run


def make_handler(gate: Gate, token: str, kicker: ReplyKicker | None = None,
                 hook_secret: str = "") -> type[BaseHTTPRequestHandler]:
    routes = {"/approval": gate.approval, "/send": gate.send, "/enroll": gate.enroll}

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            self._reply(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

        def do_POST(self) -> None:  # noqa: N802
            path, _, query = self.path.partition("?")
            if path == "/hook/reply":  # GoHighLevel's webhook can't set a bearer header: the secret rides the URL
                given = (parse.parse_qs(query).get("k") or [""])[0]
                if not (kicker and hook_secret and hmac.compare_digest(given, hook_secret)):
                    return self._reply(401, {"ok": False, "error": "unauthorized"})
                self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 1_000_000))  # the body isn't kept
                return self._reply(200, kicker.hit())
            auth = self.headers.get("Authorization", "")
            if not token or not hmac.compare_digest(auth, f"Bearer {token}"):
                return self._reply(401, {"ok": False, "error": "unauthorized"})
            route = routes.get(self.path)
            if not route:
                return self._reply(404, {"ok": False, "error": "not found"})
            try:
                req = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 5_000_000)))
                self._reply(200, route(req))
            except GHLError as exc:  # GoHighLevel's answer: 422 = it refused (nothing sent), 502 = outcome unknown
                self._reply(422 if exc.rejected else 502, {"ok": False, "error": str(exc)[:300]})
            except FcmError as exc:  # the gate refused: nothing was sent
                self._reply(403, {"ok": False, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001 - the agent gets the reason, never a stack
                self._reply(502, {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]})

        def log_message(self, fmt: str, *args: Any) -> None:  # requests are logged without bodies or the hook secret
            print(f"gate {self.command} {self.path.partition('?')[0]} {args[1] if len(args) > 1 else ''}", flush=True)

    return Handler


def from_env() -> tuple[Gate, str]:
    from .ghl import LiveGHL
    token = os.environ.get("GATE_TOKEN", "")
    if len(token) < 24:
        raise FcmError("GATE_TOKEN must be set (24+ random characters, shared with the agent as FCM_SEND_GATE_TOKEN)")
    ghl = LiveGHL(token=os.environ.get("GATE_GHL_API_KEY", ""), location_id=os.environ.get("GATE_GHL_LOCATION_ID", ""))
    approvers = {u.strip() for u in os.environ.get("GATE_APPROVER_SLACK_IDS", "").split(",") if u.strip()}
    slack_token, channel = os.environ.get("GATE_SLACK_BOT_TOKEN", ""), os.environ.get("GATE_SLACK_CHANNEL", "")
    slack = SlackApprovals(slack_token, channel, approvers) if (slack_token or channel or approvers) else None
    ledger = Ledger(Path(os.environ.get("GATE_DB", "gate.sqlite3")))
    demo_only = os.environ.get("GATE_DEMO_ONLY", "1").strip().lower() not in {"0", "no", "false"}
    require = os.environ.get("GATE_REQUIRE_APPROVAL", "0").strip().lower() in {"1", "yes", "true"}
    return Gate(ghl, slack, ledger, demo_only=demo_only, require_approval=require,
                sent_tag=os.environ.get("GATE_SENT_TAG", "")), token


def kicker_from_env() -> tuple[ReplyKicker | None, str]:
    secret = os.environ.get("GATE_REPLY_HOOK_SECRET", "")
    key, computer = os.environ.get("GATE_ORGO_API_KEY", ""), os.environ.get("GATE_ORGO_COMPUTER_ID", "")
    job = os.environ.get("GATE_TRIAGE_JOB_ID", "")
    if not (secret and key and computer and job):
        return None, ""
    if len(secret) < 24:
        raise FcmError("GATE_REPLY_HOOK_SECRET must be 24+ random characters")
    return ReplyKicker(orgo_triage(key, computer, job), float(os.environ.get("GATE_REPLY_DELAY", "20"))), secret


def serve(port: int) -> None:
    gate, token = from_env()
    kicker, hook_secret = kicker_from_env()
    print(f"send gate on :{port} (demo only: {gate.demo_only}, approval required: {gate.require_approval}, "
          f"location {gate.ghl.location_id}, reply webhook: {'on' if kicker else 'off'})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), make_handler(gate, token, kicker, hook_secret)).serve_forever()


class GateClient:
    """The agent's side: asks the gate for any Slack approval and hands it each message to send."""

    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(self.url + path, data=json.dumps(body).encode(), method="POST",
                              headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                                       "User-Agent": "FundingAffiliateManager/1.0"})
        try:
            with request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read(1_000_000))
        except request.HTTPError as exc:
            try:
                reason = json.loads(exc.read(2000)).get("error", "")
            except Exception:  # noqa: BLE001
                reason = ""
            # 403 the gate refused, 422 GoHighLevel refused: either way nothing went out. Anything else may have.
            raise GHLError(f"send gate {'refused' if exc.code in (403, 422) else 'error'} ({exc.code}): {reason}",
                           status=exc.code) from exc
        except (OSError, ValueError) as exc:
            raise GHLError(f"send gate unreachable or garbled: {exc}", status=0) from exc

    def approval(self, action_id: str, action_digest: str) -> dict[str, Any]:
        return self._post("/approval", {"action_id": action_id, "digest": action_digest})

    def send(self, row: dict[str, Any], payload: dict[str, Any], n: int) -> dict[str, Any]:
        return self._post("/send", {"action_id": row["action_id"], "kind": row["kind"], "payload": payload,
                                    "digest": row["payload_hash"], "n": n})

    def enroll(self, row: dict[str, Any], payload: dict[str, Any], contact_id: str) -> dict[str, Any]:
        return self._post("/enroll", {"action_id": row["action_id"], "kind": row["kind"], "payload": payload,
                                      "digest": row["payload_hash"], "contact_id": contact_id})


def client_from_env() -> GateClient | None:
    url = os.getenv("FCM_SEND_GATE_URL", "").strip()
    return GateClient(url, os.getenv("FCM_SEND_GATE_TOKEN", "")) if url else None


def token_can_send(ghl: Any) -> str:
    """Probe whether a location token holds `conversations/message.write`, without sending anything: a message to a
    contact id that can't exist. A token without the scope gets 401 "not authorized for this scope"; one with it
    gets past auth and fails on the contact. Returns "no", "yes" or "unknown"."""
    from .errors import GHLError
    try:
        ghl._call("POST", "/conversations/messages",
                  body={"type": "SMS", "contactId": "fcm-scope-probe-does-not-exist", "message": "."})
    except GHLError as exc:
        text = str(exc).lower()
        if exc.status == 401 and "scope" in text:
            return "no"
        if exc.status in (400, 404, 422) or (exc.status == 403 and "scope" not in text):
            return "yes"
        return "unknown"
    return "yes"
