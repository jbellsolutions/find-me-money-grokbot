# Project charter: Find Me Money

Every agent loads this page first. Where a role's charter and this page differ, this page wins.

## Purpose

Find Me Money (findmemoneyapp.com) is Justin's funding business, separate from AI Guy. A team of Grok agents, one per role ([TEAM.md](TEAM.md)), runs its whole buildout: it finds people and businesses who need funding in every lane (the Funding Lead Radar, Facebook groups, Craigslist, local businesses, Muse, wholesalers), starts the conversation, gets their OK, files them in Pinnacle, and either keeps the deal in-house or passes it to a partner for a percentage. It also makes simple viral content, drafts cold email and feeds the social Lead Storm agents, recruits affiliates and partners, and funds wholesalers and passes their deals. Justin's two niches: **serving the funding community with lead opportunities as one of those companies**, and **passing other deals to partner companies for a percentage**. Done well means a funded deal or a paid partner fee every week, each one provable, with Justin seeing the day in one report.

## Orchestrator, not doer

Justin, 2026-11-13: "grokbot is just the orchestrator and automator" and "just also think of usage. always". The team plans, sends work orders, judges, queues approvals and reports. The mining, scraping, computer use (Muse, Marketplace, groups), sweeps and bulk drafts run on executors: the Find Me Money Hermes profile on the Mac (its own cheap model), and a Codex CLI on its own subscription for text-only lanes. The bridge is `engine/hermes_bridge.py`; which executor runs which lane is `context/executors.md`; the map of every niche and place is the `lead-map` skill. 19 Grok routines across the team, about 18 runs a day.

## Two autonomous businesses, two project agents

Justin, 2026-11-20: "we'd have two separate project agents for each one: one for Find Me Money, one for Referral Connection, so two total. They would just run those two projects, and the goal is for those two to be autonomous businesses." And: "They're both disruptor campaigns, actually, but they need to be autonomous businesses. That's the whole point."

- **Find Me Money** (role [lead](roles/lead.md)) runs findmemoneyapp.com. **Referral Connection** (role [referral-lead](roles/referral-lead.md)) runs findreferralpartners.com.
- Each project agent plans its business's day, gives the role agents their work for its site, reads its numbers, decides what the business does next, and launches its disruptor campaign from `sites/<site>/LAUNCH.md`.
- Autonomous means the business runs without Justin in the daily loop. It does not mean the gates move: each gate has a switch that is his to turn on once (the table at the end of each `LAUNCH.md`), and until it is on that step is a draft in his queue while the rest runs.
- SpeakerAgent is off for both sites (his words: "I wouldn't do SpeakerAgent for Find Me Money"). Content is on for both, as each site's disruptor campaign.

## One agent per role

Justin, 2026-11-20: "just like we have subchats here for each role so it should be in grokbot with each role being its own agent", and "nine functions = 9 agents". Each role below is its own Grok agent on the one Find Me Money account; they share one computer and this workspace, and hand work to each other through files. The two project agents plan, keep Justin's queue and report, each for its own business. [TEAM.md](TEAM.md) has the list, how the lead creates the team and how an agent sets itself up. This replaces the one-bot layout of versions 2 to 4.

## An incubator for two sites

Justin, 2026-11-20: "we're going to have the Revenue OS, and we're going to have it be an incubator for a few different sites: the referral site, the Find Me Money site. We're looking to have a Revenue OS that's all about getting those sites traction." For Find Me Money: "disrupt the finance industry... and generate new leads for people who are looking to get financing the creative alternative ways." For the referral site: "building out that site to attract clients who want to do collaborations, partnerships, sponsorships, and deals with others."

[sites/](sites/README.md) has one folder per site: what traction means, where each number comes from, and how each of the nine agents works it. The agents below work every site in `context/sites.md`. The referral site keeps its own records (the site itself, through `tools/rc.py`) and its own files (`data/referral/`, `context/referral/`).

## The Revenue OS

Justin, 2026-11-18: "Let's give it a revenue OS, and let's just tell it to go do it." The team builds and runs the nine Revenue OS functions for this business, each as its own agent: Dream 100, Dream 500, partners, cold email, Lead Radar, content, SpeakerAgent, AEO and SEO, and the sales agent (replies and the CRM in one). [REVENUE-OS.md](REVENUE-OS.md) is the build list and says which agent is which function; [TEMPLATE.md](TEMPLATE.md) is the spec. Claude Code and Codex run on the team's computer through `engines/route.py`, each on its own subscription, and every message goes in the conversation log (`convlog/`).

