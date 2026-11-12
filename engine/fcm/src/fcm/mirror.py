"""Show each lead's Obsidian note inside GoHighLevel, as one pinned note on the contact card.

    fcm ghl mirror                          # dry run: how many cards would get a new or changed note
    fcm ghl mirror --contact <id> --apply   # one card first, to see how it reads in GoHighLevel
    fcm ghl mirror --apply                  # every partner; re-runs only touch notes whose text changed

The vault stays the memory. GoHighLevel gets a read-only copy titled "Context card (Obsidian)": the profile,
what they want, how they work, open loops, the revenue plan, calls, the manager's notes and the latest timeline.
The frontmatter, the fact ledger's source markers and wiki-link syntax are left out. Edits belong in Obsidian (the
Manager notes section); the next mirror overwrites the GoHighLevel copy.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

TITLE = "Context card (Obsidian)"
HEADER = "🧠 CONTEXT CARD, from Obsidian"
MAX_CHARS = 9000
TIMELINE_LINES = 200  # MAX_CHARS is the real limit: the oldest lines go first
SKIP_SECTIONS = {"Facts"}  # the same facts already appear, readable, under the sections above them

_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_COMMENT = re.compile(r"\s*%%.*?%%", re.S)
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_ITALIC = re.compile(r"(?<![\w])_([^_\n]+)_(?![\w])")
_DAY_TWICE = re.compile(r"^- (\d{4}-\d\d-\d\d) \1 ")  # "- 2026-10-07 [[Daily/2026-10-07]] —" once unlinked


def _plain_link(m: re.Match[str]) -> str:
    return m.group(2) or m.group(1).rsplit("/", 1)[-1]


def render(note: str, note_path: str) -> str:
    """The note as GoHighLevel shows it: plain text, sections kept, plumbing removed."""
    text = _COMMENT.sub("", _FRONTMATTER.sub("", note, count=1))
    text = _ITALIC.sub(r"\1", _LINK.sub(_plain_link, text))
    out: list[str] = [HEADER, f"Source: {note_path} (edit in Obsidian; this copy is replaced on every sync)", ""]
    section, timeline = "", []
    for line in text.splitlines():
        if line.startswith("# "):
            continue  # the name is already the card's title
        if line.startswith("## "):
            section = line[3:].strip()
            if section not in SKIP_SECTIONS and section != "Timeline":
                while out and not out[-1].strip():
                    out.pop()
                out += ["", section.upper()]
            continue
        if section in SKIP_SECTIONS:
            continue
        line = line.replace("**", "").replace("- [ ] ", "☐ ").replace("- [x] ", "☑ ")
        if section == "Timeline":
            if line.strip():
                timeline.append(_DAY_TWICE.sub(r"- \1 ", line))
            continue
        if line.strip() or (out and out[-1].strip()):
            out.append(line)
    if timeline:
        while out and not out[-1].strip():
            out.pop()
        keep = timeline[-TIMELINE_LINES:]
        while len(keep) > 1 and len("\n".join(out + keep)) > MAX_CHARS - 60:
            keep.pop(0)
        out += ["", f"TIMELINE (latest {len(keep)} of {len(timeline)})"] + keep
    body = "\n".join(out).strip() + "\n"
    if len(body) > MAX_CHARS:
        body = body[: MAX_CHARS - 40].rsplit("\n", 1)[0] + "\n… (the full note is in Obsidian)\n"
    return body


def _partners(settings: Any) -> list[tuple[str, str]]:
    db = settings.state_dir / "fcm.sqlite3"
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    try:
        return [(r[0], r[1]) for r in conn.execute(
            "SELECT contact_id, note_path FROM partners WHERE note_path != '' ORDER BY name")]
    finally:
        conn.close()


def _existing(ghl: Any, contact_id: str) -> dict[str, Any] | None:
    for n in ghl.list_notes(contact_id):
        if n.get("title") == TITLE or str(n.get("body", "")).startswith(HEADER):
            return n
    return None


def mirror(settings: Any, ghl: Any, *, apply: bool = False, limit: int = 0, contact_id: str = "",
           log: Callable[[str], None] = lambda _l: None) -> dict[str, Any]:
    partners = _partners(settings)
    if contact_id:
        partners = [p for p in partners if p[0] == contact_id]
    if limit:
        partners = partners[:limit]
    report = {"apply": apply, "partners": len(partners), "created": 0, "updated": 0, "unchanged": 0,
              "missing_note": 0, "failed": 0}
    for cid, rel in partners:
        path = Path(settings.vault_dir) / rel
        if not path.exists():
            report["missing_note"] += 1
            continue
        body = render(path.read_text(), rel)
        try:
            old = _existing(ghl, cid)
            if old and old.get("body") == body:
                report["unchanged"] += 1
                continue
            report["updated" if old else "created"] += 1
            if apply:
                if old:
                    ghl.update_note(cid, old["id"], body, title=TITLE, pinned=True)
                else:
                    ghl.add_note(cid, body, title=TITLE, pinned=True)
                log(f"{'updated' if old else 'created'} {rel}")
        except Exception as exc:  # one card failing never stops the rest
            report["failed"] += 1
            log(f"failed {rel}: {exc}")
    return report


def mirror_one(settings: Any, ghl: Any, contact_id: str, note_path: str) -> None:
    """After the agent writes a partner's note: refresh that card's copy. Never raises (triage must not stop)."""
    try:
        path = Path(settings.vault_dir) / note_path
        if not note_path or not path.exists():
            return
        body = render(path.read_text(), note_path)
        old = _existing(ghl, contact_id)
        if old is None:
            ghl.add_note(contact_id, body, title=TITLE, pinned=True)
        elif old.get("body") != body:
            ghl.update_note(contact_id, old["id"], body, title=TITLE, pinned=True)
    except Exception:  # noqa: BLE001 - the copy in GoHighLevel is a convenience; the vault is the record
        return
