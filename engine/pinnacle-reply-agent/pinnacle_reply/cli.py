"""`reply-agent`: the Reply Agent's tools from a shell. Output is JSON (the ledger note is Markdown).

    reply-agent status
    reply-agent cycle [--max-drafts N] [--dry-run]     # one loop; desk writes only while REPLY_WRITE=on
    reply-agent ledger [--markdown] | queue [--state unattended] [--persona P1] | chase | personas
    reply-agent loops [--markdown]                     # the 6 pm loop-close audit: every open loop, how old
    reply-agent audit                                  # every draft on Lead Radar's desk against the checker
    reply-agent check "reply text" | -
    reply-agent draft LEAD_ID [--guidance "..."] [--write]
    reply-agent assign LEAD_ID POSTER | hold LEAD_ID "reason" | skip LEAD_ID "reason" [--write]
    reply-agent mark LEAD_ID POSTER [--won] [--note "..."] [--text "what was posted"] [--url URL] [--write]
    reply-agent answered LEAD_ID "what they wrote" | conversation LEAD_ID
    reply-agent ghl [status|prepare|send] [--limit N] [--only LEAD_ID]   # send needs REPLY_GHL=on
    reply-agent vault                                  # write every lead into the Obsidian vault, commit, push
    reply-agent lanes                                  # read every lane now and count it (the ledger isn't touched)
    reply-agent hub [--send]                           # the hub check-offs and booked calls; --send needs REPLY_HUB=on
    reply-agent post [--dry-run] [--limit N]           # post checked drafts in their threads; needs REPLY_POST=on
    reply-agent post-status                            # the posting switches, accounts, today's caps, queue, last posts
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import checks, config, cycle, ledger, loops, ops, poster, radar


def _print(value: Any) -> None:
    print(value if isinstance(value, str) else json.dumps(value, indent=1, default=str))


def status() -> dict[str, Any]:
    try:
        import anthropic  # noqa: F401
        sdk = True
    except ImportError:
        sdk = False
    return {"radar": radar.health(), "write_to_desk": config.WRITE, "model": config.MODEL, "anthropic_sdk": sdk,
            "anthropic_key": bool(config._env("ANTHROPIC_API_KEY")), "ledger": str(config.LEDGER_DB),
            "lanes": str(config.LANES_FILE), "vault": str(config.VAULT_DIR) if config.VAULT_DIR else None,
            "max_drafts_per_cycle": config.MAX_DRAFTS,
            "posting": {"on": config.POST, "platforms": sorted(config.POST_PLATFORMS), "follow": config.FOLLOW,
                        "reddit": bool(config.REDDIT_REFRESH_TOKEN), "youtube": bool(config.YOUTUBE_REFRESH_TOKEN)},
            "ghl": {"on": config.GHL, "token": bool(config.GHL_TOKEN), "location": config.GHL_LOCATION or None,
                    "from_state": config.GHL_FROM, "record": config.GHL_RECORD},
            "lane_reads": {"only": sorted(config.LANES_ON) or "every lane",
                      "creators_db": bool(config.CREATORS_DB_URL),
                      "hub": {"url": config.HUB_URL or None, "password": bool(config.HUB_PASSWORD), "report": config.HUB},
                      "funding_machine": {"location": config.FM_GHL_LOCATION, "calendars": config.FM_CALENDARS,
                                          "token": bool(config.FM_GHL_TOKEN) or config.FM_ENV_FILE.exists()}}}


def audit() -> dict[str, Any]:
    """Check every draft already on the desk. Counts and rule names only: no lead text leaves this function."""
    items = radar.queue_all(status="drafted").get("items") or []
    g3, full, by_writer = Counter(), Counter(), Counter()
    failing_g3 = failing_full = 0
    for it in items:
        text = (it.get("reply") or {}).get("draft") or ""
        by_writer[(it.get("reply") or {}).get("by") or "?"] += 1
        a, b = checks.g3_violations(text), checks.violations(text)
        failing_g3 += bool(a)
        failing_full += bool(b)
        g3.update(a)
        full.update(b)
    return {"drafts": len(items), "written_by": dict(by_writer), "fail_g3": failing_g3, "g3_rules_broken": dict(g3),
            "fail_persona_rules": failing_full, "all_rules_broken": dict(full)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="reply-agent", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    c = sub.add_parser("cycle")
    c.add_argument("--max-drafts", type=int, default=None)
    c.add_argument("--dry-run", action="store_true", help="never write to the desk, even with REPLY_WRITE on")
    sub.add_parser("ledger").add_argument("--markdown", action="store_true")
    q = sub.add_parser("queue")
    q.add_argument("--state", default="unattended")
    q.add_argument("--persona", default="")
    q.add_argument("--poster", default="")
    q.add_argument("--limit", type=int, default=50)
    sub.add_parser("chase")
    sub.add_parser("loops").add_argument("--markdown", action="store_true")
    sub.add_parser("personas")
    sub.add_parser("audit")
    ck = sub.add_parser("check")
    ck.add_argument("text")
    ck.add_argument("--kind", choices=["first", "follow_up"], default="first")
    d = sub.add_parser("draft")
    d.add_argument("lead_id")
    d.add_argument("--guidance", default="")
    d.add_argument("--write", action="store_true")
    a = sub.add_parser("assign")
    a.add_argument("lead_id")
    a.add_argument("poster")
    h = sub.add_parser("hold")
    h.add_argument("lead_id")
    h.add_argument("reason")
    s = sub.add_parser("skip")
    s.add_argument("lead_id")
    s.add_argument("reason")
    s.add_argument("--write", action="store_true")
    m = sub.add_parser("mark")
    m.add_argument("lead_id")
    m.add_argument("poster")
    m.add_argument("--won", action="store_true")
    m.add_argument("--note", default="")
    m.add_argument("--text", default="", help="what was posted, when it isn't the draft")
    m.add_argument("--url", default="", help="where it was posted")
    m.add_argument("--write", action="store_true")
    an = sub.add_parser("answered")
    an.add_argument("lead_id")
    an.add_argument("answer")
    sub.add_parser("conversation").add_argument("lead_id")
    g = sub.add_parser("ghl")
    g.add_argument("action", nargs="?", default="status", choices=["status", "prepare", "send"])
    g.add_argument("--limit", type=int, default=None, help="leads to send (1 for a canary)")
    g.add_argument("--only", default="", help="send only this lead")
    sub.add_parser("vault")
    sub.add_parser("lanes")
    sub.add_parser("hub").add_argument("--send", action="store_true", help="post what changed (needs REPLY_HUB=on)")
    po = sub.add_parser("post")
    po.add_argument("--dry-run", action="store_true", help="say what would go; post nothing")
    po.add_argument("--limit", type=int, default=None, help="posts at most (1 for a canary)")
    sub.add_parser("post-status")
    args = p.parse_args(argv)
    try:
        _print(dispatch(args))
    except (ValueError, KeyError, radar.RadarError, RuntimeError) as exc:
        _print({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return 1
    return 0


def dispatch(a: argparse.Namespace) -> Any:
    if a.cmd == "status":
        return status()
    if a.cmd == "cycle":
        return cycle.run(a.max_drafts, a.dry_run)
    if a.cmd == "loops":
        out = loops.run()
        return loops.markdown(out) if a.markdown else out
    if a.cmd == "ledger":
        rep = ops.report()
        return ledger.markdown(rep, datetime.now(timezone.utc).date().isoformat()) if a.markdown else rep
    if a.cmd == "queue":
        return ops.queue(a.state, a.persona, a.poster, a.limit)
    if a.cmd == "chase":
        return ops.chase()
    if a.cmd == "personas":
        return ops.personas()
    if a.cmd == "audit":
        return audit()
    if a.cmd == "check":
        return ops.check(sys.stdin.read() if a.text == "-" else a.text, a.kind)
    if a.cmd == "draft":
        return ops.draft_one(a.lead_id, a.guidance, dry_run=not a.write)
    if a.cmd == "assign":
        return ops.assign(a.lead_id, a.poster)
    if a.cmd == "hold":
        return ops.hold(a.lead_id, a.reason)
    if a.cmd == "skip":
        return ops.skip(a.lead_id, a.reason, dry_run=not a.write)
    if a.cmd == "mark":
        return ops.mark(a.lead_id, a.poster, "won" if a.won else "replied", a.note, dry_run=not a.write,
                        text=a.text, url=a.url)
    if a.cmd == "answered":
        return ops.answered(a.lead_id, a.answer)
    if a.cmd == "conversation":
        return ops.conversation(a.lead_id)
    if a.cmd == "ghl":
        return ops.crm(a.action, a.limit, a.only)
    if a.cmd == "vault":
        return ops.memory()
    if a.cmd == "lanes":
        return ops.lanes_now()
    if a.cmd == "hub":
        return ops.checklist(a.send)
    if a.cmd == "post":
        return poster.run_now(a.dry_run, a.limit)
    if a.cmd == "post-status":
        return poster.status()
    raise ValueError(f"unknown command {a.cmd}")


if __name__ == "__main__":
    sys.exit(main())