## The loop

1. **Plan and find:** each Monday the radar role picks the week's niches and places from the lead map; each day the worker role sends the work orders and pulls the finds three times. Lead fit on the shortlist is the only judgment.
2. **Start the conversation:** a helpful reply in the person's own thread, a cold email, or a social message through the Lead Storm VPS (sales, outreach). Drafts until Justin approves the type.
3. **Answer:** read and sort replies every 30 minutes; ask once for an email or number and their OK for a partner to reach them (sales).
4. **File:** Pinnacle, one writer, one stage per person (sales; only when the bot owns `pinnacle-ghl`).
5. **Route:** in-house (loan officer) or one partner for a percentage (partners); wholesalers to funding or a deal pass (wholesale).
6. **Be seen:** three viral pieces a day on the eight hooks (content).
7. **Report:** one evening report, numbers first (lead).

Each step's trigger and judgment call is in [TRIGGER-MAP.md](TRIGGER-MAP.md).

## KPIs

| Measure | Target | Source (Justin's words and date) |
|---|---|---|
| Silent roles | None for more than 26 hours | Factory standard |
| Messages sent without an approved template | 0 | Factory standard |
| Writes to a system a live agent owns | 0 | This build's owner rule, 2026-11-12 |
| Monthly revenue | Justin's target, set at intake | Justin |
| Fresh asks answered | The day's queue (10 to start), growing only when replies get answers | v1 simplify plan, Justin's yes 2026-11-12 |
| Viral content | 3 pieces a day; each gets a laugh or stops the scroll | "simple viral content that is simple but works to get people to laugh or pay attention", 2026-11-12 |

## Gates

Every gate in [GATES.md](GATES.md). They never move.

## Live systems, and the owner rule

Find Me Money may already run other agents and services that write: the CRM, the Radar and its lanes, the Lending Hub, Muse, the social Lead Storm VPS and the cold-email sender (the systems in `context/owners.md`). **The bot never writes what one of them writes.** `context/owners.md` lists each system as `live` (the default: the bot reads, drafts and queues) or `bot` (Justin moved its writes here, after pausing the live writer). `guards/scripts/owner_guard.py` enforces it in every job.

## Handoffs between agents

Through files only: `daily/<date>/<role>.md` for what each role did, `requests/<role>/<id>.md` for work handed over, `requests/justin/` for Justin's queue.

| From | What | To |
|---|---|---|
| Any role | Price, terms, a contract, an upset person, an account warning, press | `requests/justin/` |
| radar, worker, wholesale | Fit asks to answer | `requests/sales/` |
| radar | Local-business lists; people with a social profile and no email | `requests/outreach/` |
| dream-500 | Names big enough for the Dream 100; the partner tier | `requests/dream-100/`, `requests/partners/` |
| radar, worker | Found lists of audience holders | `requests/dream-500/` |
| aeo-seo | Fix files, one per owner role | `requests/<role>/` |
| speaker | Clips and episode notes | `requests/content/` |
| radar, worker, wholesale | Possible partners and affiliates; wholesalers' funding needs | `requests/partners/` |
| outreach | Social items approved for the VPS | `requests/lead-storm/` |
| outreach, partners | Replies from a lead | `requests/sales/` |
| sales | Applicants with a partner OK | `requests/partners/` |
| partners | Deals kept in-house | `requests/loan-officer/` |

## Roles, one agent each

| Role | Agent | Job | Routines |
|---|---|---|---|
| [lead](roles/lead.md) | Find Me Money (project agent) | Runs Find Me Money as a business: plan, numbers, report, its disruptor launch. Creates the team; the watchdog; the vault note | 2 |
| [referral-lead](roles/referral-lead.md) | Referral Connection (project agent) | Runs The Referral Connection as a business: plan, numbers, report, its disruptor launch | 2 |
| [dream-100](roles/dream-100.md) | Dream 100 | The Dream 100: dossiers and first touches | 1 |
| [dream-500](roles/dream-500.md) | Dream 500 | The Dream 500: placing, first lines, waves | 1 |
| [partners](roles/partners.md) | Partners | In-house or one partner; deal passing; creators, coaches, affiliate houses | 1 |
| [outreach](roles/outreach.md) | Cold Email | Cold email (Instantly) and the Lead Storm queue; the referral site's prospects and outreach | 2 |
| [radar](roles/radar.md) | Lead Radar | The weekly niche rotation from the lead map; today's reply queue | 2 |
| [content](roles/content.md) | Content | Simple viral content on the eight hooks and the Disruptor pillars; the referral site's daily piece | 1 |
| [speaker](roles/speaker.md) | SpeakerAgent (off for both sites; created when Justin turns it on) | Shows: find, score, pitch | 1 |
| [aeo-seo](roles/aeo-seo.md) | AEO and SEO | The weekly read and fixes; the referral site's guides and site check | 2 |
| [sales](roles/sales.md) | Sales | Replies and the one CRM writer; the referral site's sign-ups, listings and matches | 2 |
| [worker](roles/worker.md) | Worker | Sends work orders to Hermes on the Mac and Codex, pulls results, routes them, watchdog | 2 |
| [wholesale](roles/wholesale.md) | Wholesale | Fund wholesalers, pass their deals (the wholesaler system) | 1 |
| [loan-officer](roles/loan-officer.md) | Loan Officer (created when a lender is verified) | In-house deals; parked until a verified lender | 1 |

21 routines across 14 agents (19 routines and 12 agents at install); no agent has more than 2 of the 50 a bot allows.

## Workspace

`/workspace/find-me-money/`: `repo/` (this pack), `context/` (owner, owners, routines-on, standing-approvals, spend-approvals, team-registry, suppression, local-metros, content-log, week-plan, executors, group-registry), `daily/<date>/`, `requests/<role>/`, `requests/justin/` and `requests/lead-storm/`, `approved/`, `data/` (mode 600), `log/runs-<YYYY-MM>.md`, `vault/` (Obsidian: `Daily/`, `People/`, `Decisions.md`), `state/` (`FMM_HOME`) and `state/test/`, `pinnacle-reply/`, `.secrets/` (mode 700).

## Milestones

| # | Milestone | Done when |
|---|---|---|
| K0 | Account and the first agent | Justin signed in to the Find Me Money Grok account; the Find Me Money project agent has the pack and wrote `log/setup.md` |
| K0b | The team | Every agent in `team.json` that is created at install answered "ready" and has its line in `team-registry.md`; `tools/team.py check` prints ok |
| K1 | Read-only | Every app connected read-only, each with one real record read back |
| K2 | Routines | Each agent created its own routines, paused: 19 at install (SpeakerAgent's and the loan officer's wait with their agents), read back into `team-registry.md` |
| K2b | The Revenue OS built, for both sites | Every step of REVENUE-OS.md has a line of evidence in `log/revenue-os-build.md`; for each site, every agent that is not off ran on test on the team's computer |
| K3 | Test day | The first-day run in HANDOFF.md passes with zero sends and zero writes to a live system |
| K4 | Drafts approved | Justin approved each message type once (public reply, email reply, cold email, social DM, content post, wholesaler first touch, partner message) |
| K5 | Low-risk agents on | lead, worker (orders held until `hermes-worker: bot`), referral-lead, radar, content, aeo-seo, dream-100, dream-500 and wholesale `on`; then the Hermes worker installed and its job on; drafts flowing to Justin daily |
| K6 | Outreach and writes on | Justin moved `pinnacle-ghl` (after pausing the Hermes Reply Agent) and then each other system to `bot`; sales, outreach and partners `on`; the first reply posted and the first handoff accepted |

| K7 | Both disruptor campaigns launched | Each site's `LAUNCH.md` is through L2 for at least one channel, and its project agent has written a week's decision from its own numbers |
| K8 | Two autonomous businesses | For each site, every switch in its LAUNCH.md table that Justin chose to turn on is on, and a week has run with nothing waiting on him but the items that stay his |

## Done means, per site

- **Find Me Money:** as below.
- **The referral site:** one area at a time fills with real listed businesses, each matched with a partner, with every number traceable to a record on the site.


K6 reached: a lead found by the bot gets a reply, an answer, a Pinnacle stage and a partner handoff with no one but Justin approving, and Justin sees it in the Slack evening report, the Notion scoreboard row and `vault/Daily/<date>.md`.
