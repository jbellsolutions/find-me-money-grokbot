# Trigger map

The loop is deterministic: schedules start every step (GrokBot takes no webhooks, so sweeps stand in for them), scripts move the data, and the agent makes only the judgment call inside. Gates stay on until replies prove good. Every cron is UTC (Eastern is UTC-5 in winter). **50 routines max per bot; this uses 29.** `tools/check.py` counts the Schedule rows below.

**Routine names are exact.** The name in the "Routine" column is the routine's title in Grok, its line in `context/routines-on.md` (`<name>: off|test|on`), and the `--routine` argument the guards and job scripts get. Change one, change all four.

**Writes to a live system** go through `guards/scripts/owner_guard.py check <system> --routine "<name>"`. Every system starts `live` in `context/owners.md`, so the bot reads and drafts and the live system keeps writing. Justin moves one system at a time to `bot`.

## The loop, step by step

| # | Step | Started by | Role | Judgment call | Human gate |
|---|---|---|---|---|---|
| 1 | Plan the day | Schedule `30 12 * * *` | lead | What matters today | None |
| 2 | Find leads in every lane: the Radar queue, Facebook groups, Craigslist, local businesses, Muse, wholesalers | Schedules (radar, muse, wholesale) | radar, muse, wholesale | Lead fit: keep, hold with a reason, or skip | Spend past rung 0 (spend guard) |
| 3 | File and draft the reply in the person's own thread | Schedule `0 */2 * * *` | sales | Copy: does it answer what they asked, in the charter voice? | Every reply until `public_reply: auto` |
| 4 | Outreach drafts: cold email, the Lead Storm queue, local businesses | Schedules (outreach) | outreach | Copy and who gets it | Every message until its type is `auto`; the sender stays the live system |
| 5 | Content: three simple viral pieces a day on the eight hooks | Schedule `0 15 * * *` | content | Funny, simple, relatable (score 4+ on each) | Each channel's first post; every post until `fmm_content_post: auto` |
| 6 | Read answers and sort them | Sweep `*/30 * * * *`, sort `15 */2 * * *` | sales | Interested, question, not now, opt-out, wrong person; the next message | Opt-outs recorded at once, no gate |
| 7 | Applications and the CRM stage | Schedule `45 */2 * * *` | sales | Is the stage true? | CRM writes: `pinnacle-ghl: bot` and `crm-writes: on` |
| 8 | Route: in-house or one partner; pass a deal for a percentage | Schedule `40 17 * * *` | partners | Partner choice with one line of reason | Every handoff is a proposal Justin approves |
| 9 | Wholesalers: fund them or pass their deal | Schedules (wholesale) | wholesale | Right who; buyer or lender match | Every message; contracts and fees are Justin's |
| 10 | In-house deal desk | Schedule `0 21 * * *` | loan-officer | Is the file complete? | Parked until Justin names a verified lender |
| 11 | Report | Schedule `30 23 * * *` | lead | Proof check on each number | None |

## Every schedule, by role

### lead

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 12 * * *` | Morning plan | A plan for each role in `daily/<date>/lead.md` and Slack |
| Schedule | `50 */3 * * *` | Watchdog | `beat.py status --hours 26`, Grok's run records; one Slack line per SILENT role or a send with no approved template |
| Schedule | `5 */2 * * *` | Scorecard | `bash repo/engine/jobs/fmm-scorecard.sh` (counts only, no model) |
| Schedule | `30 23 * * *` | Evening report | The day's numbers to Slack, one Notion row, `vault/Daily/<date>.md`, the scrubbed line for the single brain |

### radar

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 5 * * *` | Mine Facebook groups | `bash repo/engine/jobs/fmm-fbgroups.sh` (runs only when `fbgroups-lane: bot`; the live Hermes lane mines them now) |
| Schedule | `0 9 * * *` | Craigslist read | `craigslist-lane`: the business categories, rung 0 first; fit rows to the Radar or `requests/sales/` |
| Schedule | `0 10 * * 1-5` | Local businesses | `local-business-lane`: one metro, free Scrapebox places; the list to `requests/outreach/` |
| Schedule | `0 12 * * *` | Pick today's queue | `funding-radar`: asks from the last 2 days, high tier first, up to 10, through `guards.py send public_reply` |

