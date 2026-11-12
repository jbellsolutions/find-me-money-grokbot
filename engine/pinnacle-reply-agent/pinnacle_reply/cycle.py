"""One cycle of the Reply Agent's loop (charter §2): pull every lead, attend each one, report the ledger.

    1. Pull every lead from every lane it can read (sources.py) into the ledger: Lead Radar's desk (all statuses),
       the creators pipeline, website forms, the Funding Machine inbox. A lane it can't read is reported, not fatal.
    2. For each unattended lead, best tier first and each lane in turn: hold it on Justin's rules, or draft it
       (Claude), or skip or hold it with the model's reason. Drafts go through the checker; a failing draft is held,
       never assigned. Website and inbox leads are private conversations: they wait on a person, never drafted.
    3. Draft the follow-up for every answered lead that lacks one.
    4. Write drafts and skips to the desk only while REPLY_WRITE is on, and never over a person's work. The first
       cycle with writes on also catches the desk up on everything recorded while they were off.
    4b. Posting (poster.py): read what was said under our posts, then post checked drafts in the lead's own thread,
       follow-ups first, high tier first, within each platform's daily cap. Only with REPLY_POST on (`posting`).
    5. Report the ledger, unattended first, and write it as a daily note.
    6. GHL: work out what each answered lead and its conversation need there, and send it while REPLY_GHL is on.
    7. The vault: every lead and its whole conversation as Obsidian notes, committed and pushed.
    8. The hub: check off each checklist line the lanes feed, the agent itself, and today's booked calls
       (REPLY_HUB on; off, the check-offs are worked out and shown).

Before drafting, the hub's quiet list (`GET /api/distribution/quiet`, REPLY_GHL on) marks the leads a funding partner has;
they are state `partner` and get no draft and no post. A hub that can't be read pauses follow-ups to leads in GHL.

Only Lead Radar's desk takes writes (REPLY_WRITE). The other lanes are read; what the agent does with their leads
stays in the ledger and the vault.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from . import checks, config, drafter, ghl, hub, lanes, ledger, poster, radar, sources, vault

TIER_RANK = {"high": 0, "medium": 1, "low": 2}


def desk(item: dict[str, Any]) -> bool:
    """Whether a lead lives on Lead Radar's desk, the only place the agent ever writes back to."""
    return (item.get("source") or "lead-radar") == "lead-radar"


