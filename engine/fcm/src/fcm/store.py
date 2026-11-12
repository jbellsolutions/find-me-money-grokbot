"""SQLite ledger: frozen outbound actions, one-time approvals, standing approvals,
daily caps, the external-write kill switch, and an append-only audit log."""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    recipients INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL,
    approval_id TEXT NOT NULL DEFAULT '',
    result_json TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS actions_dedupe ON actions(kind, payload_hash);
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    digest TEXT NOT NULL,
    approver TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS standing_approvals (
    standing_id TEXT PRIMARY KEY,
    workflow_key TEXT NOT NULL,
    max_per_day INTEGER NOT NULL,
    approver TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS counters (
    day TEXT NOT NULL,
    kind TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, kind)
);
CREATE TABLE IF NOT EXISTS flags (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    decision TEXT NOT NULL,
    result TEXT NOT NULL,
    details_json TEXT NOT NULL
);
-- One row per message in an approved batch, written before the send and updated after it.
-- state: pending | sending | sent | failed | unknown | skipped | held_back. "unknown" means GoHighLevel may have
-- delivered it (a timeout, a 5xx); a person settles it and it is never resent automatically.
CREATE TABLE IF NOT EXISTS outbox (
    action_id TEXT NOT NULL,
    n INTEGER NOT NULL,
    contact_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    channel TEXT NOT NULL,
    state TEXT NOT NULL,
    message_id TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    booked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (action_id, n)
);
CREATE INDEX IF NOT EXISTS outbox_contact ON outbox(contact_id, kind, state);
-- A partner gets one kickoff, ever: a second one can't even be claimed for sending.
CREATE UNIQUE INDEX IF NOT EXISTS outbox_one_kickoff ON outbox(contact_id)
    WHERE kind = 'kickoff' AND state IN ('sending', 'sent', 'unknown');
