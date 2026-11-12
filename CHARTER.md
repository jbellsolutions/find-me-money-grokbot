# Project charter: Find Me Money

The bot loads this page first. Where a role's charter and this page differ, this page wins.

## Purpose

Find Me Money (findmemoneyapp.com) is Justin's funding business, separate from AI Guy. This one Grok bot runs its whole buildout: it finds people and businesses who need funding in every lane (the Funding Lead Radar, Facebook groups, Craigslist, local businesses, Muse, wholesalers), starts the conversation, gets their OK, files them in Pinnacle, and either keeps the deal in-house or passes it to a partner for a percentage. It also makes simple viral content, drafts cold email and feeds the social Lead Storm agents, recruits affiliates and partners, and funds wholesalers and passes their deals. Justin's two niches: **serving the funding community with lead opportunities as one of those companies**, and **passing other deals to partner companies for a percentage**. Done well means a funded deal or a paid partner fee every week, each one provable, with Justin seeing the day in one report.

## The loop

1. **Find:** every lane reads (radar, muse, wholesale roles). Lead fit is the only judgment.
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

## Handoffs between roles

Through files only: `daily/<date>/<role>.md` for what each role did, `requests/<role>/<id>.md` for work handed over, `requests/justin/` for Justin's queue.

| From | What | To |
|---|---|---|
| Any role | Price, terms, a contract, an upset person, an account warning, press | `requests/justin/` |
| radar, muse, wholesale | Fit asks to answer | `requests/sales/` |
| radar | Local-business lists; people with a social profile and no email | `requests/outreach/` |
| radar, muse, wholesale | Possible partners and affiliates; wholesalers' funding needs | `requests/partners/` |
| outreach | Social items approved for the VPS | `requests/lead-storm/` |
| outreach, partners | Replies from a lead | `requests/sales/` |
| sales | Applicants with a partner OK | `requests/partners/` |
| partners | Deals kept in-house | `requests/loan-officer/` |

## Roles

| Role | Job | Routines |
|---|---|---|
| [lead](roles/lead.md) | Plans the day, watchdog, scorecard, evening report, vault note, Justin's queue | 4 |
| [radar](roles/radar.md) | Lead fit: the Radar queue, Facebook groups, Craigslist, local businesses | 4 |
| [muse](roles/muse.md) | Runs MetaMuse on the Orgo Mac by computer use; the daily Muse file | 3 |
| [content](roles/content.md) | Simple viral content on the eight hooks | 2 |
| [outreach](roles/outreach.md) | Cold email (Instantly) and the Lead Storm queue | 3 |
| [sales](roles/sales.md) | The sales agent: replies, answers, capture, the Pinnacle stage, applications | 6 |
| [partners](roles/partners.md) | In-house or one partner; deal passing for a percentage; affiliates | 4 |
| [loan-officer](roles/loan-officer.md) | In-house deals; parked until a verified lender | 1 |
| [wholesale](roles/wholesale.md) | Fund wholesalers, pass their deals | 2 |

29 routines of the 50 a bot allows.

## Workspace

`/workspace/find-me-money/`: `repo/` (this pack), `context/` (owner, owners, routines-on, standing-approvals, spend-approvals, team-registry, suppression, local-metros, content-log), `daily/<date>/`, `requests/<role>/`, `requests/justin/` and `requests/lead-storm/`, `approved/`, `data/` (mode 600), `log/runs-<YYYY-MM>.md`, `vault/` (Obsidian: `Daily/`, `People/`, `Decisions.md`), `state/` (`FMM_HOME`) and `state/test/`, `pinnacle-reply/`, `.secrets/` (mode 700).

## Milestones

| # | Milestone | Done when |
|---|---|---|
| K0 | Account and bot | Justin signed in to the Find Me Money Grok account; the bot has the pack and wrote `log/setup.md` |
| K1 | Read-only | Every app connected read-only, each with one real record read back |
| K2 | Routines | All 29 routines created and paused, read back into `team-registry.md` |
| K3 | Test day | The first-day run in HANDOFF.md passes with zero sends and zero writes to a live system |
| K4 | Drafts approved | Justin approved each message type once (public reply, email reply, cold email, social DM, content post, wholesaler first touch, partner message) |
| K5 | Low-risk lanes on | lead, radar, muse (read-only), content and wholesale `on`; drafts flowing to Justin daily |
| K6 | Outreach and writes on | Justin moved `pinnacle-ghl` (after pausing the Hermes Reply Agent) and then each other system to `bot`; sales, outreach and partners `on`; the first reply posted and the first handoff accepted |

## Done means

K6 reached: a lead found by the bot gets a reply, an answer, a Pinnacle stage and a partner handoff with no one but Justin approving, and Justin sees it in the Slack evening report, the Notion scoreboard row and `vault/Daily/<date>.md`.
