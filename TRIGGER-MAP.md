# Trigger map

**GrokBot is the orchestrator and automator; the work runs elsewhere** (Justin, 2026-11-13: "grokbot is just the orchestrator and automator", "just also think of usage. always"). The bot plans, sends work orders, judges, queues approvals and reports. The doing runs on:

| Executor | Runs | Why there |
|---|---|---|
| **Hermes on the Mac** (the `find-me-money` profile, its own cheap model) | Facebook groups by theme, Marketplace and Muse (computer use on the Mac itself), Craigslist, local places, wholesaler call cards; plus the profile's own 12 jobs: the reply cycle, the 30-minute reply sweep, reply sorting, the lead sweep, the day check, the handoff watch, the scorecard, loop close | Browser, Muse and sign-ins live on that Mac; high-frequency sweeps cost Grok nothing there |
| **Codex CLI** (on the team's computer, its own subscription) | Bulk first drafts (no web search in `codex exec`, so research stays on Hermes) | Moves that spend off Grok's weekly allowance (usage-mastery trick 29) |
| **The Grok team** (two project agents and one agent per role) | 21 routines, 19 at install, about 20 runs a day | Judgment only: what to work, lead fit on the shortlist, the best copy, partner choice, what to tell Justin |

Which executor runs which lane is `context/executors.md`; the bridge is `engine/hermes_bridge.py` (one Orgo call per put or pull). Every cron is UTC. **One agent per role** (Justin, 2026-11-20: "each role being its own agent"; [TEAM.md](TEAM.md)): and two project agents, one per business (Justin, 2026-11-20). 14 agents on one account, sharing one computer: 12 at install, SpeakerAgent and the loan officer later. 21 routines in all, at most 2 on one agent of the 50 a bot allows. The team runs two sites ([sites/](sites/README.md)): a routine works every site in `context/sites.md`, and three routines are the referral site's own. `tools/check.py` counts the Schedule rows below. Routine names are exact: the Grok title, the line in `context/routines-on.md`, and the `--routine` the guards get.

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
| 13 | Dream 100 and Dream 500 | Schedule `10 16 * * 1-5` (Dream 100), `40 16 * * 1-5` (Dream 500) | GrokBot | Who is worth a dossier; the first touch | Every first touch |
| 14 | Shows (off for both sites) | Schedule `20 16 * * 2,4` | GrokBot (Codex scores fit) | Which shows to open; the pitch | Every pitch |
| 15 | AEO and SEO read | Schedule `0 14 * * 2` | GrokBot (Codex judges the gaps) | Which fix goes to which role | Tracking-tool spend; site changes are pull requests |
| 16 | The referral site: intake, listings, matches, introductions | Schedule `45 14,21 * * *` | GrokBot | Real business or spam; who fits whom | Every introduction; site writes need `referral-site: bot` |
| 17 | The referral site: prospects and outreach | Schedule `30 16 * * 1-5` | GrokBot | Does this business have customers it can reach; the one reason it would want a partner | Every message |
| 18 | The referral site: guides | Schedule `30 14 * * 3,5` | GrokBot (Claude Code drafts) | Which question is worth a page; is every claim true | Every published guide |
| 19 | The referral business: its plan and its report | Schedule `40 12 * * *`, `40 23 * * *` | GrokBot | What the business does next, from its own numbers | None |

## Every schedule, by agent

One agent per role ([TEAM.md](TEAM.md), `team.json`). An agent creates and owns only the routines in its own section, and each routine's prompt starts `Role: <role>.`

### lead

Agent: **Find Me Money**, the project agent for Find Me Money.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 12 * * *` | Morning plan | Find Me Money's plan for the day, from the next open step of `sites/find-me-money/LAUNCH.md`, yesterday's results and Justin's queue, written to each role agent's `requests/<role>/find-me-money-plan-<date>.md`; Slack |
| Schedule | `30 23 * * *` | Evening report | Find Me Money's numbers to Slack, one Notion row, the scrubbed single-brain line; for the whole team the watchdog, `vault/Daily/<date>.md` and the conversation log's day close (`convlog/gate.py day`); Mondays add the week's decision and the usage audit (`usage/AUDIT.md`) |

### referral-lead

Agent: **Referral Connection**, the project agent for The Referral Connection.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `40 12 * * *` | Referral plan | The referral site's plan for the day, from `rc.py stats`, the next open step of `sites/referral-connection/LAUNCH.md` and yesterday's results, written to each role agent's `requests/<role>/referral-connection-plan-<date>.md`; Slack |
| Schedule | `40 23 * * *` | Referral report | The site's numbers (sign-ups by source and area, listings, matches by stage, guides) to Slack, one Notion row, its section of `vault/Daily/<date>.md`; Mondays add the week's decision |

### dream-100

Agent: **Dream 100**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `10 16 * * 1-5` | Dream 100 desk | Candidates scored with `agents/dream-100/dream100.py`, a dossier and a first-touch draft for the next few; follow-ups that are due |

### dream-500

Agent: **Dream 500**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `40 16 * * 1-5` | Dream 500 desk | `agents/dream-500/dream500.py place` on found lists (the 100 tier to `requests/dream-100/`, the partner tier to `requests/partners/`); first lines for the next wave; follow-ups that are due |

### partners

Agent: **Partners**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `40 17 * * *` | Partner desk | Partner match for applicants; affiliate and partner replies; on Tuesdays and Thursdays, pick this week's creators, coaches and affiliate houses from the worker's research and draft first touches |

### outreach

Agent: **Cold Email**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 17 * * 1-5` | Outreach drafts | Cold email (Instantly) and the Lead Storm queue from the worker's lists and Codex's drafts; Mondays also the read-only deliverability check |
| Schedule | `30 16 * * 1-5` | Referral outreach | `prospect-finder`: local businesses in the launch area into `data/prospects.csv`; `outreach-drafts`: one-to-one drafts and replies, each link tagged with its source |

### radar

Agent: **Lead Radar**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 11 * * 1` | Niche rotation | `lead-map`: score last week's lanes by answers per find; write `context/week-plan.md` (niches, group themes, Marketplace categories, metros, creators, coaches, affiliate houses) |
| Schedule | `0 13 * * *` | Pick today's queue | `funding-radar` plus the worker's finds: up to 10 fresh asks, the best draft each, through `guards.py send public_reply`; the day's finds are judged with `agents/lead-radar/radar.py score` (Codex) and kept leads go to the sales agent through the log |

### content

Agent: **Content**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 15 * * *` | Daily content | `fmm-viral-content`: three pieces on three hooks, drafted through `agents/content/content.py draft` (Claude Code); one piece a day for the referral site; Mondays also the weekly read and next week's hook rotation |

### speaker

Agent: **SpeakerAgent**. Off for both sites (Justin, 2026-11-20); the agent and this routine are created only when he turns it on.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `20 16 * * 2,4` | Speaker desk | `agents/speaker/speaker.py find`, `score`, `draft`, `due`: shows found and scored, pitches and follow-ups as drafts; nothing is drafted until the speaker profile is in |

### aeo-seo

Agent: **AEO and SEO**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 14 * * 2` | Weekly AEO read | `agents/aeo-seo/aeo.py pull`, `judge`, `read`: leads, front-page terms, the share of AI answers that named us, one fix file per owner role. Until the tracking tool's key is in: `cost` only, and the panel and terms files. Both sites; for the referral site also `site-check` and `rc.py stats` by source |
| Schedule | `30 14 * * 3,5` | Referral guides | `guide-publisher`: one brief, one draft, saved to the referral site as a draft (`rc.py page-put`); a brief for the site's repo when a page is missing |

### sales

Agent: **Sales**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `15 14,20 * * *` | Sales desk | Read the Hermes profile's sorted replies and loop list; draft the next message for each "needs a person"; propose stages. Sorts on Codex (`route.py --agent sales-crm`), reads the person's vault note first, logs every reply and draft with `convlog/gate.py` |
| Schedule | `45 14,21 * * *` | Referral desk | `directory-desk`: sign-ups, connection requests and removals read from the site, real sign-ups listed; `matchmaker`: pairs matched and recorded, introductions drafted, each pair followed to a paid campaign |

### worker

Agent: **Worker**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 12 * * *` | Dispatch | `hermes_bridge.py put <lane> '<args>'` for each item in this week's plan (`context/week-plan.md`); orders to Codex run here at once |
| Schedule | `0 15,19,23 * * *` | Pull | `hermes_bridge.py pull`, then route each result file to `requests/<role>/`; `hermes_bridge.py status` and `beat.py status`: one Slack line per silent lane or agent |

### wholesale

Agent: **Wholesale**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 18 * * *` | Wholesale desk | The worker's call cards: funding need to partners, deals to pass matched, first-touch drafts |

### loan-officer

Agent: **Loan Officer (created when Justin names a verified lender)**.

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 21 * * 1,3,5` | In-house desk | Any deal kept in-house; "parked: no verified lender" until Justin names one |

## Usage, before and after

| | v1 (Nov 12) | v2 | v3 (the Revenue OS) | v4 (two sites) | v5 (one agent per role) | v6 (two project agents) |
|---|---|---|---|---|---|---|
| Grok routines | 29 | 12 | 15 | 18 | 19, across 13 agents | 21, across 14 agents (19 at install) |
| Grok runs a day | about 130 (the 30-minute and 2-hourly sweeps) | about 13 | about 14 | about 17 | about 18 | about 20 |
| Where the sweeps run | Grok | Hermes on the Mac (its own 12 jobs, already installed and paused) | Hermes on the Mac | Hermes on the Mac | Hermes on the Mac | Hermes on the Mac |
| Where research and bulk drafts run | Grok | Hermes (research), Codex CLI or Hermes (drafts) | Hermes (research); Claude Code and Codex on the bot's computer, through `engines/route.py` | As v3 | As v3 | As v3 |
