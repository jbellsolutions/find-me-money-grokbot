---
name: worker-bridge
description: How the Find Me Money bot hands work to its executors and gets results back - work orders to the Hermes worker on the Mac or to a Codex CLI, pulling results, routing them to roles, and the watchdog on silent lanes. Use for the Dispatch and Pull routines, "send this to Hermes", "who runs this lane", or a lane that went quiet.
---

# Worker bridge

Justin, 2026-11-13: "grokbot is just the orchestrator and automator", "just also think of usage. always - what can we push to the hermes on mac?", and "we will not just use hermes on VPS/Orgo but also we can use a CLI subscription like codex to subsidize usage on grokbot".

So the bot does judgment and plumbing calls only. Everything mechanical, frequent, or done with a browser runs on an executor.

| Executor | Where | Runs | Switch |
|---|---|---|---|
| `hermes-mac` | The Find Me Money Hermes profile on the Mac in `MUSE_COMPUTER` | Every lane; the only one for Marketplace, Muse, groups by theme and anything needing the Mac's sign-ins | owner `hermes-worker: bot` once Justin installed the worker (`hermes-worker/install.sh --go`) and turned its one job on |
| `codex` | A Codex CLI on this bot's own computer, signed in to its own subscription | The `drafts` lane only: `codex exec` has no web search, so research lanes stay on Hermes | owner `codex-cli: bot` once Justin installed Codex and signed it in |

`context/executors.md` picks per lane, e.g. `drafts: codex`. A lane with no line goes to `hermes-mac`.

## Commands

```
E=python3 repo/engine/hermes_bridge.py
$E lanes                                   # every lane, its args, and who runs it
$E put places '{"metro":"Tampa","category":"roofing"}' --routine "Dispatch"
$E pull                                    # new results into state/hermes/<lane>/
$E status                                  # Hermes heartbeats per lane, inbox depth, outbox counts
```

- A work order carries a lane and short checked values only. Never free text, never a lead's words: that is how a post can't become a command on the Mac.
- `put` with the owner still `live` keeps the order in `requests/hermes/` and says held. That is the normal state until Justin's yes.
- Each `put`, `pull` or `status` is one Orgo call. Batch: one Dispatch run sends the day's orders; three Pull runs a day collect.

## Dispatch (daily)

Read `context/week-plan.md` (written by the radar role's Niche rotation from the `lead-map` skill). Send each line as one `put`, at most 12 a day unless Justin set another cap. Spend: a lane that would use paid credits needs `spend_guard.py` first.

## Pull (three times a day)

1. `$E pull`.
2. Drop every research or find row with no source link (`repo/usage/scripts/check_shape.py`) and count the dropped rows in the run line: a row without a link may be invented. Then route each new file by lane: `fbgroups`, `muse`, `marketplace`, `craigslist` → `requests/radar/` (lead fit) and `requests/sales/` (fit rows); `places` → `requests/outreach/`; `influencers`, `affiliate-houses`, `coaches` → `requests/partners/`; `wholesalers` → `requests/wholesale/`; `drafts` → the role that asked; `group-discovery` → `context/group-registry.md` (theme, count kept, never the links); `profile/` (the Hermes profile's own approval queue, gates, heartbeats and loop list) → `requests/sales/`.
3. `$E status` and `beat.py status --hours 26`: one Slack line for each lane silent past its expected run and each role silent past 26 hours.
4. Read only what you route: skim with `repo/usage/scripts/pick.py` and `shorten.py`, never paste whole outputs into chat.

## Proof

A find counts when its file exists with a link. A send counts only with the live system's confirmation. Hermes's and Codex's work is drafts until a person or an approved sender acts.
