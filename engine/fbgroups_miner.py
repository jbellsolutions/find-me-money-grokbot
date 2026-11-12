#!/usr/bin/env python3
"""Founder lane: read the newest posts in Facebook funding groups, grade funding asks, import them to the Radar.

Groups come from the Reply Agent's ledger (groups where funding asks were already found). Reads go through the
owner's One API gateway (ScrapeCreators group posts, 3 posts and 1 credit per read) under a running One API goal.
Grading uses Claude Haiku. High and medium asks go to the Funding Radar's import as lane "founder-fbgroups", so
they land on Comment leads, the Reply Agent drafts them and Pinnacle files them. Nothing is posted or sent.

    python3 lanes/fbgroups_miner.py --groups groups.txt --pages 2 --max-groups 200 --state state.json [--go]

Secrets: ANTHROPIC_API_KEY and RADAR_IMPORT_TOKEN are read from ENV_FILE (default: the Lending Hub's .env.local),
never printed. The One API client reads its own config (~/.config/one-api/client.json).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLIENT = Path.home() / ".claude/skills/one-api/scripts/client.py"
ENV_FILE = Path(os.environ.get("ENV_FILE", "/workspace/find-me-money/.secrets/fmm.env"))
RADAR = os.environ.get("RADAR_URL", "").rstrip("/")  # the Funding Radar, set at intake
TRIAL = "first-live-trial-20261102"
MODEL = "claude-haiku-5-5"
CATEGORIES = ("real-estate", "small-business", "trucking", "creator", "gig", "credit")

GRADER = """You grade Facebook group posts for Find Me Money Group, a business-funding marketplace.
For each post decide if the AUTHOR is asking for money for a business or an investment property (working capital,
equipment, SBA, merchant cash advance, business credit lines, hard money, fix-and-flip, DSCR, bridge loans, startup
funding, truck or equipment financing, business credit building) right now or soon.
fit "high": a clear, current ask for funding with some detail. "medium": a likely ask, vague or early.
"none": everything else: lenders, brokers or coaches advertising, consumer personal loans, a home they live in,
memes, news, hiring, selling a service, or no text.
Return only JSON: {"results": [{"i": <index>, "fit": "high"|"medium"|"none", "need": "<one line: what money, for
what, where if stated>", "category": "<one of real-estate, small-business, trucking, creator, gig, credit, then
/subtype, max 80 chars>", "who": "<who they are, one line>", "quote": "<their words, max 160 chars>"}]}"""


def secrets() -> dict[str, str]:
    out = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip().removeprefix("export ")
            if k in ("ANTHROPIC_API_KEY", "RADAR_IMPORT_TOKEN"):
                out[k] = v.strip().strip("'\"")
    missing = {"ANTHROPIC_API_KEY", "RADAR_IMPORT_TOKEN"} - out.keys()
    if missing:
        raise SystemExit(f"{ENV_FILE} lacks {', '.join(sorted(missing))}")
    return out


def one_api(tool: str, args: dict, request_id: str, goal: str | None = None) -> dict:
    cmd = [sys.executable, "-I", str(CLIENT), "call", tool, "--arguments", json.dumps(args), "--request-id", request_id]
    if goal:
        cmd += ["--goal-id", goal]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"status": "client_error", "error": (out.stdout + out.stderr)[-400:]}


def new_goal(n: int, stamp: str) -> str:
    rid = f"fmm-fbgroups-{stamp}-g{n:02d}"
    d = one_api("goal.create", {
        "objective": "Founder lane: read the newest posts in Facebook funding groups, grade funding asks, import them "
                     "into the Funding Radar as lane founder-fbgroups.",
        "criteria": ["Newest posts read from funding groups", "Asks graded high or medium with a stated need",
                     "Asks imported into the Radar with source URLs"],
        "trial_id": TRIAL, "create_request_id": rid, "step_limit": 100}, rid)
    return d["receipt"]["output"]["id"]


def grade(posts: list[dict], key: str) -> list[dict]:
    items = [{"i": i, "text": (p.get("text") or "")[:1200], "group": p.get("_group")} for i, p in enumerate(posts)]
    tool = {"name": "record_asks", "description": "Record the posts graded high or medium. Leave out every 'none'.",
            "input_schema": {"type": "object", "required": ["results"], "properties": {"results": {"type": "array", "items": {
                "type": "object", "required": ["i", "fit", "need", "category"], "properties": {
                    "i": {"type": "integer"}, "fit": {"type": "string", "enum": ["high", "medium"]},
                    "need": {"type": "string"}, "category": {"type": "string"}, "who": {"type": "string"},
                    "quote": {"type": "string"}}}}}}}
    body = {"model": MODEL, "max_tokens": 8000, "system": GRADER + "\nRecord only high and medium posts with the record_asks tool.",
            "tools": [tool], "tool_choice": {"type": "tool", "name": "record_asks"},
            "messages": [{"role": "user", "content": json.dumps(items)}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        blocks = json.load(r)["content"]
    use = next((b for b in blocks if b.get("type") == "tool_use"), None)
    return [x for x in ((use or {}).get("input") or {}).get("results", []) if 0 <= x.get("i", -1) < len(posts)]


def radar_import(leads: list[dict], token: str) -> dict:
    if not RADAR:
        raise SystemExit("RADAR_URL is not set (intake)")
    req = urllib.request.Request(RADAR + "/api/leads/import", data=json.dumps({"lane": "founder-fbgroups", "leads": leads}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", required=True)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--max-groups", type=int, default=50)
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--state", required=True)
    ap.add_argument("--go", action="store_true", help="import to the Radar (otherwise grade and report only)")
    a = ap.parse_args()
    keys = secrets()
    state_path = Path(a.state)
    state = json.loads(state_path.read_text()) if state_path.exists() else {"done": [], "seen": [], "reads": 0, "imported": 0}
    groups = [l.split()[0] for l in Path(a.groups).read_text().splitlines() if l.strip() and not l.startswith("groups:")]
    groups = [g for g in groups if g not in state["done"]][: a.max_groups]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    cutoff = datetime.now(timezone.utc) - timedelta(days=a.days)
    goal, steps, gn = None, 0, 0
    batch: list[dict] = []
    seen = set(state["seen"])

    def flush():
        nonlocal batch
        if not batch:
            return
        res = grade(batch, keys["ANTHROPIC_API_KEY"])
        leads = []
        for r in res:
            if r.get("fit") not in ("high", "medium") or not r.get("need"):
                continue
            p = batch[r["i"]]
            cat = str(r.get("category") or "small-business")
            if not cat.startswith(CATEGORIES):
                cat = "small-business/" + cat
            leads.append({"url": p["url"], "platform": "facebook", "fit": r["fit"], "need": r["need"][:300],
                          "category": cat[:80], "who": (r.get("who") or "")[:200], "quote": (r.get("quote") or "")[:300],
                          "text": (p.get("text") or "")[:2000], "author": (p.get("author") or {}).get("name"),
                          "posted_at": p.get("creation_time"), "parent_url": f"https://www.facebook.com/groups/{p['_group']}/",
                          "source": f"group:{p['_group']}", "confidence": 0.8 if r["fit"] == "high" else 0.6,
                          "id": f"FBG-{p['id']}"})
        out = {"graded": len(batch), "asks": len(leads)}
        if leads and a.go:
            out["radar"] = radar_import(leads, keys["RADAR_IMPORT_TOKEN"])
            state["imported"] += out["radar"].get("imported", 0)
        print(json.dumps(out), flush=True)
        batch = []

    for g in groups:
        cursor, failed = None, False
        for page in range(a.pages):
            if goal is None or steps >= 95:
                gn += 1
                goal, steps = new_goal(gn, stamp), 0
            params = {"url": f"https://www.facebook.com/groups/{g}/", "sort_by": "CHRONOLOGICAL"}
            if cursor:
                params["cursor"] = cursor
            d = one_api("treg.social.read", {"endpoint_id": "scrapecreators.x.v1-facebook-group-posts", "params": params,
                                             "max_cost_usd": 0.01}, f"fmm-fbg-{stamp}-{g}-p{page}", goal)
            steps += 1
            state["reads"] += 1
            body = (((d.get("receipt") or {}).get("output") or {}).get("output") or {})
            if d.get("status") != "returned" or not body.get("success"):
                err = str(d.get("error") or body)[:200]
                print(json.dumps({"group": g, "status": d.get("status"), "error": err}), flush=True)
                if "usage limit" in err or "limit reached" in err:
                    flush()
                    state["seen"] = list(seen)[-20000:]
                    state_path.write_text(json.dumps(state))
                    print(json.dumps({"stopped": "daily provider cap reached", "reads": state["reads"],
                                      "imported_total": state["imported"], "groups_done": len(state["done"])}))
                    return 0
                failed = True
                break
            fresh = 0
            for p in body.get("posts") or []:
                t = p.get("creation_time")
                if not p.get("text") or p["id"] in seen or not t:
                    continue
                if datetime.fromisoformat(t.replace("Z", "+00:00")) < cutoff:
                    continue
                p["_group"] = g
                seen.add(p["id"])
                batch.append(p)
                fresh += 1
            if len(batch) >= 30:
                flush()
            cursor = body.get("cursor")
            if not cursor or not fresh:
                break
        if not failed:
            state["done"].append(g)
        state["seen"] = list(seen)[-20000:]
        state_path.write_text(json.dumps(state))
    flush()
    state["seen"] = list(seen)[-20000:]
    state_path.write_text(json.dumps(state))
    print(json.dumps({"reads": state["reads"], "imported_total": state["imported"], "groups_done": len(state["done"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
