# The Revenue OS, an incubator for two sites: the bot's build list

Justin, 2026-11-18: "Let's just give it to GrokBot... have it go build it. Let's give it a revenue OS, and let's just tell it to go do it."

Justin, 2026-11-20: "we're going to have the Revenue OS, and we're going to have it be an incubator for a few different sites: the referral site, the Find Me Money site. We're looking to have a Revenue OS that's all about getting those sites traction."

The two sites, what traction means for each and how each agent serves it: [sites/](sites/README.md). Every step below is done for both sites unless it says otherwise.

This page is what the team builds, in order, after HANDOFF.md Part 2. The Revenue OS is nine agents that run everything in front of the sales call ([TEMPLATE.md](TEMPLATE.md) is the spec). This pack already holds part of each one. The team builds the rest on its own computer, each agent its own function, runs each on test, and keeps one list of what only Justin can do.

## What is in the pack, and what is not

| Part | In the pack | State |
|---|---|---|
| The nine agents' specs | [agents/](agents/README.md): a process, a status page, prompts and a script per agent | Written and tested offline on a Mac. None has run on a Grok bot |
| Which engine each agent thinks with | [agents.json](agents.json), [engines/route.py](engines/route.py) | Tested: one real call through each CLI on a Mac. Not tested on a bot's computer |
| The conversation log | [convlog/](convlog/), [CONVERSATION-LOG.md](CONVERSATION-LOG.md) | Tested offline (`tools/selftest.py`) |
| The two sites | [sites/](sites/README.md): for each site a `SITE.md`, a `campaign.json` and `settings/` (one file per agent) | Filled from what each site has. Empty values are Justin's to give ([NEEDS-JUSTIN.md](NEEDS-JUSTIN.md), Tracks C and D) |
| The Disruptor message | [sites/find-me-money/MESSAGING.md](sites/find-me-money/MESSAGING.md) | The public outline. The full document is private and given at intake |
| The referral site's tool and skills | `tools/rc.py`; `skills/sales/directory-desk`, `matchmaker`; `skills/aeo-seo/guide-publisher`, `site-check`; `skills/outreach/prospect-finder`, `outreach-drafts` | From the site's own pack v1.0.0. The tool was tested against the live site by the site's chat; not run from a bot |
| The business's own roles, skills, guards, the reply engine, the worker for the Mac | `roles/`, `skills/`, `guards/`, `engine/`, `hermes-worker/` | As in pack v2: built, never installed |
| LinkedIn | [LINKEDIN.md](LINKEDIN.md), `linkedin/` | Off for this business |

Each agent's `STATUS.md` says what its chat built and what it did not. Where a status page lists something as not built (a runner, a finder, a call path to a tool), the bot builds it in its workspace.

## Which agent is which function

Nine functions, nine Grok agents (Justin, 2026-11-20: "nine functions = 9 agents"; [TEAM.md](TEAM.md)). Each agent builds and runs its own function, for both sites.

| Function | Engine | Grok agent (role) | Routine | Settings, in each `sites/<site>/settings/` |
|---|---|---|---|---|
| Dream 100 | GrokBot | Dream 100 (dream-100) | Dream 100 desk | `dream-100.json` |
| Dream 500 | GrokBot | Dream 500 (dream-500) | Dream 500 desk | `dream-500.json` |
| Partners, collaborators, influencers | GrokBot | Partners (partners) | Partner desk | `partners.json` |
| Cold email | GrokBot (first lines on Codex) | Cold Email (outreach) | Outreach drafts (Find Me Money), Referral outreach (the referral site) | `cold-email.json` |
| Lead Radar | Codex | Lead Radar (radar) | Pick today's queue, Niche rotation | `lead-radar.json` |
| Content | Claude Code | Content (content) | Daily content | `content.json` |
| Podcast SpeakerAgent | Codex | SpeakerAgent (speaker): off for both sites, not created at install | Speaker desk | `speaker.json` |
| AEO and SEO | Codex | AEO and SEO (aeo-seo) | Weekly AEO read (both), Referral guides (the referral site) | `aeo-seo.json` |
| Sales agent (replies and the CRM) | Codex, model GPT-6 Luna | Sales (sales) | Sales desk (Find Me Money), Referral desk (the referral site) | `sales-crm.json` |

Each site has its own project agent (Find Me Money, role lead; Referral Connection, role referral-lead): its plan, its report and the launch of its disruptor campaign from `sites/<site>/LAUNCH.md`. Find Me Money also closes the conversation log's day for the team. The worker, wholesale and loan-officer agents are this business's own.

## Build order

The lead does section 0, then creates the team ([TEAM.md](TEAM.md)). Each function's agent then does its own numbered section as part of setting itself up; the lead does section 10. If the other agents cannot be created yet, the lead writes each section's steps to `requests/<role>/revenue-os-build.md` and goes on. For each step: do it, run its check, and write one line in `log/revenue-os-build.md` (what was built, the command and output that shows it, what waits on Justin). A step that waits on Justin does not stop the next one: put the item on the list and go on.

