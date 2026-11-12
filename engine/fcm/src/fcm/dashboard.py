"""The dashboard lane: what the API token can't do, the agent does on the GHL dashboard on its own desktop.

The workflows live in config/dashboard-tasks.json. Each one names its triggers, the access it needs, who
approves it, its steps, and the API read that proves it worked. This module uses them three ways:

- **Ahead of a launch** (`fcm launch access --client X`): every task the launch will need, plus the ones it
  might fall back to, become one access request, grouped by who has to provide what. Logins, MFA, admin
  clicks and spend approvals are asked for before the work starts, not discovered halfway.
- **When an API call hits a roadblock** (`classify`, the `fcm_api_roadblock` tool): status, message and path
  map to a known dashboard task, a retry, or the generic fallback procedure.
- **When `fcm launch check` fails** (`for_check`): the failing check names the dashboard task that fixes it.

The agent drives its own Orgo computer's desktop: Chrome there, signed in to GHL by a person. There is no
second computer and no second browser. Because the agent can click anything on that desktop, approvals don't
rest on the box: a send goes out only if the approver's own Slack account approved it, and that person's
Slack is never signed in on the agent's desktop. Both are asked for up front on every launch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import FcmError

ALWAYS_ASKED = ("send.gate", "approver.slack.id", "desktop.no.personal.slack")
WHO_ORDER = ["Justin", "the client", "the client's GHL admin (or Justin for a demo)", "the client's Slack admin",
             "the client's the old CRM admin", "the client (they pay usage) and Justin"]


def load(config_dir: Path) -> dict[str, Any]:
    path = Path(config_dir) / "dashboard-tasks.json"
    if not path.exists():
        raise FcmError(f"no {path}: the dashboard workflows ship in config/")
    registry = json.loads(path.read_text())
    problems = validate(registry)
    if problems:
        raise FcmError(f"{path}: " + "; ".join(problems))
    return registry


def validate(registry: dict[str, Any]) -> list[str]:
    problems = []
    access = registry.get("access", {})
    for tid, t in registry.get("tasks", {}).items():
        for field in ("title", "why_not_api", "steps", "verify", "approval", "where"):
            if not t.get(field):
                problems.append(f"{tid}: no {field}")
        for need in t.get("needs", []):
            if need not in access:
                problems.append(f"{tid}: needs unknown access {need!r}")
        for trig in t.get("triggers", []):
            if not set(trig) <= {"status", "message", "path", "method", "check", "detail", "intent"}:
                problems.append(f"{tid}: unknown trigger field in {trig}")
        if t.get("secret_moment") and not any("SECRET MOMENT" in s for s in t.get("steps", [])):
            problems.append(f"{tid}: a secret moment must be spelled out in the steps")
        if "spend.approval" in t.get("needs", []) and not (t.get("final_click") or t.get("human_only")) \
                and not any("Stop before Submit" in s for s in t.get("steps", [])):
            problems.append(f"{tid}: spends money, so a person must make the final click (final_click)")
        if t.get("final_click") and not any("FINAL CLICK" in s for s in t.get("steps", [])):
            problems.append(f"{tid}: final_click must be spelled out in the steps")
    for aid, a in access.items():
        for field in ("ask", "who", "why", "how"):
            if not a.get(field):
                problems.append(f"access {aid}: no {field}")
    if not registry.get("fallback", {}).get("steps"):
        problems.append("no fallback procedure")
    return problems


# ── roadblocks ────────────────────────────────────────────────────────────────
def guard(env: dict[str, str]) -> tuple[bool, str]:
    """Dashboard work is open: this is our own sub-account. A spot for a stop if one is ever needed."""
    return False, ""


def classify(registry: dict[str, Any], *, status: int = 0, message: str = "", path: str = "", method: str = "",
             intent: str = "", locked: tuple[bool, str] = (False, "")) -> dict[str, Any]:
    """What to do about a failed API call: retry, a known dashboard task, or the generic fallback.
    `locked` is `guard(env)`: while it holds, no dashboard task is handed out."""
    result = _classify(registry, status=status, message=message, path=path, method=method, intent=intent)
    if locked[0] and result["kind"] in ("dashboard", "unknown"):
        return {"kind": "waiting_on_approval", "task": result.get("task"), "next": locked[1] +
                ". Tell the manager what you needed and stop; nothing on the dashboard until it's approved."}
    return result


def _classify(registry: dict[str, Any], *, status: int, message: str, path: str, method: str,
              intent: str) -> dict[str, Any]:
    msg, intent_l = (message or "").lower(), (intent or "").lower()
    if status == 429:
        return {"kind": "rate_limit", "task": None, "next": "wait and retry with backoff; nothing for the dashboard"}
    if status >= 500 or (status == 0 and not intent_l):  # no status + an intent = "the API can't do this at all"
        return {"kind": "transient", "task": None,
                "next": "retry with backoff (twice); if it persists, tell the manager GoHighLevel is failing"}
    best: tuple[int, str] | None = None
    for tid, t in registry["tasks"].items():
        for trig in t.get("triggers", []):
            if "check" in trig or "intent" in trig:
                continue
            if trig.get("status") and status not in trig["status"]:
                continue
            if trig.get("message") and trig["message"] not in msg:
                continue
            if trig.get("method") and trig["method"].upper() != (method or "").upper():
                continue
            if trig.get("path") and not _path_matches(trig["path"], path):
                continue
            score = sum(1 for k in ("message", "path", "method") if trig.get(k))
            if best is None or score > best[0]:
                best = (score, tid)
        if intent_l and any(i in intent_l for i in t.get("intents", [])):
            if best is None or best[0] < 1:
                best = (1, tid)
    if best:
        t = registry["tasks"][best[1]]
        kind = "human_only" if t.get("human_only") else "dashboard"
        return {"kind": kind, "task": best[1], "title": t["title"], "why_not_api": t["why_not_api"],
                "needs": t.get("needs", []), "approval": t["approval"],
                "next": ("tell the manager; a person does this one" if kind == "human_only"
                         else f"follow dashboard task {best[1]} (fcm_dashboard_task) after the approval it names")}
    return {"kind": "unknown", "task": None, "next": "follow the fallback procedure",
            "fallback": registry["fallback"]["steps"]}


def _path_matches(pattern: str, path: str) -> bool:
    path = (path or "").split("?")[0]
    if pattern.endswith("/") and not path.endswith("/"):
        path += "/"
    return path == pattern


def for_check(registry: dict[str, Any], check: str, detail: str = "") -> str:
    """The dashboard task that fixes a failing `fcm launch check` line, or ''."""
    detail_l = (detail or "").lower()
    if check == "account active" and "not active" in detail_l:
        return "ghl.account.reactivate"
    for tid, t in registry["tasks"].items():
        for trig in t.get("triggers", []):
            if trig.get("check") == check and (not trig.get("detail") or trig["detail"].lower() in detail_l):
                return tid
    return ""


# ── ahead of a launch ─────────────────────────────────────────────────────────
def launch_tasks(registry: dict[str, Any], manifest: dict[str, Any]) -> list[tuple[str, str]]:
    """[(task id, 'planned' | 'if the API path fails')] for this client, first-things first."""
    ghl = manifest.get("ghl") or {}
    planned: list[str] = []
    contingent = ["ghl.account.reactivate", "ghl.subaccount.create", "ghl.pit.scopes.edit"]
    if manifest.get("texting"):
        planned += ["ghl.a2p.register", "ghl.phone.purchase"]
    if (ghl.get("token_mode") or "pit") == "oauth":
        planned += ["ghl.marketplace.app", "ghl.marketplace.install"]
    else:
        planned.append("ghl.pit.create")
    if ghl.get("snapshot_id"):
        contingent.append("ghl.snapshot.load")
    else:
        planned += ["ghl.pipelines.build", "ghl.workflows.build"]
    if manifest.get("calls"):
        planned.append("ghl.transcription.enable")
    if manifest.get("slack", True):
        planned.append("slack.app.install")
    tasks = registry["tasks"]
    first = [t for t in planned if tasks[t].get("first")]
    ordered = first + [t for t in planned if t not in first]
    return [(t, "planned") for t in ordered] + [(t, "if the API path fails") for t in contingent if t not in planned]


def access_request(registry: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Everything the launch needs from people, asked once, before the work starts."""
    tasks = launch_tasks(registry, manifest)
    needs: dict[str, dict[str, Any]] = {}
    if manifest.get("data_mode", "client-data") == "client-data" and "client.data.approval" in registry["access"]:
        needs["client.data.approval"] = {**registry["access"]["client.data.approval"], "id": "client.data.approval",
                                         "for": ["every dashboard and API step on their sub-account"],
                                         "only_if": False}
    # The approval guarantee, on every launch: a send gate off the agent's computer, whose Slack approval it
    # accepts, and that person's Slack never signed in on the agent's desktop (where the agent could click it).
    if manifest.get("pack") and "client.intake" in registry["access"]:
        company = manifest.get("company") or {}
        if not all(str(company.get(k, "")).strip() for k in ("name", "kind", "offer", "audience")) \
                or not str(manifest.get("manager_name", "")).strip():
            needs["client.intake"] = {**registry["access"]["client.intake"], "id": "client.intake",
                                      "for": ["the agent's persona and knowledge pack"], "only_if": False}
    for always in ALWAYS_ASKED:
        if always in registry["access"]:
            needs[always] = {**registry["access"][always], "id": always,
                             "for": ["releasing any send (Slack-verified approvals)"], "only_if": False}
    for tid, when in tasks:
        for need in registry["tasks"][tid].get("needs", []):
            entry = needs.setdefault(need, {**registry["access"][need], "id": need, "for": [], "only_if": True})
            entry["for"].append(registry["tasks"][tid]["title"])
            if when == "planned":
                entry["only_if"] = False
    by_who: dict[str, list[dict[str, Any]]] = {}
    for entry in needs.values():
        by_who.setdefault(entry["who"], []).append(entry)
    order = {w: i for i, w in enumerate(WHO_ORDER)}
    return {"client": manifest.get("client", ""),
            "tasks": [{"id": t, "title": registry["tasks"][t]["title"], "when": w,
                       "human_only": bool(registry["tasks"][t].get("human_only")),
                       "approval": registry["tasks"][t]["approval"]} for t, w in tasks],
            "by_who": dict(sorted(by_who.items(), key=lambda kv: order.get(kv[0], 99)))}


