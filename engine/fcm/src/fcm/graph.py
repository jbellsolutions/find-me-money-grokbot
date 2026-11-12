"""Relationship graph: what the agent knows about each partner, and where it came from.

Three layers, each with one job:
  * Obsidian vault  the partner note a person opens (fcm.vault), linked to tier, niche, manager, source
                    and product hubs, so Obsidian's graph view is the relationship graph.
  * SQLite index    facts, interactions and hub edges in fcm.sqlite3: segment queries, wave order,
                    variant stats. `reindex()` rebuilds the facts from the vault's ## Facts lines.
  * GHL fields      tier, profile summary, completeness, next step: what the team sees in GoHighLevel
                    (the engine syncs these after every write).

`remember()` is the one writer and `profile()` the one reader. Every fact keeps its source and date.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .cadence import Affiliate
from .store import Store, now_iso
from .vault import Vault

SCHEMA = """
CREATE TABLE IF NOT EXISTS partners (
    contact_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    note_path TEXT NOT NULL DEFAULT '',
    tier TEXT NOT NULL DEFAULT '',
    niche TEXT NOT NULL DEFAULT '',
    manager TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    lifecycle TEXT NOT NULL DEFAULT '',
    deals INTEGER NOT NULL DEFAULT 0,
    completeness INTEGER NOT NULL DEFAULT 0,
    revenue_plan TEXT NOT NULL DEFAULT '',
    kickoff_variant TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    value TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    observed_on TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS facts_by_contact ON facts(contact_id, active);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    at TEXT NOT NULL,
    ref TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    variant TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS interactions_once ON interactions(kind, ref);
CREATE INDEX IF NOT EXISTS interactions_by_contact ON interactions(contact_id, kind);
CREATE TABLE IF NOT EXISTS edges (
    contact_id TEXT NOT NULL,
    hub_type TEXT NOT NULL,
    hub TEXT NOT NULL,
    PRIMARY KEY (contact_id, hub_type, hub)
);
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL DEFAULT '',
    processed_at TEXT NOT NULL
);
"""

SOURCE_LABELS = {"record": "record", "csv_history": "imported notes",
                 "csv": "import", "ghl_note": "CRM note", "ghl_message": "past message",
                 "reply": "text reply", "call": "call", "manual": "manager", "agent": "agent"}
# Values that must never land in the profile: long digit runs (account, card, ID numbers) and SSN-shaped strings.
NEVER_STORE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9,}\b|\bpassword\b|\bssn\b|\bsocial security\b", re.I)
FACT_LINE = re.compile(r"^- (?P<label>[^:]+): (?P<value>.+?) _\((?P<source>[^)]*), (?P<date>\d{4}-\d{2}-\d{2})\)_ "
                       r"%%(?P<slot>\w+) (?P<type>[\w-]+) (?P<ref>\S*)%%$")


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _join(values: list[str]) -> str:
    values = [v for v in values if v]
    if len(values) <= 1:
        return "".join(values)
    return ", ".join(values[:-1]) + " and " + values[-1]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().rstrip(".;,")[:300]


SOURCE_NAMES = {"linkedin": "LinkedIn", "skool": "Skool", "facebook": "Facebook", "legacy-import": "Legacy import"}


def _distinct(values: list[str]) -> list[str]:
    """Drop a value another one already says: "small trucking companies" inside "small trucking companies and a
    few logistics outfits"."""
    low = [v.lower() for v in values]
    return [v for i, v in enumerate(values) if not any(i != j and low[i] in w for j, w in enumerate(low))]


def _upper_first(text: str) -> str:
    """Hub names: capitalize the first letter only, so CPA stays CPA and ISO stays ISO."""
    return text[:1].upper() + text[1:]


