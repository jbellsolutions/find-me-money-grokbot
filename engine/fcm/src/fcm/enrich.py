"""Show what the agent remembers about each partner on their GoHighLevel card: custom fields and tags.

    fcm ghl enrich                          # dry run: how many cards would change
    fcm ghl enrich --contact <id> --apply   # one card first
    fcm ghl enrich --apply                  # every partner; re-runs only write what changed

The values come from the agent's own memory (the profile the graph builds from the fact ledger, the interactions
table and the revenue plan), the same source the agent reads when it drafts. So the card and the agent agree.
The engine calls `memory_fields` / `memory_tags` from `_sync_profile` whenever the agent writes a profile; this
module's `enrich` is the backfill for partners whose profile was written before these fields existed.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from .mirror import _partners

SEP = "; "
TEXT_MAX = 250  # a GoHighLevel TEXT field; LARGE_TEXT takes more
LARGE_TEXT_MAX = 2000
LARGE_TEXT_KEYS = {"goals"}

# field key -> profile slot(s) whose values are joined with "; "
SLOT_FIELDS = {"client_types": "client_types", "deal_types": "deal_types", "deal_size": "deal_size",
               "regions": "regions", "goals": "goals", "best_time": "best_time", "blockers": "blockers",
               "needs": "needs"}
# every field this module may write (all are optional on a location that has not been bootstrapped yet)
KEYS = (*SLOT_FIELDS, "preferred_channel", "next_question", "open_loops", "calls_held", "revenue_plan",
        "kickoff_variant")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def _join(values: list[Any], limit: int) -> str:
    seen: list[str] = []
    for v in values:
        v = str(v).strip()
        if v and v.lower() not in {s.lower() for s in seen}:
            seen.append(v)
    return SEP.join(seen)[:limit]


def _channel(values: list[str]) -> str:
    """Their best way to reach them, as the card's sms/email choice. A call preference has no option, so it is left."""
    for v in reversed(values):
        low = v.lower()
        if "email" in low:
            return "email"
        if "text" in low or "sms" in low:
            return "sms"
    return ""


def memory_fields(graph: Any, p: dict[str, Any]) -> dict[str, Any]:
    """The card fields for one partner's profile. Empty memory leaves a field out, so a card never gets blanked."""
    v = p.get("values", {})
    out: dict[str, Any] = {}
    for key, slot in SLOT_FIELDS.items():
        text = _join(v.get(slot, []), LARGE_TEXT_MAX if key in LARGE_TEXT_KEYS else TEXT_MAX)
        if text:
            out[key] = text
    if ch := _channel(v.get("channel", [])):
        out["preferred_channel"] = ch
    if p.get("next_question"):
        out["next_question"] = p["next_question"]["question"][:TEXT_MAX]
    if loops := _join([loop["text"] for loop in p.get("open_loops", [])], TEXT_MAX):
        out["open_loops"] = loops
    out["calls_held"] = len(graph.interactions(p["contact_id"], ["call"], limit=1000))
    out["revenue_plan"] = "yes" if (p.get("revenue_plan") or "").strip() else "no"
    if p.get("kickoff_variant") in {"A", "B", "C", "L"}:
        out["kickoff_variant"] = p["kickoff_variant"]
    return out


def missing_tags(have: list[str], want: list[str]) -> list[str]:
    """GoHighLevel lower-cases tags, so compare that way or every run would add them again."""
    held = {t.lower() for t in have}
    return [t for t in want if t.lower() not in held]


def memory_tags(graph: Any, p: dict[str, Any]) -> list[str]:
    cid = p["contact_id"]
    tags: list[str] = []
    if niche := slug(p.get("niche", "")):
        tags.append(f"niche:{niche}")
    tags += [f"needs:{s}" for s in dict.fromkeys(slug(n) for n in p.get("values", {}).get("deal_types", [])) if s]
    if p.get("kickoff_variant") in {"A", "B", "C", "L"}:
        tags.append(f"kickoff:{p['kickoff_variant']}".lower())
    inbound = graph.interactions(cid, ["reply", "inbound_other"], limit=1000)
    if any(i["kind"] == "reply" for i in inbound):
        tags.append("fcm:replied")
    if graph.interactions(cid, ["call"], limit=1):
        tags.append("fcm:call-held")
    if (p.get("revenue_plan") or "").strip():
        tags.append("fcm:plan-ready")
    if any(i["summary"].startswith("(identity_question)") for i in inbound):
        tags.append("fcm:identity-question")
    return tags


def _same(old: Any, new: Any) -> bool:
    try:
        return float(old) == float(new)
    except (TypeError, ValueError):
        return str(old if old is not None else "") == str(new)


def changed(card_fields: dict[str, Any], want: dict[str, Any], mapped: Any) -> dict[str, Any]:
    """Only mapped fields whose value on the card differs from memory."""
    return {k: v for k, v in want.items() if k in mapped and not _same(card_fields.get(k), v)}


def enrich(engine: Any, *, apply: bool = False, limit: int = 0, contact_id: str = "",
           log: Callable[[str], None] = lambda _l: None) -> dict[str, Any]:
    settings = engine.settings
    partners = _partners(settings)
    if contact_id:
        partners = [p for p in partners if p[0] == contact_id]
    if limit:
        partners = partners[:limit]
    mapped = settings.field_ids()
    report: dict[str, Any] = {"apply": apply, "partners": len(partners), "updated": 0, "unchanged": 0,
                              "fields_written": 0, "tags_added": 0, "failed": 0,
                              "fields_not_on_location": sorted(set(KEYS) - set(mapped))}
    for cid, _rel in partners:
        try:
            aff = engine.affiliate(cid)
            p = engine.profile_get(cid, aff=aff)
            fields = changed(aff.fields, memory_fields(engine.graph, p), mapped)
            tags = missing_tags(aff.tags, memory_tags(engine.graph, p))
            if not fields and not tags:
                report["unchanged"] += 1
                continue
            if apply:
                if fields:
                    engine._set_fields(cid, fields)
                if tags:
                    engine.ghl.add_tags(cid, tags)
                log(f"updated {aff.name} ({cid}): {len(fields)} fields, {len(tags)} tags")
            report["updated"] += 1
            report["fields_written"] += len(fields)
            report["tags_added"] += len(tags)
        except Exception as exc:  # one card failing never stops the rest
            report["failed"] += 1
            log(f"failed {cid}: {exc}")
    return report