### 0. The ground

1. `python3 repo/tools/selftest.py` and `python3 repo/tools/check_campaign.py repo/sites/*/campaign.json`. Both must pass on this computer.
2. For each folder in `repo/sites/`, copy its `campaign.json` and `settings/*.json` to `context/revenue-os/<site>/`. The workspace copies are the live ones: Justin's answers go there, never into `repo/`. Create `data/referral/` and `context/referral/` (mode 700). Write `context/sites.md`: `find-me-money: test` and `referral-connection: test`. Read each site's `SITE.md`.
3. Put `BOT_HOME=/workspace/find-me-money`, `CAMPAIGN=find-me-money` and `CONVLOG_TZ=America/New_York` in `.secrets/fmm.env`. Work for the referral site runs with `CAMPAIGN=referral-connection` in front of the command, so every log line carries its site.
4. **Engines.** When Justin has said yes to the install (Track C1): `npm install -g @anthropic-ai/claude-code @openai/codex`, his two sign-ins (C2), then `python3 repo/engines/route.py --check` and one real call through each. Until then the router gives every CLI agent's work to the bot itself, so the build goes on.
5. **The conversation log.** Write one test item, then `python3 repo/convlog/gate.py drafted <item>`, `check <item>` and `day`. From here on every draft, send and inbound message of every agent goes through `gate.py`.

6. **The messaging document** (Find Me Money). Ask Justin for it once (NEEDS-JUSTIN D1) and save it in `context/messaging/`. Until it is in, content and outreach for Find Me Money are drafted from `repo/sites/find-me-money/MESSAGING.md` alone.
7. **The referral site.** When Justin has given the site's admin key (D3): `python3 repo/tools/rc.py stats` reads one real record. Add `referral-site: live` to `context/owners.md`; it becomes `bot` on his word (D4). Until the key is in, the referral site's agents are built and tested against made-up rows.

### 1. Sales agent (replies and the CRM)

Starts from `roles/sales.md`, `skills/sales/`, `engine/pinnacle-reply-agent`, `engine/fcm` and `agents/sales-crm/PROCESS.md`.

- Build the runner the status page lists as not built: for each reply the Mac's sweeps sorted, read the person's vault note, sort the reply on Codex (`route.py --agent sales-crm`), draft the answer, log it, queue it for Justin.
- One vault note per person in `vault/People/`, added to on every reply, read before every draft.
- It runs on test: drafts and the log only. Two live agents on the Mac file and answer today. The bot writes the CRM and answers only after Justin names the base and switches the other off (Track C5), then says `pinnacle-ghl: bot` and `crm-writes: on`.
- Check: a test reply goes in with `gate.py inbound`, comes out as a logged draft in `requests/justin/`, and `owner_guard.py check pinnacle-ghl` still prints `live`.

- **The referral site.** The sales agent's records are the site's own. Build the Referral desk from `skills/sales/directory-desk` and `skills/sales/matchmaker`: intake (`rc.py signups --status new`, `connections`, `removals`), a listing for each real sign-up, pairs matched and recorded, introductions drafted and logged, each pair followed. A sponsorship, a collaboration or a deal is matched the same way: by what each side wrote they want.
- Check, referral site: with the key in, `rc.py stats` and `rc.py signups --status new`; one introduction draft in `requests/justin/` and in the log; `owner_guard.py check referral-site` prints `live`.

### 2. Lead Radar

Starts from the live Funding Radar, `roles/radar.md`, `skills/radar/` and `agents/lead-radar/radar.py`.

- Feed the day's finds (the Radar's fresh asks and the worker's finds) to `radar.py score --settings context/revenue-os/<site>/lead-radar.json`. Kept leads are logged and handed to the sales agent in `requests/sales/`.
- Check: `radar.py score --test` on today's asks, then `radar.py today`.

- **The referral site.** The same script with `context/revenue-os/referral-connection/lead-radar.json`: owners asking in public for a partner, a sponsor, a collaboration or a deal. A kept lead gets a draft that points to the sign-up page; a community or newsletter owner goes to `requests/partners/`.

### 3. Content

Starts from `roles/content.md`, the eight hooks in `skills/content/fmm-viral-content` and `agents/content/`.

- The three daily pieces are drafted through `agents/content/content.py draft` (Claude Code), in the four formats, on the eight hooks.
- Every outlet waits on a brand account and a publisher (Track C7). Until then pieces are drafts in Justin's queue. Every video tool is off: each is spend.
- Check: `content.py draft` on one source, then `content.py queue`.

- **Find Me Money: the Disruptor.** Pieces are drafted on the eight pillars in `repo/sites/find-me-money/MESSAGING.md`, in its content types and voice, alongside the eight hooks. A piece that needs a proof point, a count or a screenshot waits for the private document and Justin's clearing of that claim.
- **The referral site.** One piece a day pointing to the sign-up page, from `context/revenue-os/referral-connection/content.json`.