class Graph:
    def __init__(self, store: Store, vault: Vault, schema: dict[str, Any], default_manager: str = "",
                 generic_managers: Iterable[str] = ()):
        self.store = store
        self.vault = vault
        self.default_manager = default_manager
        self.generic_managers = set(generic_managers)
        self.slots: dict[str, dict[str, Any]] = {s["key"]: s for s in schema.get("slots", [])}
        self.sections: dict[str, str] = schema.get("sections", {})
        self.key_slots = [k for k, s in self.slots.items() if s.get("key_slot")]
        with self.store.connection() as conn:
            conn.executescript(SCHEMA)

    # ── facts in ─────────────────────────────────────────────────────────────
    def normalize(self, facts: Iterable[Any], meta: bool = False) -> list[Any]:
        """Accept {"slot","value"} dicts (optionally with their own source_type, source_ref, observed_on) or
        "slot: value" strings; unknown slots become notes. Returns (slot, value) pairs, or dicts with meta."""
        out: list[Any] = []
        for item in facts or []:
            extra: dict[str, str] = {}
            if isinstance(item, dict):
                slot, value = str(item.get("slot") or item.get("key") or "note"), item.get("value")
                extra = {k: str(item[k]) for k in ("source_type", "source_ref", "observed_on") if item.get(k)}
            else:
                slot, _, value = str(item).partition(":")
                if not value:
                    slot, value = "note", slot
            slot = slot.strip().lower().replace(" ", "_")
            value = _clean(value)
            if not value or NEVER_STORE.search(value):
                continue
            slot = slot if slot in self.slots else "note"
            out.append({"slot": slot, "value": value, **extra} if meta else (slot, value))
        return out

    def remember(self, aff: Affiliate, *, facts: Iterable[Any] = (), source_type: str = "manual",
                 source_ref: str = "", day: str = "", interaction: dict[str, Any] | list[dict[str, Any]] | None = None,
                 revenue_plan: str | None = None, close_loops: Iterable[int] = ()) -> dict[str, Any]:
        """Write what we learned: facts (deduped, newest wins for single-value slots), an interaction,
        a revenue plan, closed loops. Then regenerate the partner note and the index row."""
        day = day or date.today().isoformat()
        ref = re.sub(r"\s+", "_", source_ref.strip())[:120]
        added: list[dict[str, str]] = []
        with self.store.connection() as conn:
            for fact in self.normalize(facts, meta=True):
                slot, value = fact["slot"], fact["value"]
                row = conn.execute("SELECT id, active FROM facts WHERE contact_id = ? AND slot = ? AND value = ? "
                                   "COLLATE NOCASE", (aff.id, slot, value)).fetchone()
                if row and row["active"]:
                    continue
                if not self.slots.get(slot, {}).get("multi"):
                    conn.execute("UPDATE facts SET active = 0 WHERE contact_id = ? AND slot = ? AND active = 1",
                                 (aff.id, slot))
                if row:
                    conn.execute("UPDATE facts SET active = 1 WHERE id = ?", (row["id"],))
                else:
                    conn.execute("INSERT INTO facts(contact_id, slot, value, source_type, source_ref, observed_on, "
                                 "created_at) VALUES(?,?,?,?,?,?,?)",
                                 (aff.id, slot, value, fact.get("source_type", source_type),
                                  re.sub(r"\s+", "_", fact.get("source_ref", ref))[:120],
                                  fact.get("observed_on", day)[:10], now_iso()))
                added.append({"slot": slot, "value": value})
            for loop_id in close_loops or ():
                conn.execute("UPDATE facts SET active = 0 WHERE id = ? AND contact_id = ? AND slot = 'open_loop'",
                             (int(loop_id), aff.id))
            for i, item in enumerate([interaction] if isinstance(interaction, dict) else interaction or []):
                conn.execute("INSERT OR IGNORE INTO interactions(contact_id, kind, at, ref, summary, variant) "
                             "VALUES(?,?,?,?,?,?)",
                             (aff.id, item["kind"], (item.get("at") or day)[:10],
                              item.get("ref") or f"{aff.id}:{item['kind']}:{now_iso()}:{i}",
                              str(item.get("summary") or "").strip()[:600], item.get("variant", "")))
            if revenue_plan is not None:
                conn.execute("INSERT INTO partners(contact_id, revenue_plan) VALUES(?, ?) ON CONFLICT(contact_id) "
                             "DO UPDATE SET revenue_plan = excluded.revenue_plan", (aff.id, revenue_plan.strip()))
        path, profile = self.render(aff, day)
        return {"facts_added": added, "note": str(path), "profile": profile}

    def close_loops(self, contact_id: str, starts_with: str) -> int:
        with self.store.connection() as conn:
            cur = conn.execute("UPDATE facts SET active = 0 WHERE contact_id = ? AND slot = 'open_loop' AND active = 1 "
                               "AND value LIKE ?", (contact_id, starts_with + "%"))
            return cur.rowcount

    def set_variant(self, contact_id: str, variant: str) -> None:
        with self.store.connection() as conn:
            conn.execute("INSERT INTO partners(contact_id, kickoff_variant) VALUES(?, ?) ON CONFLICT(contact_id) "
                         "DO UPDATE SET kickoff_variant = excluded.kickoff_variant", (contact_id, variant))

    # ── messages already triaged ─────────────────────────────────────────────
    def seen(self, message_ids: Iterable[str]) -> set[str]:
        ids = [m for m in message_ids if m]
        if not ids:
            return set()
        with self.store.connection() as conn:
            rows = conn.execute(f"SELECT message_id FROM processed_messages WHERE message_id IN "
                                f"({','.join('?' * len(ids))})", ids).fetchall()
        return {r["message_id"] for r in rows}

    def last_processed_at(self, contact_id: str) -> str:
        """When we last triaged a text from this partner (this server's clock)."""
        with self.store.connection() as conn:
            row = conn.execute("SELECT MAX(processed_at) at FROM processed_messages WHERE contact_id = ?",
                               (contact_id,)).fetchone()
        return (row["at"] if row else "") or ""

    def mark_seen(self, message_ids: Iterable[str], contact_id: str) -> None:
        with self.store.connection() as conn:
            for mid in message_ids:
                if mid:
                    conn.execute("INSERT OR IGNORE INTO processed_messages(message_id, contact_id, processed_at) "
                                 "VALUES(?,?,?)", (mid, contact_id, now_iso()))

    # ── interactions ─────────────────────────────────────────────────────────
    def has_interaction(self, kind: str, ref: str) -> bool:
        with self.store.connection() as conn:
            return conn.execute("SELECT 1 FROM interactions WHERE kind = ? AND ref = ?", (kind, ref)).fetchone() \
                is not None

    def contacts_with(self, kind: str) -> set[str]:
        with self.store.connection() as conn:
            return {r["contact_id"] for r in conn.execute("SELECT DISTINCT contact_id FROM interactions WHERE kind = ?",
                                                          (kind,)).fetchall()}

    def interactions(self, contact_id: str, kinds: Iterable[str] = (), limit: int = 50) -> list[dict[str, Any]]:
        kinds = list(kinds)
        sql = "SELECT kind, at, ref, summary, variant FROM interactions WHERE contact_id = ?"
        args: list[Any] = [contact_id]
        if kinds:
            sql += f" AND kind IN ({','.join('?' * len(kinds))})"
            args += kinds
        with self.store.connection() as conn:
            rows = conn.execute(sql + " ORDER BY at DESC, id DESC LIMIT ?", (*args, limit)).fetchall()
        return [dict(r) for r in rows]

    # ── the profile ──────────────────────────────────────────────────────────
    def facts(self, contact_id: str) -> list[dict[str, Any]]:
        with self.store.connection() as conn:
            rows = conn.execute("SELECT id, slot, value, source_type, source_ref, observed_on FROM facts "
                                "WHERE contact_id = ? AND active = 1 ORDER BY observed_on, id", (contact_id,)).fetchall()
        return [dict(r) for r in rows]

    def profile(self, aff: Affiliate, today: date) -> dict[str, Any]:
        """Everything the agent knows about one partner, shaped for drafting and for the note."""
        facts = self.facts(aff.id)
        slots: dict[str, list[dict[str, Any]]] = {}
        for f in facts:
            slots.setdefault(f["slot"], []).append(f)
        record = {"tier": aff.tier, "niche": str(aff.fields.get("niche") or "").strip()}
        for key, value in record.items():  # what the CRM record says counts, even before anyone confirms it
            if value and key not in slots:
                slots[key] = [{"id": 0, "slot": key, "value": value, "source_type": "record", "source_ref": "",
                               "observed_on": str(aff.fields.get("join_date") or today.isoformat())[:10]}]
        filled = [k for k in self.key_slots if slots.get(k)]
        completeness = round(100 * len(filled) / max(len(self.key_slots), 1))
        askable = sorted((s for k, s in self.slots.items() if s.get("question") and not slots.get(k)),
                         key=lambda s: s.get("ask_rank", 99))
        next_question = {"slot": askable[0]["key"], "question": askable[0]["question"]} if askable else None
        with self.store.connection() as conn:
            row = conn.execute("SELECT revenue_plan, kickoff_variant FROM partners WHERE contact_id = ?",
                               (aff.id,)).fetchone()
        history = self.interactions(aff.id, limit=40)
        values = {k: [f["value"] for f in v] for k, v in slots.items()}
        loops = [{"id": f["id"], "text": f["value"], "since": f["observed_on"]} for f in slots.get("open_loop", [])]
        joined = aff.day("join_date")
        engaged = any(i["kind"] in {"reply", "call"} for i in history)
        return {
            "contact_id": aff.id,
            "name": aff.name,
            "first_name": aff.first_name,
            "tier": aff.tier,
            "plan": str(aff.fields.get("plan") or ""),
            "niche": record["niche"],
            "source": aff.source,
            "lifecycle": aff.lifecycle,
            "joined": joined.isoformat() if joined else "",
            "tenure_months": ((today.year - joined.year) * 12 + today.month - joined.month) if joined else None,
            "deals": aff.deals_submitted,
            "last_deal": str(aff.fields.get("last_deal_date") or "")[:10],
            "last_reply": str(aff.fields.get("last_reply_date") or "")[:10],
            "manager": self.manager_name(aff),
            "values": values,
            "facts": facts,
            "open_loops": loops,
            "completeness": completeness,
            "filled_slots": filled,
            "next_question": next_question,
            "open_questions": [{"slot": a["key"], "question": a["question"]} for a in askable],
            "summary": self.summary(aff, values, loops),
            "revenue_plan": (row["revenue_plan"] if row else "") or "",
            "kickoff_variant": (row["kickoff_variant"] if row else "") or "",
            "engaged": engaged,
            "kickoff": next((t.split(":", 1)[1] for t in aff.tags if t.startswith("fcm:kickoff-")), ""),
            "history": history[:12],
        }

    def manager_name(self, aff: Affiliate) -> str:
        """The partner's named manager: the one who signs their texts and owns the relationship."""
        name = str(aff.fields.get("assigned_manager") or "").strip()
        return self.default_manager if name in self.generic_managers else name or self.default_manager

    def summary(self, aff: Affiliate, values: dict[str, list[str]], loops: list[dict[str, Any]]) -> str:
        """Five short lines a manager can read before a call. Built from facts only, never invented."""
        niche = (values.get("niche") or [""])[-1]
        tier = (values.get("tier") or [""])[-1]
        joined = aff.day("join_date")
        role = niche or "partner"
        first = f"{_article(role).capitalize()} {role}"
        if tier:
            first += f" on the {tier} tier"
        if joined:
            first += f", partner since {joined:%B %Y}"
        lines = [first + "."]
        n, last = aff.deals_submitted, aff.day("last_deal_date")
        if n:
            lines.append(f"Has sent {n} deal{'s' if n != 1 else ''}" + (f", the last in {last:%B %Y}." if last else "."))
        else:  # imported records often carry the last deal date without a count
            lines.append(f"Last deal in {last:%B %Y}." if last else "No deals sent yet.")
        work = []
        if values.get("client_types"):
            work.append(f"Works mostly with {_join(_distinct(values['client_types'])[-2:])}")
        if values.get("deal_types"):
            need = f"their clients usually need {_join(_distinct(values['deal_types'])[-3:])}"
            if values.get("deal_size"):
                need += f" ({values['deal_size'][-1]})"
            work.append(need)
        if work:
            text = "; ".join(work)
            lines.append(text[0].upper() + text[1:] + ".")
        if values.get("goals"):
            lines.append(f"Working toward: {values['goals'][-1]}.")
        reach = [v[-1] for k in ("channel", "best_time") if (v := values.get(k))]
        if reach or loops:
            tail = f"Best reached by {', '.join(reach)}." if reach else ""
            if loops:
                tail += f" {len(loops)} open loop{'s' if len(loops) != 1 else ''}."
            lines.append(tail.strip())
        return " ".join(lines[:5])

    # ── the note ─────────────────────────────────────────────────────────────
    def next_step(self, profile: dict[str, Any]) -> str:
        if profile["open_loops"]:
            return profile["open_loops"][0]["text"][:120]
        if profile["kickoff"] == "pending":
            return "Kickoff text queued"
        if profile["kickoff"] == "sent":
            return "Waiting on a reply to the kickoff"
        if profile["next_question"]:
            return "Ask: " + profile["next_question"]["question"]
        return "Keep the two-week cadence"

    def render(self, aff: Affiliate, day: str) -> tuple[Path, dict[str, Any]]:
        today = date.fromisoformat(day[:10])
        p = self.profile(aff, today)
        hubs: list[tuple[str, str]] = []
        if p["tier"]:
            hubs.append(("tier", p["tier"]))
        if p["niche"]:
            hubs.append(("niche", _upper_first(p["niche"])))
        if p["manager"]:
            hubs.append(("manager", p["manager"]))
        if p["source"] and p["source"] != "unknown":
            hubs.append(("source", SOURCE_NAMES.get(p["source"], _upper_first(p["source"].replace("-", " ")))))
        for need in p["values"].get("deal_types", [])[-4:]:
            hubs.append(("product", _upper_first(need)))
        labels = {"tier": "Tier", "niche": "Does", "manager": "Manager", "source": "Came from", "product": "Clients need"}
        grouped: dict[str, list[str]] = {}
        for kind, name in hubs:
            grouped.setdefault(kind, []).append(self.vault.hub_link(kind, name))
        links = " · ".join(f"**{labels[k]}** {', '.join(v)}" for k, v in grouped.items())

        def lines(section: str) -> str:
            out = []
            for key, slot in self.slots.items():
                if slot.get("section") != section or key == "open_loop":
                    continue
                for f in [f for f in p["facts"] if f["slot"] == key] or (
                        [{"value": v, "source_type": "record", "observed_on": ""} for v in p["values"].get(key, [])]
                        if slot.get("from_record") else []):
                    when = f" _({SOURCE_LABELS.get(f['source_type'], f['source_type'])}" + (
                        f", {f['observed_on']})_" if f["observed_on"] else ")_")
                    out.append(f"- **{slot['label']}:** {f['value']}{when}")
            return "\n".join(out)

        profile_text = p["summary"] + f"\n\nProfile {p['completeness']}% complete."
        if p["next_question"]:
            profile_text += f" Next question to ask: _{p['next_question']['question']}_"
        loops = "\n".join(f"- [ ] {l['text']} _(since {l['since']})_" for l in p["open_loops"])
        facts = "\n".join(
            f"- {self.slots.get(f['slot'], {}).get('label', f['slot'])}: {f['value']} "
            f"_({SOURCE_LABELS.get(f['source_type'], f['source_type'])}, {f['observed_on']})_ "
            f"%%{f['slot']} {f['source_type']} {f['source_ref'] or '-'}%%" for f in p["facts"])
        calls = "\n".join(f"- {i['at']} {i['summary']}" for i in self.interactions(aff.id, ["call"], limit=20))
        record = "\n".join(f"- {i['at'][:10]} {_upper_first(i['summary'])}" for i in self.interactions(aff.id, ["history"], limit=8))
        background = "\n".join(x for x in (lines("history"), ("**From their record:**\n" + record) if record else "") if x)
        sections = [
            ("Profile", profile_text),
            (self.sections.get("goals", "What they want"), lines("goals")),
            (self.sections.get("work", "How they work"), lines("work")),
            (self.sections.get("loops", "Open loops"), loops),
            ("Revenue plan", p["revenue_plan"] or "_Drafted once they've engaged and the profile is at least "
                                                  "60% complete._"),
            (self.sections.get("history", "History"), background),
            ("Facts", facts),
            ("Calls", calls),
        ]
        front = {"tier": p["tier"], "plan": p["plan"], "niche": p["niche"], "joined": p["joined"],
                 "tenure_months": p["tenure_months"] if p["tenure_months"] is not None else "",
                 "lifecycle": p["lifecycle"].removeprefix("aff:"), "source": p["source"], "deals": p["deals"],
                 "last_deal": p["last_deal"], "last_reply": p["last_reply"],
                 "preferred_channel": (p["values"].get("channel") or [aff.fields.get("preferred_channel") or ""])[-1],
                 "manager": f"[[Managers/{p['manager']}]]" if p["manager"] else "",
                 "profile_completeness": p["completeness"], "kickoff": p["kickoff"],
                 "kickoff_variant": p["kickoff_variant"], "next_step": self.next_step(p), "updated": day}
        path = self.vault.write_partner(aff.name, aff.id, front, links, sections)
        with self.store.connection() as conn:
            conn.execute(
                "INSERT INTO partners(contact_id, name, note_path, tier, niche, manager, source, lifecycle, deals, "
                "completeness, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(contact_id) DO UPDATE SET "
                "name = excluded.name, note_path = excluded.note_path, tier = excluded.tier, niche = excluded.niche, "
                "manager = excluded.manager, source = excluded.source, lifecycle = excluded.lifecycle, "
                "deals = excluded.deals, completeness = excluded.completeness, updated_at = excluded.updated_at",
                (aff.id, aff.name, str(path.relative_to(self.vault.root)), p["tier"], p["niche"], p["manager"],
                 p["source"], p["lifecycle"], p["deals"], p["completeness"], now_iso()))
            conn.execute("DELETE FROM edges WHERE contact_id = ?", (aff.id,))
            conn.executemany("INSERT OR IGNORE INTO edges(contact_id, hub_type, hub) VALUES(?,?,?)",
                             [(aff.id, kind, name) for kind, name in hubs])
        p["note_path"] = str(path.relative_to(self.vault.root))
        p["next_step"] = front["next_step"]
        return path, p

    # ── queries ──────────────────────────────────────────────────────────────
    def query(self, *, tier: str = "", niche: str = "", slot: str = "", contains: str = "", hub: str = "",
              min_completeness: int = 0, max_completeness: int = 100, limit: int = 50) -> list[dict[str, Any]]:
        """Segment the program: e.g. Gold partners whose clients need equipment financing."""
        sql = ("SELECT DISTINCT p.contact_id, p.name, p.tier, p.niche, p.manager, p.lifecycle, p.deals, "
               "p.completeness, p.note_path FROM partners p")
        where, args = ["p.completeness BETWEEN ? AND ?"], [min_completeness, max_completeness]
        if slot or contains:
            sql += " JOIN facts f ON f.contact_id = p.contact_id AND f.active = 1"
            if slot:
                where.append("f.slot = ?")
                args.append(slot)
            if contains:
                where.append("f.value LIKE ?")
                args.append(f"%{contains}%")
        if hub:
            sql += " JOIN edges e ON e.contact_id = p.contact_id"
            where.append("e.hub LIKE ?")
            args.append(f"%{hub}%")
        if tier:
            where.append("p.tier = ? COLLATE NOCASE")
            args.append(tier)
        if niche:
            where.append("p.niche LIKE ?")
            args.append(f"%{niche}%")
        sql += " WHERE " + " AND ".join(where) + " ORDER BY p.deals DESC, p.completeness DESC LIMIT ?"
        with self.store.connection() as conn:
            return [dict(r) for r in conn.execute(sql, (*args, limit)).fetchall()]

    def stats(self) -> dict[str, Any]:
        with self.store.connection() as conn:
            partners = conn.execute("SELECT COUNT(*) n, COALESCE(AVG(completeness), 0) avg FROM partners").fetchone()
            facts = conn.execute("SELECT COUNT(*) n FROM facts WHERE active = 1").fetchone()["n"]
            by_source = {r["source_type"]: r["n"] for r in conn.execute(
                "SELECT source_type, COUNT(*) n FROM facts WHERE active = 1 GROUP BY source_type")}
            hubs = {r["hub_type"]: r["n"] for r in conn.execute(
                "SELECT hub_type, COUNT(DISTINCT hub) n FROM edges GROUP BY hub_type")}
            links = conn.execute("SELECT COUNT(*) n FROM edges").fetchone()["n"]
            buckets = {r["b"]: r["n"] for r in conn.execute(
                "SELECT CASE WHEN completeness >= 80 THEN '80-100' WHEN completeness >= 50 THEN '50-79' "
                "WHEN completeness >= 30 THEN '30-49' ELSE '0-29' END b, COUNT(*) n FROM partners GROUP BY b")}
            calls = conn.execute("SELECT COUNT(*) n FROM interactions WHERE kind = 'call'").fetchone()["n"]
            plans = conn.execute("SELECT COUNT(*) n FROM partners WHERE revenue_plan != ''").fetchone()["n"]
        return {"partners": partners["n"], "avg_completeness": round(partners["avg"], 1), "facts": facts,
                "facts_by_source": by_source, "hubs": hubs, "hub_links": links, "completeness_buckets": buckets,
                "calls": calls, "revenue_plans": plans}

    def variant_stats(self) -> dict[str, dict[str, Any]]:
        """Kickoff variants: sent, replied after the kickoff, and talked on a call."""
        with self.store.connection() as conn:
            rows = conn.execute(
                "SELECT k.variant v, COUNT(DISTINCT k.contact_id) sent, "
                "COUNT(DISTINCT CASE WHEN r.kind = 'reply' THEN r.contact_id END) replied, "
                "COUNT(DISTINCT CASE WHEN r.kind = 'call' THEN r.contact_id END) calls "
                "FROM interactions k LEFT JOIN interactions r ON r.contact_id = k.contact_id "
                "AND r.kind IN ('reply', 'call') AND r.at >= k.at WHERE k.kind = 'kickoff_sent' GROUP BY k.variant")
            out = {}
            for r in rows:
                out[r["v"] or "?"] = {"sent": r["sent"], "replied": r["replied"], "calls": r["calls"],
                                      "reply_rate": round(r["replied"] / max(r["sent"], 1), 3)}
        return dict(sorted(out.items()))

    def reindex(self) -> dict[str, Any]:
        """Rebuild the facts table from the vault's partner notes (the vault is the source of truth)."""
        restored = 0
        with self.store.connection() as conn:
            for path in sorted((self.vault.root / "Partners").glob("*.md")):
                text = path.read_text()
                cid = re.search(r"^ghl_contact_id:\s*\"?([^\"\n]+)", text, re.M)
                if not cid:
                    continue
                for line in text.splitlines():
                    m = FACT_LINE.match(line)
                    if not m:
                        continue
                    exists = conn.execute("SELECT 1 FROM facts WHERE contact_id = ? AND slot = ? AND value = ?",
                                          (cid.group(1), m["slot"], m["value"])).fetchone()
                    if exists:
                        continue
                    conn.execute("INSERT INTO facts(contact_id, slot, value, source_type, source_ref, observed_on, "
                                 "created_at) VALUES(?,?,?,?,?,?,?)",
                                 (cid.group(1), m["slot"], m["value"], m["type"], "" if m["ref"] == "-" else m["ref"],
                                  m["date"], now_iso()))
                    restored += 1
        return {"ok": True, "facts_restored": restored}