### muse

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 14 * * *` | Muse morning session | `metamuse-operator` on the Muse Mac (`MUSE_COMPUTER`) by computer use: ask Muse for today's funding asks and partner openings (types only when `muse-app: bot`; otherwise screenshot and read) |
| Schedule | `0 20 * * *` | Muse collect | Read Muse's results and its drafted first touches into today's Muse file; drafts to `requests/justin/` |
| Schedule | `30 20 * * *` | Muse import | `metamuse-leads` `muse_to_radar.py`: the day's file into the Radar as `lane-muse` (when `funding-radar: bot`), else `requests/sales/` |

### content

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 15 * * *` | Daily content | `fmm-viral-content`: three pieces on three hooks, scored, to `requests/justin/` |
| Schedule | `0 16 * * 1` | Weekly content batch | Ten pieces across all eight hooks and last week's read |

### outreach

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 11 * * 1` | Deliverability check | `winnr-instantly`, read-only: inbox health, bounce and reply rates; a plan to `requests/justin/` if anything is off |
| Schedule | `0 17 * * 1-5` | Cold email drafts | Campaign copy and lists for Instantly (local businesses, wholesalers, partners), verified with `verify-emails`; drafts only while `cold-email-sender: live` |
| Schedule | `30 17 * * *` | Lead Storm feed | `lead-storm-handoff`: approved social targets and messages into `requests/lead-storm/`; read the VPS's reports |

### sales

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 */2 * * *` | File and draft | `bash repo/engine/jobs/fmm-cycle.sh` (CRM outbox only when `pinnacle-ghl: bot`) |
| Schedule | `*/30 * * * *` | Read answers | `bash repo/engine/jobs/fcm-job.sh triage "Read answers"` |
| Schedule | `15 */2 * * *` | Sort replies | The answers the sweep found: sort, draft the next message, record opt-outs |
| Schedule | `45 */2 * * *` | Applications | `bash repo/engine/jobs/fcm-job.sh sweep "Applications"` |
| Schedule | `20 16 * * *` | Day check | `bash repo/engine/jobs/fcm-job.sh day "Day check"` |
| Schedule | `0 23 * * *` | Loop close | `bash repo/engine/jobs/fmm-loop-close.sh` |

### partners

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `40 17 * * *` | Partner match | `lending-hub-distribution`: preview, then propose in-house or one partner with a reason |
| Schedule | `0 18,22,2 * * *` | Handoff watch | `bash repo/engine/jobs/fcm-job.sh watch "Handoff watch"` |
| Schedule | `0 19 * * 2,4` | Affiliate recruiting | `affiliate-manager`, `partner-fit-review`: ten new partner or affiliate candidates, researched, drafts only |
| Schedule | `30 19 * * *` | Affiliate replies | `affiliate-reply-triage`: sort partner and affiliate replies, draft the next step |

### loan-officer

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `0 21 * * *` | In-house desk | Any deal kept in-house: intake checklist, missing documents; writes "parked: no verified lender" until Justin names one |

### wholesale

| Kind | When | Routine | Does |
|---|---|---|---|
| Schedule | `30 13 * * *` | Wholesaler sweep | `wholesale-funding`: today's wholesaler rows (radar-cl output, Radar, groups, Muse), call cards |
| Schedule | `30 18 * * *` | Wholesale match | Funding need to the partner desk; deals to pass matched to buyer and lender partners; drafts |

## What changed from the v1 pack

- Nine roles instead of five, 29 routines instead of 14: muse, content, outreach and wholesale are new; reply desk and CRM desk are one **sales** role (one CRM writer); the shared jobs are the **lead** role.
- Every job script asks the owner guard before it writes, so the bot and the live systems (other agents, the Radar services, the CRM) never write the same thing.
- The Railway Radar's own cron still runs its daily sweep; the bot doesn't start it.
