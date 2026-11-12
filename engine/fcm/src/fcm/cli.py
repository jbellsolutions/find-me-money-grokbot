"""`fcm` — command line for the operator, cron and the agent's no-model jobs.

  Leads and handoffs (the job this agent exists for)
    fcm leads sync [--apply] [--limit N] [--contact ID]   every lead's context card, Obsidian note and GHL copy
    fcm leads card ID [--apply]                           one lead
    fcm handoffs propose [--apply] [--limit N]            send qualified leads to the hub's handoff ledger
    fcm handoffs intro HANDOFF [--apply]                  the intro to both sides (held by the send switch)
    fcm handoffs watch [--apply]                          the 7-day clock: nudges, check-ins, re-pairing
    fcm handoffs status                                   open handoffs and what each one is waiting on
    fcm sales triage [--apply] [--limit N]                sort new campaign replies; drafts stay held
    fcm sales stage CONTACT STAGE --pipeline P --why W [--apply]    move a lead forward
    fcm sales drafts                                      what's waiting for a person
    fcm sales social [--limit N]                          the social queue
    fcm sales suppress-sync                               tell the sender who said stop (held until the switch)
    fcm day [--apply]                                     run the whole day and list every open loop
    fcm collections run|drafts [--apply]                  what's overdue, and held drafts to each partner
    fcm craigslist route [--apply]                        Craigslist posters into the home CRM (held by HUB_CL_TO_CRM)
    fcm partners sync [--apply]                           one Obsidian note per backend partner, with a scorecard

  Engine
    fcm status | sweep [--apply] | queue | brief ID | inbox [--ids] | scorecard | actions [--state S]
    fcm execute ACTION | cancel ACTION --reason R | outbox [status|finish|resume] [--action ID]
    fcm cadence run-standing | stop "reason"
    fcm profile ID | graph query|stats|reindex
    fcm calls ingest [--ghl] [--file F --contact ID]
    fcm ghl bootstrap|discover|mirror|enrich [--apply] [--limit N] [--contact ID]
    fcm gate serve|can-send | dashboard list|show|render|classify | daily-report [--day D] [--publish] [--text]

  Approving a batch, settling an unknown send and lifting a stop are human decisions. There is deliberately no command
  for them here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import cadence
from .config import Settings
from .engine import FcmEngine
from .errors import FcmError


def _print(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def _write_report(settings: Settings, title: str, body: str) -> Path:
    """Discovery reports stay on the agent's computer, in the vault's Reports/ folder (never in the repo)."""
    folder = settings.vault_dir / "Reports"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{title}.md"
    path.write_text(body)
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fcm", description="Funding CRM Manager")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sp = sub.add_parser("sweep")
    sp.add_argument("--apply", action="store_true", help="apply lifecycle tag/stage changes")
    sub.add_parser("queue")
    sp = sub.add_parser("brief")
    sp.add_argument("contact_id")
    sp = sub.add_parser("inbox")
    sp.add_argument("--ids", action="store_true", help="only the ids of untriaged texts (the cron monitor)")
    sub.add_parser("scorecard")
    sp = sub.add_parser("actions")
    sp.add_argument("--state", default="")
    sp = sub.add_parser("cancel")
    sp.add_argument("action_id")
    sp.add_argument("--reason", required=True)
    sp = sub.add_parser("outbox")
    sp.add_argument("what", nargs="?", choices=["status", "finish", "resume"], default="status")
    sp.add_argument("--action", default="")
    sp = sub.add_parser("profile")
    sp.add_argument("contact_id")
    sp = sub.add_parser("graph")
    sp.add_argument("what", choices=["query", "stats", "reindex"])
    sp.add_argument("--tier", default="")
    sp.add_argument("--niche", default="")
    sp.add_argument("--slot", default="")
    sp.add_argument("--contains", default="")
    sp.add_argument("--hub", default="")
    sp.add_argument("--min", type=int, default=0)
    sp.add_argument("--limit", type=int, default=50)
    sp = sub.add_parser("calls")
    sp.add_argument("what", choices=["ingest"])
    sp.add_argument("--ghl", action="store_true", help="GoHighLevel phone calls instead of the call inbox")
    sp.add_argument("--file", default="")
    sp.add_argument("--contact", default="")
    sp = sub.add_parser("execute")
    sp.add_argument("action_id")
    sp = sub.add_parser("cadence")
    sp.add_argument("what", choices=["run-standing"])
    sp = sub.add_parser("stop")
    sp.add_argument("reason")
    sp = sub.add_parser("ghl")
    sp.add_argument("what", choices=["bootstrap", "discover", "mirror", "enrich"])
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--limit", type=int, default=0)
    sp.add_argument("--contact", default="", help="mirror, enrich: one contact id")
    sp = sub.add_parser("gate", help="the send gate (runs OFF the agent's computer; see fcm.gate)")
    sp.add_argument("what", choices=["serve", "can-send"])
    sp.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")))
    sp = sub.add_parser("daily-report", help="what went out, who replied, handoffs, follow-ups")
    sp.add_argument("--day", default="", help="YYYY-MM-DD (default today)")
    sp.add_argument("--publish", action="store_true", help="also write it to Obsidian")
    sp.add_argument("--text", action="store_true", help="print only the Slack text")
    sp = sub.add_parser("dashboard", help="what the API token can't do: the agent's dashboard workflows")
    sp.add_argument("what", choices=["list", "show", "render", "classify"])
    sp.add_argument("task", nargs="?", default="")
    sp.add_argument("--status", type=int, default=0)
    sp.add_argument("--message", default="")
    sp.add_argument("--path", default="")
    sp.add_argument("--method", default="")
    sp.add_argument("--intent", default="")
    sp = sub.add_parser("leads", help="every lead's context card, Obsidian note and GHL copy")
    sp.add_argument("what", choices=["sync", "card"])
    sp.add_argument("contact_id", nargs="?", default="")
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--limit", type=int, default=0)
    sp.add_argument("--contact", default="")
    sp = sub.add_parser("day", help="run the whole day and list every open loop")
    sp.add_argument("--apply", action="store_true")
    sp = sub.add_parser("collections", help="overdue money and held drafts")
    sp.add_argument("what", choices=["run", "drafts"])
    sp.add_argument("--apply", action="store_true")
    sp = sub.add_parser("craigslist", help="Craigslist posters into the home CRM")
    sp.add_argument("what", choices=["route"])
    sp.add_argument("--apply", action="store_true")
    sp = sub.add_parser("sales", help="campaign replies, stage moves, drafts and the social queue")
    sp.add_argument("what", choices=["triage", "stage", "drafts", "social", "suppress-sync"])
    sp.add_argument("contact_id", nargs="?", default="")
    sp.add_argument("stage", nargs="?", default="")
    sp.add_argument("--pipeline", default="Lead Radar Leads")
    sp.add_argument("--why", default="")
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--limit", type=int, default=50)
    sp = sub.add_parser("handoffs", help="pairing, the intro and the 7-day clock")
    sp.add_argument("what", choices=["propose", "intro", "watch", "status"])
    sp.add_argument("handoff_id", nargs="?", default="")
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--limit", type=int, default=0)
    sp = sub.add_parser("partners", help="one Obsidian note per backend partner")
    sp.add_argument("what", choices=["sync"])
    sp.add_argument("--apply", action="store_true")
    args = p.parse_args(argv)

    try:
        settings = Settings.load()
        if args.cmd == "gate":
            from .gate import serve, token_can_send
            if args.what == "can-send":
                from .ghl import LiveGHL
                print(token_can_send(LiveGHL()))
                return 0
            serve(args.port)
            return 0
        if args.cmd == "dashboard":
            from . import dashboard
            registry = dashboard.load(settings.config_dir)
            if args.what == "list":
                _print({tid: {"title": t["title"], "approval": t["approval"], "human_only": bool(t.get("human_only"))}
                        for tid, t in registry["tasks"].items()})
            elif args.what == "show":
                _print(dashboard.task_text(registry, args.task))
            elif args.what == "render":
                print(dashboard.render_markdown(registry), end="")
            else:
                _print(dashboard.classify(registry, status=args.status, message=args.message, path=args.path,
                                          method=args.method, intent=args.intent,
                                          locked=dashboard.guard(dict(os.environ))))
            return 0
        if args.cmd == "ghl":
            from .ghl import open_backend
            if args.what == "discover":
                from . import ghl_discover
                report = ghl_discover.discover(open_backend(settings), settings)
                path = _write_report(settings, f"GoHighLevel discovery {report['generated_at'][:10]}",
                                     ghl_discover.render(report))
                _print({"report": str(path), "fields_missing": report["custom_fields"]["agent_fields_missing"],
                        "workflows": report["workflows"]["agent_workflows"],
                        "might_also_message_partners": report["workflows"]["might_also_message_partners"]})
                return 0
            if args.what == "mirror":
                from .mirror import mirror
                _print(mirror(settings, open_backend(settings), apply=args.apply, limit=args.limit,
                              contact_id=args.contact, log=lambda line: print(line, file=sys.stderr)))
                return 0
            if args.what == "enrich":
                from .enrich import enrich
                _print(enrich(FcmEngine(settings=settings, backend=open_backend(settings)), apply=args.apply,
                              limit=args.limit, contact_id=args.contact, log=lambda line: print(line, file=sys.stderr)))
                return 0
            from .bootstrap import bootstrap
            _print(bootstrap(settings, dry_run=not args.apply))
            return 0
        engine = FcmEngine(settings=settings)
        if args.cmd == "leads":
            from . import leads
            if args.what == "card":
                _print(leads.card_one(engine, args.contact_id or args.contact, apply=args.apply))
            else:
                _print(leads.sync(engine, apply=args.apply, limit=args.limit, contact_id=args.contact,
                                  log=lambda line: print(line, file=sys.stderr)))
            return 0
        if args.cmd == "day":
            from . import loops
            _print(loops.daily(engine, apply=args.apply))
            return
        if args.cmd == "collections":
            from . import collections_agent
            _print(collections_agent.run(engine, apply=args.apply) if args.what == "run" else {"drafts": collections_agent.drafts(engine)})
            return
        if args.cmd == "craigslist":
            from .hubapi import Hub
            _print(Hub().craigslist(apply=args.apply))
            return
        if args.cmd == "sales":
            from . import sales, social
            if args.what == "triage":
                _print(sales.triage_inbox(engine, apply=args.apply, limit=args.limit))
            elif args.what == "stage":
                _print(sales.move_stage(engine, args.contact_id, args.pipeline, args.stage, args.why, apply=args.apply))
            elif args.what == "drafts":
                _print({"drafts": sales.book(engine).drafts("held")})
            elif args.what == "social":
                _print({"counts": social.queue(engine).counts(), "waiting": social.queue(engine).waiting(args.limit)})
            else:
                _print(sales.sync_suppressions(engine))
            return
        if args.cmd == "handoffs":
            from . import handoffs
            if args.what == "propose":
                _print(handoffs.propose_qualified(engine, apply=args.apply, limit=args.limit))
            elif args.what == "intro":
                _print(handoffs.intro(engine, args.handoff_id, apply=args.apply))
            elif args.what == "watch":
                _print(handoffs.watch(engine, apply=args.apply))
            else:
                _print(handoffs.status(engine))
            return 0
        if args.cmd == "partners":
            from . import handoffs
            _print(handoffs.partner_notes(engine, apply=args.apply))
            return 0
        if args.cmd == "status":
            _print(engine.status())
        elif args.cmd == "sweep":
            _print(engine.sweep(apply_lifecycle=args.apply))
        elif args.cmd == "queue":
            _print(engine.daily_queue())
        elif args.cmd == "brief":
            _print(engine.affiliate_brief(args.contact_id))
        elif args.cmd == "inbox":
            if args.ids:  # stable output for the cron monitor: same pending texts, same bytes
                page = engine.reply_inbox_page(limit=10**6)
                ids = sorted(i for r in page["rows"] for i in r["message_ids"])
                if ids:  # the hour makes texts a failed triage run left behind wake the agent again, hourly
                    print("\n".join(ids + [f"retry {engine.now():%Y-%m-%dT%H}"]))
            else:
                _print(engine.reply_inbox_page())
        elif args.cmd == "scorecard":
            _print(engine.scorecard())
        elif args.cmd == "daily-report":
            r = engine.daily_report(args.day, publish=args.publish)
            print(r["slack_text"]) if args.text else _print(r)
        elif args.cmd == "actions":
            _print([engine._action_view(r) for r in engine.store.list_actions(args.state)])
        elif args.cmd == "cancel":
            _print(engine.cancel_action(args.action_id, args.reason))
        elif args.cmd == "outbox":
            if args.what == "resume":  # cron, no model: finish approved batches as recipients' windows open
                engine.heartbeat()  # proves the scheduler is alive; `fcm status` reports when it goes stale
                result = engine.resume_paused()
                if result["resumed"]:  # silent when nothing happened, so the cron job only speaks up when it sent
                    _print(result)
            else:
                _print(engine.finish_bookkeeping() if args.what == "finish" else engine.outbox_status(args.action))
        elif args.cmd == "profile":
            _print(engine.profile_get(args.contact_id))
        elif args.cmd == "graph":
            if args.what == "stats":
                _print(engine.graph.stats())
            elif args.what == "reindex":
                _print(engine.graph.reindex())
            else:
                _print(engine.graph.query(tier=args.tier, niche=args.niche, slot=args.slot, contains=args.contains,
                                          hub=args.hub, min_completeness=args.min, limit=args.limit))
        elif args.cmd == "calls":
            from . import calls
            if args.file:
                _print(calls.ingest(engine, calls.parse_file(Path(args.file).expanduser()), contact_id=args.contact))
            elif args.ghl:
                _print(calls.poll_ghl(engine, contact_id=args.contact))
            else:
                _print(calls.poll_drop(engine))
        elif args.cmd == "execute":
            _print(engine.execute(args.action_id))
        elif args.cmd == "cadence":
            _print(engine.run_standing_cadence())
        elif args.cmd == "stop":
            _print(engine.emergency_stop(args.reason))
        return 0
    except FcmError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
