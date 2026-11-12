"""The Funding Affiliate Manager operating core.

Three kinds of work, three levels of trust:

  READ            sweep, briefs, queues, reply inbox, scorecard       — always allowed
  CRM HYGIENE     lifecycle tags, notes, follow-up tasks, date fields — autonomous, audited, capped
  OUTBOUND        messages, workflow enrollments, broadcasts          — frozen, digested, approved once

Outbound follows the funding-director pattern: prepare (freeze + digest) ->
request approval (card for the manager) -> approve (ONLY via the untrusted
approvals MCP, so Hermes asks the human) -> execute (consumes the approval once).
Recurring bulk cadence can run under a bounded, expiring standing approval.

Demo mode (FCM_DEMO_MODE=1, the default): only contacts tagged `fcm:test-contact`
receive real messages or enrollments. Everyone else is a simulated send, written to the
contact as a GHL note so the demo shows exactly what would have gone out.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from dataclasses import replace
from datetime import UTC, date, datetime, time as dtime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from . import cadence, drafting, extract, timezones
from .cadence import KICKOFF_DONE, KICKOFF_PENDING, KICKOFF_SENT, Affiliate, affiliate_from_contact
from .config import Settings
from .errors import FcmError, GHLError
from .gate import client_from_env
from .ghl import GHLBackend, iso_time, open_backend
from .graph import SOURCE_NAMES, Graph
from .store import Store, digest, now_iso, stable_json
from .vault import Vault

BANNED_PHRASES = (
    "guarantee",
    "100% approval",
    "no credit check",
    "instant approval",
    "risk-free",
    "risk free",
    "get rich",
    "can't lose",
    "cannot lose",
)
# Partner messages go out in the named manager's voice: never about AI, and never a claim about who is typing.
VOICE_LINT = (re.compile(r"\bAI\b"),
              re.compile(r"artificial intelligence|chat ?bot|\bbots?\b|language model|automated (?:message|text|"
                         r"reply|system)|virtual assistant|ai assistant|drafted (?:by|with)|not a (?:bot|robot)|"
                         r"(?:i'?m|i am) (?:a )?(?:real )?(?:person|human)\b", re.I))
REPLY_PERSONALLY_TAG = "fcm:reply-personally"
TAKEOVER_WINDOW = timedelta(minutes=15)  # a person's message this recent means they're in the conversation right now
# A reply that isn't a no is a hot lead: the manager hears about it.
# "Later" is good but not hot; a no, an opt-out, HELP and a wrong number are not leads.
NOT_HOT_INTENTS = {"check_back_later", "not_interested", "unsubscribe", "help", "wrong_number"}
# Replies the manager leads (program_tags.manager). The agent answers every other reply itself.
MANAGER_INTENTS = {"has_deal", "will_send_deals", "book_call", "question", "commission_question", "identity_question",
                   "wants_service"}
DEAL_INTENTS = {"has_deal", "will_send_deals"}  # "might have a deal": the Potential Deal stage (program_tags.potential_deal)
# While a partner has a lead the agent stays quiet, except for the intro and the two scheduled check-ins (spec 36).
PARTNER_WINDOW_KINDS = {"handoff_intro", "handoff_checkin"}
SIM_PARTNER_TAG = "fcm:sim-partner"  # a simulated partner in the live demo (fcm.demo); never a real person
KICKOFF_KINDS = {"kickoff", "kickoff_nudge"}
EMAIL_OPT_OUT_LINE = "Reply UNSUBSCRIBE and we'll stop emailing you."
REVIEW_THREAD_MAX = 12_000  # characters of review posted into Slack; bigger batches are read in the vault
# Where a batch can be sent from: approved once, then resumable (paused by quiet hours or the stop switch, or a
# run that died mid-way) until its approval expires. Only messages still "pending" in the outbox ever go out.
SENDABLE_STATES = ("approved", "paused", "executing", "needs_reconcile")
SERVICES = {"funnel", "reactivation", "email_campaigns", "social", "crm_help"}
MANAGER_TASK_PREFIXES = ("CALL ", "Answer ", "Scope ", "Reply personally")  # human work; a sent touch never closes these
MANAGER_TASK_MARK = "[For the manager]"
SERVICE_LABELS = {"funnel": "a funnel page", "reactivation": "lead reactivation", "email_campaigns": "email campaigns",
                  "social": "social content", "crm_help": "CRM help"}
BULK_WORKFLOW_KEYS = {"onboarding", "biweekly_touch", "monthly_offer", "dormant_reactivation",
                      "dead_reactivation", "newsletter", "event_invite", "new_offer"}
STANDING_ALLOWED = {"onboarding", "biweekly_touch", "monthly_offer", "dormant_reactivation", "dead_reactivation"}
OFFER_KINDS = {"monthly_offer", "new_offer"}
LIFECYCLE_STAGE = {
    "aff:applied": "applied",
    "aff:onboarding": "onboarded",
    "aff:active": "active",
    "aff:producing": "producing",
    "aff:quiet": "quiet",
    "aff:dormant": "dormant",
    "aff:dead": "dormant",
    "aff:reactivated": "reactivated",
}


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _no_mentions(text: str) -> str:
    """Partner text posted to Slack can't ping anyone: no <!channel>, @here, <@U…>."""
    text = re.sub(r"<[!@#][^>]*>", "[mention]", str(text or ""))
    return re.sub(r"@(?=(?:here|channel|everyone)\b)", "@\u200b", text, flags=re.I)


def _slack_safe(text: str) -> str:
    """...and inside the card it can't restyle it either: no markup characters."""
    return re.sub(r"[*_~`>]", "", _no_mentions(text)).replace("<", "‹").replace(">", "›")


def _chunks(text: str, size: int) -> list[str]:
    """Split on blank lines into pieces under `size` characters (one Slack message each)."""
    out, cur = [], ""
    for block in text.split("\n\n"):
        if cur and len(cur) + len(block) + 2 > size:
            out.append(cur)
            cur = ""
        cur = (cur + "\n\n" + block) if cur else block
        while len(cur) > size:
            out.append(cur[:size])
            cur = cur[size:]
    return out + ([cur] if cur else [])


