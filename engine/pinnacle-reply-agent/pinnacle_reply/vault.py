"""The Reply Agent's Obsidian vault: every lead and every word of its conversation, where Justin can open it.

    Home.md                          the counts, and a link to every hub
    Leads/<who: need> (<id6>).md     one note per lead: state, links, what they need, the reply to post,
                                     the whole conversation (## Timeline) and ## Your notes, which code never touches
    Lanes/ Platforms/ Campaigns/ States/   hub notes, so Obsidian's graph links each lead to its lane, platform,
                                     campaign and state
    Ledgers/Reply ledger <day>.md    the daily ledger (cycle.py)

The ledger is the source: notes are regenerated from it, and the Timeline from its append-only `messages`, so a note
can always be rebuilt. A note is rewritten only when its text changed, so git sees real changes only. Their words are
quoted as data, without emails or phone numbers (ledger.scrub), and the SQLite ledger never goes into the vault.

publish() pulls first (so edits made in Obsidian come in), writes, commits, and pushes when the vault has a remote.
A pull that can't be applied is aborted and the agent's commit goes to a side branch: never conflict markers.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, lanes, ledger

PLATFORMS = {"facebook": "Facebook", "tiktok": "TikTok", "reddit": "Reddit", "skool": "Skool", "instagram": "Instagram",
             "linkedin": "LinkedIn", "youtube": "YouTube", "forum": "Forums", "web": "Web"}
STATE_NAMES = {"unattended": "Unattended", "waiting": "Waiting", "held": "Held", "skipped": "Skipped",
               "replied": "Replied", "answered": "Answered", "partner": "With a partner"}
KIND_LINE = {"post": "Their post", "answer": "They wrote back", "reply": "Reply posted", "draft": "Reply drafted",
             "held": "Held", "skipped": "Skipped", "partner": "Funding partner"}
YOURS = "## Your notes"
GITIGNORE = ".obsidian/workspace.json\n.obsidian/workspace-mobile.json\n.trash/\n.DS_Store\n"


def _safe(name: str, limit: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]\n\r\t]+', " ", name)
    name = " ".join(name.split()).strip(" .")
    return (name[:limit].rsplit(" ", 1)[0] if len(name) > limit else name) or "lead"


def _id6(lead_id: str) -> str:
    return hashlib.sha1(lead_id.encode()).hexdigest()[:6]


def stem(row: dict[str, Any]) -> str:
    """The lead note's file name, without .md: 'Jane D.: hard money for a flip (a1b2c3)'."""
    return f"{_safe(title(row))} ({_id6(row['id'])})"


def obsidian_link(row: dict[str, Any]) -> str:
    """Opens the lead's note in Justin's Obsidian (the vault named config.VAULT_NAME on his Mac)."""
    from urllib.parse import quote
    return f"obsidian://open?vault={quote(config.VAULT_NAME, safe='')}&file={quote('Leads/' + stem(row), safe='')}"


def platform_name(p: str | None) -> str:
    return PLATFORMS.get((p or "").lower(), (p or "Unknown").title())


def title(row: dict[str, Any]) -> str:
    """Who and what: 'Jane D.: hard money for a flip in Tampa', or 'Facebook asker: …' when there's no author."""
    who = (row.get("author") or "").strip()
    if not who or who.isdigit():  # Facebook gives some authors only as a numeric profile id
        who = f"{platform_name(row.get('platform'))} asker"
    need = " ".join((row.get("need") or "").split())
    if len(need) > 60:
        need = need[:60].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return f"{who}: {need}" if need else who


def lane_name(pid: str | None) -> str:
    p = lanes.persona(pid)
    return _safe(f"{pid} {p.get('lane') or ''}" if pid else "No lane", 60)


def _quote(text: str, indent: str = "  ") -> list[str]:
    text = ledger.scrub(text).replace("[[", "[ [").replace("]]", "] ]")  # their words never become graph links
    return [f"{indent}> {line}" if line.strip() else f"{indent}>" for line in (text or "(empty)").splitlines()]


def _stamp(at: str | None) -> str:
    try:
        t = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
        t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return t.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return str(at or "")[:16]


def _front(row: dict[str, Any], last: str) -> list[str]:
    def q(v: Any) -> str:
        return '"' + str(v if v is not None else "").replace("\\", "\\\\").replace('"', '\\"') + '"'
    tags = ["lead", f"lane/{(row.get('persona') or 'none').lower()}", f"platform/{(row.get('platform') or 'unknown').lower()}",
            f"state/{row['state']}"]
    out = ["---", "type: lead", f"lead_id: {q(row['id'])}", f"source: {row.get('source') or 'lead-radar'}",
           f"platform: {row.get('platform') or ''}", f"kind: {row.get('kind') or ''}", f"tier: {row.get('tier') or ''}",
           f"campaign: {q(row.get('campaign'))}", f"lane: {row.get('persona') or ''}", f"poster: {q(row.get('poster'))}",
           f"state: {row['state']}", f"reason: {q(row.get('reason'))}", f"url: {q(row.get('url'))}",
           f"posted_at: {q(row.get('posted_at'))}", f"first_seen: {q(row.get('first_seen'))}", f"last_event: {q(last)}"]
    if row.get("ghl_contact_id"):
        out.append(f"ghl_contact_id: {q(row['ghl_contact_id'])}")
    return out + [f"tags: [{', '.join(tags)}]", "---", ""]