def outstanding(req: dict[str, Any], received: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(planned access still missing, fallback-only access still missing), given the manifest's access_received."""
    entries = [e for v in req["by_who"].values() for e in v if e["id"] not in (received or {})]
    return [e for e in entries if not e["only_if"]], [e for e in entries if e["only_if"]]


def render_access(req: dict[str, Any]) -> str:
    lines = [f"# What the {req['client']} launch needs from people, before it starts", ""]
    for who, entries in req["by_who"].items():
        lines.append(f"## {who}")
        for e in sorted(entries, key=lambda e: e["only_if"]):
            tag = " (only if the API path fails)" if e["only_if"] else ""
            lines.append(f"- **{e['ask']}**{tag}")
            lines.append(f"  - why: {e['why']}")
            lines.append(f"  - how: {e['how']}")
            lines.append(f"  - unlocks: {'; '.join(dict.fromkeys(e['for']))}")
        lines.append("")
    lines.append("## The dashboard work this launch plans")
    for t in req["tasks"]:
        who = "a person" if t["human_only"] else "the agent, on its own desktop"
        lines.append(f"- {t['title']} ({t['id']}): {who}; {t['when']}; approval: {t['approval']}")
    return "\n".join(lines) + "\n"


# ── the doc ───────────────────────────────────────────────────────────────────
def render_markdown(registry: dict[str, Any]) -> str:
    out = ["# Dashboard workflows: what the API token can't do",
           "",
           "Generated from `config/dashboard-tasks.json` by `fcm dashboard render`. Edit the JSON, not this file.",
           "",
           "The agent does these on its **own desktop**: Chrome on the Orgo computer it runs on, signed in to GHL",
           "by a person. Every task names who approves it. The agent never types a password, never handles an",
           "MFA code or a token, and never makes a FINAL CLICK (purchase, submit, publish, a billable create):",
           "it sets everything up and a person clicks over VNC. On a sub-account holding the client's real",
           "partners, dashboard work waits for the client's written systems approval, the same as the API. UI",
           "labels come from GHL help articles and haven't been checked live. The agent follows what the",
           "screenshot shows, and searches the docs when a label differs.",
           "",
           "Approvals don't rest on that desktop: a send goes out only if the approver's own Slack account approved",
           "it, checked against Slack's API at send time, and the approver's personal Slack is never signed in on",
           "the agent's desktop.",
           "",
           "Before a launch, `fcm launch access --client <name>` turns these tasks into one request for logins,",
           "admin clicks and spend approvals.",
           ""]
    for tid, t in registry["tasks"].items():
        out.append(f"## {t['title']} (`{tid}`)")
        out.append("")
        out.append(f"- **Why not the API:** {t['why_not_api']}")
        trig = [_trigger_text(x) for x in t.get("triggers", [])]
        if trig:
            out.append(f"- **Triggered by:** {'; '.join(trig)}")
        out.append(f"- **Where:** {t['where']}. **Approval:** {t['approval']}."
                   + (" **A person does this one.**" if t.get("human_only") else ""))
        if t.get("needs"):
            out.append(f"- **Needs, asked ahead:** {', '.join(registry['access'][n]['ask'] for n in t['needs'])}")
        out.append("")
        out += [f"{i}. {s}" for i, s in enumerate(t["steps"], 1)]
        out.append("")
        out.append(f"**Proof:** {t['verify']}"
                   + (f"  \n**Sources:** {', '.join('help article ' + s for s in t['sources'])}" if t.get("sources") else ""))
        out.append("")
    out.append(f"## {registry['fallback']['title']}")
    out.append("")
    out += [f"{i}. {s}" for i, s in enumerate(registry["fallback"]["steps"], 1)]
    out.append("")
    return "\n".join(out)


def _trigger_text(t: dict[str, Any]) -> str:
    if "check" in t:
        return f"`fcm launch check` fails on '{t['check']}'"
    if "intent" in t:
        return f"the launch includes {t['intent']}"
    bits = []
    if t.get("method") or t.get("path"):
        bits.append(f"{t.get('method', '')} {t.get('path', '')}".strip())
    if t.get("status"):
        bits.append("HTTP " + "/".join(map(str, t["status"])))
    if t.get("message"):
        bits.append(f"\"{t['message']}\"")
    return " ".join(bits)


def task_text(registry: dict[str, Any], task_id: str) -> dict[str, Any]:
    t = registry["tasks"].get(task_id)
    if not t:
        raise FcmError(f"no dashboard task {task_id!r}; known: {', '.join(registry['tasks'])}")
    return {"id": task_id, **t, "needs": [{"id": n, **registry["access"][n]} for n in t.get("needs", [])]}

