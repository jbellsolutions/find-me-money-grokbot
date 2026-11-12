"""Obsidian vault memory: daily notes, one profile note per partner, hub notes, call notes, review files.

The vault is plain markdown with wiki-links so Justin (or the client's manager) can open it in
Obsidian and see exactly what the agent did and what it knows about each partner. Partner notes
link to hub notes (tier, niche, manager, source, products), so Obsidian's graph view is the
relationship graph. Semantic search can be layered on top; these files stay the source of truth.

A partner note is found by the last six characters of the GHL contact id in its file name, so a
rename moves the note instead of starting a second one. Only two parts of it are not regenerated:
`## Manager notes` (the human's, never touched by code) and `## Timeline` (append-only, always last).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FOLDERS = ("Daily", "Leads", "Partners", "Calls", "Reviews", "Tiers", "Niches", "Managers", "Sources", "Products",
           "Campaigns", "Events", "Newsletters", "Reports")
HUB_FOLDERS = {"tier": "Tiers", "niche": "Niches", "manager": "Managers", "source": "Sources", "product": "Products"}
HUB_BLURB = {"tier": "Partners on this tier", "niche": "Partners in this line of work",
             "manager": "Partners this manager owns", "source": "Partners who came in through this source",
             "product": "Partners whose clients need this"}
MANAGER_NOTES = "## Manager notes"
TIMELINE = "## Timeline"
MANAGER_PLACEHOLDER = "_Yours. The agent reads this section and never edits it._"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|#^\[\]]", "", text).strip()
    return re.sub(r"\s+", " ", cleaned)[:80] or "untitled"


def _yaml_value(value: Any) -> str:
    if value is None or value == "":
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\n", " ").strip()
    if re.search(r"[:#\[\]{}&*!|>'\"%@`,]", text) or text.lower() in {"yes", "no", "true", "false", "null"}:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def frontmatter(values: dict[str, Any]) -> str:
    return "---\n" + "".join(f"{k}: {_yaml_value(v)}\n" for k, v in values.items()) + "---\n"


def _frontmatter_id(path: Path) -> str:
    try:
        head = path.read_text()[:600]
    except OSError:
        return ""
    match = re.search(r"^ghl_contact_id:\s*\"?([^\"\n]+)", head, re.M)
    return match.group(1).strip() if match else ""


def _section(text: str, heading: str) -> str:
    """Body of one `## ` section (empty when absent)."""
    start = text.find("\n" + heading + "\n")
    if start < 0:
        return ""
    start += len(heading) + 2
    end = text.find("\n## ", start)
    return text[start:end if end >= 0 else len(text)].strip("\n")


class Vault:
    def __init__(self, root: Path, timezone: str = "America/New_York"):
        self.root = root
        self.tz = ZoneInfo(timezone)
        self._by_id6: dict[str, list[Path]] | None = None
        for folder in FOLDERS:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    # ── partner notes ────────────────────────────────────────────────────────
    def partner_path(self, name: str, contact_id: str) -> Path:
        """The partner's note, found by id. Renames a note whose partner changed name, and moves a note
        from the old Affiliates/ folder into Partners/. Returns the path for a new note when none exists."""
        id6 = contact_id[-6:]
        want = self.root / "Partners" / f"{_slug(name)} ({id6}).md"
        if want.exists():
            return want
        if self._by_id6 is None:  # one directory scan per Vault, not one per lookup (13,000 notes)
            self._by_id6 = {}
            for folder in ("Partners", "Affiliates"):
                directory = self.root / folder
                for path in directory.glob("* (??????).md") if directory.is_dir() else ():
                    self._by_id6.setdefault(path.stem[-7:-1], []).append(path)
        for path in list(self._by_id6.get(id6, [])):
            if path.exists() and _frontmatter_id(path) in ("", contact_id):
                path.rename(want)
                self._by_id6[id6] = [p for p in self._by_id6[id6] if p != path] + [want]
                return want
        self._by_id6.setdefault(id6, []).append(want)
        return want

    def partner_link(self, name: str, contact_id: str) -> str:
        return f"[[Partners/{_slug(name)} ({contact_id[-6:]})|{name}]]"

    affiliate_link = partner_link

    def _new_partner(self, name: str, contact_id: str, source: str, lifecycle: str) -> str:
        return (frontmatter({"type": "partner", "ghl_contact_id": contact_id, "source": source or "unknown",
                             "lifecycle": lifecycle or "unknown"})
                + f"# {name}\n\n{MANAGER_NOTES}\n{MANAGER_PLACEHOLDER}\n\n{TIMELINE}\n")

    def affiliate(self, name: str, contact_id: str, line: str, *, source: str = "", lifecycle: str = "",
                  day: str = "") -> Path:
        """Append one dated line to the partner's timeline (the note's last section)."""
        path = self.partner_path(name, contact_id)
        if not path.exists():
            path.write_text(self._new_partner(name, contact_id, source, lifecycle))
        day = day or self._now().date().isoformat()
        text = path.read_text()
        if f"\n{TIMELINE}\n" not in "\n" + text:
            text = text.rstrip("\n") + f"\n\n{TIMELINE}\n"
        line = re.sub(r"\s+", " ", line).strip()
        path.write_text(text.rstrip("\n") + f"\n- {day} [[Daily/{day}]] — {line}\n")
        return path

    def write_partner(self, name: str, contact_id: str, front: dict[str, Any], links: str,
                      sections: list[tuple[str, str]]) -> Path:
        """Regenerate a partner note from the profile, keeping Manager notes and the Timeline as they are."""
        path = self.partner_path(name, contact_id)
        old = path.read_text() if path.exists() else ""
        manager = _section(old, MANAGER_NOTES) or MANAGER_PLACEHOLDER
        timeline = _section(old, TIMELINE)
        parts = [frontmatter({"type": "partner", "ghl_contact_id": contact_id, **front}), f"# {name}\n"]
        if links:
            parts.append(links + "\n")
        for heading, body in sections:
            parts.append(f"## {heading}\n{body.strip() or '_Nothing yet._'}\n")
        parts.append(f"{MANAGER_NOTES}\n{manager}\n")
        parts.append(f"{TIMELINE}\n{timeline}\n" if timeline else f"{TIMELINE}\n")
        path.write_text("\n".join(parts))
        return path

    def read_partner_section(self, name: str, contact_id: str, heading: str) -> str:
        path = self.partner_path(name, contact_id)
        return _section(path.read_text(), heading) if path.exists() else ""

    # ── hubs: the nodes partners link to ─────────────────────────────────────
    def hub_link(self, kind: str, name: str) -> str:
        folder = HUB_FOLDERS[kind]
        slug = _slug(name)
        path = self.root / folder / f"{slug}.md"
        if not path.exists():
            path.write_text(frontmatter({"type": f"hub-{kind}", "name": name})
                            + f"# {name}\n\n{HUB_BLURB[kind]} link here. Open the graph view to see them.\n")
        return f"[[{folder}/{slug}|{name}]]"

    # ── calls and reviews ────────────────────────────────────────────────────
    def call_note(self, day: str, name: str, front: dict[str, Any], sections: list[tuple[str, str]]) -> Path:
        base = f"{day} {_slug(name)}"
        path = self.root / "Calls" / f"{base}.md"
        n = 2
        while path.exists():
            path = self.root / "Calls" / f"{base} {n}.md"
            n += 1
        body = [frontmatter({"type": "call", "date": day, **front}), f"# Call with {name} ({day})\n"]
        body += [f"## {heading}\n{text.strip() or '_None._'}\n" for heading, text in sections]
        path.write_text("\n".join(body))
        return path

    def review(self, action_id: str, purpose: str, summary: str, messages: list[dict[str, Any]],
               day: str = "") -> Path:
        """Every message in a batch, in full, numbered for `approve <id> except 4, 17`."""
        day = day or self._now().date().isoformat()
        path = self.root / "Reviews" / f"{day} {_slug(purpose)} ({action_id}).md"
        lines = [frontmatter({"type": "review", "date": day, "action_id": action_id, "messages": len(messages)}),
                 f"# Review: {purpose}\n", f"{summary}\n",
                 f"Approve all with `approve {action_id}`, or hold some back with "
                 f"`approve {action_id} except 4, 17` (the numbers below).\n"]
        for i, m in enumerate(messages, 1):
            meta = [m.get("channel", ""), m.get("kind", ""), m.get("delivery", "")]
            if m.get("segments"):
                meta.append(f"{m['segments']} segment{'s' if m['segments'] != 1 else ''}")
            if m.get("variant"):
                meta.append(f"variant {m['variant']}")
            who = self.partner_link(m.get("name", ""), m["contact_id"]) if m.get("name") else m["contact_id"]
            lines.append(f"### {i}. {who}\n_{' · '.join(x for x in meta if x)}_\n")
            ctx = m.get("context") or {}
            if ctx:  # what the approver has to see to judge a reply: their words, ours, and how we read them
                said = ctx.get("their_last") or {}
                if said:
                    lines.append(f"**They wrote** ({said.get('at') or 'date unknown'}):\n> "
                                 + (said.get("text") or "(no text)").replace("\n", "\n> ") + "\n")
                ours = ctx.get("our_last") or {}
                if ours:
                    lines.append(f"**Our last message** ({ours.get('at', '')}):\n> "
                                 + ours.get("text", "").replace("\n", "\n> ") + "\n")
                read = f"**Read as:** {ctx.get('intent') or '—'}"
                if ctx.get("move"):
                    read += f" · **Planned move:** {ctx['move']}"
                lines.append(read + "\n")
                for flag in ctx.get("flags", []):
                    lines.append(f"⚠️ {flag}\n")
                lines.append("**Draft:**\n")
            if m.get("subject"):
                lines.append(f"**Subject:** {m['subject']}\n")
            lines.append("> " + m.get("body", "").replace("\n", "\n> ") + "\n")
        path.write_text("\n".join(lines))
        self.log("Review file", f"[[Reviews/{path.stem}]] — {len(messages)} messages", day=day)
        return path

    # ── daily log and campaigns ──────────────────────────────────────────────
    def daily_path(self, day: str = "") -> Path:
        day = day or self._now().date().isoformat()
        return self.root / "Daily" / f"{day}.md"

    def log(self, title: str, body: str = "", day: str = "") -> Path:
        path = self.daily_path(day)
        if not path.exists():
            path.write_text(
                f"---\ntype: daily\ndate: {path.stem}\n---\n# {path.stem} — Funding Affiliate Manager\n\n"
            )
        stamp = self._now().strftime("%H:%M")
        with path.open("a") as handle:
            handle.write(f"\n### {stamp} — {title}\n")
            if body.strip():
                handle.write(body.rstrip() + "\n")
        return path

    def campaign(self, title: str, body: str, kind: str = "campaign", day: str = "") -> Path:
        day = day or self._now().date().isoformat()
        folder = {"newsletter": "Newsletters", "event": "Events", "report": "Reports"}.get(kind, "Campaigns")
        path = self.root / folder / f"{day} {_slug(title)}.md"
        path.write_text(f"---\ntype: {kind}\ndate: {day}\n---\n# {title}\n\n{body.rstrip()}\n")
        self.log(f"{kind.title()} saved", f"[[{folder}/{path.stem}]]", day=day)
        return path
