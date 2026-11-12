---
name: funding-radar
description: Read today's funding asks from the Funding Lead Radar, decide lead fit (keep, hold with a reason, skip), and build today's reply queue from asks in the last 2 days, high tier first. Also imports a lane's file (Muse, Facebook groups) into the Radar. Use for "what did the Radar find", "today's reply queue", "pick today's 10", "import Muse's file".
---

# The Funding Radar

Live at `RADAR_URL` (set at intake), signed in with `RADAR_PASSWORD`. It runs its own daily sweep; the bot does not start it and never redeploys it.

## The calls

| Need | Call |
|---|---|
| The desk: asks and their reply state | `GET /api/replies` (paged) |
| Mark an ask | `POST /api/replies/{id}` with `drafted`, `replied`, `skipped` or `won` |
| Import a lane's finds | `POST /api/leads/import` (each row: platform, url, parent_url, author_handle, need, quote, lane tag such as `lane-muse` or `lane-fbgroups`) |
| Prospects (partners, not borrowers) | `GET /api/prospects` |

Each signal has `platform`, `url`, `parent_url`, `author_handle`, `author_url`, `tier` (high, medium, low), `confidence`, `need` and `quote`.

## Lead fit

Keep a real business or investor funding ask, posted in the last 7 days, that we can answer in its own thread. Hold (with the reason): a mortgage or refinance on a home someone lives in, for personal use (Justin routes those), anything unclear. Skip: sellers, resolved posts, spam, our own posts.

## Today's queue

Asks from the last 2 days, high tier first, newest first, at most the `public_reply` daily cap (10 to start). Never the backlog: asks older than 7 days are not worked.

## Lanes

- **Facebook groups** (`engine/fbgroups_miner.py`, through One API, 100 reads a day cap by treg): imports as `lane-fbgroups`.
- **Muse** (the `metamuse-leads` skill): one file a day, imported as `lane-muse`. On trial: after 100 imported finds, compare answers per find with the Radar's.
- Credits: every paid read goes through `guards.py spend <pool>` first. Under one day's burn, say so in the report.
