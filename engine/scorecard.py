#!/usr/bin/env python3
"""The Find Me Money scorecard: ten numbers for today and the last 7 days. Reads only.

    scorecard.py [--ledger PATH] [--env FILE] [--json] [--no-crm] [--vault DIR]

Asks found, replies posted and answers come from the Reply Agent's ledger (SQLite, opened read-only). Leads captured,
partner OKs, applications, calls booked, handoffs, funded and paid come from the CRM (Pinnacle Funding Group), read
with the token already in the Reply Agent's .env. It writes nothing to the CRM or the ledger. With --vault it adds
one line to today's scorecard note there.

A number it can't read is shown as "?" and the reason is listed, so a broken source never looks like a zero.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
# Pinnacle Funding Group's location id, set at intake (PINNACLE_GHL_LOCATION_ID in the environment or the --env file).
# The scorecard refuses any other account, and refuses every account while it is unset.
HOME_CRM = os.environ.get("PINNACLE_GHL_LOCATION_ID", "").strip()
COLUMNS = ("asks", "replies", "answers", "captured", "partner_oks", "applications", "calls", "handoffs", "funded", "paid")
LABELS = {"asks": "asks", "replies": "replies", "answers": "answers", "captured": "captured",
          "partner_oks": "partner OKs", "applications": "applications", "calls": "calls", "handoffs": "handoffs",
          "funded": "funded", "paid": "paid"}
TAGS = {"captured": "contact:captured", "partner_oks": "consent:partner-ok", "applications": "fi:applied"}
# A deal counts once it has reached the stage, so later stages count too.
# "Call Booked" in Partner Recruiting is a call with a would-be partner, not a funding call: it isn't counted.
STAGES = {"calls": {"booked", "plan call booked", "plan call held", "appointment booked"},
          "handoffs": {"sent to partner", "partner accepted", "application in", "funded", "paid"},
          "funded": {"funded", "paid", "commission invoiced", "commission collected"},
          "paid": {"paid", "commission collected"}}
PARTNER_PIPELINE = "partner handoffs"  # handoffs, and partner-funded deals, are counted only in this pipeline
Transport = Callable[[str, dict], dict]


def day_bounds(today: date, days: int) -> tuple[str, str]:
    """UTC ISO bounds for the last `days` Eastern days ending today."""
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), ET)
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), ET)
    utc = ZoneInfo("UTC")
    return start.astimezone(utc).isoformat(), end.astimezone(utc).isoformat()


# ---------------------------------------------------------------------------------------------------- the ledger
def ledger_counts(path: Path, today: date, days: int) -> dict[str, int]:
    """Asks first seen, replies posted and answers read in the window. Opened read-only: it can't change the ledger."""
    lo, hi = day_bounds(today, days)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        asks = conn.execute("SELECT count(*) FROM leads WHERE first_seen >= ? AND first_seen < ?", (lo, hi)).fetchone()[0]
        out = {"asks": asks, "replies": 0, "answers": 0}
        for kind, n in conn.execute("SELECT kind, count(*) FROM messages WHERE at >= ? AND at < ? "
                                    "AND kind IN ('reply', 'answer') GROUP BY kind", (lo, hi)):
            out["replies" if kind == "reply" else "answers"] = n
        return out
    finally:
        conn.close()


# ------------------------------------------------------------------------------------------------------- the CRM
def http_get(token: str, pause: float = 0.6) -> Transport:
    def get(path: str, params: dict) -> dict:
        url = "https://services.leadconnectorhq.com" + path + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Version": "2021-07-28",
                                                   "Accept": "application/json",
                                                   "User-Agent": "fmm-scorecard/0.1"})
        for attempt in range(4):  # the CRM allows about 20 reads in 10 seconds: go gently, and wait when told to
            time.sleep(pause)
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 3:
                    raise
                time.sleep(min(float(exc.headers.get("Retry-After") or 5), 15))
        return {}
    return get


def stage_names(get: Transport, location: str) -> dict[str, tuple[str, str]]:
    """stage id -> (pipeline name, stage name), lower-cased."""
    out = {}
    for pipe in get("/opportunities/pipelines", {"locationId": location}).get("pipelines", []):
        for stage in pipe.get("stages", []):
            out[stage["id"]] = (str(pipe.get("name", "")).lower(), str(stage.get("name", "")).lower())
    return out


def crm_events(get: Transport, location: str, today: date, days: int, max_pages: int = 60) -> list[tuple[str, str]]:
    """One pass over the CRM: (column, when) for each tagged contact added and each deal that reached a counted stage
    in the last `days` days. Narrower windows are counted from this list, so the CRM is read once per run."""
    if not HOME_CRM or location != HOME_CRM:
        raise ValueError("the scorecard reads only Pinnacle Funding Group (PINNACLE_GHL_LOCATION_ID, set at intake)")
    lo, hi = day_bounds(today, days)
    events: list[tuple[str, str]] = []
    for column, tag in TAGS.items():
        after, after_id = None, None
        for _ in range(max_pages):
            params = {"locationId": location, "query": tag, "limit": 100}
            if after:
                params.update(startAfter=after, startAfterId=after_id)
            page = get("/contacts/", params).get("contacts", [])
            for c in page:
                if tag in (c.get("tags") or []) and lo <= str(c.get("dateAdded", "")) < hi:
                    events.append((column, str(c["dateAdded"])))
            if len(page) < 100:
                break
            after, after_id = page[-1].get("startAfter", [None, None])[0], page[-1].get("id")
            if not after:
                break
    # Only the stages that count are asked for, one small search each: nearly every deal sits at New Lead.
    wanted = set().union(*STAGES.values())
    for stage_id, (pipeline, stage) in stage_names(get, location).items():
        if stage not in wanted:
            continue
        for page_no in range(1, max_pages + 1):
            opps = get("/opportunities/search", {"location_id": location, "pipeline_stage_id": stage_id, "limit": 100,
                                                 "page": page_no}).get("opportunities", [])
            for o in opps:
                if o.get("pipelineStageId") != stage_id:  # never trust the filter alone
                    continue
                changed = str(o.get("lastStageChangeAt") or o.get("updatedAt") or "")
                if not (lo <= changed < hi):
                    continue
                if stage in STAGES["calls"]:
                    events.append(("calls", changed))
                if PARTNER_PIPELINE in pipeline:
                    events += [(column, changed) for column in ("handoffs", "funded", "paid") if stage in STAGES[column]]
                elif stage in STAGES["funded"]:  # a deal we worked ourselves
                    events.append(("funded", changed))
                    if stage in STAGES["paid"]:
                        events.append(("paid", changed))
            if len(opps) < 100:
                break
    return events