-- Contacts held by a prepared batch, so a second batch can't pick them up while the first is still open.
CREATE TABLE IF NOT EXISTS reservations (
    contact_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (contact_id, action_id)
);
-- How far the inbox has read each conversation (every inbound message up to here has been triaged).
CREATE TABLE IF NOT EXISTS inbox_watermark (
    conversation_id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL,
    scanned_through TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

OPEN_ACTION_STATES = ("prepared", "approval_requested", "approved", "executing", "paused")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode()).hexdigest()[:16]


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(SCHEMA)
            try:  # approvals made before approve-with-exceptions existed
                conn.execute("ALTER TABLE approvals ADD COLUMN excluded_json TEXT NOT NULL DEFAULT '[]'")
            except sqlite3.OperationalError:
                pass

    @contextlib.contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # flags / kill switch
    def get_flag(self, key: str, default: str = "") -> str:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM flags WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_flag(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO flags(key, value, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value, now_iso()),
            )

    # counters
    def count(self, day: str, kind: str) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT count FROM counters WHERE day = ? AND kind = ?", (day, kind)).fetchone()
        return int(row["count"]) if row else 0

    def bump(self, day: str, kind: str, amount: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO counters(day, kind, count) VALUES(?,?,?) "
                "ON CONFLICT(day, kind) DO UPDATE SET count = count + excluded.count",
                (day, kind, amount),
            )

    # audit
    def audit(self, *, actor: str, action: str, resource: str, decision: str, result: str,
              details: dict[str, Any] | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO audit(at, actor, action, resource, decision, result, details_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (now_iso(), actor, action, resource, decision, result, stable_json(details or {})),
            )

    def recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # actions
    def get_action(self, action_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM actions WHERE action_id = ?", (action_id,)).fetchone()
        return dict(row) if row else None

    def find_action(self, kind: str, payload_hash: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM actions WHERE kind = ? AND payload_hash = ?",
                               (kind, payload_hash)).fetchone()
        return dict(row) if row else None

    def insert_action(self, row: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO actions(action_id, kind, payload_json, payload_hash, recipients, state, summary, "
                "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (row["action_id"], row["kind"], row["payload_json"], row["payload_hash"], row["recipients"],
                 row["state"], row["summary"], row["created_at"], row["updated_at"]),
            )

    def update_action(self, action_id: str, **values: Any) -> None:
        values["updated_at"] = now_iso()
        cols = ", ".join(f"{k} = ?" for k in values)
        with self.connection() as conn:
            conn.execute(f"UPDATE actions SET {cols} WHERE action_id = ?", (*values.values(), action_id))

    def transition(self, action_id: str, from_states: tuple[str, ...], to_state: str) -> bool:
        """Move an action between states only if it is still in one of from_states (two runs can't both win)."""
        with self.connection() as conn:
            cur = conn.execute(f"UPDATE actions SET state = ?, updated_at = ? WHERE action_id = ? AND state IN "
                               f"({','.join('?' * len(from_states))})", (to_state, now_iso(), action_id, *from_states))
            return cur.rowcount == 1

    # reservations: contacts held by an open batch
    def reserve(self, action_id: str, kind: str, contact_ids: list[str]) -> None:
        with self.connection() as conn:
            conn.executemany("INSERT OR IGNORE INTO reservations(contact_id, action_id, kind, created_at) "
                             "VALUES(?,?,?,?)", [(c, action_id, kind, now_iso()) for c in contact_ids])

    def reserved(self, contact_ids: list[str] | None = None, kinds: tuple[str, ...] = (),
                 exclude_action: str = "") -> dict[str, str]:
        """contact_id -> action_id for contacts held by another batch that is still open."""
        sql = (f"SELECT r.contact_id, r.action_id FROM reservations r JOIN actions a ON a.action_id = r.action_id "
               f"WHERE a.state IN ({','.join('?' * len(OPEN_ACTION_STATES))}) AND r.action_id != ?")
        args: list[Any] = [*OPEN_ACTION_STATES, exclude_action]
        if kinds:
            sql += f" AND r.kind IN ({','.join('?' * len(kinds))})"
            args += list(kinds)
        with self.connection() as conn:
            rows = conn.execute(sql, args).fetchall()
        wanted = set(contact_ids) if contact_ids is not None else None
        return {r["contact_id"]: r["action_id"] for r in rows if wanted is None or r["contact_id"] in wanted}

    # outbox
    def outbox_init(self, action_id: str, messages: list[dict[str, Any]]) -> None:
        with self.connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO outbox(action_id, n, contact_id, kind, channel, state, created_at, updated_at) "
                "VALUES(?,?,?,?,?,'pending',?,?)",
                [(action_id, n, m["contact_id"], m.get("kind", ""), m["channel"], now_iso(), now_iso())
                 for n, m in enumerate(messages, 1)])

    def outbox(self, action_id: str = "", states: tuple[str, ...] = (), contact_id: str = "",
               kinds: tuple[str, ...] = (), limit: int = 5000) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM outbox WHERE 1 = 1", []
        for col, value in (("action_id", action_id), ("contact_id", contact_id)):
            if value:
                sql += f" AND {col} = ?"
                args.append(value)
        for col, values in (("state", states), ("kind", kinds)):
            if values:
                sql += f" AND {col} IN ({','.join('?' * len(values))})"
                args += list(values)
        with self.connection() as conn:
            rows = conn.execute(sql + " ORDER BY created_at, action_id, n LIMIT ?", (*args, limit)).fetchall()
        return [dict(r) for r in rows]

    def outbox_claim(self, action_id: str, n: int) -> bool:
        """pending -> sending. False if another run took it, or (for a kickoff) the contact already has one."""
        try:
            with self.connection() as conn:
                cur = conn.execute("UPDATE outbox SET state = 'sending', updated_at = ? WHERE action_id = ? AND n = ? "
                                   "AND state = 'pending'", (now_iso(), action_id, n))
                return cur.rowcount == 1
        except sqlite3.IntegrityError:
            self.outbox_set(action_id, n, state="skipped", detail="this partner already has a kickoff")
            return False

    def outbox_set(self, action_id: str, n: int, **values: Any) -> None:
        values["updated_at"] = now_iso()
        cols = ", ".join(f"{k} = ?" for k in values)
        with self.connection() as conn:
            conn.execute(f"UPDATE outbox SET {cols} WHERE action_id = ? AND n = ?", (*values.values(), action_id, n))

    def kickoff_claimed(self, contact_ids: list[str] | None = None) -> set[str]:
        """Contacts with a kickoff that went out, is going out, or may have gone out."""
        with self.connection() as conn:
            rows = conn.execute("SELECT DISTINCT contact_id FROM outbox WHERE kind = 'kickoff' AND state IN "
                                "('sending', 'sent', 'unknown')").fetchall()
        found = {r["contact_id"] for r in rows}
        return found if contact_ids is None else found & set(contact_ids)

    # inbox watermarks
    def watermark(self, conversation_id: str) -> str:
        with self.connection() as conn:
            row = conn.execute("SELECT scanned_through FROM inbox_watermark WHERE conversation_id = ?",
                               (conversation_id,)).fetchone()
        return row["scanned_through"] if row else ""

    def set_watermark(self, conversation_id: str, contact_id: str, scanned_through: str) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO inbox_watermark(conversation_id, contact_id, scanned_through, updated_at) "
                         "VALUES(?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET scanned_through = "
                         "excluded.scanned_through, updated_at = excluded.updated_at",
                         (conversation_id, contact_id, scanned_through, now_iso()))

    def list_actions(self, state: str = "", limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as conn:
            if state:
                rows = conn.execute("SELECT * FROM actions WHERE state = ? ORDER BY created_at DESC LIMIT ?",
                                    (state, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # approvals
    def insert_approval(self, row: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO approvals(approval_id, action_id, digest, approver, created_at, expires_at, excluded_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (row["approval_id"], row["action_id"], row["digest"], row["approver"], row["created_at"],
                 row["expires_at"], row.get("excluded_json", "[]")),
            )

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        return dict(row) if row else None

    def use_approval(self, approval_id: str) -> bool:
        """Consume a one-time approval atomically; False if it was already used."""
        with self.connection() as conn:
            cur = conn.execute("UPDATE approvals SET used_at = ? WHERE approval_id = ? AND used_at = ''",
                               (now_iso(), approval_id))
            return cur.rowcount == 1

    # standing approvals
    def insert_standing(self, row: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO standing_approvals(standing_id, workflow_key, max_per_day, approver, created_at, "
                "expires_at, reason) VALUES(?,?,?,?,?,?,?)",
                (row["standing_id"], row["workflow_key"], row["max_per_day"], row["approver"], row["created_at"],
                 row["expires_at"], row.get("reason", "")),
            )

    def active_standing(self, workflow_key: str) -> dict[str, Any] | None:
        now = now_iso()
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM standing_approvals WHERE workflow_key = ? AND revoked_at = '' AND expires_at > ? "
                "ORDER BY created_at DESC LIMIT 1",
                (workflow_key, now),
            ).fetchone()
        return dict(row) if row else None

    def list_standing(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM standing_approvals ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def revoke_standing(self, standing_id: str, reason: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "UPDATE standing_approvals SET revoked_at = ?, reason = ? WHERE standing_id = ? AND revoked_at = ''",
                (now_iso(), reason, standing_id),
            )
            return cur.rowcount == 1