def _fair(rows: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(taken, left): up to `limit` rows, one lane at a time in turn, so a big lane never starves a small one.
    Each lane keeps its own order (answered follow-ups first, then best tier, newest)."""
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_lane.setdefault(r.get("source") or "lead-radar", []).append(r)
    taken: list[dict[str, Any]] = []
    while len(taken) < limit and any(by_lane.values()):
        for lane in list(by_lane):
            if by_lane[lane] and len(taken) < limit:
                taken.append(by_lane[lane].pop(0))
    return taken, [r for rest in by_lane.values() for r in rest]


def _note_file(rep: dict[str, Any]) -> list[str]:
    day = datetime.now(timezone.utc).date().isoformat()
    text = ledger.markdown(rep, day)
    out = []
    targets = [config.STATE_DIR / "ledgers"] + ([config.VAULT_DIR / "Ledgers"] if config.VAULT_DIR else [])
    for folder in targets:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"Reply ledger {day}.md"
        path.write_text(text, encoding="utf-8")
        out.append(str(path))
    return out


def _apply(conn, item: dict[str, Any], row: dict[str, Any], out: dict[str, Any], dry_run: bool) -> str:
    """Record one drafter decision (reply, skip or hold) and write it to the desk if allowed. Returns which."""
    persona = lanes.persona(row["persona"]).get("name", "no lane")
    if not desk(item):
        dry_run = True  # only Lead Radar's desk takes writes; the other lanes' leads stay in the ledger
    if out["action"] == "reply":
        ledger.record(conn, row["id"], draft=out["reply"], violations="", drafted_at=ledger.now(), desk_written=0,
                      local_state="" if row.get("local_state") != "answered" else "answered", reason="")
        if row.get("local_state") != "answered" and desk(item):
            wrote = radar.save_draft(item, out["reply"], f"reply-agent: draft in {persona}'s lane, for {row['poster']}",
                                     dry_run)
            if wrote.get("written"):
                ledger.record(conn, row["id"], desk_written=1)
        return "drafted"
    if out["action"] == "skip":
        ledger.record(conn, row["id"], local_state="skipped", reason=out["reason"], desk_written=0)
        if radar.save_skip(item, out["reason"], dry_run).get("written"):
            ledger.record(conn, row["id"], desk_written=1)
        return "skipped"
    ledger.record(conn, row["id"], local_state="held", reason=out["reason"],
                  draft="", violations=", ".join(out.get("violations") or []))
    if item.get("reply", {}).get("draft") and not checks.passes(item["reply"]["draft"]):
        if radar.save_hold(item, out["reason"], dry_run).get("written"):
            ledger.record(conn, row["id"], desk_written=1)
    return "held"


def flush(conn, by_id: dict[str, dict[str, Any]], dry_run: bool) -> dict[str, int]:
    """Push what the ledger has and the desk doesn't: marks a person reported, the agent's skips, its drafts.
    Compared by content, so drafts made while REPLY_WRITE was off reach the desk on the first cycle with it on.
    Follow-ups stay in the ledger: the desk has no answered status yet (F2)."""
    pushed = {"marks": 0, "skips": 0, "drafts": 0, "cleared": 0}
    if dry_run or not config.WRITE:
        return pushed
    for row in [dict(r) for r in conn.execute("SELECT * FROM leads")]:
        item = by_id.get(row["id"])
        if item is None or not desk(item):
            continue
        on_desk = row.get("radar_status") or "new"
        if row.get("marked_by") and on_desk not in ("replied", "won"):
            out, kind = radar.save_replied(item, row["marked_by"]), "marks"
        elif row.get("local_state") == "skipped" and on_desk != "skipped":
            out, kind = radar.save_skip(item, row.get("reason") or "not a lead"), "skips"
        elif (row.get("draft") and row.get("local_state") != "answered" and row.get("radar_draft") != row["draft"]
              and checks.passes(row["draft"])):
            out, kind = radar.save_draft(item, row["draft"], f"reply-agent: draft for {row['poster']}"), "drafts"
        elif row.get("local_state") == "held" and row.get("radar_draft") and not checks.passes(row["radar_draft"]):
            out, kind = radar.save_hold(item, row.get("reason") or "held"), "cleared"
        else:
            continue
        if out.get("written"):
            pushed[kind] += 1
            ledger.record(conn, row["id"], desk_written=1)
    return pushed


def run(max_drafts: int | None = None, dry_run: bool = False, client=None,
        items: list[dict[str, Any]] | None = None, reads: list[dict[str, Any]] | None = None,
        drivers: dict[str, Any] | None = None) -> dict[str, Any]:
    """One cycle. `reads` (or `items`, as Lead Radar's desk alone) replaces the live pull: tests, or a saved queue.
    `max_drafts` 0 only counts. `drivers` replaces the platforms' posting drivers (tests)."""
    max_drafts = config.MAX_DRAFTS if max_drafts is None else max_drafts
    conn = ledger.connect()
    started = ledger.now()
    cid = conn.execute("INSERT INTO cycles (started_at) VALUES (?)", (started,)).lastrowid
    conn.commit()
    if reads is None:
        reads = sources.read_all() if items is None else [{"lane": "lead-radar", "ok": True, "items": items, "why": ""}]
    read = {r["lane"]: "" if r["ok"] else (r.get("why") or "not read") for r in reads}
    truncated = any(r.get("truncated") for r in reads)
    items = [i for r in reads for i in r.get("items") or []]
    by_id = {i["id"]: i for i in items}
    synced = {"new": 0, "seen": 0}
    for r in reads:
        got = ledger.sync(conn, r.get("items") or [], source=r["lane"])
        synced = {k: synced[k] + got[k] for k in synced}
    errors: list[str] = [f"{r['lane']} not read: {r['why']}" for r in reads if not r["ok"] and r["lane"] != "craigslist"]
    try:
        caught_up = flush(conn, by_id, dry_run)
    except radar.RadarError as exc:
        caught_up, errors = {}, [f"catching the desk up failed: {exc}"]

    # Spec 36: a lead a funding partner has gets nothing from the agent. If the hub can't be read, follow-ups to leads
    # already in GHL pause this cycle (first replies carry on) and the cycle goes on.
    partner = hub.partner_check(conn)
    if partner["unknown"]:
        errors.append(f"the hub's quiet list couldn't be read, so follow-ups to leads in GHL wait: {partner['why']}")

    done = {"drafted": 0, "skipped": 0, "held": 0, "follow_ups": 0, "rule_holds": 0, "left_for_next_cycle": 0,
            "paused_unknown_partner": 0}
    todo = [dict(r) for r in conn.execute("SELECT * FROM leads WHERE state='unattended'")]
    todo.sort(key=lambda r: r["posted_at"] or "", reverse=True)  # newest first within a tier (stable sort)
    todo.sort(key=lambda r: TIER_RANK.get(r["tier"] or "low", 3))
    answered = [dict(r) for r in conn.execute("SELECT * FROM leads WHERE state='answered' AND reason='follow-up to draft'")]
    if partner["unknown"]:
        done["paused_unknown_partner"] = sum(1 for r in answered if r.get("ghl_contact_id"))
        answered = [r for r in answered if not r.get("ghl_contact_id")]

    ready: list[dict[str, Any]] = []
    for row in answered + todo:
        item = by_id.get(row["id"])
        if item is None or item.get("policy") == "direct":
            continue
        if row["state"] == "unattended":
            ok, _why = radar.writable(item) if desk(item) else (True, "")
            if not ok:
                continue  # a person's draft that breaks a rule: reported, never rewritten by the agent
            hold = lanes.rule_hold(item)
            if hold:
                ledger.record(conn, row["id"], local_state="held", reason=hold)
                done["rule_holds"] += 1
                continue
        ready.append(row)
    taken, left = _fair(ready, max(0, max_drafts))
    done["left_for_next_cycle"] = len(left)
    jobs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in taken:
        item = by_id[row["id"]]
        if row["state"] == "answered":
            item = ledger.with_answer(conn, row, item)
        jobs.append((row, item))

    if jobs:
        try:
            client = client or drafter._client()
        except drafter.DraftError as exc:
            errors.append(str(exc))
            jobs = []
    stop = False
    # The model calls run side by side; every ledger and desk write stays on this thread, in completion order.
    with ThreadPoolExecutor(max_workers=max(1, min(config.WORKERS, len(jobs) or 1))) as pool:
        futures = {pool.submit(drafter.draft, item, row["persona"], client): (row, item) for row, item in jobs}
        for fut in as_completed(futures):
            row, item = futures[fut]
            if stop or fut.cancelled():
                continue
            try:
                what = _apply(conn, item, row, fut.result(), dry_run)
            except drafter.DraftError as exc:
                errors.append(f"{row['id']}: {exc}")
                if "key" in str(exc) or "unknown model" in str(exc):
                    stop = True  # every call would fail the same way
                    for f in futures:
                        f.cancel()
                continue
            except radar.RadarError as exc:
                errors.append(f"{row['id']}: desk write failed: {exc}")
                continue
            done["follow_ups" if row["state"] == "answered" else what] += 1

    try:
        posting = poster.run(conn, dry_run, by_id=by_id, drivers=drivers, hold_follow_ups=partner["unknown"])
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:  # posting never stops a cycle
        posting = {"errors": [f"posting failed: {type(exc).__name__}: {exc}"[:300]]}
    errors += posting.get("errors") or []
    rep = ledger.report(conn, truncated, read)
    files = _note_file(rep)
    crm = ghl.run(conn) if not dry_run else {"prepare": ghl.prepare(conn), "sent": False, "why": "dry run"}
    left = (crm.get("attach") or {}).get("capture_days_left")
    if left is not None and left <= ghl.CAPTURE_WARN_DAYS:
        errors.append(f"a detail someone gave has no creators-sync contact to go to, and is dropped in {left} days: "
                      "approve that person's writes on radar-creators")
    memory = vault.publish(conn)
    ran = next((r.get("ran") for r in reads if r["lane"] == "creators"), None)
    checklist = hub.report(conn, read, dry_run, ran=ran)
    lanes_read = {r["lane"]: {"read": r["ok"], "leads": len(r.get("items") or []), "why": r.get("why") or "",
                              **({"ran": r["ran"]} if r.get("ran") else {})} for r in reads}
    summary = {"cycle": cid, "started_at": started, "pulled": len(items), "lanes": lanes_read, **synced, **done,
               "caught_up": caught_up, "errors": errors[:20],
               "dry_run": dry_run or not config.WRITE, "ledger": rep, "notes": files, "ghl": crm, "vault": memory,
               "hub": checklist, "posting": posting, "partner": partner}
    conn.execute("UPDATE cycles SET finished_at=?, summary=? WHERE id=?", (ledger.now(), json.dumps(summary, default=str), cid))
    conn.commit()
    return summary