class FcmEngine:
    def __init__(self, settings: Settings | None = None, backend: GHLBackend | None = None,
                 today: date | None = None):
        self.settings = settings or Settings.load()
        self.ghl = backend or open_backend(self.settings)
        self.store = Store(self.settings.state_dir / "fcm.sqlite3")
        self.tz = ZoneInfo(self.settings.cadence["timezone"])
        self.vault = Vault(self.settings.vault_dir, self.settings.cadence["timezone"])
        kick = self.settings.kickoff
        self.graph = Graph(self.store, self.vault, self.settings.profile_schema,
                           default_manager=str(kick.get("default_sender", "")),
                           generic_managers=kick.get("generic_manager_names", []))
        self._today = today
        self.clock: Any = None  # tests set a callable returning an aware datetime
        self.actor = os.getenv("FCM_ACTOR", "funding-crm-manager")
        self._extractor: Any = None

    def _track(self, what: str, fn: Any) -> None:
        """A project-board write. This agent has no board: GHL and the vault are the record."""

    def _attribution_tag(self, what: str) -> str:
        prefix = str(self.settings.kickoff.get("attribution_tag_prefix", "")).strip()
        return f"{prefix}:{what}" if prefix else ""

    def _card_link(self, contact_id: str) -> str:
        loc = os.getenv("GHL_LOCATION_ID", "") or str(self.settings.ghl_map.get("location_id", ""))
        return f"https://app.gohighlevel.com/v2/location/{loc}/contacts/detail/{contact_id}" if loc else contact_id

    def _track_reply(self, aff: Affiliate, intent: str, text: str, taken: list[str], alert: str) -> None:
        from .report import COMPLIANCE, NEEDS_PERSON
        today = self.today().isoformat()
        about = (f"**{aff.name}** replied ({intent}) on {today}:\n\n> {text[:600]}\n\n"
                 f"What the agent did: {'; '.join(taken) or 'logged'}\n\nGHL: {self._card_link(aff.id)}\n"
                 f"Obsidian: Partners/{aff.name} ({aff.id[:6]})")

        def write(tr: Any) -> None:
            came_back = any("aff:reactivated" in x for x in taken)
            known = tr.find("reactivated", aff.id)
            if came_back or known:  # one task per partner who came back; every later reply is a comment
                tr.upsert("reactivated", aff.id, aff.name, "" if known else about,
                          tags=["reactivated"] if came_back else None, comment=f"{today} ({intent}): {text[:500]}")
            if intent in NEEDS_PERSON:
                tr.upsert("followups", f"{aff.id}:{intent}:{today}", f"{aff.name}: {NEEDS_PERSON[intent]}",
                          about + (f"\n\n{alert}" if alert else ""), tags=[intent.replace("_", "-")])
            if intent in COMPLIANCE:
                tr.upsert("compliance", f"{aff.id}:{intent}:{today}", f"{aff.name}: {COMPLIANCE[intent]}", about,
                          tags=[intent.replace("_", "-")])
        self._track(f"reply:{aff.id}", write)

    @property
    def extractor(self) -> Any:
        """Facts from replies and calls: the model when FCM_DRAFT_MODEL is set, keyword rules otherwise."""
        if self._extractor is None:
            self._extractor = extract.open_extractor(list(self.graph.slots))
        return self._extractor

    @extractor.setter
    def extractor(self, value: Any) -> None:
        self._extractor = value

    # ── clock ────────────────────────────────────────────────────────────────
    def today(self) -> date:
        return self._today or datetime.now(self.tz).date()

    def now(self) -> datetime:
        """The send clock. With a pinned day (tests, simulations) sends happen at 14:00 Eastern that day."""
        if self.clock:
            return self.clock()
        if self._today:
            return datetime.combine(self._today, dtime(18, 0), tzinfo=UTC)
        return datetime.now(UTC)

    # ── status ───────────────────────────────────────────────────────────────
    HEARTBEAT_STALE_MINUTES = 30  # the resume job beats every 20 minutes

    def heartbeat(self) -> None:
        (self.settings.state_dir / "heartbeat").write_text(datetime.now(UTC).isoformat(timespec="seconds"))

    def scheduler_state(self) -> dict[str, Any]:
        """Whether the scheduled jobs are actually running, from the heartbeat the resume job writes."""
        path = self.settings.state_dir / "heartbeat"
        if not path.exists():
            return {"ok": None, "detail": "no heartbeat yet (the 20-minute resume job hasn't run)"}
        try:
            beat = datetime.fromisoformat(path.read_text().strip())
        except ValueError:
            return {"ok": False, "detail": "unreadable heartbeat"}
        minutes = int((datetime.now(UTC) - beat).total_seconds() // 60)
        ok = minutes <= self.HEARTBEAT_STALE_MINUTES
        return {"ok": ok, "last_beat": beat.isoformat(), "minutes_ago": minutes,
                "detail": "running" if ok else "scheduler down: no routine has run for "
                f"{minutes} minutes (check the gateway: `hermes cron status`)"}

    def status(self) -> dict[str, Any]:
        s = self.settings
        result: dict[str, Any] = {
            "handoff_sends": "on" if os.getenv("FCM_SEND_HANDOFFS") == "1" else "held",
            "ghl_mode": s.ghl_mode,
            "crm": s.crm,
            "channel": s.channel,
            "demo_mode": s.demo_mode,
            "ghl_profile": s.profile or "(unset)",
            "configured_location_id": s.ghl_map.get("location_id", ""),
            "custom_fields_mapped": len(s.field_ids()),
            "workflows_mapped": sorted(k for k, v in s.ghl_map.get("workflows", {}).items() if v),
            "external_writes_enabled": self.store.get_flag("external_writes_enabled", "true") == "true",
            "stop_reason": self.store.get_flag("stop_reason", ""),
            "today": self.today().isoformat(),
            "sent_today": {
                "personal_messages": self.store.count(self.today().isoformat(), "personal_messages"),
                "enrollments": self.store.count(self.today().isoformat(), "enrollments"),
            },
            "pending_approvals": len(self.store.list_actions("approval_requested")),
            "paused_batches": len(self.store.list_actions("paused")),
            "sends_to_settle": len(self.store.outbox(states=("unknown",))),
            "standing_approvals": [r for r in self.store.list_standing() if not r["revoked_at"]],
            "vault": str(s.vault_dir),
            "scheduler": self.scheduler_state(),
        }
        try:
            location = self.ghl.location()
            result["ghl_connected"] = True
            result["ghl_location_name"] = location.get("name", "")
        except FcmError as exc:
            result["ghl_connected"] = False
            result["ghl_error"] = str(exc)
        return result

    # ── reads ────────────────────────────────────────────────────────────────
    def affiliates(self, tags: list[str] | None = None, query: str = "", limit: int = 20000) -> list[Affiliate]:
        """The program's partners only: with a cohort tag configured, a contact without it is never returned
        (a sub-account can hold far more contacts than the program's own)."""
        field_ids = self.settings.field_ids()
        cohort = self.settings.cohort_tag
        if cohort and cohort not in (tags or []):
            tags = [cohort, *(tags or [])]
        if cohort and not query.strip() and hasattr(self.ghl, "all_contacts"):
            return [affiliate_from_contact(c, field_ids) for c in self.ghl.all_contacts(tags=tags)][:limit]
        out: list[Affiliate] = []
        page = 1
        while len(out) < limit:
            batch = self.ghl.search_contacts(query=query, tags=tags, limit=min(500, limit - len(out)), page=page)
            out.extend(affiliate_from_contact(c, field_ids) for c in batch)
            if len(batch) < 500:
                break
            page += 1
        return out

    def affiliate(self, contact_id: str) -> Affiliate:
        return affiliate_from_contact(self.ghl.get_contact(contact_id), self.settings.field_ids())

    def in_cohort(self, aff: Affiliate) -> bool:
        """One of the program's partners (or no cohort configured). Everyone else in the sub-account is off-limits."""
        cohort = self.settings.cohort_tag
        return not cohort or cohort in aff.tags

    def sweep(self, apply_lifecycle: bool = False, detail_limit: int = 25) -> dict[str, Any]:
        affiliates = self.affiliates()
        plan = cadence.sweep(affiliates, self.today(), self.settings.cadence)
        applied = 0
        if apply_lifecycle:
            by_id = {a.id: a for a in affiliates}
            for change in plan["lifecycle_changes"]:
                self._apply_lifecycle(by_id[change["contact_id"]], change["to"], "daily sweep")
                applied += 1
        plan["lifecycle_applied"] = applied
        self.vault.log(
            "Daily sweep",
            f"- affiliates: {plan['total_affiliates']}\n- cohorts: {plan['cohorts']}\n"
            f"- silent 30+: {plan['silent_30_plus']} · silent 90+: {plan['silent_90_plus']}\n"
            f"- personal touches due: {len(plan['personal_queue'])} (+{plan['personal_overflow']} overflow)\n"
            f"- bulk due: {plan['bulk_counts']}\n- lifecycle changes applied: {applied}",
            day=self.today().isoformat(),
        )
        self.store.audit(actor=self.actor, action="sweep", resource=self.today().isoformat(),
                         decision="read", result="ok",
                         details={"cohorts": plan["cohorts"], "applied": applied})
        if detail_limit >= 0:
            plan["personal_queue"] = plan["personal_queue"][:detail_limit]
            plan["bulk_queue"] = {k: v[:detail_limit] for k, v in plan["bulk_queue"].items()}
        return plan

    def affiliate_brief(self, contact_id: str) -> dict[str, Any]:
        aff = self.affiliate(contact_id)
        ev = cadence.evaluate(aff, self.today(), self.settings.cadence)
        notes = self.ghl.list_notes(contact_id)[-10:]
        tasks = [t for t in self.ghl.list_tasks(contact_id) if not t.get("completed")]
        messages: list[dict[str, Any]] = []
        for conv in self.ghl.list_conversations(contact_id=contact_id, limit=3):
            for m in self.ghl.list_messages(conv["id"], limit=10):
                messages.append({"direction": m.get("direction"), "type": m.get("messageType"),
                                 "date": m.get("dateAdded"), "body": (m.get("body") or "")[:500]})
        messages.sort(key=lambda m: m.get("date") or "", reverse=True)
        return {
            "affiliate": aff.summary(),
            "email": aff.email,
            "phone": aff.phone,
            "tags": aff.tags,
            "fields": aff.fields,
            "days_silent": ev.days_silent,
            "days_since_touch": ev.days_since_touch,
            "target_lifecycle": ev.target_lifecycle,
            "due_today": [d.to_dict() for d in ev.due],
            "open_tasks": tasks,
            "recent_notes": notes,
            "recent_messages": messages[:10],
            "profile": self.profile_get(contact_id, aff=aff),
            "drafting_rules": f"Use {self.settings.knowledge('05-conversation-playbook.md')} and "
                              "08-kickoff-framework.md. Write as "
                              "the partner's manager (profile.manager), short, warm, peer-to-peer, one question. "
                              "Build on profile.summary and their own words. Never mention AI or drafting. No "
                              "guaranteed approvals, rates, or income claims.",
        }

    def daily_queue(self) -> dict[str, Any]:
        plan = self.sweep(apply_lifecycle=False, detail_limit=-1)
        queue = []
        for item in plan["personal_queue"]:
            open_tasks = [t for t in self.ghl.list_tasks(item["contact_id"]) if not t.get("completed")]
            queue.append({**item, "open_tasks": [{"id": t["id"], "title": t.get("title"),
                                                  "due": t.get("dueDate")} for t in open_tasks]})
        return {"date": plan["date"], "personal_queue": queue, "overflow": plan["personal_overflow"],
                "bulk_counts": plan["bulk_counts"]}

    def reply_inbox(self, limit: int = 25) -> list[dict[str, Any]]:
        return self.reply_inbox_page(limit)["rows"]

    def reply_inbox_page(self, limit: int = 25) -> dict[str, Any]:
        """Every inbound text not yet triaged, oldest first, read or unread. A thread somebody already opened in
        the GoHighLevel app, or one where our next message landed on top of their reply, still gets triaged:
        what counts is whether each inbound message id has been recorded, not GoHighLevel's unread flag."""
        lookback = int(self.settings.cadence.get("inbox_lookback_days", 14))
        since = (self.now() - timedelta(days=lookback)).replace(microsecond=0).isoformat()
        found = []
        for conv in self.ghl.list_recent_conversations(since):
            conv_id = str(conv.get("id", ""))
            last = iso_time(conv.get("lastMessageDate"))
            if conv_id and last and last <= self.store.watermark(conv_id):
                continue  # nothing new in this conversation since every inbound in it was triaged
            thread = self.ghl.list_messages(conv_id, limit=50)
            inbound = [m for m in thread
                       if m.get("direction") == "inbound" and "CALL" not in str(m.get("messageType", "")).upper()
                       and iso_time(m.get("dateAdded")) >= since]
            seen = self.graph.seen([str(m.get("id", "")) for m in inbound])
            fresh = sorted((m for m in inbound if str(m.get("id", "")) not in seen),
                           key=lambda m: iso_time(m.get("dateAdded")))
            if not fresh:
                if conv_id and last:
                    self.store.set_watermark(conv_id, str(conv.get("contactId", "")), last)
                continue
            if self.settings.cohort_tag:
                try:
                    member = self.in_cohort(self.affiliate(str(conv.get("contactId", ""))))
                except FcmError:
                    member = False
                if not member:  # their other contacts' texts stay with their team; never triaged as a partner
                    if conv_id and last:  # and the thread isn't re-read until something new arrives in it
                        self.store.set_watermark(conv_id, str(conv.get("contactId", "")), last)
                    continue
            found.append((conv, fresh, thread))
        found.sort(key=lambda cf: iso_time(cf[1][0].get("dateAdded")))  # the longest-waiting partner first
        rows = []
        for conv, fresh, thread in found[:limit]:
            contact_id = conv.get("contactId", "")
            handling = self._takeover(contact_id, thread)
            parts = []
            for m in fresh:
                body = (m.get("body") or "").strip()
                media = [str(a) for a in (m.get("attachments") or []) if a]
                parts.append(body + "".join(f"\n[attachment] {a}" for a in media) if media else body)
            text = "\n".join(p for p in parts if p)
            try:
                who = self.affiliate(contact_id).summary()
            except FcmError:
                who = {"id": contact_id}
            by_email = all(str(m.get("messageType", "")).upper() == "TYPE_EMAIL" for m in fresh)
            rows.append({"contact": who, "conversation_id": conv.get("id"), "last_message": text[:1200],
                         "manager_handling": handling,  # record it, send nothing: the manager has this conversation
                         "channel": "email" if by_email else "sms",  # answer on the channel they wrote on
                         "subject": next((str(m["subject"]) for m in reversed(fresh) if m.get("subject")), ""),
                         "message_ids": [str(m.get("id")) for m in fresh if m.get("id")],
                         "messages": [{"id": m.get("id"), "date": iso_time(m.get("dateAdded")),
                                       "body": (m.get("body") or "")[:600],
                                       "attachments": [str(a) for a in (m.get("attachments") or []) if a]}
                                      for m in fresh],
                         "received": iso_time(fresh[-1].get("dateAdded")),
                         "baseline": cadence.classify_reply(text)})
        return {"rows": rows, "remaining": max(0, len(found) - limit)}

    # ── the relationship graph ───────────────────────────────────────────────
    def remember(self, aff: Affiliate, **kwargs: Any) -> dict[str, Any]:
        """Write to the graph (vault note + index), then mirror the profile into the partner's GHL fields."""
        out = self.graph.remember(aff, day=self.today().isoformat(), **kwargs)
        self._sync_profile(aff, out["profile"])
        return out

    def _sync_profile(self, aff: Affiliate, p: dict[str, Any]) -> None:
        values = {"profile_summary": p["summary"][:2000], "profile_completeness": p["completeness"],
                  "next_step": p.get("next_step", "")[:250], "obsidian_note": p.get("note_path", "")}
        from . import enrich  # what the agent remembers, as card fields and tags
        values.update(enrich.memory_fields(self.graph, p))
        mapped = self.settings.field_ids()
        values = {k: v for k, v in values.items() if k in mapped and not enrich._same(aff.fields.get(k), v)}
        if values:
            self._set_fields(aff.id, values)
        try:  # a tag that cannot be added never stops the agent writing its profile
            tags = enrich.missing_tags(aff.tags, enrich.memory_tags(self.graph, p))
            if tags:
                self.ghl.add_tags(aff.id, tags)
        except Exception:  # noqa: BLE001
            pass
        if self.store.get_flag("external_writes_enabled", "true") == "true":  # the card's pinned copy of the note; never raises
            from .mirror import mirror_one
            mirror_one(self.settings, self.ghl, aff.id, p.get("note_path", ""))

    def profile_get(self, contact_id: str, aff: Affiliate | None = None) -> dict[str, Any]:
        aff = aff or self.affiliate(contact_id)
        p = self.graph.profile(aff, self.today())
        p["next_step"] = self.graph.next_step(p)
        return p

    def facts_record(self, contact_id: str, facts: list[Any], source_type: str = "manual", source_ref: str = "",
                     close_loops: list[int] | None = None) -> dict[str, Any]:
        """Add what the manager or the agent learned outside a reply or call (a conversation, research)."""
        aff = self.affiliate(contact_id)
        out = self.remember(aff, facts=facts, source_type=source_type or "manual", source_ref=source_ref,
                            close_loops=close_loops or [])
        self.store.audit(actor=self.actor, action="facts.record", resource=contact_id, decision="autonomous",
                         result="ok", details={"added": len(out["facts_added"]), "source": source_type})
        return {"ok": True, "facts_added": out["facts_added"], "completeness": out["profile"]["completeness"],
                "note": out["note"]}

    def pre_call_brief(self, contact_id: str, why: str = "") -> dict[str, Any]:
        """knowledge/program/pre-call-brief.md, filled from the profile, for the manager before a call."""
        aff = self.affiliate(contact_id)
        p = self.profile_get(contact_id, aff=aff)
        v = p["values"]
        said = next((i["summary"] for i in p["history"] if i["kind"] == "reply"), "")
        tasks = [t.get("title", "") for t in self.ghl.list_tasks(contact_id) if not t.get("completed")]
        fits = sorted({x for n in v.get("deal_types", []) for x in drafting.PRODUCTS.get(n, [])})
        lines = [
            f"**Partner:** {p['name']}, {p['niche'] or 'partner'}. Came from {SOURCE_NAMES.get(p['source'], p['source'])}. "
            f"Joined {p['joined'] or 'unknown'}"
            + (f". Tier: {p['tier']}" if p["tier"] else ""),
            f"**Lifecycle:** {p['lifecycle'].removeprefix('aff:') or 'unknown'}. Last reply {p['last_reply'] or 'none'}, last deal "
            f"{p['last_deal'] or 'none'}, deals sent {p['deals']}",
            f"**Who they are:** {p['summary']}",
            f"**What they told us last:** {said.split(') ', 1)[-1] if said else 'nothing yet'}",
            f"**What they want:** {'; '.join(v.get('goals', []) + v.get('needs', [])) or 'ask'}",
            f"**Open loops / tasks:** {'; '.join([l['text'] for l in p['open_loops']] + tasks) or 'none'}",
            f"**Why this call:** {why or 'get to know them and agree a plan'}",
            f"**Recommended outcome:** a first deal or a date for one, and the next check-in on the calendar",
            f"**Programs that fit their clients:** {', '.join(fits[:3]) or 'ask what their clients need'}",
            f"**Ask if it doesn't come up:** {p['next_question']['question'] if p['next_question'] else 'nothing open'}",
            "**Do NOT promise:** approvals, rates, timelines, commission changes, or payout dates",
            "**Recording:** say at the start that the call is recorded so you remember what you talked about",
        ]
        brief = "\n".join(f"- {line}" for line in lines)
        self.vault.log("Pre-call brief", f"- {self.vault.partner_link(aff.name, aff.id)}\n{brief}",
                       day=self.today().isoformat())
        return {"ok": True, "contact_id": contact_id, "brief": brief}

    def write_revenue_plan(self, contact_id: str, plan: str = "", drafter: Any = None) -> dict[str, Any]:
        """Save the partner's revenue plan. Without text, draft it from the profile."""
        aff = self.affiliate(contact_id)
        if not plan.strip():
            p = self.profile_get(contact_id, aff=aff)
            plan = (drafter or drafting.open_drafter(self.settings.kickoff)).revenue_plan(p)
        self._lint(plan)
        out = self.remember(aff, revenue_plan=plan, interaction={"kind": "revenue_plan",
                                                                 "ref": f"{aff.id}:plan:{self.today().isoformat()}",
                                                                 "summary": "revenue plan written"})
        self.vault.log("Revenue plan", f"- {self.vault.partner_link(aff.name, aff.id)}", day=self.today().isoformat())
        return {"ok": True, "plan": plan, "note": out["note"]}

    # ── CRM hygiene (autonomous, audited) ─────────────────────────────────────
    def _set_fields(self, contact_id: str, values: dict[str, Any]) -> None:
        payload = [{"id": self.settings.field_id(k), "field_value": v} for k, v in values.items()]
        self.ghl.update_contact(contact_id, {"customFields": payload})

    def _apply_lifecycle(self, aff: Affiliate, lifecycle: str, reason: str) -> None:
        if lifecycle not in cadence.LIFECYCLE_TAGS:
            raise FcmError(f"unknown lifecycle tag {lifecycle}")
        stale = [t for t in aff.tags if t in cadence.LIFECYCLE_TAGS and t != lifecycle]
        if stale:
            self.ghl.remove_tags(aff.id, stale)
        self.ghl.add_tags(aff.id, [lifecycle])
        self._sync_lifecycle_stage(aff, lifecycle)
        self.vault.affiliate(aff.name, aff.id, f"lifecycle {aff.lifecycle or '—'} → {lifecycle} ({reason})",
                             source=aff.source, lifecycle=lifecycle, day=self.today().isoformat())
        self.graph.render(replace(aff, tags=[t for t in aff.tags if t not in stale] + [lifecycle]),
                          self.today().isoformat())
        self.store.audit(actor=self.actor, action="lifecycle.set", resource=aff.id, decision="autonomous",
                         result="ok", details={"from": aff.lifecycle, "to": lifecycle, "reason": reason})

    def _sync_lifecycle_stage(self, aff: Affiliate, lifecycle: str) -> None:
        try:
            pipeline = self.settings.pipeline("lifecycle")
        except FcmError:
            return  # pipeline not built yet; tags remain the source of truth
        stage_key = LIFECYCLE_STAGE.get(lifecycle, "")
        stage_id = pipeline.get("stages", {}).get(stage_key, "")
        if stage_id:
            self.ghl.upsert_opportunity(pipeline_id=pipeline["id"], stage_id=stage_id, contact_id=aff.id,
                                        name=f"{aff.name} — affiliate")

    def set_lifecycle(self, contact_id: str, lifecycle: str, reason: str) -> dict[str, Any]:
        aff = self.affiliate(contact_id)
        self._apply_lifecycle(aff, lifecycle, reason)
        return {"ok": True, "contact_id": contact_id, "lifecycle": lifecycle}

    def add_note(self, contact_id: str, body: str) -> dict[str, Any]:
        if not body.strip():
            raise FcmError("note body is empty")
        note = self.ghl.add_note(contact_id, body.strip())
        aff = self.affiliate(contact_id)
        self.vault.affiliate(aff.name, aff.id, f"note: {body.strip()[:200]}", day=self.today().isoformat())
        self.store.audit(actor=self.actor, action="note.add", resource=contact_id, decision="autonomous",
                         result="ok", details={"chars": len(body)})
        return {"ok": True, "note_id": note.get("id", "")}

    def schedule_followup(self, contact_id: str, due_date: str, note: str, title: str = "",
                          customer_touch: bool = True) -> dict[str, Any]:
        """A GHL task on the contact. customer_touch=True is a "check back with me" promise: it also sets
        next_touch_date/cadence_note so the agent drafts a touch that morning. False is internal work for
        the human (call, answer, scope) and never feeds an outbound message."""
        due = cadence.parse_day(due_date)
        if not due:
            raise FcmError("due_date must be YYYY-MM-DD")
        if due < self.today():
            raise FcmError("due_date is in the past")
        aff = self.affiliate(contact_id)
        name = title or f"Follow up with {aff.first_name} — {note[:60]}"
        same = next((t for t in self.ghl.list_tasks(contact_id) if not t.get("completed") and t.get("title") == name), None)
        if same:  # one open task per job: each new reply used to open another
            self.ghl.add_note(contact_id, f"Also on the open task \"{name}\": {note}")
            return {"ok": True, "task_id": same.get("id", ""), "due": str(same.get("dueDate", ""))[:10], "existing": True}
        assignee = self.settings.ghl_map.get("users", {}).get("manager", "")
        task = self.ghl.create_task(
            contact_id,
            name,
            datetime.combine(due, datetime.min.time(), self.tz).replace(hour=10).astimezone(UTC).isoformat(),
            body=note if customer_touch else f"{MANAGER_TASK_MARK} {note}",
            assigned_to=assignee,
        )
        if customer_touch:
            self._set_fields(contact_id, {"next_touch_date": due.isoformat(), "cadence_note": note[:250]})
            self.ghl.add_note(contact_id, f"Follow-up scheduled for {due.isoformat()}: {note}")
        else:
            self.ghl.add_note(contact_id, f"Task for the manager, due {due.isoformat()}: {note}")
        self.vault.affiliate(aff.name, aff.id, f"follow-up set for [[Daily/{due.isoformat()}]] — {note}",
                             day=self.today().isoformat())
        self.store.audit(actor=self.actor, action="followup.schedule", resource=contact_id,
                         decision="autonomous", result="ok", details={"due": due.isoformat()})
        return {"ok": True, "task_id": task.get("id", ""), "due": due.isoformat()}

    def complete_task(self, contact_id: str, task_id: str, reason: str) -> dict[str, Any]:
        """Close a task that's done, and say why on the partner's timeline."""
        if not reason.strip():
            raise FcmError("say why the task is done")
        aff = self.affiliate(contact_id)
        task = next((t for t in self.ghl.list_tasks(contact_id) if t.get("id") == task_id), None)
        if not task:
            raise FcmError(f"no task {task_id} on {aff.name}'s card")
        self.ghl.complete_task(contact_id, task_id)
        self.vault.affiliate(aff.name, aff.id, f"task closed: {task.get('title')}. {reason.strip()[:200]}",
                             day=self.today().isoformat())
        self.store.audit(actor=self.actor, action="task.complete", resource=contact_id, decision="autonomous",
                         result="ok", details={"task": task_id, "reason": reason[:200]})
        return {"ok": True, "task_id": task_id}

    def stage_tag(self, contact_id: str, stage: str) -> dict[str, Any]:
        """A call or a deal someone logged by hand: the stage's tag, and stage_sync.py moves the card."""
        if stage not in {"call_booked", "potential_deal"}:
            raise FcmError("stage must be call_booked or potential_deal")
        tag = self.settings.program_tag(stage)
        if not tag:
            raise FcmError(f"no tag set for {stage}")
        aff = self.affiliate(contact_id)
        self.ghl.add_tags(contact_id, [tag])
        self.vault.affiliate(aff.name, aff.id, f"stage: {tag}", day=self.today().isoformat())
        self.store.audit(actor=self.actor, action="stage.tag", resource=contact_id, decision="autonomous",
                         result="ok", details={"tag": tag})
        return {"ok": True, "tag": tag}

    def queue_growth_service(self, contact_id: str, service: str, note: str = "") -> dict[str, Any]:
        if service not in SERVICES:
            raise FcmError(f"service must be one of {sorted(SERVICES)}")
        aff = self.affiliate(contact_id)
        self.ghl.add_tags(contact_id, [f"want:{service.replace('_', '-')}"])
        opp: dict[str, Any] = {}
        try:
            pipeline = self.settings.pipeline("services")
            stage_id = pipeline.get("stages", {}).get("interested", "")
            if stage_id:
                opp = self.ghl.upsert_opportunity(pipeline_id=pipeline["id"], stage_id=stage_id,
                                                  contact_id=contact_id,
                                                  name=f"{aff.name} — {service.replace('_', ' ')}")
        except FcmError:
            pass
        label = SERVICE_LABELS.get(service, service.replace("_", " "))
        self.schedule_followup(contact_id, self.today().isoformat(), f"Scope {label} for {aff.name}. {note}",
                               title=f"Scope {label} for {aff.first_name}", customer_touch=False)
        self.vault.log("Growth service queued", f"- {self.vault.affiliate_link(aff.name, aff.id)} wants **{label}**"
                       f" {('— ' + note) if note else ''}", day=self.today().isoformat())
        return {"ok": True, "service": service, "opportunity_id": opp.get("id", "")}

    def record_reply(self, contact_id: str, text: str, intent: str = "", follow_up_date: str = "",
                     summary: str = "", facts: list[Any] | None = None, service: str = "",
                     message_ids: list[str] | None = None) -> dict[str, Any]:
        """Apply the outcome of one inbound reply to the CRM and the partner's profile. The model passes its
        own intent and facts; the keyword baselines fill in when it doesn't. STOP, HELP and wrong numbers are
        always honored and never count as a reply; "is this a bot?" always goes to the manager."""
        ids = [str(i) for i in (message_ids or []) if i]
        if ids and len(self.graph.seen(ids)) == len(ids):
            return {"ok": True, "duplicate": True, "intent": "", "actions_taken": [], "manager_alert": "",
                    "draft_reply": False}
        aff = self.affiliate(contact_id)
        if not self.in_cohort(aff):  # a lead or client of theirs texting the same number: not ours to triage
            self.graph.mark_seen(ids, contact_id)
            return {"ok": True, "skipped": f"not a program partner (no {self.settings.cohort_tag} tag)",
                    "intent": "", "actions_taken": [], "manager_alert": "", "draft_reply": False}
        baseline = cadence.classify_reply(text)
        if baseline["intent"] in cadence.NO_DRAFT_INTENTS:
            intent = baseline["intent"]
        intent = intent or baseline["intent"]
        today = self.today()
        taken: list[str] = []
        loops: list[dict[str, str]] = []
        extra_facts: list[dict[str, str]] = []
        counts_as_reply = intent not in cadence.NON_REPLY_INTENTS
        engaged = counts_as_reply and intent != "not_interested"
        if counts_as_reply:
            self._set_fields(contact_id, {"last_reply_date": today.isoformat()})
            taken.append("last_reply_date=today")
        alert = ""

        def end_kickoff() -> None:
            nonlocal aff
            kickoff = [t for t in aff.tags if t in (KICKOFF_PENDING, KICKOFF_SENT)]
            if kickoff:  # the conversation has started (or ended): the kickoff track is done with them
                self.ghl.remove_tags(contact_id, kickoff)
                self.ghl.add_tags(contact_id, [KICKOFF_DONE])
                aff = replace(aff, tags=[t for t in aff.tags if t not in kickoff] + [KICKOFF_DONE])
                taken.append("kickoff track closed")

        if intent == "unsubscribe":
            self.ghl.add_tags(contact_id, [cadence.DNC_TAG])
            self.ghl.update_contact(contact_id, {"dnd": True})
            self.ghl.add_note(contact_id, f"Opted out: {text[:200]}")
            taken.append("DNC + dnd set")
            alert = f"{aff.name} opted out. No further outreach."
        elif intent == "help":
            end_kickoff()  # no automated nudge to someone who asked for help; the manager follows up
            self.ghl.add_note(contact_id, f"Texted HELP: {text[:200]}")
            self.schedule_followup(contact_id, today.isoformat(), f"{aff.first_name} texted HELP. The carrier HELP "
                                   "auto-reply covers the required details; check in personally if they need more.",
                                   title=f"Answer {aff.first_name}'s HELP text", customer_touch=False)
            taken.append("HELP: task for the manager, no drafted reply")
            alert = f"{aff.name} texted HELP. Nothing was drafted; a task is on your list."
        elif intent == "wrong_number":
            self.ghl.add_tags(contact_id, [cadence.WRONG_NUMBER_TAG])
            end_kickoff()
            self.ghl.add_note(contact_id, f"Wrong number reported: {text[:200]}")
            self.schedule_followup(contact_id, today.isoformat(), f"Whoever has {aff.first_name}'s number says it's "
                                   "the wrong person. Find the right number; no texts go to this one until then.",
                                   title=f"Fix {aff.first_name}'s phone number", customer_touch=False)
            taken.append("wrong number: texts blocked, task to fix it")
            alert = f"{aff.name}'s number reached the wrong person. Texts to it are blocked until it's fixed."
        else:
            was, _ = cadence.target_lifecycle(aff, today, self.settings.cadence)
            if engaged and (aff.lifecycle in {"aff:quiet", "aff:dormant", "aff:dead"}
                            or was in {"aff:quiet", "aff:dormant", "aff:dead"}):
                self._apply_lifecycle(aff, "aff:reactivated", f"replied: {intent}")
                aff = self.affiliate(contact_id)
                taken.append("lifecycle → aff:reactivated")
            end_kickoff()
            self.ghl.add_note(contact_id, f"Reply ({intent}): {summary or text[:400]}")
            if intent == "identity_question":
                self.ghl.add_tags(contact_id, [REPLY_PERSONALLY_TAG])
                self.schedule_followup(contact_id, today.isoformat(),
                                       f"{aff.first_name} asked who they're texting with: \"{text[:160]}\". Reply to "
                                       "them yourself. The agent won't draft anything to them until this task is done.",
                                       title=f"Reply personally to {aff.first_name}", customer_touch=False)
                taken.append("personal reply task for the manager")
                alert = (f"{aff.name} asked if they're texting with a real person. Please reply to them yourself; "
                         "I won't draft anything to them until your task is done.")
            elif intent == "not_interested":
                self.ghl.add_tags(contact_id, [cadence.NOT_INTERESTED_TAG])
                taken.append("not interested: no more kickoff or reactivation texts")
                alert = f"{aff.name} isn't interested right now: {text[:120]}"
            elif intent == "has_deal":
                self.ghl.add_tags(contact_id, ["deal:incoming"])
                self.schedule_followup(contact_id, today.isoformat(),
                                       f"Has a deal to send — call today. They said: {text[:160]}",
                                       title=f"CALL {aff.first_name} — has a deal", customer_touch=False)
                loops.append({"slot": "open_loop", "value": f"Call about the deal they have ({today.isoformat()})"})
                taken.append("deal:incoming + same-day call task")
                alert = f"🔥 {aff.name} says they have a deal. Same-day call task created."
            elif intent == "book_call":
                when = baseline.get("proposed_time", "")
                self.schedule_followup(contact_id, today.isoformat(),
                                       f"{aff.first_name} wants a call" + (f": {when}" if when else "") +
                                       f". They said: {text[:160]}",
                                       title=f"CALL {aff.first_name}" + (f" — {when}" if when else " — book a time"),
                                       customer_touch=False)
                loops.append({"slot": "open_loop", "value": f"Call {when or 'to be booked'} ({today.isoformat()})"})
                taken.append("call task" + (f" for {when}" if when else ""))
                alert = f"📞 {aff.name} wants to talk" + (f" {when}" if when else "") + "."
            elif intent == "will_send_deals":
                loops.append({"slot": "open_loop", "value": f"{aff.first_name}: plans to send deals; ask for the first one"})
                taken.append("open loop: ask for their first deal")
                alert = f"{aff.name} says they plan to send deals."
            elif intent == "check_back_later":
                # In the GHL campaign, "later" parks them (program_tags.later): W-8b holds them 60 days, then the
                # check-ins resume. A "later" is a request to defer contact, so the manager's task waits as long.
                later_tag, campaign_tag = self.settings.program_tag("later"), self.settings.program_tag("campaign")
                parked = bool(later_tag and campaign_tag and campaign_tag in {t.lower() for t in aff.tags})
                if parked:
                    self.ghl.add_tags(contact_id, [later_tag])
                    taken.append(f"{later_tag}: parked 60 days")
                due = cadence.parse_day(follow_up_date) or today + timedelta(days=60 if parked else 14)
                self.schedule_followup(contact_id, due.isoformat(), summary or f"They asked: {text[:160]}")
                loops.append({"slot": "open_loop", "value": f"Check back on {due.isoformat()}: "
                                                            f"{(summary or text)[:100]}"})
                taken.append(f"follow-up task {due.isoformat()}")
            elif intent == "wants_service":
                chosen = service if service in SERVICES else baseline.get("service", "crm_help")
                self.queue_growth_service(contact_id, chosen, text[:160])
                loops.append({"slot": "open_loop", "value": f"Scope {SERVICE_LABELS.get(chosen, chosen)} for them"})
                taken.append(f"growth service queued: {chosen}")
                alert = f"{aff.name} wants help with {SERVICE_LABELS.get(chosen, 'CRM help')}."
            elif intent in {"commission_question", "question"}:
                self.schedule_followup(contact_id, today.isoformat(), f"Call and answer: {text[:180]}",
                                       title=f"CALL {aff.first_name}: answer their question", customer_touch=False)
                loops.append({"slot": "open_loop", "value": f"Answer their question: {text[:90]}"})
                taken.append("answer task today")
                alert = f"{aff.name} asked: {text[:140]}"
            elif intent == "event_interest":
                self.ghl.add_tags(contact_id, ["want:event"])
                taken.append("want:event")
            if baseline.get("prefers_text"):
                extra_facts.append({"slot": "channel", "value": "text"})
            if baseline.get("empty"):
                alert = alert or f"{aff.name} sent a message with no text (a picture or file?). Open it in GoHighLevel."
        learned: list[Any] = []
        if intent not in cadence.NO_DRAFT_INTENTS:
            learned = list(facts) if facts is not None else self.extractor.extract_text(text)["facts"]
        ref = ids[-1] if ids else digest({"c": contact_id, "t": text, "d": today.isoformat()})
        kind = "reply" if counts_as_reply else "inbound_other"  # STOP/HELP/wrong number never count as a reply
        out = self.remember(aff, facts=learned + extra_facts + loops, source_type="reply", source_ref=ref,
                            interaction={"kind": kind, "ref": ref, "summary": f"({intent}) {text[:260]}"})
        if out["facts_added"]:
            taken.append(f"{len(out['facts_added'])} profile fact(s)")
        self.graph.mark_seen(ids, contact_id)
        mark_read = getattr(self.ghl, "mark_read", None)
        if mark_read:
            try:
                mark_read(contact_id)
            except FcmError:
                pass  # dedupe above already keeps a re-listed reply from being triaged twice
        self.vault.affiliate(aff.name, aff.id, f"replied ({intent}): {text[:160]}", day=today.isoformat())
        self.vault.log("Reply triaged", f"- {self.vault.affiliate_link(aff.name, aff.id)} — **{intent}** — "
                       f"{'; '.join(taken)}", day=today.isoformat())
        if counts_as_reply and (tag := self._attribution_tag("replied")):
            try:
                self.ghl.add_tags(contact_id, [tag])
                taken.append(tag)
            except FcmError:
                pass
        if counts_as_reply and intent not in NOT_HOT_INTENTS and (hot := self.settings.program_tag("hot")):
            try:  # a warm reply: the tag starts the client's "text the manager" workflow
                self.ghl.add_tags(contact_id, [hot])
                taken.append(hot)
            except FcmError:
                pass
        stage_tag = ""
        if counts_as_reply and intent in DEAL_INTENTS:
            stage_tag = self.settings.program_tag("potential_deal")
        elif intent == "book_call" and baseline.get("proposed_time"):  # a time is agreed, so they have a call
            stage_tag = self.settings.program_tag("call_booked")
        if stage_tag:
            try:
                self.ghl.add_tags(contact_id, [stage_tag])
                taken.append(stage_tag)
            except FcmError:
                pass
        if intent in MANAGER_INTENTS and (lead := self.settings.program_tag("manager")):
            try:
                self.ghl.add_tags(contact_id, [lead])
                taken.append(lead)
            except FcmError:
                pass
        self.store.audit(actor=self.actor, action="reply.record", resource=contact_id, decision="autonomous",
                         result="ok", details={"intent": intent, "taken": taken})
        self._track_reply(aff, intent, text, taken, alert)
        return {"ok": True, "intent": intent, "baseline": baseline, "actions_taken": taken, "manager_alert": alert,
                "facts_added": out["facts_added"], "completeness": out["profile"]["completeness"],
                "next_question": out["profile"]["next_question"], "counts_as_reply": counts_as_reply,
                "draft_reply": intent not in cadence.NO_DRAFT_INTENTS and not self._manager_handling(aff)}

    def record_deal(self, contact_id: str, note: str = "") -> dict[str, Any]:
        aff = self.affiliate(contact_id)
        today = self.today().isoformat()
        self._set_fields(contact_id, {"last_deal_date": today, "deals_submitted": aff.deals_submitted + 1})
        self.ghl.remove_tags(contact_id, ["deal:incoming"])
        for task in self.ghl.list_tasks(contact_id):
            if not task.get("completed") and str(task.get("title", "")).startswith("CALL "):
                self.ghl.complete_task(contact_id, task["id"])
        self._apply_lifecycle(aff, "aff:producing", "deal submitted")
        self.ghl.add_note(contact_id, f"Deal submitted {today}. {note}")
        self.graph.close_loops(contact_id, "Call about the deal")
        self.graph.close_loops(contact_id, f"{aff.first_name}: send us")  # the file they promised is the deal
        self.remember(self.affiliate(contact_id), interaction={"kind": "deal", "ref": f"{contact_id}:deal:{today}",
                                                              "summary": f"deal submitted. {note}"[:200]})
        self.vault.log("Deal recorded", f"- {self.vault.affiliate_link(aff.name, aff.id)} submitted a deal. {note}",
                       day=today)
        if tag := self._attribution_tag("deal-submitted"):
            self.ghl.add_tags(contact_id, [tag])
        self.store.audit(actor=self.actor, action="deal.record", resource=contact_id, decision="autonomous",
                         result="ok", details={"note": note[:200]})
        self._track(f"deal:{contact_id}", lambda tr: tr.upsert(
            "reactivated", contact_id, aff.name, f"**{aff.name}**: deal submitted {today}. {note}\n\nGHL: "
            f"{self._card_link(contact_id)}" if not tr.find("reactivated", contact_id) else "",
            tags=["deal-submitted"], comment=f"{today}: deal submitted. {note}"))
        return {"ok": True, "deals_submitted": aff.deals_submitted + 1}

    # ── outbound: prepare ────────────────────────────────────────────────────
    def _lint(self, text: str) -> None:
        lowered = text.lower()
        hits = [p for p in BANNED_PHRASES if p in lowered]
        if hits:
            raise FcmError(f"message contains non-compliant language: {hits} — see "
                           f"{self.settings.knowledge('06-compliance-guardrails.md')}")
        if re.search(r"\b\d{1,2}(\.\d+)?\s?%\s*(apr|interest|rate)", lowered):
            raise FcmError("message states a specific rate; rates only from a sourced program card in the knowledge pack")

    def _lint_voice(self, text: str) -> None:
        """Partner messages never mention AI or drafting and never claim who is typing (identity questions go
        to the manager, who answers personally)."""
        for pattern in VOICE_LINT:
            hit = pattern.search(text)
            if hit:
                raise FcmError(f"partner messages never talk about AI or who is typing (found {hit.group(0)!r}); "
                               "see files/SOUL.md")

    def _manager_handling(self, aff: Affiliate) -> bool:
        """True while the manager has this conversation (program_tags.takeover): the agent still reads and records
        what they say, and sends nothing. Taking the tag off hands it back."""
        tag = self.settings.program_tag("takeover")
        return bool(tag and tag in aff.tags)

    def _person_wrote(self, thread: list[dict[str, Any]], since: str) -> bool:
        """A person on the team sent something in this thread since then (GHL names the user; the agent's sends are
        in the outbox by message id, an email's id in its meta)."""
        rows = [m for m in thread if m.get("direction") == "outbound" and m.get("userId")
                and str(m.get("messageType", "")).upper() in ("TYPE_SMS", "TYPE_EMAIL")
                and iso_time(m.get("dateAdded")) >= since]
        if not rows:
            return False
        with self.store.connection() as conn:
            ours = {r[0] for r in conn.execute("SELECT message_id FROM outbox WHERE message_id != ''")}
        return any(m.get("id") not in ours and not ours.intersection(
            str(e) for e in ((m.get("meta") or {}).get("email") or {}).get("messageIds") or []) for m in rows)

    def _takeover(self, contact_id: str, thread: list[dict[str, Any]], since: str = "") -> bool:
        """True if the manager has this partner. A person who just wrote in the thread takes it over: a partner often
        answers before the send log sees that message."""
        tag = self.settings.program_tag("takeover")
        if not tag or not contact_id:
            return False
        try:
            if self._manager_handling(self.affiliate(contact_id)):
                return True
        except FcmError:
            return False
        since = since or (self.now() - TAKEOVER_WINDOW).replace(microsecond=0).isoformat()
        if not self._person_wrote(thread, since):
            return False
        self.ghl.add_tags(contact_id, [tag])
        return True

    def _personal_reply_pending(self, aff: Affiliate) -> bool:
        """True while the manager still owes this partner a personal answer to "is this a bot?"."""
        if REPLY_PERSONALLY_TAG not in aff.tags:
            return False
        open_task = any(not t.get("completed") and str(t.get("title", "")).startswith("Reply personally")
                        for t in self.ghl.list_tasks(aff.id))
        if not open_task:
            self.ghl.remove_tags(aff.id, [REPLY_PERSONALLY_TAG])
        return open_task

    @staticmethod
    def _family(kind: str) -> str:
        """Batches conflict within a family: two kickoff batches, or two replies, for the same partner. A routine
        check-in batch never blocks answering someone who just wrote (it is skipped at send time instead)."""
        return "kickoff" if kind in KICKOFF_KINDS else "reply" if kind == "reply" else ""

    def _reserve(self, action_id: str, messages: list[dict[str, Any]]) -> None:
        by_family: dict[str, list[str]] = {}
        for m in messages:
            if family := self._family(m.get("kind", "")):
                by_family.setdefault(family, []).append(m["contact_id"])
        for family, ids in by_family.items():
            self.store.reserve(action_id, family, ids)

    def _freeze(self, kind: str, payload: dict[str, Any], recipients: int, summary: str) -> dict[str, Any]:
        payload = {**payload, "location_id": self.ghl.location_id, "prepared_for": self.today().isoformat()}
        payload_hash = digest({"kind": kind, "payload": payload})
        existing = self.store.find_action(kind, payload_hash)
        messages = payload.get("messages", []) if kind == "send_messages" else []
        if existing and existing["state"] not in {"expired", "cancelled"}:
            return self._action_view(existing)
        for family in {self._family(m.get("kind", "")) for m in messages} - {""}:
            ids = [m["contact_id"] for m in messages if self._family(m.get("kind", "")) == family]
            held = self.store.reserved(ids, kinds=(family,), exclude_action=existing["action_id"] if existing else "")
            if held:
                names = {m["contact_id"]: m.get("name", m["contact_id"]) for m in messages}
                raise FcmError("already in another open batch (cancel it or let it expire first): " +
                               ", ".join(f"{names[c]} → {a}" for c, a in sorted(held.items())))
        if existing:  # the same batch again after it expired or was cancelled: reopen it with a fresh clock
            self.store.update_action(existing["action_id"], state="prepared", approval_id="", created_at=now_iso())
            self._reserve(existing["action_id"], messages)
            return self._action_view(self.store.get_action(existing["action_id"]))
        row = {"action_id": _new_id("act"), "kind": kind, "payload_json": stable_json(payload),
               "payload_hash": payload_hash, "recipients": recipients, "state": "prepared",
               "summary": summary, "created_at": now_iso(), "updated_at": now_iso()}
        self.store.insert_action(row)
        self._reserve(row["action_id"], messages)
        self.store.audit(actor=self.actor, action=f"{kind}.prepare", resource=row["action_id"],
                         decision="approval-required", result="prepared",
                         details={"recipients": recipients, "summary": summary})
        return self._action_view(row)

    def _action_view(self, row: dict[str, Any]) -> dict[str, Any]:
        import json as _json
        payload = _json.loads(row["payload_json"])
        view = {k: row[k] for k in ("action_id", "kind", "state", "recipients", "summary", "created_at")}
        view["action_digest"] = row["payload_hash"]
        view["demo_mode"] = self.settings.demo_mode
        if row["kind"] == "send_messages":
            view["preview"] = [{"contact_id": m["contact_id"], "name": m.get("name", ""), "channel": m["channel"],
                                "subject": m.get("subject", ""), "body": " ".join(m["body"].split())[:480],
                                "delivery": m.get("delivery", ""), "segments": m.get("segments", 0),
                                "they_wrote": (m.get("context") or {}).get("their_last", {}).get("text", "")[:300],
                                "flags": (m.get("context") or {}).get("flags", [])}
                               for m in payload["messages"][:8]]
        else:
            view["workflow_key"] = payload.get("workflow_key", "")
            view["sample_contacts"] = payload.get("names", [])[:8]
            if payload.get("custom_values"):
                view["custom_values"] = {k: str(v)[:280] for k, v in payload["custom_values"].items()}
        if row.get("result_json"):
            view["result"] = _json.loads(row["result_json"])
        return view

    def _delivery_mode(self, aff: Affiliate) -> str:
        if SIM_PARTNER_TAG in aff.tags:  # the live demo's simulated crowd: texts go to the simulator, never a phone
            return "mock"
        if self.settings.ghl_mode == "mock" and self.settings.crm == "ghl":
            return "mock" if (not self.settings.demo_mode or aff.is_test_contact) else "simulated"
        if not self.settings.demo_mode or aff.is_test_contact:
            return "live"
        from .ghl import synthetic_demo
        if not synthetic_demo():
            # A real sub-account: a "simulated" send would still use up the partner's one kickoff
            # and write a send that never happened onto their card. Test mode there refuses them instead.
            raise FcmError(f"test mode: on the client's live sub-account only contacts tagged {cadence.TEST_CONTACT_TAG} "
                           f"can be messaged, and {aff.name} isn't one (until launch: FCM_DEMO_MODE=1)")
        return "simulated"

    def kicked_off_ids(self) -> set[str]:
        """Everyone whose kickoff went out (or may have), whatever their tags say: a CRM write that failed after
        the send can leave the tags behind, but the outbox and the history don't forget."""
        return self.store.kickoff_claimed() | self.graph.contacts_with("kickoff_sent")

    def kicked_off(self, aff: Affiliate) -> bool:
        """A partner who has had their kickoff (or may have: an unsettled send) never gets another one."""
        return (bool({KICKOFF_SENT, KICKOFF_DONE} & set(aff.tags)) or bool(self.store.kickoff_claimed([aff.id]))
                or bool(self.graph.interactions(aff.id, ["kickoff_sent"], limit=1)))

    def _email_footer(self, delivery: str) -> str:
        """Commercial email carries the sender's postal address and a working opt-out (CAN-SPAM)."""
        k = self.settings.kickoff
        address = str(k.get("mailing_address") or "").strip()
        from .config import unresolved
        if unresolved(address):
            address = ""  # FMM_MAILING_ADDRESS not set at intake: refuse below
        if not address and delivery == "live":
            raise FcmError("set mailing_address in config/kickoff.json (the company's postal address) before any "
                           "email goes out: commercial email has to carry it")
        return "\n\n--\n" + str(k["company"]) + (f", {address}" if address else "") + "\n" + EMAIL_OPT_OUT_LINE

    def _latest_inbound(self, contact_id: str) -> tuple[str, str] | None:
        """The partner's newest text straight from GoHighLevel (it may not have been triaged yet)."""
        try:
            found = [m for conv in self.ghl.list_conversations(contact_id=contact_id, limit=3)
                     for m in self.ghl.list_messages(conv.get("id", ""), limit=20)
                     if m.get("direction") == "inbound" and "CALL" not in str(m.get("messageType", "")).upper()]
        except FcmError:
            return None
        if not found:
            return None
        newest = max(found, key=lambda m: iso_time(m.get("dateAdded")))
        return (newest.get("body") or "").strip(), iso_time(newest.get("dateAdded"))

    def _reply_context(self, aff: Affiliate, kind: str, body: str, move: str = "") -> dict[str, Any]:
        """What the approver needs next to a reply: what the partner said, what we said last, how it was read,
        and anything about the draft that doesn't fit. Built here, from the record, never from the model."""
        if kind in KICKOFF_KINDS:
            return {}
        history = self.graph.interactions(aff.id, ["reply", "inbound_other", "kickoff_sent", "nudge_sent",
                                                   "message_sent"], limit=12)
        theirs = next((i for i in history if i["kind"] in {"reply", "inbound_other"}), None)
        ours = next((i for i in history if i["kind"] in drafting.OUR_MESSAGES), None)
        their_text, their_at = "", ""
        latest = self._latest_inbound(aff.id) if kind == "reply" else None
        if latest:
            their_text, their_at = latest
        elif theirs:
            their_text, their_at = re.sub(r"^\([a-z_]+\)\s*", "", theirs["summary"]), theirs["at"]
        if not their_text and not ours and not latest:
            return {}
        base = cadence.classify_reply(their_text) if their_text else {"intent": ""}
        return {"their_last": {"at": their_at, "text": their_text[:600]},
                "our_last": {"at": ours["at"], "text": ours["summary"][:400]} if ours else {},
                "intent": base["intent"], "move": move[:40],
                "flags": self._context_flags(their_text, base, ours["summary"] if ours else "", body, latest)}

    def _context_flags(self, their: str, base: dict[str, Any], ours: str, draft: str,
                       latest: tuple[str, str] | None) -> list[str]:
        flags: list[str] = []
        d = draft.lower()
        if latest is not None and not latest[0]:
            flags.append("Their last message has no text (a picture or file?). Open it in GoHighLevel first.")
        if not their:
            return flags
        signals = cadence.reply_signals(their)
        offered = signals["proposed_time"]
        if offered:
            keys = [w for w in re.findall(r"[a-z0-9:]+", offered.lower())
                    if w not in {"at", "this", "next", "after", "before", "around"}]
            link = str(self.settings.kickoff.get("calendar_link") or "")
            if not any(k in d for k in keys) or (link and link.lower() in d):
                flags.append(f"They offered a time (\"{offered}\"); the draft doesn't confirm it.")
        if signals["prefers_text"] and re.search(r"\bcall\b[^?]*\?", d):
            flags.append("They said texting is easier; the draft asks for a call.")
        if base["intent"] in {"book_call", "has_deal", "will_send_deals"} and d.startswith("good question"):
            flags.append(f"Read as {base['intent']}, but the draft answers it like a question.")
        asked_before = [q.strip().lower() for q in re.findall(r"[^.!?]*\?", ours)]
        if any(q and q in d for q in asked_before):
            flags.append("The draft asks the same question as our last message.")
        if ours and draft and " ".join(draft.lower().split()[:3]) == " ".join(ours.lower().split()[:3]):
            flags.append("The draft opens the same way as our last message.")
        return flags

    def prepare_messages(self, messages: list[dict[str, Any]], purpose: str = "personal touches") -> dict[str, Any]:
        """Freeze a batch of individually drafted messages for one manager approval."""
        if not messages:
            raise FcmError("no messages to prepare")
        self.expire_stale()
        kickoff_batch = all(str(m.get("kind", "")) in KICKOFF_KINDS for m in messages)
        cap = int(self.settings.kickoff["batch_max"] if kickoff_batch else self.settings.cadence["batch_approval_max"])
        if len(messages) > cap:
            raise FcmError(f"batch has {len(messages)} messages; max per approval is {cap}")
        frozen = []
        seen = set()
        for m in messages:
            contact_id = str(m.get("contact_id", "")).strip()
            channel = str(m.get("channel", "")).lower()
            body = str(m.get("body", "")).strip()
            kind = str(m.get("kind", "personal_checkin"))
            if not contact_id or contact_id in seen:
                raise FcmError(f"missing or duplicate contact_id: {contact_id!r}")
            seen.add(contact_id)
            if channel not in {"sms", "email"}:
                raise FcmError(f"{contact_id}: channel must be sms or email")
            if not body:
                raise FcmError(f"{contact_id}: empty body")
            self._lint(body + " " + str(m.get("subject", "")))
            self._lint_voice(body + " " + str(m.get("subject", "")))
            aff = self.affiliate(contact_id)
            if not self.in_cohort(aff):
                raise FcmError(f"{aff.name} isn't one of the program's partners (no {self.settings.cohort_tag} tag)")
            if aff.is_dnc:
                raise FcmError(f"{aff.name} is do-not-contact")
            if self._personal_reply_pending(aff):
                raise FcmError(f"{aff.name} asked who they're texting with; the manager replies personally first")
            if self._manager_handling(aff) and kind not in PARTNER_WINDOW_KINDS:
                raise FcmError(f"a partner has the conversation with {aff.name}; only the scheduled check-ins go out")
            if kind == "kickoff" and self.kicked_off(aff):
                raise FcmError(f"{aff.name} already had their kickoff")
            delivery = self._delivery_mode(aff)
            segments = 0
            if channel == "sms":
                if not aff.phone:
                    raise FcmError(f"{aff.name} has no phone for SMS")
                if aff.sms_blocked:
                    raise FcmError(f"{aff.name}'s number was reported wrong; fix it before texting")
                body = cadence.sms_normalize(body)
                if kind != "reply" and drafting.STOP_SUFFIX.strip().lower() not in body.lower():
                    body = body.rstrip() + drafting.STOP_SUFFIX
                if len(body) > 480:
                    raise FcmError(f"{aff.name}: SMS longer than 480 characters")
                segments = cadence.sms_segments(body)["segments"]
                limit = int(self.settings.kickoff["max_segments"])
                if kind in KICKOFF_KINDS and segments > limit:
                    raise FcmError(f"{aff.name}: kickoff texts stay within {limit} SMS segments (this is {segments})")
            if channel == "email":
                if not aff.email:
                    raise FcmError(f"{aff.name} has no email")
                if aff.no_email:
                    raise FcmError(f"{aff.name} opted out of email")
                if EMAIL_OPT_OUT_LINE not in body:
                    body = body.rstrip() + self._email_footer(delivery)
            context = self._reply_context(aff, kind, body, str(m.get("move", "")))
            frozen.append({"contact_id": contact_id, "name": aff.name, "channel": channel, "kind": kind,
                           "subject": str(m.get("subject", ""))[:150], "body": body,
                           "delivery": delivery, "segments": segments,
                           **({"variant": str(m["variant"])} if m.get("variant") else {}),
                           **({"context": context} if context else {})})
        real = sum(1 for m in frozen if m["delivery"] in {"live", "mock"})
        summary = f"{len(frozen)} {purpose} ({real} real, {len(frozen) - real} simulated)"
        billed = sum(m["segments"] for m in frozen)
        if billed:
            summary += f" · {billed} SMS segment{'s' if billed != 1 else ''}"
        flagged = sum(1 for m in frozen if m.get("context", {}).get("flags"))
        if flagged:
            summary += f" · {flagged} flagged for a closer look"
        return self._freeze("send_messages", {"messages": frozen, "purpose": purpose}, len(frozen), summary)

    def prepare_enrollment(self, workflow_key: str, contact_ids: list[str] | None = None,
                           from_sweep_kind: str = "", purpose: str = "",
                           custom_values: dict[str, str] | None = None) -> dict[str, Any]:
        """Freeze a bulk workflow enrollment (cadence, newsletter, event, new offer)."""
        self.expire_stale()
        if workflow_key not in BULK_WORKFLOW_KEYS:
            raise FcmError(f"workflow_key must be one of {sorted(BULK_WORKFLOW_KEYS)}")
        workflow_id = self.settings.workflow_id(workflow_key)
        if from_sweep_kind:
            plan = cadence.sweep(self.affiliates(), self.today(), self.settings.cadence)
            contact_ids = [i["contact_id"] for i in plan["bulk_queue"].get(from_sweep_kind, [])]
        ids = sorted(dict.fromkeys(contact_ids or []))
        if not ids:
            raise FcmError("no contacts to enroll")
        cap = int(self.settings.cadence["daily_bulk_enroll_cap"])
        already = self.store.count(self.today().isoformat(), "enrollments")
        if already + len(ids) > cap:
            raise FcmError(f"enrolling {len(ids)} would exceed today's cap ({already}/{cap})")
        names, deliveries = [], {}
        amap = {a.id: a for a in self.affiliates()} if len(ids) > 25 else {}
        for cid in ids:
            aff = amap.get(cid) or self.affiliate(cid)
            if aff.is_dnc:
                continue
            names.append(aff.name)
            deliveries[cid] = self._delivery_mode(aff)
        ids = [cid for cid in ids if cid in deliveries]
        if custom_values:
            for value in custom_values.values():
                self._lint(str(value))
        real = sum(1 for v in deliveries.values() if v in {"live", "mock"})
        summary = (f"enroll {len(ids)} in {workflow_key} ({real} real, {len(ids) - real} simulated)"
                   + (f" — {purpose}" if purpose else ""))
        payload = {"workflow_key": workflow_key, "workflow_id": workflow_id, "contact_ids": ids,
                   "deliveries": deliveries, "names": names, "purpose": purpose,
                   "custom_values": custom_values or {}}
        return self._freeze("enroll_workflow", payload, len(ids), summary)

    # ── outbound: expiry and cancel ──────────────────────────────────────────
    def expire_stale(self) -> list[str]:
        """Batches nobody approved within action_ttl_hours expire, which frees their partners for the next batch.
        A wave drafted Monday and approved Thursday would otherwise text the same people as Tuesday's wave."""
        ttl = int(self.settings.cadence.get("action_ttl_hours", 48))
        cutoff = (datetime.now(UTC) - timedelta(hours=ttl)).replace(microsecond=0).isoformat()
        expired = []
        for state in ("prepared", "approval_requested"):
            for row in self.store.list_actions(state, limit=5000):
                if row["created_at"] < cutoff and self.store.transition(row["action_id"], (state,), "expired"):
                    expired.append(row["action_id"])
                    self.store.audit(actor=self.actor, action=f"{row['kind']}.expire", resource=row["action_id"],
                                     decision="autonomous", result="expired", details={"ttl_hours": ttl})
        return expired

    def cancel_action(self, action_id: str, reason: str) -> dict[str, Any]:
        """Withdraw a batch that hasn't started sending. Cancelling only ever sends less, so it needs no approval."""
        row = self.store.get_action(action_id)
        if not row:
            raise FcmError(f"unknown action {action_id}")
        if not self.store.transition(action_id, ("prepared", "approval_requested", "approved"), "cancelled"):
            raise FcmError(f"action is {row['state']}; only a batch that hasn't started sending can be cancelled")
        self.store.audit(actor=self.actor, action=f"{row['kind']}.cancel", resource=action_id, decision="autonomous",
                         result="cancelled", details={"reason": reason})
        return {"ok": True, "action_id": action_id, "state": "cancelled"}

    # ── outbound: approve / execute ──────────────────────────────────────────
    def request_approval(self, action_id: str) -> dict[str, Any]:
        self.expire_stale()
        row = self.store.get_action(action_id)
        if not row:
            raise FcmError(f"unknown action {action_id}")
        if row["state"] not in {"prepared", "approval_requested"}:
            raise FcmError(f"action is {row['state']}, not awaiting approval")
        self.store.update_action(action_id, state="approval_requested")
        view = self._action_view({**row, "state": "approval_requested"})
        lines = [f"*Approval needed* — {row['summary']}",
                 f"action `{action_id}` · digest `{row['payload_hash']}` · demo mode: {self.settings.demo_mode}"]
        if client_from_env():
            lines.append(f"This sends without approval. To hold messages back first, post from your own account: "
                         f"`approve {action_id} {row['payload_hash']} except 4, 17`; `revoke {action_id}` stops it.")
        if row["kind"] == "send_messages":
            payload = json.loads(row["payload_json"])
            review = self.vault.review(action_id, payload.get("purpose", "messages"), row["summary"],
                                       payload["messages"], day=self.today().isoformat())
            view["review_file"] = str(review)
            view["review_thread"] = self._review_thread(review.read_text(), payload["messages"])
            full = len(payload["messages"]) <= 8
            lines.append(f"Every message in full: `{review.relative_to(self.vault.root)}`"
                         + (" (all shown below)" if full else f" ({len(payload['messages'])} messages; open the "
                            "file in Obsidian to read them all)"))
            flagged = [i for i, m in enumerate(payload["messages"], 1) if m.get("context", {}).get("flags")]
            if flagged:
                lines.append(f"⚠️ Look closely at {', '.join(map(str, flagged))}: the draft may not fit what they said.")
            for i, m in enumerate(payload["messages"][:8], 1):
                subj = f" — _{_slack_safe(m['subject'])}_" if m.get("subject") else ""
                body = m["body"] if full else m["body"][:180]
                ctx = m.get("context") or {}
                said = ""
                if ctx.get("their_last", {}).get("text") or ctx.get("intent"):
                    said = (f" They wrote: “{_slack_safe(ctx.get('their_last', {}).get('text', ''))[:220]}”"
                            f" (read as {ctx.get('intent') or '?'}"
                            + (f", move: {ctx['move']}" if ctx.get("move") else "") + ").")
                warn = "".join(f" ⚠️ {f}" for f in ctx.get("flags", []))
                lines.append(f"{i}. {_slack_safe(m['name'])} ({m['channel']}, {m['delivery']}){subj}:{said}{warn}"
                             f" Draft: {_slack_safe(body)}")
        if view.get("sample_contacts"):
            lines.append("Contacts: " + ", ".join(view["sample_contacts"]) +
                         (" …" if row["recipients"] > len(view["sample_contacts"]) else ""))
        for key, value in (view.get("custom_values") or {}).items():
            lines.append(f"{key}: {value}")
        lines.append(f"Reply *approve {action_id}* to send, *approve {action_id} except 4, 17* to hold some back, "
                     "or tell me what to change.")
        view["approval_card"] = "\n".join(lines)
        return view

    @staticmethod
    def _review_thread(review: str, messages: list[dict[str, Any]]) -> list[str]:
        """What the agent posts under the card. A small batch goes in full. A big one (a 250-text kickoff wave is
        ~90k characters, and re-typing that into Slack every wave would cost more than the whole reactivation's
        drafting) stays in the vault, and only the messages flagged for a closer look are posted."""
        if len(review) <= REVIEW_THREAD_MAX:
            return [_no_mentions(c) for c in _chunks(review, 3500)]
        sections = review.split("\n### ")
        flagged = [f"### {sections[i]}" for i, m in enumerate(messages, 1)
                   if i < len(sections) and (m.get("context") or {}).get("flags")][:10]
        return [_no_mentions(c) for c in _chunks("\n\n".join(flagged), 3500)] if flagged else []

    def approve(self, action_id: str, action_digest: str, approver: str,
                exclude: list[int] | None = None) -> dict[str, Any]:
        """Record a human approval. Exposed ONLY on the untrusted approvals MCP. `exclude` holds back messages
        by their number in the review file; everything else in the batch is approved as frozen."""
        self.expire_stale()
        row = self.store.get_action(action_id)
        if not row:
            raise FcmError(f"unknown action {action_id}")
        if row["state"] == "expired":
            raise FcmError("this batch expired before it was approved; prepare it again so it is checked fresh")
        if row["state"] != "approval_requested":
            raise FcmError(f"action is {row['state']}; request approval first")
        if action_digest != row["payload_hash"]:
            raise FcmError("digest does not match the frozen action — re-read the approval card")
        if not approver.strip():
            raise FcmError("approver name is required")
        excluded = sorted({int(x) for x in (exclude or [])})
        if excluded and row["kind"] != "send_messages":
            raise FcmError("exceptions apply to message batches only")
        if any(not 1 <= x <= int(row["recipients"]) for x in excluded):
            raise FcmError(f"exceptions must be message numbers between 1 and {row['recipients']}")
        ttl = int(self.settings.cadence["approval_ttl_hours"])
        approval = {"approval_id": _new_id("apr"), "action_id": action_id, "digest": action_digest,
                    "approver": approver.strip(), "created_at": now_iso(), "excluded_json": json.dumps(excluded),
                    "expires_at": (datetime.now(UTC) + timedelta(hours=ttl)).replace(microsecond=0).isoformat()}
        self.store.insert_approval(approval)
        self.store.update_action(action_id, state="approved", approval_id=approval["approval_id"])
        self.store.audit(actor=approver, action=f"{row['kind']}.approve", resource=action_id, decision="human",
                         result="approved", details={"expires_at": approval["expires_at"], "held_back": excluded})
        return {"ok": True, "action_id": action_id, "approval_id": approval["approval_id"],
                "expires_at": approval["expires_at"], "held_back": excluded}

    def _require_writes_enabled(self) -> None:
        if self.store.get_flag("external_writes_enabled", "true") != "true":
            raise FcmError(f"external writes are stopped: {self.store.get_flag('stop_reason', '')}")

    def _auto_approve(self, row: dict[str, Any]) -> dict[str, Any]:
        """Approve a prepared batch nobody approved, so it can execute. Recorded like any approval, as "auto"."""
        ttl = int(self.settings.cadence["approval_ttl_hours"])
        approval = {"approval_id": _new_id("apr"), "action_id": row["action_id"], "digest": row["payload_hash"],
                    "approver": "auto", "created_at": now_iso(), "excluded_json": "[]",
                    "expires_at": (datetime.now(UTC) + timedelta(hours=ttl)).replace(microsecond=0).isoformat()}
        self.store.insert_approval(approval)
        self.store.update_action(row["action_id"], approval_id=approval["approval_id"])
        if not self.store.transition(row["action_id"], ("prepared", "approval_requested"), "approved"):
            raise FcmError("another run is already sending this batch")
        self.store.audit(actor=self.actor, action=f"{row['kind']}.approve", resource=row["action_id"],
                         decision="autonomous", result="approved", details={"expires_at": approval["expires_at"]})
        return self.store.get_action(row["action_id"])

    def execute(self, action_id: str) -> dict[str, Any]:
        """Send a prepared batch (approving it as "auto" if nobody approved it). Safe to call again: a batch paused
        by quiet hours or the stop switch, or a run that died mid-way, picks up where it stopped while its approval
        lasts, and only messages that never started are sent. A message whose outcome is unknown is left for a
        person to settle."""
        import json as _json
        self._require_writes_enabled()
        self._require_sends_on()
        self.expire_stale()
        row = self.store.get_action(action_id)
        if not row:
            raise FcmError(f"unknown action {action_id}")
        gate = client_from_env()
        if gate and row["state"] == "approval_requested":
            # With a send gate, Justin may have approved in Slack (holding messages back); honor it if so.
            found = gate.approval(action_id, row["payload_hash"])
            if found.get("approved"):
                self.approve(action_id, row["payload_hash"], f"slack:{found['approver']}", found.get("exclude", []))
                row = self.store.get_action(action_id)
        if row["state"] in {"prepared", "approval_requested"}:
            row = self._auto_approve(row)
        if row["state"] not in SENDABLE_STATES:
            raise FcmError(f"action is {row['state']}; prepare it again to send it")
        approval = self.store.get_approval(row["approval_id"])
        if not approval or approval["digest"] != row["payload_hash"]:
            raise FcmError("approval does not match this action")
        if self._approval_lapsed(approval, started=row["state"] != "approved"):
            self.store.update_action(action_id, state="approval_requested")
            raise FcmError("approval expired — request a fresh one" +
                           (" to send the rest of this batch" if row["state"] != "approved" else ""))
        payload = _json.loads(row["payload_json"])
        if payload.get("location_id") != self.ghl.location_id:
            raise FcmError("action was prepared for a different GHL location")
        if row["state"] == "approved":
            if not self.store.use_approval(approval["approval_id"]):
                raise FcmError("approval was already used")
            if not self.store.transition(action_id, ("approved",), "executing"):
                raise FcmError("another run is already sending this batch")
        else:
            self.store.transition(action_id, (row["state"],), "executing")
        result: dict[str, Any] = {}
        # A crashed message batch can resume from its outbox; a crashed enrollment has no outbox, so it stops
        # in a state nothing sends from (re-running it could enroll everyone twice).
        state = "paused" if row["kind"] == "send_messages" else "interrupted"
        self._gate = (gate, row) if gate else None
        try:
            if row["kind"] == "send_messages":
                held = set(json.loads(approval.get("excluded_json") or "[]"))
                result = self._execute_messages(payload, action_id=action_id, held_back=held,
                                                prepared_at=row["created_at"])
                state = result.pop("state")
            elif row["kind"] == "enroll_workflow":
                result = self._execute_enrollment(payload)
                state = "stopped" if result.get("stopped") else (
                    "executed" if not result["failed"] else "executed_with_errors")
            else:
                raise FcmError(f"unknown action kind {row['kind']}")
        finally:  # never leave a batch stuck in "executing": a crash leaves it paused, resumable from the outbox
            self.store.update_action(action_id, state=state, result_json=stable_json(result))
        self.store.audit(actor=self.actor, action=f"{row['kind']}.execute", resource=action_id,
                         decision=f"approved:{approval['approver']}", result=state,
                         details={k: v for k, v in result.items() if k != "per_contact"})
        return {"ok": True, "action_id": action_id, "state": state, **result}

    def _touch_bookkeeping(self, aff: Affiliate, channel: str, kind: str) -> None:
        values: dict[str, Any] = {"last_touch_date": self.today().isoformat(), "last_touch_channel": channel}
        if kind in OFFER_KINDS:
            values["last_offer_date"] = self.today().isoformat()
        if kind == "scheduled_followup":
            values["next_touch_date"] = ""
            for task in self.ghl.list_tasks(aff.id):
                due = cadence.parse_day(task.get("dueDate"))
                manager_work = (str(task.get("title", "")).startswith(MANAGER_TASK_PREFIXES)
                                or str(task.get("body", "")).startswith(MANAGER_TASK_MARK))
                if not task.get("completed") and due and due <= self.today() and not manager_work:
                    self.ghl.complete_task(aff.id, task["id"])
        self._set_fields(aff.id, values)

    def _approval_lapsed(self, approval: dict[str, Any], started: bool) -> bool:
        """An approval must be used within approval_ttl_hours. Once a batch has started, the texts it held back
        for the recipients' quiet hours may finish for resume_ttl_hours after the approval (an evening approval
        whose West Coast texts wait for the morning)."""
        if not started:
            return approval["expires_at"] < now_iso()
        hours = int(self.settings.cadence.get("resume_ttl_hours", 36))
        limit = (datetime.fromisoformat(approval["created_at"]) + timedelta(hours=hours)).isoformat()
        return limit < now_iso()

    @staticmethod
    def _sends_off() -> bool:
        """On the live agent (FCM_SEND_GUARD=1) nothing reaches a person until Justin's switch is on."""
        return os.getenv("FCM_SEND_GUARD") == "1" and os.getenv("FCM_SEND_HANDOFFS") != "1"

    def _require_sends_on(self) -> None:
        if self._sends_off():
            raise FcmError("sending is off (FCM_SEND_HANDOFFS): nothing goes out until it's on")

    def resume_paused(self) -> dict[str, Any]:
        """Send what paused batches held back, as each recipient's window opens. Runs on a schedule without the
        model: it only finishes batches a person already approved, and never re-sends anything."""
        if self.store.get_flag("external_writes_enabled", "true") != "true" or self._sends_off():
            return {"ok": True, "stopped": True, "resumed": []}
        resumed = []
        stuck = (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0).isoformat()
        rows = self.store.list_actions("paused", limit=200) + [
            r for r in self.store.list_actions("executing", limit=200) if r["updated_at"] < stuck]  # a run killed hard
        for row in rows:
            try:
                result = self.execute(row["action_id"])
            except FcmError as exc:
                resumed.append({"action_id": row["action_id"], "error": str(exc)})
                continue
            sent = result.get("live", 0) + result.get("mock", 0) + result.get("simulated", 0)
            if sent or result["state"] != "paused":
                resumed.append({"action_id": row["action_id"], "state": result["state"], "sent": sent,
                                "still_waiting": result.get("pending", 0)})
        return {"ok": True, "resumed": resumed}

    def _stale(self, aff: Affiliate, m: dict[str, Any], prepared_at: str = "") -> str:
        """Why a message approved earlier shouldn't go out now ("" if it still should)."""
        kind = m.get("kind", "")
        if aff.is_dnc:
            return "opted out after approval"
        if self._manager_handling(aff) and kind not in PARTNER_WINDOW_KINDS:
            return "the manager took this conversation over"
        if m["channel"] == "sms" and aff.sms_blocked:
            return "number reported wrong after approval"
        if m["channel"] == "email" and aff.no_email:
            return "opted out of email after approval"
        if kind == "kickoff" and (KICKOFF_PENDING not in aff.tags or self.kicked_off(aff)):
            return "no longer waiting on a kickoff"
        if kind == "kickoff_nudge" and KICKOFF_SENT not in aff.tags:
            return "no longer waiting on a nudge (they replied, or the kickoff track ended)"
        if cadence.NOT_INTERESTED_TAG in aff.tags and kind in KICKOFF_KINDS:
            return "said they're not interested"
        if kind not in KICKOFF_KINDS and kind != "reply" and prepared_at:
            heard = self.graph.last_processed_at(aff.id)
            if heard and heard >= prepared_at:  # both stamped by this server's clock; a tie counts as after
                return "they wrote after this was drafted; answer what they said instead"
        if kind == "reply":  # compared with the newest text frozen into the batch, in GoHighLevel's own clock
            answered = str(((m.get("context") or {}).get("their_last") or {}).get("at") or "")
            newer = self._latest_inbound(aff.id)
            if newer and newer[1] and newer[1][: len(answered) or None] > answered:
                return "they wrote again after this reply was drafted; draft it fresh"
            if answered and self.settings.program_tag("takeover"):  # the manager answered while this waited to go out
                try:
                    thread = [m for conv in self.ghl.list_conversations(contact_id=aff.id, limit=3)
                              for m in self.ghl.list_messages(conv.get("id", ""), limit=20)]
                except FcmError:
                    thread = []
                if self._takeover(aff.id, thread, since=answered):
                    return "the manager answered them first"
        return ""

    def _send_window_open(self, aff: Affiliate, m: dict[str, Any]) -> bool:
        """Quiet hours are the recipient's: checked per text, in their time zone, at the moment of sending.
        FCM_IGNORE_SMS_WINDOW only works against the mock CRM (demos at odd hours), never for a real text."""
        if m["channel"] != "sms" or m["delivery"] == "simulated" or SIM_PARTNER_TAG in aff.tags:
            return True  # nobody's phone: a note in demo mode, or a simulated partner
        if m["delivery"] == "mock" and os.getenv("FCM_IGNORE_SMS_WINDOW"):
            return True
        c = self.settings.cadence
        return timezones.in_window(aff.phone, self.now(), int(c["sms_window_start_hour"]), int(c["sms_window_end_hour"]))

    def _execute_messages(self, payload: dict[str, Any], action_id: str = "",
                          held_back: set[int] | None = None, prepared_at: str = "") -> dict[str, Any]:
        messages = payload["messages"]
        self.store.outbox_init(action_id, messages)
        orphaned = (datetime.now(UTC) - timedelta(minutes=10)).replace(microsecond=0).isoformat()
        for r in self.store.outbox(action_id, states=("sending",)):
            if r["updated_at"] < orphaned:  # a run was killed mid-send: GoHighLevel may or may not have it
                self.store.outbox_set(action_id, r["n"], state="unknown",
                                      detail="a run stopped while sending this; check the GoHighLevel conversation")
        rows = {r["n"]: r for r in self.store.outbox(action_id)}
        counts = {"live": 0, "mock": 0, "simulated": 0, "failed": 0, "held_back": 0, "skipped": 0, "unknown": 0,
                  "deferred": 0}
        per_contact = []
        pause = float(self.settings.kickoff.get("send_pause_seconds", 0) or 0)
        stopped = ""
        for n, m in enumerate(messages, 1):
            if n % 10 == 0:
                self.store.update_action(action_id)  # heartbeat: a live run is never mistaken for a dead one
            if rows[n]["state"] != "pending":
                continue  # already settled by an earlier run
            if n in (held_back or set()):
                self.store.outbox_set(action_id, n, state="held_back")
                counts["held_back"] += 1
                per_contact.append({"contact_id": m["contact_id"], "ok": True, "held_back": True})
                continue
            if self.store.get_flag("external_writes_enabled", "true") != "true":  # read fresh for every message
                stopped = self.store.get_flag("stop_reason", "stopped")
                break
            try:
                aff = self.affiliate(m["contact_id"])
                why = self._stale(aff, m, prepared_at)
            except Exception as exc:  # noqa: BLE001 - nothing was sent; record it and keep going
                self.store.outbox_set(action_id, n, state="failed", detail=f"before sending: {exc}"[:300])
                counts["failed"] += 1
                per_contact.append({"contact_id": m["contact_id"], "ok": False, "error": str(exc)})
                continue
            if why:
                self.store.outbox_set(action_id, n, state="skipped", detail=why)
                counts["skipped"] += 1
                per_contact.append({"contact_id": aff.id, "ok": True, "skipped": why})
                continue
            if not self._send_window_open(aff, m):
                counts["deferred"] += 1  # stays pending; the next run inside their window sends it
                per_contact.append({"contact_id": aff.id, "ok": True, "deferred": "outside their quiet-hours window"})
                continue
            if not self.store.outbox_claim(action_id, n):
                counts["skipped"] += 1
                per_contact.append({"contact_id": aff.id, "ok": True, "skipped": "already handled"})
                continue
            try:
                if m["delivery"] == "simulated":
                    note = self.ghl.add_note(aff.id, f"[SIMULATED {m['channel'].upper()} — demo mode, not delivered]\n"
                                                     f"{m.get('subject', '')}\n{m['body']}".strip())
                    message_id = str((note or {}).get("id", "simulated"))
                else:
                    if getattr(self, "_gate", None):  # the gate sends; this computer's token can't
                        gate, gate_row = self._gate
                        sent = gate.send(gate_row, payload, n)
                    else:
                        sent = self.ghl.send_message(aff.id, m["channel"], m["body"], m.get("subject", ""))
                    message_id = str((sent or {}).get("messageId") or (sent or {}).get("id") or "")
            except Exception as exc:  # noqa: BLE001 - every outcome is recorded; nothing is retried blindly
                definite = m["delivery"] == "simulated" or (isinstance(exc, GHLError) and exc.rejected) or (
                    isinstance(exc, FcmError) and not isinstance(exc, GHLError))
                state = "failed" if definite else "unknown"
                self.store.outbox_set(action_id, n, state=state, detail=str(exc)[:300])
                counts[state] += 1
                per_contact.append({"contact_id": aff.id, "ok": False, "error": str(exc), "outcome": state})
                continue
            self.store.outbox_set(action_id, n, state="sent", message_id=message_id)
            counts[m["delivery"]] += 1
            per_contact.append({"contact_id": aff.id, "delivery": m["delivery"], "ok": True})
            self._bookkeep(action_id, n, aff, m)
            if m["delivery"] == "live" and m["channel"] == "sms" and pause:
                time.sleep(pause)  # pace live texts under the A2P throughput limit
        sent = counts["live"] + counts["mock"] + counts["simulated"]
        self.store.bump(self.today().isoformat(), "personal_messages", sent)
        pending = sum(1 for r in self.store.outbox(action_id, states=("pending",)))
        unknown = len(self.store.outbox(action_id, states=("unknown",)))
        failed = len(self.store.outbox(action_id, states=("failed",)))
        state = ("paused" if stopped or pending else "needs_reconcile" if unknown
                 else "executed_with_errors" if failed else "executed")
        self.vault.log("Messages sent", f"- {payload['purpose']}: live {counts['live']}, mock {counts['mock']}, "
                       f"simulated {counts['simulated']}, failed {counts['failed']}, skipped {counts['skipped']}"
                       + (f", held back {counts['held_back']}" if counts["held_back"] else "")
                       + (f", **{counts['unknown']} unknown — settle them**" if counts["unknown"] else "")
                       + (f", {pending} waiting ({'stopped: ' + stopped if stopped else 'quiet hours'})"
                          if pending else ""), day=self.today().isoformat())
        return {**counts, "pending": pending, "stopped": stopped, "state": state, "per_contact": per_contact}

    def _bookkeep(self, action_id: str, n: int, aff: Affiliate, m: dict[str, Any]) -> bool:
        """After a send: touch dates, kickoff tags, the partner's history and note. Its own step, so a slow CRM
        write can't make a delivered text look failed (and get sent again); it is retried until it lands."""
        try:
            self._touch_bookkeeping(aff, m["channel"], m.get("kind", ""))
            self._after_send(aff, m, f"{action_id}:{n}")
            self.vault.affiliate(aff.name, aff.id, f"{m['delivery']} {m['channel']} ({m.get('kind', '')}): "
                                 f"{m['body'][:140]}", day=self.today().isoformat())
        except Exception as exc:  # noqa: BLE001
            self.store.outbox_set(action_id, n, detail=f"sent; bookkeeping failed, will retry: {exc}"[:300])
            return False
        self.store.outbox_set(action_id, n, booked=1, detail="")
        return True

    def finish_bookkeeping(self) -> dict[str, Any]:
        """Retry the CRM updates for messages that went out but whose bookkeeping failed."""
        done, failed = 0, 0
        for r in self.store.outbox(states=("sent",)):
            if r["booked"]:
                continue
            action = self.store.get_action(r["action_id"])
            m = json.loads(action["payload_json"])["messages"][r["n"] - 1]
            try:
                aff = self.affiliate(r["contact_id"])
            except FcmError:
                failed += 1
                continue
            if self._bookkeep(r["action_id"], r["n"], aff, m):
                done += 1
            else:
                failed += 1
        return {"ok": True, "finished": done, "still_failing": failed}

    def outbox_status(self, action_id: str = "") -> dict[str, Any]:
        rows = self.store.outbox(action_id)
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["state"]] = counts.get(r["state"], 0) + 1
        return {"counts": counts,
                "unknown": [{k: r[k] for k in ("action_id", "n", "contact_id", "kind", "detail")}
                            for r in rows if r["state"] == "unknown"],
                "bookkeeping_pending": sum(1 for r in rows if r["state"] == "sent" and not r["booked"]),
                "paused_actions": [a["action_id"] for a in self.store.list_actions("paused", limit=200)]}

    def settle(self, action_id: str, n: int, outcome: str, actor: str) -> dict[str, Any]:
        """A person decides what happened to a message whose send outcome is unknown (they check GoHighLevel's
        conversation). "sent" books it; "not_sent" frees the partner for a later batch. Approvals surface only."""
        if outcome not in {"sent", "not_sent"}:
            raise FcmError("outcome must be sent or not_sent")
        if not actor.strip():
            raise FcmError("actor name is required")
        rows = self.store.outbox(action_id, states=("unknown",))
        r = next((x for x in rows if x["n"] == int(n)), None)
        if not r:
            raise FcmError(f"message {n} of {action_id} isn't waiting to be settled")
        self.store.outbox_set(action_id, int(n), state="sent" if outcome == "sent" else "failed",
                              detail=f"settled {outcome} by {actor.strip()}")
        if outcome == "sent":
            m = json.loads(self.store.get_action(action_id)["payload_json"])["messages"][int(n) - 1]
            self._bookkeep(action_id, int(n), self.affiliate(r["contact_id"]), m)
        if not self.store.outbox(action_id, states=("unknown", "pending")):
            failed = self.store.outbox(action_id, states=("failed",))
            self.store.transition(action_id, ("needs_reconcile",), "executed_with_errors" if failed else "executed")
        self.store.audit(actor=actor.strip(), action="outbox.settle", resource=f"{action_id}:{n}", decision="human",
                         result=outcome, details={"contact_id": r["contact_id"]})
        return {"ok": True, "action_id": action_id, "n": int(n), "outcome": outcome}

    def _after_send(self, aff: Affiliate, m: dict[str, Any], ref: str) -> None:
        """Kickoff tags move along, and every personal message becomes part of the partner's history."""
        kind = m.get("kind", "")
        tags = list(aff.tags)
        if kind == "kickoff":
            self.ghl.remove_tags(aff.id, [KICKOFF_PENDING])
            self.ghl.add_tags(aff.id, [KICKOFF_SENT])
            tags = [t for t in tags if t != KICKOFF_PENDING] + [KICKOFF_SENT]
            self.graph.set_variant(aff.id, m.get("variant", ""))
        elif kind == "kickoff_nudge":
            self.ghl.remove_tags(aff.id, [KICKOFF_SENT])
            self.ghl.add_tags(aff.id, [KICKOFF_DONE])
            tags = [t for t in tags if t != KICKOFF_SENT] + [KICKOFF_DONE]
        interaction = {"kickoff": "kickoff_sent", "kickoff_nudge": "nudge_sent"}.get(kind, "message_sent")
        self.remember(replace(aff, tags=tags), interaction={"kind": interaction, "ref": ref or digest(m),
                                                            "summary": m["body"][:400], "variant": m.get("variant", "")})

    def _execute_enrollment(self, payload: dict[str, Any]) -> dict[str, Any]:
        counts = {"live": 0, "mock": 0, "simulated": 0, "failed": 0}
        per_contact = []
        key = payload["workflow_key"]
        if payload.get("custom_values"):
            update = getattr(self.ghl, "update_custom_value_by_name", None)
            if update is None:
                raise FcmError("custom value updates are not supported by this backend")
            for name, value in payload["custom_values"].items():
                update(name, value)
        kind = {"monthly_offer": "monthly_offer", "new_offer": "new_offer"}.get(key, key)
        channel = "workflow"
        # one paged read instead of a GET per contact — keeps 10k-affiliate runs inside GHL rate limits
        amap = {a.id: a for a in self.affiliates()} if len(payload["contact_ids"]) > 25 else {}
        stopped = 0
        for i, cid in enumerate(payload["contact_ids"]):
            if self.store.get_flag("external_writes_enabled", "true") != "true":  # the stop switch, per contact
                stopped = len(payload["contact_ids"]) - i
                break
            delivery = payload["deliveries"].get(cid, "simulated")
            try:
                aff = amap.get(cid) or self.affiliate(cid)
                if aff.is_dnc:
                    raise FcmError("contact opted out after approval")
                if delivery == "simulated":
                    self.ghl.add_note(cid, f"[SIMULATED ENROLLMENT — demo mode] workflow: {key}")
                else:
                    if getattr(self, "_gate", None):
                        gate, gate_row = self._gate
                        gate.enroll(gate_row, payload, cid)
                    else:
                        self.ghl.enroll_workflow(cid, payload["workflow_id"])
                if key == "onboarding" and aff.lifecycle == "aff:applied":
                    self._apply_lifecycle(aff, "aff:onboarding", "onboarding sequence started")
                if key not in {"event_invite"}:
                    self._touch_bookkeeping(aff, channel, kind)
                counts[delivery] += 1
                per_contact.append({"contact_id": cid, "delivery": delivery, "ok": True})
            except FcmError as exc:
                counts["failed"] += 1
                per_contact.append({"contact_id": cid, "ok": False, "error": str(exc)})
        self.store.bump(self.today().isoformat(), "enrollments",
                        counts["live"] + counts["mock"] + counts["simulated"])
        self.vault.log("Workflow enrollment", f"- {key}: live {counts['live']}, mock {counts['mock']}, "
                       f"simulated {counts['simulated']}, failed {counts['failed']}"
                       + (f", {stopped} not enrolled (stopped)" if stopped else "")
                       + (f" — {payload['purpose']}" if payload.get("purpose") else ""),
                       day=self.today().isoformat())
        return {**counts, "stopped": stopped, "per_contact": per_contact}

    # ── standing approvals for recurring bulk cadence ─────────────────────────
    def activate_standing(self, workflow_key: str, max_per_day: int, days: int, approver: str) -> dict[str, Any]:
        """Human-approve recurring cadence enrollments. Approvals MCP only."""
        if workflow_key not in STANDING_ALLOWED:
            raise FcmError(f"standing approvals are limited to {sorted(STANDING_ALLOWED)}")
        if not 1 <= max_per_day <= int(self.settings.cadence["daily_bulk_enroll_cap"]):
            raise FcmError("max_per_day is out of range")
        if not 1 <= days <= 90:
            raise FcmError("standing approvals last 1–90 days")
        if not approver.strip():
            raise FcmError("approver name is required")
        row = {"standing_id": _new_id("std"), "workflow_key": workflow_key, "max_per_day": max_per_day,
               "approver": approver.strip(), "created_at": now_iso(),
               "expires_at": (datetime.now(UTC) + timedelta(days=days)).replace(microsecond=0).isoformat()}
        self.store.insert_standing(row)
        self.store.audit(actor=approver, action="standing.activate", resource=row["standing_id"], decision="human",
                         result="active", details={"workflow_key": workflow_key, "max_per_day": max_per_day,
                                                   "days": days})
        return {"ok": True, **row}

    def revoke_standing(self, standing_id: str, reason: str) -> dict[str, Any]:
        ok = self.store.revoke_standing(standing_id, reason)
        self.store.audit(actor=self.actor, action="standing.revoke", resource=standing_id, decision="autonomous",
                         result="revoked" if ok else "not-found", details={"reason": reason})
        return {"ok": ok}

    def run_standing_cadence(self) -> dict[str, Any]:
        """Execute today's bulk cadence under active standing approvals (the cron path)."""
        self._require_writes_enabled()
        self._require_sends_on()
        plan = cadence.sweep(self.affiliates(), self.today(), self.settings.cadence)
        results: dict[str, Any] = {}
        for kind, items in plan["bulk_queue"].items():
            standing = self.store.active_standing(kind)
            if not standing:
                results[kind] = {"skipped": "no standing approval", "due": len(items)}
                continue
            ids = [i["contact_id"] for i in items][: int(standing["max_per_day"])]
            if not ids:
                continue
            action = self.prepare_enrollment(kind, contact_ids=ids, purpose=f"standing approval {standing['standing_id']}")
            self.store.update_action(action["action_id"], state="approval_requested")
            approval = {"approval_id": _new_id("apr"), "action_id": action["action_id"],
                        "digest": action["action_digest"], "approver": f"standing:{standing['standing_id']}",
                        "created_at": now_iso(),
                        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).replace(microsecond=0).isoformat()}
            self.store.insert_approval(approval)
            self.store.update_action(action["action_id"], state="approved", approval_id=approval["approval_id"])
            results[kind] = self.execute(action["action_id"])
            results[kind].pop("per_contact", None)
        return {"date": self.today().isoformat(), "results": results}

    # ── kill switch ──────────────────────────────────────────────────────────
    def emergency_stop(self, reason: str) -> dict[str, Any]:
        self.store.set_flag("external_writes_enabled", "false")
        self.store.set_flag("stop_reason", reason or "stopped")
        self.store.audit(actor=self.actor, action="external_writes.stop", resource="all", decision="stop",
                         result="stopped", details={"reason": reason})
        self.vault.log("EMERGENCY STOP", f"All outbound frozen: {reason}", day=self.today().isoformat())
        return {"ok": True, "external_writes_enabled": False, "reason": reason}

    def resume(self, actor: str) -> dict[str, Any]:
        self.store.set_flag("external_writes_enabled", "true")
        self.store.set_flag("stop_reason", "")
        self.store.audit(actor=actor, action="external_writes.resume", resource="all", decision="human",
                         result="resumed", details={})
        return {"ok": True, "external_writes_enabled": True}

    # ── reporting ────────────────────────────────────────────────────────────
    def scorecard(self) -> dict[str, Any]:
        today = self.today()
        affs = self.affiliates()
        plan = cadence.sweep(affs, today, self.settings.cadence)

        def within(key: str, days: int) -> int:
            return sum(1 for a in affs if (d := a.day(key)) and (today - d).days <= days)

        by_source: dict[str, int] = {}
        for a in affs:
            by_source[a.source] = by_source.get(a.source, 0) + 1
        total = len(affs) or 1
        replied_30 = within("last_reply_date", 30)
        touched_30 = within("last_touch_date", 30)
        return {
            "date": today.isoformat(),
            "affiliates": len(affs),
            "by_source": dict(sorted(by_source.items(), key=lambda kv: -kv[1])),
            "cohorts": plan["cohorts"],
            "submitted_deal_last_30d": within("last_deal_date", 30),
            "replied_last_30d": replied_30,
            "touched_last_30d": touched_30,
            "reply_rate_30d": round(replied_30 / max(touched_30, 1), 3),
            "active_rate": round((plan["cohorts"].get("aff:active", 0) + plan["cohorts"].get("aff:producing", 0)
                                  + plan["cohorts"].get("aff:reactivated", 0)) / total, 3),
            "silent_90_plus": plan["silent_90_plus"],
            "dnc": sum(1 for a in affs if a.is_dnc),
            "open_growth_services": sum(1 for a in affs if any(t.startswith("want:") for t in a.tags)),
        }

    def daily_report(self, day: str = "", publish: bool = False) -> dict[str, Any]:
        """What went out, who replied to what, reactivations, deals, follow-ups, compliance (fcm.report).
        publish: also write it to today's Obsidian daily note and the Daily Reports list."""
        from . import report as reporting
        when = cadence.parse_day(day) if day else self.today()
        r = reporting.daily_report(self, when)
        if publish:
            self.vault.log(f"Daily report {r['date']}", reporting.to_markdown(r), day=r["date"])
            self._track(f"daily:{r['date']}", lambda tr: tr.upsert(
                "daily", f"daily:{r['date']}", f"Daily report {r['date']}: {r['sent']['real']} out, "
                f"{len(r['replies'])} replied, {len(r['reactivated'])} reactivated", reporting.to_markdown(r)))
            self.store.audit(actor=self.actor, action="report.daily", resource=r["date"], decision="autonomous",
                             result="published", details={"sent": r["sent"]["real"], "replies": len(r["replies"])})
        return r

    def read_file(self, path: str, offset: int = 0, max_chars: int = 20000) -> dict[str, Any]:
        """Read-only access to the knowledge base and the Obsidian vault, the only files the agent needs.
        (The agent has no shell, file or code tools: those could approve its own sends.) A directory lists its
        markdown files. Paths start with knowledge/ or vault/; nothing outside those two folders can be read."""
        roots = {"knowledge": (self.settings.config_dir.parent / "knowledge").resolve(),
                 "vault": self.settings.vault_dir.resolve()}
        head, _, rest = (path or "").strip().lstrip("/").partition("/")
        if head not in roots:
            raise FcmError("path must start with knowledge/ or vault/")
        target = (roots[head] / rest).resolve()
        if not target.is_relative_to(roots[head]) or any(
                part.startswith(".") for part in target.relative_to(roots[head]).parts):
            raise FcmError("that path is outside the knowledge base and the vault")
        if target.is_dir():
            files = sorted(str(f.relative_to(roots[head])) for f in target.rglob("*.md")
                           if not any(p.startswith(".") for p in f.relative_to(roots[head]).parts))
            return {"path": f"{head}/{rest}".rstrip("/"), "files": files[:500], "count": len(files)}
        if not target.exists() or target.suffix not in {".md", ".json", ".txt", ".csv"}:
            raise FcmError(f"no readable file at {head}/{rest}")
        text = target.read_text(errors="replace")
        part = text[max(0, offset): max(0, offset) + max(1, min(max_chars, 50000))]
        return {"path": f"{head}/{rest}", "chars": len(text), "offset": offset, "content": part,
                "more": offset + len(part) < len(text)}

    def daily_note(self, title: str, body: str) -> dict[str, Any]:
        """Append to today's daily note in the vault (summaries, decisions, what went out)."""
        self._lint(body)
        path = self.vault.log(title.strip()[:80] or "Note", body, day=self.today().isoformat())
        return {"ok": True, "path": str(path)}

    def save_campaign_note(self, title: str, body: str, kind: str = "campaign") -> dict[str, Any]:
        self._lint(body)
        path = self.vault.campaign(title, body, kind=kind, day=self.today().isoformat())
        return {"ok": True, "path": str(path)}
