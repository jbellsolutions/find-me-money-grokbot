# The Revenue OS for Find Me Money: the bot's build list

Justin, 2026-11-18: "Let's just give it to GrokBot... have it go build it. Let's give it a revenue OS, and let's just tell it to go do it."

This page is what the bot builds, in order, after HANDOFF.md Part 2. The Revenue OS is nine agents that run everything in front of the sales call ([TEMPLATE.md](TEMPLATE.md) is the spec). This pack already holds part of each one. The bot builds the rest on its own computer, runs each on test, and keeps one list of what only Justin can do.

## What is in the pack, and what is not

| Part | In the pack | State |
|---|---|---|
| The nine agents' specs | [agents/](agents/README.md): a process, a status page, prompts and a script per agent | Written and tested offline on a Mac. None has run on a Grok bot |
| Which engine each agent thinks with | [agents.json](agents.json), [engines/route.py](engines/route.py) | Tested: one real call through each CLI on a Mac. Not tested on a bot's computer |
| The conversation log | [convlog/](convlog/), [CONVERSATION-LOG.md](CONVERSATION-LOG.md) | Tested offline (`tools/selftest.py`) |
| Find Me Money's settings | [campaign.json](campaign.json), [settings/](settings/) (one file per agent) | Filled from what the business has. Empty values are Justin's to give ([NEEDS-JUSTIN.md](NEEDS-JUSTIN.md), Track C) |
| The business's own roles, skills, guards, the reply engine, the worker for the Mac | `roles/`, `skills/`, `guards/`, `engine/`, `hermes-worker/` | As in pack v2: built, never installed |
| LinkedIn | [LINKEDIN.md](LINKEDIN.md), `linkedin/` | Off for this business |

Each agent's `STATUS.md` says what its chat built and what it did not. Where a status page lists something as not built (a runner, a finder, a call path to a tool), the bot builds it in its workspace.

## Which role works which agent

One bot, the same nine roles as before. A role works its agents during its own routines.

| Agent | Engine | Role | Routine | Settings |
|---|---|---|---|---|
| Dream 100 | GrokBot | partners | Dream desk | `settings/dream-100.json` |
| Dream 500 | GrokBot | partners | Dream desk | `settings/dream-500.json` |
| Partners, collaborators, influencers | GrokBot | partners | Partner desk | `settings/partners.json` |
| Cold email | GrokBot (first lines on Codex) | outreach | Outreach drafts | `settings/cold-email.json` |
| Lead Radar | Codex | radar | Pick today's queue, Niche rotation | `settings/lead-radar.json` |
| Content | Claude Code | content | Daily content | `settings/content.json` |
| Podcast SpeakerAgent | Codex | outreach | Speaker desk | `settings/speaker.json` |
| AEO and SEO | Codex | content | Weekly AEO read | `settings/aeo-seo.json` |
| Sales agent (replies and the CRM) | Codex, model GPT-6 Luna | sales | Sales desk | `settings/sales-crm.json` |

The lead role stays the orchestrator: the day's plan, the day close of the conversation log, the report. The wholesale and loan-officer roles and the worker's lanes on the Mac are this business's own and stay as they are.

## Build order

Work down the list. For each step: do it, run its check, and write one line in `log/revenue-os-build.md` (what was built, the command and output that shows it, what waits on Justin). A step that waits on Justin does not stop the next one: put the item on the list and go on.

### 0. The ground

1. `python3 repo/tools/selftest.py` and `python3 repo/tools/check_campaign.py repo/campaign.json`. Both must pass on this computer.
2. Copy `repo/settings/*.json` and `repo/campaign.json` to `context/revenue-os/`. The workspace copies are the live ones: Justin's answers go there, never into `repo/`.
3. Put `BOT_HOME=/workspace/find-me-money`, `CAMPAIGN=find-me-money` and `CONVLOG_TZ=America/New_York` in `.secrets/fmm.env`.
4. **Engines.** When Justin has said yes to the install (Track C1): `npm install -g @anthropic-ai/claude-code @openai/codex`, his two sign-ins (C2), then `python3 repo/engines/route.py --check` and one real call through each. Until then the router gives every CLI agent's work to the bot itself, so the build goes on.
5. **The conversation log.** Write one test item, then `python3 repo/convlog/gate.py drafted <item>`, `check <item>` and `day`. From here on every draft, send and inbound message of every agent goes through `gate.py`.

### 1. Sales agent (replies and the CRM)

Starts from `roles/sales.md`, `skills/sales/`, `engine/pinnacle-reply-agent`, `engine/fcm` and `agents/sales-crm/PROCESS.md`.