def count_events(events: list[tuple[str, str]], today: date, days: int) -> dict[str, int]:
    lo, hi = day_bounds(today, days)
    out = {k: 0 for k in COLUMNS[3:]}
    for column, when in events:
        if lo <= when < hi:
            out[column] += 1
    return out


def crm_counts(get: Transport, location: str, today: date, days: int) -> dict[str, int]:
    """Tagged contacts added, and deals whose stage changed, in the window."""
    return count_events(crm_events(get, location, today, days), today, days)


# ----------------------------------------------------------------------------------------------------- the card
def build(today: date, ledger: Callable[[int], dict] | None, crm: Callable[[int], dict] | None) -> dict[str, Any]:
    card: dict[str, Any] = {"day": today.isoformat(), "today": {}, "week": {}, "unread": []}
    for label, days in (("today", 1), ("week", 7)):
        row: dict[str, Any] = {k: "?" for k in COLUMNS}
        for name, source in (("ledger", ledger), ("crm", crm)):
            if source is None:
                continue
            try:
                row.update(source(days))
            except Exception as exc:  # noqa: BLE001 - a source that fails is reported, never guessed
                why = f"{name}: {type(exc).__name__}: {exc}"[:160]
                if why not in card["unread"]:
                    card["unread"].append(why)
        card[label] = row
    if ledger is None:
        card["unread"].append("ledger: not read")
    if crm is None:
        card["unread"].append("crm: not read")
    return card


def line(row: dict[str, Any]) -> str:
    return " · ".join(f"{LABELS[k]} {row.get(k, '?')}" for k in COLUMNS)


def text(card: dict[str, Any]) -> str:
    when = date.fromisoformat(card["day"]).strftime("%a %d %b").replace(" 0", " ")
    out = [f"Find Me Money · {when}", f"Today   {line(card['today'])}", f"7 days  {line(card['week'])}"]
    out += [f"Not read: {why}" for why in card["unread"]]
    return "\n".join(out)


def read_env(path: Path) -> dict[str, str]:
    out = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def write_note(vault: Path, card: dict[str, Any], now: datetime) -> Path:
    """One line per run in today's scorecard note. Counts only: no names, no contact details."""
    folder = vault / "Scorecard"
    folder.mkdir(parents=True, exist_ok=True)
    note = folder / f"{card['day']}.md"
    if not note.exists():
        note.write_text(f"# Scorecard {card['day']}\n\n| time (ET) | " + " | ".join(LABELS[k] for k in COLUMNS)
                        + " |\n|---|" + "---|" * len(COLUMNS) + "\n", encoding="utf-8")
    with note.open("a", encoding="utf-8") as f:
        f.write(f"| {now.astimezone(ET):%H:%M} | " + " | ".join(str(card["today"].get(k, "?")) for k in COLUMNS) + " |\n")
    return note


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--ledger", type=Path, default=Path.home() / ".pinnacle-reply" / "state" / "ledger.sqlite")
    p.add_argument("--env", type=Path, default=Path.home() / ".hermes" / "profiles" / "pinnacle-reply-agent" / ".env")
    p.add_argument("--vault", type=Path, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-crm", action="store_true", help="the ledger's three numbers only")
    a = p.parse_args(argv)
    now = datetime.now(ET)
    today = now.date()
    ledger = (lambda days: ledger_counts(a.ledger, today, days)) if a.ledger.exists() else None
    crm = None
    if not a.no_crm and a.env.exists():
        env = read_env(a.env)
        global HOME_CRM
        HOME_CRM = HOME_CRM or env.get("PINNACLE_GHL_LOCATION_ID", "").strip()
        token, location = env.get("GHL_API_KEY", ""), env.get("GHL_LOCATION_ID", "")
        if token and location:
            get, cache = http_get(token), {}

            def crm(days: int) -> dict[str, int]:
                if "events" not in cache:  # read once, for the widest window; a failure is raised again each time
                    try:
                        cache["events"] = crm_events(get, location, today, 7)
                    except Exception as exc:  # noqa: BLE001
                        cache["events"] = exc
                if isinstance(cache["events"], Exception):
                    raise cache["events"]
                return count_events(cache["events"], today, days)
    card = build(today, ledger, crm)
    if a.vault:
        card["note"] = str(write_note(a.vault, card, now))
    print(json.dumps(card, indent=1) if a.json else text(card))
    return 0


if __name__ == "__main__":
    sys.exit(main())
