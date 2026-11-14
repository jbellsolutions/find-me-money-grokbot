# Trigger map

**GrokBot is the orchestrator and automator; the work runs elsewhere** (Justin, 2026-11-13: "grokbot is just the orchestrator and automator", "just also think of usage. always"). The bot plans, sends work orders, judges, queues approvals and reports. The doing runs on:

| Executor | Runs | Why there |
|---|---|---|
| **Hermes on the Mac** (the `find-me-money` profile, its own cheap model) | Facebook groups by theme, Marketplace and Muse (computer use on the Mac itself), Craigslist, local places, wholesaler call cards; plus the profile's own 12 jobs: the reply cycle, the 30-minute reply sweep, reply sorting, the lead sweep, the day check, the handoff watch, the scorecard, loop close | Browser, Muse and sign-ins live on that Mac; high-frequency sweeps cost Grok nothing there |
| **Codex CLI** (on this bot's computer, its own subscription) | Bulk first drafts (no web search in `codex exec`, so research stays on Hermes) | Moves that spend off Grok's weekly allowance (usage-mastery trick 29) |
| **GrokBot** (this bot) | 12 routines, about 13 runs a day | Judgment only: what to work, lead fit on the shortlist, the best copy, partner choice, what to tell Justin |

Which executor runs which lane is `context/executors.md`; the bridge is `engine/hermes_bridge.py` (one Orgo call per put or pull). Every cron is UTC. **50 routines max per bot; this uses 12.** `tools/check.py` counts the Schedule rows below. Routine names are exact: the Grok title, the line in `context/routines-on.md`, and the `--routine` the guards get.

## The loop, step by step

| # | Step | Started by | Runs on | Judgment call (Grok) | Human gate |
|---|---|---|---|---|---|
| 1 | Plan the week's niches and places | Schedule `0 11 * * 1` | GrokBot | Which niches, group themes, Marketplace categories, metros and creators this week, from last week's answers per lane | None |
| 2 | Send the day's work orders | Schedule `0 12 * * *` | GrokBot → Hermes / Codex | None: the week's plan becomes orders | Spend past free rungs (spend guard) |
| 3 | Mine, read, research, draft | The worker's 15-minute inbox job | Hermes on the Mac, Codex | None (Hermes's own model grades and drafts) | Read only; nothing posts |
| 4 | Pull results, route them, watchdog | Schedule `0 15,19,23 * * *` | GrokBot | None: files to `requests/<role>/`; alarms on silent lanes | None |
| 5 | Today's reply queue | Schedule `0 13 * * *` | GrokBot | Lead fit on the shortlist; the best draft per ask | Every reply until `public_reply: auto` |
| 6 | Content | Schedule `30 15 * * *` | GrokBot (ideas may come from Codex) | Funny, simple, relatable: score 4+ | First post per channel; every post until `fmm_content_post: auto` |
| 7 | Sales escalations | Schedule `15 14,20 * * *` | GrokBot (Hermes sorts and sweeps) | The replies Hermes marked "needs a person": next message, stage | Every message; CRM writes need `pinnacle-ghl: bot` |
| 8 | Outreach drafts | Schedule `0 17 * * 1-5` | GrokBot (Codex writes the bulk drafts) | The best variants; who gets which | Every message type; senders stay live systems |
| 9 | Partners and affiliates | Schedule `40 17 * * *` | GrokBot | In-house or one partner; which creators, coaches and houses to approach | Every handoff and partner message |
| 10 | Wholesale | Schedule `30 18 * * *` | GrokBot (Hermes builds call cards) | Funding need or deal pass; the match | Every message; contracts are Justin's |
| 11 | In-house desk | Schedule `0 21 * * 1,3,5` | GrokBot | File complete? | Parked until a verified lender |
| 12 | Report | Schedule `30 23 * * *` | GrokBot | Proof check on each number | None |

## Every schedule, by role

### lead

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 12 * * *` | Morning plan | Today's plan per role from the week's plan, yesterday's results and Justin's queue; Slack |
| Schedule | `30 23 * * *` | Evening report | Numbers to Slack, one Notion row, `vault/Daily/<date>.md`, the scrubbed single-brain line; Mondays add the usage audit (`usage/AUDIT.md`) |

### worker

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 12 * * *` | Dispatch | `hermes_bridge.py put <lane> '<args>'` for each item in this week's plan (`context/week-plan.md`); orders to Codex run here at once |
| Schedule | `0 15,19,23 * * *` | Pull | `hermes_bridge.py pull`, then route each result file to `requests/<role>/`; `hermes_bridge.py status` and `beat.py status`: one Slack line per silent lane or role |

### radar

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 11 * * 1` | Niche rotation | `lead-map`: score last week's lanes by answers per find; write `context/week-plan.md` (niches, group themes, Marketplace categories, metros, creators, coaches, affiliate houses) |
| Schedule | `0 13 * * *` | Pick today's queue | `funding-radar` plus the worker's finds: up to 10 fresh asks, the best draft each, through `guards.py send public_reply` |

### content

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 15 * * *` | Daily content | `fmm-viral-content`: three pieces on three hooks; Mondays also the weekly read and next week's hook rotation |

### outreach

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 17 * * 1-5` | Outreach drafts | Cold email (Instantly) and the Lead Storm queue from the worker's lists and Codex's drafts; Mondays also the read-only deliverability check |

### sales

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `15 14,20 * * *` | Sales desk | Read the Hermes profile's sorted replies and loop list; draft the next message for each "needs a person"; propose stages |

### partners

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `40 17 * * *` | Partner desk | Partner match for applicants; affiliate and partner replies; on Tuesdays and Thursdays, pick this week's creators, coaches and affiliate houses from the worker's research and draft first touches |

### loan-officer

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 21 * * 1,3,5` | In-house desk | Any deal kept in-house; "parked: no verified lender" until Justin names one |

### wholesale

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 18 * * *` | Wholesale desk | The worker's call cards: funding need to partners, deals to pass matched, first-touch drafts |

## Usage, before and after

| | v1 (Nov 12) | v2 |
|---|---|---|
| Grok routines | 29 | 12 |
| Grok runs a day | about 130 (the 30-minute and 2-hourly sweeps) | about 13 |
| Where the sweeps run | Grok | Hermes on the Mac (its own 12 jobs, already installed and paused) |
| Where research and bulk drafts run | Grok | Hermes (research), Codex CLI or Hermes (drafts) |
