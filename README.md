# Disruptor Revenue OS: GrokBot pack

One Revenue OS, two disruptor campaigns. Justin, 2026-11-24: "You got a main agent for each one of the two campaigns for the two projects, and then you have our Revenue OS. That should be pretty set up and straightforward, so I can just talk to each one of the two main bots about each of those two different projects."

**One-click install.** Paste this into one new Grok bot:

> Install the Disruptor Revenue OS. Download https://github.com/jbellsolutions/disruptor-revenue-os-grokbot/releases/latest/download/disruptor-revenue-os.zip, unpack it into /workspace/revenue-os/repo/, run python3 /workspace/revenue-os/repo/tools/install.py and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

Version 1.0.0.

## What it installs

| Agent | What it is |
|---|---|
| **Find Me Money** | Main agent for the Find Me Money disruptor campaign (findmemoneyapp.com). Justin talks to it about that campaign |
| **Referral Connection** | Main agent for the Referral Connection disruptor campaign (findreferralpartners.com). Justin talks to it about that campaign |
| **Lead Radar** | People asking in public for what each campaign offers: social, Skool and Whop |
| **Content** | Each campaign's disruptor content |
| **AEO and SEO** | Each site found in search and in AI answers; the referral site's guides |
| **Dream 100**, **Dream 500** | The people who already have each campaign's buyers gathered |
| **Cold Email** | Cold email to each campaign's prospects |
| **SpeakerAgent** | Podcast outreach |
| **Reply** | Answers every reply |
| **Sales and CRM** | Each campaign's records, and each person's next step |

Eleven agents, thirteen routines. The nine Revenue OS agents work both campaigns and keep them apart. Their thinking runs through Claude Code and Codex on Justin's own subscriptions (`engines/route.py`), not on Grok usage. Reports go to Slack, Notion and the vault that feeds the single brain.

## What is in the pack

| | |
|---|---|
| [INSTALL.md](INSTALL.md) | The one line, and the four steps the first agent takes |
| [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md) | The one checklist of what only Justin can do |
| [team.json](team.json), `tools/team.py`, `tools/install.py` | The team, each agent's one line and setup, the installer |
| [MASTER-PROMPT.md](MASTER-PROMPT.md), [roles/](roles/) | Every agent's memory: the team block, then its own |
| [campaigns/](campaigns/) | Per campaign: `CAMPAIGN.md`, `MESSAGING.md` (the disruptor message), `LAUNCH.md` (the launch plan and the switches that make it autonomous), settings |
| [agents/](agents/README.md), [agents.json](agents.json), [engines/](engines/route.py), [convlog/](convlog/) | The Revenue OS: each function's process and script, the engine router, the one conversation log |
| [guards/](guards/SKILL.md) | The checks an agent runs before it drafts, sends, writes or spends |
| [skills/](skills/), `tools/rc.py` | The referral site's desk, guides and outreach; the eight money hooks; the CRM map |
| `tools/check.py`, `tools/selftest.py` | The pack's own checks |
