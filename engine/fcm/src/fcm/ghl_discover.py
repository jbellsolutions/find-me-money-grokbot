"""GoHighLevel discovery: read a sub-account's setup and compare it with what the agent needs. Read-only.

It reads configuration only: the location, custom fields, tags, workflows, pipelines and users. It never reads a
contact, conversation or message. The report answers the questions to settle before the first wave:
  * which of the agent's fields, tags and workflows already exist, and which `fcm ghl bootstrap` would add;
  * which existing workflows might also text partners. Two systems texting one partner is the double-message risk;
  * who the users are, so "assigned manager" maps to a real GHL user.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .config import CUSTOM_FIELD_KEYS

OUTBOUND_HINT = re.compile(r"sms|text|reactivat|nurture|drip|follow.?up|re.?engage|campaign|blast|newsletter", re.I)


def _key(field: dict[str, Any]) -> str:
    raw = str(field.get("fieldKey") or field.get("key") or "")
    return raw.split(".", 1)[1] if raw.startswith("contact.") else raw


def discover(ghl: Any, settings: Any) -> dict[str, Any]:
    location = ghl.location() or {}
    fields = ghl.list_custom_fields()
    tags = ghl.list_tags()
    workflows = ghl.list_workflows()
    pipelines = ghl.list_pipelines()
    try:
        users = ghl.list_users()
    except Exception:  # noqa: BLE001 - a token without users.readonly still gets the rest of the report
        users = []
    taxonomy = json.loads((settings.config_dir / "tag-taxonomy.json").read_text())
    wanted_tags = sorted({t for group, values in taxonomy.items() if isinstance(values, list) for t in values})
    wf_config = json.loads((settings.config_dir / "workflows.json").read_text())
    wanted_wf = {k: v.get("name", "") for k, v in wf_config.items() if isinstance(v, dict)}
    have_keys = {_key(f) for f in fields} | {re.sub(r"\W+", "_", str(f.get("name", "")).lower()).strip("_") for f in fields}
    have_tags = {str(t.get("name", "")).lower() for t in tags}
    wf_names = {str(w.get("name", "")): w for w in workflows}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "location": {k: location.get(k) for k in ("id", "name", "timezone", "country", "state")},
        "custom_fields": {"count": len(fields),
                          "fields": [{"name": f.get("name", ""), "key": _key(f), "type": f.get("dataType", "")}
                                     for f in fields],
                          "agent_fields_present": sorted(k for k in CUSTOM_FIELD_KEYS if k in have_keys),
                          "agent_fields_missing": sorted(k for k in CUSTOM_FIELD_KEYS if k not in have_keys)},
        "tags": {"count": len(tags), "agent_tags_present": [t for t in wanted_tags if t.lower() in have_tags],
                 "agent_tags_missing": [t for t in wanted_tags if t.lower() not in have_tags]},
        "workflows": {"count": len(workflows),
                      "all": [{"name": w.get("name", ""), "status": w.get("status", "")} for w in workflows],
                      "agent_workflows": {k: ("present" if n in wf_names else "missing") for k, n in wanted_wf.items()},
                      "might_also_message_partners": [w.get("name", "") for w in workflows
                                                      if w.get("status") == "published"
                                                      and OUTBOUND_HINT.search(str(w.get("name", "")))
                                                      and w.get("name", "") not in wanted_wf.values()]},
        "pipelines": [{"name": p.get("name", ""), "stages": [s.get("name", "") for s in p.get("stages", [])]}
                      for p in pipelines],
        "users": [{"name": u.get("name") or " ".join(x for x in (u.get("firstName"), u.get("lastName")) if x),
                   "role": (u.get("roles") or {}).get("role", "") if isinstance(u.get("roles"), dict) else ""}
                  for u in users],
    }


def render(report: dict[str, Any]) -> str:
    loc, cf, tg, wf = report["location"], report["custom_fields"], report["tags"], report["workflows"]
    lines = [f"# GoHighLevel discovery, {report['generated_at'][:10]}", "",
             f"Location **{loc.get('name') or loc.get('id')}** ({loc.get('timezone') or 'timezone unknown'}). "
             "Configuration only: no contacts or messages were read.", "",
             "## What the agent needs", "",
             f"- Custom fields: {len(cf['agent_fields_present'])} of {len(CUSTOM_FIELD_KEYS)} present. Missing: "
             f"{', '.join(cf['agent_fields_missing']) or 'none'}",
             f"- Tags: {len(tg['agent_tags_present'])} present, {len(tg['agent_tags_missing'])} missing "
             "(`fcm ghl bootstrap` adds them)",
             "- Workflows: " + ", ".join(f"{k} {v}" for k, v in wf["agent_workflows"].items()), "",
             "## Workflows that might also text partners", ""]
    lines += [f"- {n}" for n in wf["might_also_message_partners"]] or ["- none found by name"]
    lines += ["", "Each one needs a decision before wave 1: pause it for partners in the program, or exclude them.",
              "", "## Pipelines", ""]
    lines += [f"- **{p['name']}**: {' → '.join(p['stages'])}" for p in report["pipelines"]] or ["- none"]
    lines += ["", "## Users (for the assigned-manager field)", ""]
    lines += [f"- {u['name']}{' (' + u['role'] + ')' if u['role'] else ''}" for u in report["users"]] or \
             ["- not readable with this token"]
    lines += ["", f"## All custom fields ({cf['count']})", "", "| Name | Key | Type |", "|---|---|---|"]
    lines += [f"| {f['name']} | `{f['key']}` | {f['type']} |" for f in cf["fields"]]
    lines += ["", f"## All workflows ({wf['count']})", ""]
    lines += [f"- {w['name']} ({w['status']})" for w in wf["all"]]
    return "\n".join(lines) + "\n"