### 4. AEO and SEO

Starts from `roles/aeo-seo.md`, the site's guide hub and answer pages and `agents/aeo-seo/`.

- Write the panel (`data/aeo/prompts.md`, 15 questions) and the buying terms (`data/aeo/terms.json`).
- `aeo.py cost` prints what the tracking tool would cost. `pull`, `judge` and `read` wait on its key and Justin's yes (Track C8). Fixes to the site are briefs for a pull request in the site's own repo, never a write to the live site.
- Check: `aeo.py selftest`, `aeo.py cost --settings context/revenue-os/<site>/aeo-seo.json`.

- **Find Me Money.** The panel questions and buying terms come from the eight pillars: one answer page and one video brief per question.
- **The referral site.** Guides through `skills/aeo-seo/guide-publisher`: one brief, one draft, saved to the site as a draft with `rc.py page-put`; published on Justin's yes. Questions cover referral partners, collaborations, sponsorships and deals. `skills/aeo-seo/site-check` each week. The first brief for the site's own repo: what the pages and the sign-up form need to say for all four.

### 5. Dream 100

Starts from `roles/dream-100.md`, `agents/dream-100/` and Justin's lists in `data/lists/`.

- Build the finder the status page lists as not built: candidates from his lists and the worker's research lanes, scored with `dream100.py score`, the best 100 in `data/dream100.csv` (mode 600, never in a report).
- A dossier per person, then a first-touch draft. Drafts wait on what Find Me Money gives a partner's audience at no cost (Track C6).
- Check: `dream100.py check-settings`, the list's row count, one dossier.

- **The referral site.** Its own list in `data/referral/dream100.csv`: chambers, associations, networking groups, local newsletters and podcasts, coworking spaces, event organisers who sell sponsorships. The offer line is drafted in its settings and Justin can replace it.

### 6. Dream 500

Starts from `roles/dream-500.md` and `agents/dream-500/`.

- `dream500.py place` splits a found list into Dream 500, Dream 100 and the wide tier by audience size. First lines are drafted on the approved template.
- Sending waits on the domain decision (Track C9).
- Check: `dream500.py selftest`, `dream500.py place` on the found list.

### 7. Partners, collaborators, influencers

Starts from `roles/partners.md`, `skills/partners/` and `agents/partners/`.

- `partners.py screen` takes Dream 100 and Dream 500 names out of the day's found rows; the fit prompt scores the rest; one first email per partner type.
- Sending waits on the domain decision. A handoff or a deal waits on one active partner and the split (Track B17).
- Check: `partners.py plan`, `partners.py screen` on one day's rows.

- **The referral site.** The wide tier of the same audience holders, from `context/revenue-os/referral-connection/partners.json`, screened against the site's own Dream lists.

### 8. Cold email

Starts from `roles/outreach.md`, `skills/outreach/` and `agents/cold-email/`.

- `cold.py match` checks a verified list against its campaign; `cold.py first-lines` writes a first line per person on Codex.
- Sending waits on the domain decision and Justin's charter for cold email (Track C9, C10).
- Check: `python3 repo/agents/cold-email/test_cold.py`.

- **The referral site.** Build the Referral outreach run from `skills/outreach/prospect-finder` and `skills/outreach/outreach-drafts`: local businesses in the launch area from public sources into `data/prospects.csv`, then one-to-one drafts, each link tagged with its source. It waits on the launch area (D6); until then it runs on the gaps the Referral desk writes down.

### 9. Podcast SpeakerAgent

Starts from `roles/speaker.md` and `agents/speaker/`.

- **Off for both sites** (Justin, 2026-11-20: "I wouldn't do SpeakerAgent for Find Me Money"). Nothing in this section is built at install and no agent is created for it. If he turns it on for a site:
- `speaker.py find` and `score` list and score shows (free reads). No pitch is drafted until Justin gives the speaker profile (Track C11).
- Check: `speaker.py report`.

### 10. Routines and the report

1. Each agent has created its own routines from its section of TRIGGER-MAP.md, paused. The lead reads `context/team-registry.md` and lists any agent or routine that is missing.
2. The Evening report runs `python3 repo/convlog/gate.py day` and carries its audit lines.
3. **Launch.** Each project agent starts its site's `LAUNCH.md` at L0 and works down it.
4. Each project agent sends Justin one message for its business: for each site, the nine agents, each with built, tested (the evidence) and what it waits on, and the site's traction numbers as they stand; then the checklist of everything only he can do, once.

## Done means

For both sites, every agent that is not off has run on test on this computer, each with a line of evidence in `log/revenue-os-build.md`; every message any of them drafted is in the conversation log; nothing was sent, posted, spent or written to a live system; and Justin has one list.
