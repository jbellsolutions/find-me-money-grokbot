# Find Me Money: the funding bot

One Grok bot for one business, [findmemoneyapp.com](https://findmemoneyapp.com). Justin, 2026-11-24: "100 leads, 100 conversations started a day... We have our direct leads with Lead Radar, and then the rest of it's just affiliates and referrals, and then we have our AEO SEO."

**Install or update:** one line each, in [INSTALL.md](INSTALL.md). **What only Justin can do:** [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md).

## How it works

The bot only orchestrates. Each routine hands one job to the **Claude Code CLI** (`tools/job.py`), with the **Codex CLI** as the second engine, so the work runs on Justin's subscriptions and not on Grok usage.

| Job | What it does | When (UTC) |
|---|---|---|
| [lead-radar](jobs/lead-radar.md) | Direct leads: people asking in public for funding; a draft answer each | 13:00 and 19:00 daily |
| [partnerships](jobs/partnerships.md) | Affiliates and referral partners: the lists, first messages, partnership emails. No direct-lead cold email | 16:00 weekdays |
| [communities](jobs/communities.md) | Skool and Whop groups: affiliates, referral partners, asks | 15:30 daily |
| [sales](jobs/sales.md) | The sales agent: every reply answered; GoHighLevel worked, with a pipeline for direct leads and one for affiliates and referral partners | 12:15, 15:15, 18:15, 21:15 daily |
| [content](jobs/content.md) | Six pieces a day. Words by the CLI, talking videos by HeyGen | 12:00 and 18:00 daily |
| [aeo-seo](jobs/aeo-seo.md) | Found on Google and named in AI answers: the read, a page and a video brief | 14:00 Tuesday and Friday |
| [plan](jobs/plan.md), [report](jobs/report.md) | The two numbers first; jobs counted by engine | 11:30; 23:30 |

## What is in the pack

| | |
|---|---|
| `MASTER-PROMPT.md`, `roles/` | The bot's memory |
| `jobs/` | One brief per job, which the CLI works from |
| `skills/claude-code-cli/`, `skills/content-tools/` | The two hard rules: every task through the Claude Code CLI; content by the CLI and HeyGen |
| `tools/job.py` | Hands a job to Claude Code, then Codex; logs which engine carried it |
| `tools/ghl.py` | GoHighLevel: reads freely, writes only when the switches allow, otherwise saves the proposal |
| `tools/heygen.py` | HeyGen renders, up to the number of videos a day Justin approved |
| `tools/update.py` | Updates an older install: deletes the referral site's things, keeps Justin's answers |
| `campaigns/find-me-money/` | The message, the plan, the settings |
| `agents/`, `skills/` | How each function works; the money hooks; the CRM's stages and tags |
| `guards/`, `convlog/` | The switches' checks; the log of every draft, send and reply |

## Not in this bot

The Referral Connection site (its own agent: [referral-connection-grokbot](https://github.com/jbellsolutions/referral-connection-grokbot)), SpeakerAgent, and cold email to direct leads.