- Build the runner the status page lists as not built: for each reply the Mac's sweeps sorted, read the person's vault note, sort the reply on Codex (`route.py --agent sales-crm`), draft the answer, log it, queue it for Justin.
- One vault note per person in `vault/People/`, added to on every reply, read before every draft.
- It runs on test: drafts and the log only. Two live agents on the Mac file and answer today. The bot writes the CRM and answers only after Justin names the base and switches the other off (Track C5), then says `pinnacle-ghl: bot` and `crm-writes: on`.
- Check: a test reply goes in with `gate.py inbound`, comes out as a logged draft in `requests/justin/`, and `owner_guard.py check pinnacle-ghl` still prints `live`.

### 2. Lead Radar

Starts from the live Funding Radar, `roles/radar.md`, `skills/radar/` and `agents/lead-radar/radar.py`.

- Feed the day's finds (the Radar's fresh asks and the worker's finds) to `radar.py score --settings context/revenue-os/lead-radar.json`. Kept leads are logged and handed to the sales agent in `requests/sales-crm/`.
- Check: `radar.py score --test` on today's asks, then `radar.py today`.

### 3. Content

Starts from `roles/content.md`, the eight hooks in `skills/content/fmm-viral-content` and `agents/content/`.

- The three daily pieces are drafted through `agents/content/content.py draft` (Claude Code), in the four formats, on the eight hooks.
- Every outlet waits on a brand account and a publisher (Track C7). Until then pieces are drafts in Justin's queue. Every video tool is off: each is spend.
- Check: `content.py draft` on one source, then `content.py queue`.

### 4. AEO and SEO

Starts from the site's guide hub and answer pages and `agents/aeo-seo/`.

- Write the panel (`data/aeo/prompts.md`, 15 questions) and the buying terms (`data/aeo/terms.json`).
- `aeo.py cost` prints what the tracking tool would cost. `pull`, `judge` and `read` wait on its key and Justin's yes (Track C8). Fixes to the site are briefs for a pull request in the site's own repo, never a write to the live site.
- Check: `aeo.py selftest`, `aeo.py cost --settings context/revenue-os/aeo-seo.json`.

### 5. Dream 100

Starts from `agents/dream-100/` and Justin's lists in `data/lists/`.

- Build the finder the status page lists as not built: candidates from his lists and the worker's research lanes, scored with `dream100.py score`, the best 100 in `data/dream100.csv` (mode 600, never in a report).
- A dossier per person, then a first-touch draft. Drafts wait on what Find Me Money gives a partner's audience at no cost (Track C6).
- Check: `dream100.py check-settings`, the list's row count, one dossier.

### 6. Dream 500

Starts from `agents/dream-500/`.

- `dream500.py place` splits a found list into Dream 500, Dream 100 and the wide tier by audience size. First lines are drafted on the approved template.
- Sending waits on the domain decision (Track C9).
- Check: `dream500.py selftest`, `dream500.py place` on the found list.

### 7. Partners, collaborators, influencers

Starts from `roles/partners.md`, `skills/partners/` and `agents/partners/`.

- `partners.py screen` takes Dream 100 and Dream 500 names out of the day's found rows; the fit prompt scores the rest; one first email per partner type.
- Sending waits on the domain decision. A handoff or a deal waits on one active partner and the split (Track B17).
- Check: `partners.py plan`, `partners.py screen` on one day's rows.

### 8. Cold email

Starts from `roles/outreach.md`, `skills/outreach/` and `agents/cold-email/`.

- `cold.py match` checks a verified list against its campaign; `cold.py first-lines` writes a first line per person on Codex.
- Sending waits on the domain decision and Justin's charter for cold email (Track C9, C10).
- Check: `python3 repo/agents/cold-email/test_cold.py`.

### 9. Podcast SpeakerAgent

Starts from `agents/speaker/`.

- `speaker.py find` and `score` list and score shows (free reads). No pitch is drafted until Justin gives the speaker profile (Track C11).
- Check: `speaker.py report`.

### 10. Routines and the report

1. Create the three new routines in TRIGGER-MAP.md (Dream desk, Speaker desk, Weekly AEO read), paused, with the other 12.
2. The Evening report runs `python3 repo/convlog/gate.py day` and carries its audit lines.
3. Send Justin one message: the nine agents, each with built, tested (the evidence) and what it waits on; then the checklist of everything only he can do, once.

## Done means

All nine agents have run on test on this computer, each with a line of evidence in `log/revenue-os-build.md`; every message any of them drafted is in the conversation log; nothing was sent, posted, spent or written to a live system; and Justin has one list.