def lead_note(row: dict[str, Any], msgs: list[dict[str, Any]], yours: str = "") -> str:
    platform, state = platform_name(row.get("platform")), STATE_NAMES.get(row["state"], row["state"])
    lane, camp = lane_name(row.get("persona")), _safe(row.get("campaign") or "no campaign", 60)
    lines = _front(row, msgs[-1]["at"] if msgs else row.get("first_seen") or "")
    lines += [f"# {title(row)}", "",
              f"**State:** [[States/{state}|{state}]] · {row.get('reason') or ''}",
              f"**Lane:** [[Lanes/{lane}|{lane}]] · **Platform:** [[Platforms/{platform}|{platform}]] · "
              f"**Campaign:** [[Campaigns/{camp}|{camp}]] · **Tier:** {row.get('tier') or '?'}",
              f"**Poster:** {row.get('poster') or 'nobody'} · **In GHL:** "
              + (f"contact `{row['ghl_contact_id']}`" if row.get("ghl_contact_id") else "not yet"), ""]
    if row.get("url"):
        lines += [f"[Open the post]({row['url']})", ""]
    lines += ["## What they need", "", ledger.scrub(row.get("need")) or "(Lead Radar gave no summary)", ""]
    draft = row.get("draft") if row["state"] in ("waiting", "answered") and row.get("draft") else ""
    if draft or (row["state"] == "waiting" and row.get("radar_draft")):
        lines += ["## Reply to post", "", *_quote(draft or row["radar_draft"], ""), ""]
    lines += ["## Timeline", ""]
    for m in msgs:
        head = f"- {_stamp(m['at'])} · **{KIND_LINE.get(m['kind'], m['kind'])}**"
        if m["kind"] in ("post", "answer") and m.get("by") and not m["by"].isdigit():
            head += f" ({m['by']})"
        elif m["kind"] == "reply":
            head += f" by {m.get('by') or 'someone'}" + (f" · [where]({m['url']})" if m.get("url") else "")
        elif m["kind"] == "draft" and m.get("by"):
            head += f" for {m['by']}"
        if m["kind"] in ("held", "skipped", "partner"):
            lines.append(f"{head}: {ledger.scrub(m['text'])}")
        else:
            lines += [head + ":", *_quote(m["text"])]
    if not msgs:
        lines.append("- Nothing yet.")
    lines += ["", YOURS, "", yours.strip() or "_Anything you write here stays: the agent never changes this section._", ""]
    return "\n".join(lines)


def _yours(text: str) -> str:
    return text.split(f"\n{YOURS}\n", 1)[1] if f"\n{YOURS}\n" in text else ""


def _write(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _hub(kind: str, name: str, rows: list[dict[str, Any]], files: dict[str, str], about: str = "") -> str:
    by_state: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_state[r["state"]].append(r)
    lines = ["---", f"type: hub", f"hub: {kind}", "---", "", f"# {name}", ""]
    if about:
        lines += [about, ""]
    lines += [f"{len(rows)} leads: " + ", ".join(f"{STATE_NAMES.get(s, s).lower()} {len(v)}" for s, v in
                                                 sorted(by_state.items(), key=lambda x: list(STATE_NAMES).index(x[0])
                                                        if x[0] in STATE_NAMES else 9)), ""]
    for s in STATE_NAMES:
        if by_state.get(s):
            lines += [f"## {STATE_NAMES[s]}", ""]
            for r in sorted(by_state[s], key=lambda r: r.get("posted_at") or "", reverse=True):
                lines.append(f"- [[Leads/{files[r['id']]}|{title(r)}]]")
            lines.append("")
    return "\n".join(lines)


def write(conn: sqlite3.Connection, root: Path | None = None) -> dict[str, Any]:
    """Regenerate the vault from the ledger. Returns how many notes changed."""
    root = root or config.VAULT_DIR
    if root is None:
        return {"vault": None, "why": "REPLY_VAULT is off"}
    (root / "Leads").mkdir(parents=True, exist_ok=True)
    _write(root / ".gitignore", GITIGNORE)
    rows = [dict(r) for r in conn.execute("SELECT * FROM leads ORDER BY first_seen")]
    existing = {p.stem.rsplit("(", 1)[-1].rstrip(")"): p for p in (root / "Leads").glob("*.md")}
    files, changed = {}, 0
    for r in rows:
        name = stem(r)
        files[r["id"]] = name
        path, old = root / "Leads" / f"{name}.md", existing.get(_id6(r["id"]))
        yours = ""
        if old is not None:
            yours = _yours(old.read_text(encoding="utf-8"))
            if old != path:
                old.rename(path)  # the summary changed: same note, new name, never a duplicate
        changed += _write(path, lead_note(r, ledger.messages(conn, r["id"]), yours))
    hubs = 0
    groups = {
        "Lanes": defaultdict(list), "Platforms": defaultdict(list), "Campaigns": defaultdict(list), "States": defaultdict(list)}
    for r in rows:
        groups["Lanes"][lane_name(r.get("persona"))].append(r)
        groups["Platforms"][platform_name(r.get("platform"))].append(r)
        groups["Campaigns"][_safe(r.get("campaign") or "no campaign", 60)].append(r)
        groups["States"][STATE_NAMES.get(r["state"], r["state"])].append(r)
    for kind, named in groups.items():
        for name, rs in named.items():
            about = ""
            if kind == "Lanes":
                pid = rs[0].get("persona")
                p = lanes.persona(pid)
                about = f"Persona {p.get('name')} ({pid}): {p.get('lane')}." if p else ""
            hubs += _write(root / kind / f"{name}.md", _hub(kind[:-1].lower(), name, rs, files, about))
    rep = ledger.report(conn)
    home = ["# Pinnacle Reply Agent", "",
            "Every lead the Reply Agent attends, and every word of its conversation. Written by the agent from its "
            "ledger; open a lead to see its Timeline, and write in its **Your notes** section.", "",
            f"**Unattended: {rep['unattended']}** of {rep['found']} · waiting {rep['waiting']} · held {rep['held']} · "
            f"skipped {rep['skipped']} · replied {rep['replied']} · answered {rep['answered']}", ""]
    for kind, named in groups.items():
        home += [f"## {kind}", "", *[f"- [[{kind}/{n}|{n}]] ({len(v)})" for n, v in sorted(named.items())], ""]
    ledgers = sorted((root / "Ledgers").glob("Reply ledger *.md")) if (root / "Ledgers").exists() else []
    if ledgers:
        home += ["## Daily ledgers", "", *[f"- [[Ledgers/{p.stem}|{p.stem}]]" for p in ledgers[-14:][::-1]], ""]
    hubs += _write(root / "Home.md", "\n".join(home))
    return {"vault": str(root), "leads": len(rows), "lead_notes_changed": changed, "hubs_changed": hubs}


# --------------------------------------------------------------------------------------------------- git
def _git(root: Path, *args: str, timeout: int = 90) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=timeout, env=env)


