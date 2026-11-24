# Find Me Money: the funding bot

One Grok bot for one business, [findmemoneyapp.com](https://findmemoneyapp.com). Justin, 2026-11-24: "keep the Find Me Money one separate and on its own. That way, it's just a funding Grok Bot."

**Install:** one line, in [INSTALL.md](INSTALL.md). **What only Justin can do:** [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md).

## How it works

The bot only orchestrates. Each routine hands one job to the **Claude Code CLI** (`tools/job.py`), with the **Codex CLI** as the second engine, so the work runs on Justin's subscriptions and not on Grok usage.

| Job | What it does | When (UTC) |
|---|---|---|
| [content](jobs/content.md) | The main purpose: six pieces a day from the message | 12:00 and 18:00 daily |
| [lead-radar](jobs/lead-radar.md) | People asking in public for funding; a draft answer each | 13:00 daily |
| [communities](jobs/communities.md) | Skool and Whop groups, for partnership and outreach | 15:00 daily |
| [partnerships](jobs/partnerships.md) | The partner lists and the partnership emails. No direct-lead cold email | 16:00 weekdays |
| [crm](jobs/crm.md) | GoHighLevel: contacts, tags, notes, stages, next steps, pipelines and workflows | 14:30 and 21:30 daily |
| [plan](jobs/plan.md), [report](jobs/report.md) | The morning plan; the nightly numbers, with jobs counted by engine | 11:30; 23:30 |

## What is in the pack

| | |
|---|---|
| `MASTER-PROMPT.md`, `roles/` | The bot's memory |
| `jobs/` | One brief per job, which the CLI works from |
| `skills/claude-code-cli/` | The rule: every task through the Claude Code CLI |
| `tools/job.py` | Hands a job to Claude Code, then Codex; logs which engine carried it |
| `tools/ghl.py` | GoHighLevel: reads freely, writes only when the switches allow, otherwise saves the proposal |
| `campaigns/find-me-money/` | The message, the plan, the settings |
| `agents/`, `skills/` | How each function works; the money hooks; the CRM's stages and tags |
| `guards/`, `convlog/` | The switches' checks; the log of every draft, send and reply |
| `tools/install.py`, `team.py`, `check.py`, `selftest.py` | The installer and the checks |

## Not in this bot

The Referral Connection site (its own agent: [referral-connection-grokbot](https://github.com/jbellsolutions/referral-connection-grokbot)), SpeakerAgent, AEO and SEO, and cold email to direct leads.