def _init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        _git(root, "init", "-q", "-b", "main")
    if not _git(root, "config", "user.email").stdout.strip():
        _git(root, "config", "user.name", "Pinnacle Reply Agent")
        _git(root, "config", "user.email", "reply-agent@pinnacle-funding.local")


def _remote(root: Path) -> str:
    return _git(root, "remote", "get-url", "origin").stdout.strip()


def pull(root: Path | None = None) -> dict[str, Any]:
    root = root or config.VAULT_DIR
    if root is None or not shutil.which("git"):
        return {"pulled": False, "why": "no vault" if root is None else "git isn't installed"}
    _init(root)
    if not _remote(root):
        return {"pulled": False, "why": "no remote yet"}
    if _git(root, "ls-remote", "--exit-code", "--heads", "origin", "main").returncode != 0:
        return {"pulled": False, "why": "the remote has no main yet"}
    got = _git(root, "pull", "-q", "--rebase", "--autostash", "origin", "main")
    if got.returncode != 0:
        _git(root, "rebase", "--abort")
        return {"pulled": False, "why": f"pull failed, aborted: {got.stderr.strip()[:200]}"}
    return {"pulled": True}


def commit_push(root: Path | None = None, message: str = "") -> dict[str, Any]:
    root = root or config.VAULT_DIR
    if root is None or not shutil.which("git"):
        return {"committed": False, "why": "no vault" if root is None else "git isn't installed"}
    _init(root)
    _git(root, "add", "-A")
    if _git(root, "diff", "--cached", "--quiet").returncode == 0:
        out: dict[str, Any] = {"committed": False, "why": "nothing changed"}
    else:
        msg = message or f"Reply Agent: ledger {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
        made = _git(root, "commit", "-q", "-m", msg)
        out = {"committed": made.returncode == 0, **({} if made.returncode == 0 else {"why": made.stderr.strip()[:200]})}
    if not _remote(root):
        return {**out, "pushed": False, "push_why": "no remote yet: the vault is on this computer only"}
    pushed = _git(root, "push", "-q", "origin", "HEAD:main")
    if pushed.returncode == 0:
        return {**out, "pushed": True}
    side = f"agent/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    _git(root, "push", "-q", "origin", f"HEAD:refs/heads/{side}")
    return {**out, "pushed": False, "push_why": f"main moved on: pushed to {side} instead ({pushed.stderr.strip()[:120]})"}


def publish(conn: sqlite3.Connection, root: Path | None = None) -> dict[str, Any]:
    """Pull, regenerate, commit, push. Never raises: a vault problem is reported, it doesn't stop a cycle."""
    root = root or config.VAULT_DIR
    if root is None:
        return {"vault": None, "why": "REPLY_VAULT is off"}
    try:
        got = pull(root)
        wrote = write(conn, root)
        return {**wrote, "pull": got, **commit_push(root)}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"vault": str(root), "error": f"{type(exc).__name__}: {exc}"}
