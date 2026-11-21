# Find Me Money: the handoff

What Justin does, then what the team does on its own. Follows the factory PLAYBOOK and the client-build GrokBot standard. Unverified platform facts are flagged *(unverified)*. This pack replaces the v1 pack (never live). Version 6 is the combined install for two autonomous businesses: two project agents (Find Me Money, Referral Connection) and one agent per role, with each site's disruptor launch plan (Justin, 2026-11-20; [sites/](sites/README.md)). Version 5 made each role its own agent (Justin, 2026-11-20: "it should be in grokbot with each role being its own agent"; [TEAM.md](TEAM.md)), which replaces the one-bot layout of versions 2 to 4. Version 4 makes the Revenue OS an incubator for two sites, Find Me Money and the referral connection site (Justin, 2026-11-20; [sites/](sites/README.md)). Version 3 added the Revenue OS: Part 3 is the bot building it (Justin, 2026-11-18: "give it a revenue OS, and let's just tell it to go do it").

## Part 1: Justin

1. **Account.** Sign in at x.ai/bot with the Grok account for **Find Me Money** only, never AI Guy's (one account per business; every bot on it shares one computer, its files and logins). Check the plan covers bots and routines. The bot never buys a plan.
2. **Desktop app.** Open the Grok desktop app. Setup runs in the one-to-one chat there (approval, secret and sign-in requests only show there).
3. **The lead agent.** Create one bot named **Find Me Money**, pin it, and set Settings → General → Bot → Timezone to **UTC**. It is the Find Me Money project agent and the first agent of the team. It creates the other eleven agents itself at Part 2 step 7: the Referral Connection project agent and one agent per role. If the app does not let a bot create a bot, it gives you a file with eleven names and one message each: create each bot, set UTC, paste its message.
4. **The pack: one link.** Paste the line below into the new bot. If the bot can't download, attach `find-me-money.zip` from the same release instead *(zip route unverified)*:

   > You are Find Me Money, the project agent that runs the Find Me Money business, and the first agent of a team. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, unpack it into /workspace/find-me-money/repo/ and follow HANDOFF.md: Part 2 from step 1, which has you create the team from TEAM.md (a second project agent, Referral Connection, and one agent per role, each its own bot on this account), then Part 3, where each agent builds its own part of the Revenue OS for both sites and each project agent launches its site's disruptor campaign from sites/<site>/LAUNCH.md. The goal is two autonomous businesses. Read MASTER-PROMPT.md, CHARTER.md, TEAM.md and sites/README.md first. Do every step that needs nothing from me without stopping. Keep one list of what only I can do and show it to me once, at the end. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

5. **Auto-review rules.** At Part 2 step 4, paste the Ask-first lines it shows into Auto-review → Custom Rules.
6. **Sign-ins and keys.** When it asks, sign in through Connect apps, one at a time. Keys go only through a secure secret card or the hidden terminal prompt with **Take over**. Rotate first any key ever pasted in a chat.

## Part 2: the lead, then the team

"The lead" on this page is the role `lead`: the Find Me Money project agent, the bot Justin created. Steps 1 to 6 are the lead's. At step 7 it creates the other agents, and each sets itself up.

1. **Workspace.** Create `/workspace/find-me-money/` with `context/`, `daily/`, `requests/` (one folder per role: `lead`, `referral-lead`, `dream-100`, `dream-500`, `partners`, `outreach`, `radar`, `content`, `speaker`, `aeo-seo`, `sales`, `worker`, `wholesale`, `loan-officer`, plus `justin`, `hermes` and `lead-storm`), `approved/`, `data/` and `data/lists/` (mode 700, files 600; copy `repo/data/lists/README.md` in for the file names and columns), `log/`, `vault/` (Obsidian: `Daily/`, `People/`, `Decisions.md`), `state/` and `state/test/`, `pinnacle-reply/`, `.secrets/` (mode 700). Write:
   - `context/routines-on.md`: every routine in TRIGGER-MAP.md as `<exact name>: off`, plus `crm-writes: off`.
   - `context/owners.md`: one line each, all `live`: `pinnacle-ghl`, `funding-radar`, `radar-cl`, `fbgroups-lane`, `lending-hub`, `muse-app`, `social-sender`, `legacy-agent`, `cold-email-sender`, `hermes-worker`, `codex-cli`, `referral-site`. Check with `python3 repo/guards/scripts/owner_guard.py list`.
   - `context/standing-approvals.md`, `context/spend-approvals.md` (both empty), `context/team-registry.md`, `context/content-log.md`, `context/local-metros.md`, `context/week-plan.md` (empty until the first Niche rotation), `context/group-registry.md`, and `context/executors.md` with `drafts: codex` once Codex is in (every other lane runs on `hermes-mac`).
   - Don't create `context/STOP`. Start `log/setup.md`. Run `python3 repo/tools/check.py` and paste its RESULT line into `log/setup.md`.
2. **Memory and skills.** Save the block in MASTER-PROMPT.md to memory word for word, then the lead's "System prompt section" from `roles/lead.md`, and no other role's: each other agent saves its own. Save `guards/SKILL.md` and every `skills/<role>/<skill>/SKILL.md` as a private skill ([SKILLS-MAP.md](SKILLS-MAP.md) says which role uses which); whether another bot on the account sees them is unverified, so each agent checks. Install the engine: `pip install httpx` and `pip install -e repo/engine/pinnacle-reply-agent`; run `python3 -m py_compile` over `repo/engine` and `python3 repo/skills/radar/craigslist-lane/scripts/scrape.py selftest`. Put each key name in `.env.example` into `.secrets/fmm.env` by hidden prompt, one at a time. The non-secret intake values (ids, service URLs, `FMM_HOSTS`, `MUSE_COMPUTER`) go in the same file; Justin pastes them from his private intake list. Write the never-touch names he gives to `.secrets/never-touch.txt` (mode 600), one per line: without that list `preflight`, `owner_guard.py`, `orgo.py` and `muse.py` refuse every guarded write. Leave `REPLY_WRITE`, `REPLY_GHL` and every `FCM_SEND_*` switch off.
3. **Intake.** Ask Justin, one at a time: his private lists (influencers, coaches, communities, the partner-target sheet) into `data/lists/` (mode 600, never in a report), the Slack channel for this team (default `#find-me-money-bot`, not the live Hermes orchestrator's channel), the Notion page for the scoreboard and drafts, the suppression list file, the first local metro, the partner list with each partner's products, states and pay, and which templates are already approved. Write `context/owner.md`; save the suppression list as `context/suppression.csv`; mark approved templates in `standing-approvals.md`.
4. **Approval rules.** Show Justin the Ask-first lines from GATES.md to paste.
5. **Connect, read-only, one at a time.** Each gets a Check that reads one real record into `log/setup.md`.

   | App | Roles | Check |
   |---|---|---|
   | Slack, the team's channel | lead, referral-lead, content | Read the last message |
   | Notion | lead, referral-lead | Read today's scoreboard row (or the page title) |
   | The Funding Radar | radar, wholesale | `GET /api/replies`: today's ask count |
   | treg, One API | radar | Account status and today's read cap |
   | Scrapebox | radar | `status`: which rungs run here |
   | browser-box | radar | `status` |
   | Orgo, the Mac in `MUSE_COMPUTER` only | worker | `owner_guard.py target "$MUSE_COMPUTER"` prints `ok`, then a screenshot shows Muse. Never any other computer |
   | GoHighLevel, Pinnacle Funding Group (read-only key first) | sales | P1 · Funding Leads stage counts |
   | The Lending Hub | sales, partners, loan-officer | `GET /api/deals`: count; `GET /api/distribution/open` |
   | Gmail | sales | Newest thread subject |
   | Instantly (read-only key first) | outreach | Campaign count and last week's reply rate |
   | Reacher (email verifier) | outreach | Verify one known address |
   | The referral site (`RC_SITE`, its admin key) | referral-lead, sales, aeo-seo, outreach | `python3 repo/tools/rc.py stats`: sign-ups, listings and matches as counts |
| The Hermes worker on the Mac | worker | `python3 repo/engine/hermes_bridge.py status` prints the worker's heartbeat (after Justin installed it) |
   | Codex CLI (if Justin installed it) | worker | `codex --version`, then `hermes_bridge.py put drafts '{"kind":"test","source":"none","limit":1}'` runs once and writes `state/worker/grok/outbox/drafts/` |

6. **Old agents.** Some of this work may already run live in other agents and services (each one is a system in `context/owners.md`). Two writers never write the same thing: every one of those systems stays `live` in `context/owners.md`, and the bot reads and drafts. Justin moves a system to `bot` only after he pauses its live writer. Record this in `log/setup.md`.
7. **Create the team.** First do section 0 of REVENUE-OS.md (the ground), so every agent finds the settings, the log and the sites in place. Then follow [TEAM.md](TEAM.md), "The lead creates the team": for each of the eleven agents (Referral Connection first, then the ten role agents), create the bot by its exact name, set UTC, send it `python3 repo/tools/team.py message <role>`, and wait for "ready". If the app won't let a bot create or message a bot *(both unverified)*, write `python3 repo/tools/team.py messages` to `requests/justin/create-the-team.md`, put it on Justin's list, and go on. Two agents are created later: SpeakerAgent, if Justin turns it on for a site, and the loan officer, when he names a verified lender.
8. **Routines, switched off.** Each agent creates only its own routines from its section of TRIGGER-MAP.md, paused, with the exact names: each project agent its two, the others theirs, 19 in all at install (21 with SpeakerAgent's and the loan officer's). Each prompt starts `Role: <role>.` and names the script or skill it runs. Each is recorded in `team-registry.md` with agent, role, cron, time zone and next run. A next run an hour or more off means that agent's time zone isn't set.
9. **Report.** The lead reads back every agent, routine and connection from `team-registry.md`, runs `python3 repo/tools/team.py check`, and sends Justin the list plus what isn't done and why.

## Part 3: the team builds the Revenue OS

[REVENUE-OS.md](REVENUE-OS.md) is the build list: the ground (the checks, the settings copied to `context/revenue-os/`, the engines, the conversation log), then the nine functions, each built by its own agent for both sites, then the routines and the report. The lead does the ground before it creates the team (Part 2 step 7); each agent does its own section as the last step of setting itself up; the lead does the report. Read [sites/README.md](sites/README.md) and each site's `SITE.md` first.

1. **Build without stopping.** A step that waits on Justin goes on the one list and the next step starts. Nothing in Part 3 sends, posts, spends, signs in or writes to a live system.
2. **Build in the workspace, not in `repo/`.** Anything a status page lists as not built (a runner, a finder, a call path) is written under `/workspace/find-me-money/build/<agent>/`, with a test beside it. `repo/` changes only when a new pack version is installed.
3. **Evidence per step.** One line per step in `log/revenue-os-build.md`: what was built, the command and its output, what waits on Justin.
4. **Engines.** The two CLIs install only on Justin's yes, and he signs them in ([NEEDS-JUSTIN.md](NEEDS-JUSTIN.md) C1, C2). Then `python3 repo/engines/route.py --check` and one real call through each, and again the next day: if a sign-in did not last the night, say so in the report.
5. **The sales agent stays on test.** Two live agents on the Mac file and answer today. The team's sales agent drafts and logs until Justin switches them (C5).
6. **Two sites, kept apart.** Each site has its own settings (`context/revenue-os/<site>/`), its own records and its own block in every report. The referral site's records are written only after Justin says `referral-site: bot`.
7. **Launch both disruptor campaigns.** Each project agent opens its site's `LAUNCH.md` and works down it from L0: Find Me Money on [sites/find-me-money/LAUNCH.md](sites/find-me-money/LAUNCH.md), Referral Connection on [sites/referral-connection/LAUNCH.md](sites/referral-connection/LAUNCH.md). L1 (the library) is all drafts and needs nothing from Justin; L2 is one yes per channel.
8. **Finish with one message per business, from its project agent.** For its site: the nine agents, each with built, tested (the evidence) and what it waits on, and the site's traction numbers; then the checklist of what only Justin can do, once.

## Usage kit (usage-mastery v1.0.0)

From `grokbot-usage-mastery`. Do these right after the workspace and memory steps.

1. Run `bash repo/usage/scripts/install.sh` (free, pinned, no keys) and paste its last line into `log/setup.md`.
2. Save `repo/usage/SKILL.md` as a private skill named usage-saver.
3. Copy `repo/usage/LEDGER.md` to `log/usage-ledger.md`. Ask Justin for the baseline reading (Settings → Usage: % used and reset date) before the first test day, and again after it.
4. The weekly audit (`repo/usage/AUDIT.md`) runs inside the Monday evening report; it adds no routine and changes nothing.
5. Check: `bash repo/usage/scripts/grep_lines.sh 'usage-mastery v' repo/usage/.. 3` prints at least one line (the rules are in place and the scripts run).
6. Show Justin the two owner-only steps, once per Grok account, and record the answers in `log/setup.md`:
   - A spending cap: grok.com/dashboard/billing → a monthly additional-usage limit, or Auto top-up off. The bot never changes billing.
   - Three lines for Auto-review → Custom Rules (chat only; routines never wait on approvals):

     ```
     Ask first before opening more than 5 web pages for one task.
     Ask first before starting a sub-agent, or a bot that is not in team.json.
     Ask first before re-running a step that has already failed twice.
     ```
## The executors (the work runs here, not on Grok)

GrokBot is the orchestrator (Justin, 2026-11-13). Two executors do the work; each is one of Justin's yeses:

1. **The Hermes worker on the Mac.** The Find Me Money Hermes profile is already on the Mac, with its own 12 jobs (the reply cycle, the 30-minute sweep, sorting, the lead sweep, the scorecard and the rest), all paused. The worker adds one more paused job, `fmm-worker-inbox`, that runs GrokBot's work orders every 15 minutes on the profile's own model. Install from a computer with this pack, Justin's yes first: `MUSE_COMPUTER=<the Mac> NEVER_TOUCH=<list> ORGO_API_KEY=<key> bash hermes-worker/install.sh` (dry run: needs only `MUSE_COMPUTER`, makes no Orgo call), then `--go`. Then turn the job on (`hermes -p find-me-money cron resume fmm-worker-inbox` on the Mac), and say "hermes-worker: bot". The install needs no Grok bot, so it can be done before Part 1.
2. **Claude Code and Codex on the team's computer**: the Revenue OS engines. Content writes on Claude Code; the sales agent, Lead Radar, AEO and SEO and bulk drafts run on Codex, each on its own subscription instead of Grok's allowance. The bot installs them on Justin's yes, he signs them in through the secure path (never a pasted token), then says "codex-cli: bot". Every call goes through `engines/route.py`.

Until then every work order is held in `requests/hermes/` and the team still plans, judges what the live Radar finds, and reports.

## Bring-up order

One agent at a time. An agent is "on" when its routines' lines in `context/routines-on.md` are `on`.

| # | Agent (role) | Why this order | Turned on first |
|---|---|---|---|
| 1 | Find Me Money (lead), Referral Connection (referral-lead) | The two project agents plan and report; they read only | Morning plan, Evening report, Referral plan, Referral report |
| 2 | Lead Radar (radar) | Plans the week and picks from the live Radar; nothing reaches a person | Niche rotation, Pick today's queue |
| 3 | Worker (worker) | Orders stay held until the Hermes worker is installed and `hermes-worker: bot` | Dispatch, Pull |
| 4 | Content (content) | Drafts only; first post per channel is Justin's | Daily content |
| 5 | AEO and SEO (aeo-seo) | Reads, briefs and guide drafts; nothing public | Weekly AEO read, Referral guides |
| 6 | Dream 100, Dream 500 | Lists, dossiers and drafts only | Dream 100 desk, Dream 500 desk |
| 7 | SpeakerAgent (speaker) | Off for both sites. Created and turned on only on Justin's word | Speaker desk |
| 8 | Wholesale (wholesale) | Call cards and drafts only | Wholesale desk |
| 9 | Partners (partners) | Proposals only | Partner desk |
| 10 | Sales (sales) | Drafts first; CRM writes only after `pinnacle-ghl: bot` (the live reply cycle paused first); site writes only after `referral-site: bot` | Sales desk, Referral desk |
| 11 | Cold Email (outreach) | The senders stay live systems | Outreach drafts, Referral outreach |
| 12 | Loan Officer (loan-officer) | Created and turned on only with a verified lender | In-house desk |

## The first-day test run

Every routine is `test` in `context/routines-on.md` and every system is `live` in `context/owners.md`, so nothing reaches a person or a live system. **Test on a routine does real work**: the `test` line goes in before every Test press.

| Step | Agent (role) | Do | Pass when |
|---|---|---|---|
| 0 | lead | The team | `python3 repo/tools/team.py check` prints ok; every agent created at install answered "ready", has its routines paused and its lines in `context/team-registry.md`; no agent's memory holds another role's section |
| 1 | lead | Morning plan | Find Me Money's plan in `daily/<date>/lead.md`, one `find-me-money-plan-<date>.md` in each role agent's `requests/<role>/`, and in the team's Slack channel; it names the LAUNCH.md step it came from |
| 2 | radar | Niche rotation | `context/week-plan.md` with up to 12 orders: at least one `group-discovery` (a coaching theme), one `marketplace`, one `influencers`, one `wholesalers` |
| 3 | worker | Dispatch | Each order is either queued on the Mac (worker installed) or held in `requests/hermes/`; none has free text |
| 4 | worker | Pull | Results routed to `requests/<role>/`; `hermes_bridge.py status` read; a silent lane gives one Slack line |
| 5 | radar | Pick today's queue | Up to 10 drafts from the last 2 days, high tier first, in `requests/justin/`; nothing older than 7 days |
| 6 | content | Daily content | Three pieces on three different hooks, each scored 4+ on funny, simple, relatable, in `requests/justin/` |
| 7 | wholesale | Wholesale desk | Scored call cards (A/B) in `requests/wholesale/`; no contract, no message sent |
| 8 | sales | Sales desk | Each "needs a person" reply has a next-message draft; `owner_guard.py check pinnacle-ghl` prints `live` |
| 9 | partners | Partner desk | Proposals only; creators, coaches and affiliate houses picked from the research with one reason each |
| 10 | outreach | Outreach drafts | Verified list and copy in `requests/justin/`; Lead Storm items say `approved: waiting on Justin` |
| 11 | All | Suppression test | Add a known name with `suppression.py add`; radar, sales, outreach, partners and wholesale all hold it |
| 12 | All | Owner test | `owner_guard.py check hermes-worker --routine "Dispatch"` prints `live` until Justin's yes |
| 13 | All | STOP test | Create `context/STOP`; the next run of every agent says stopped and does nothing; remove it |
| 13b | worker | Research spot-check | Open 5 links from each research lane's results (influencers, coaches, affiliate houses): every one exists and matches its row |
| 13c | dream-100 | Dream 100 desk | Candidates scored into `data/dream100.csv`; one dossier; first-touch drafts logged and in `requests/justin/` |
| 13c2 | dream-500 | Dream 500 desk | `dream500.py place` splits a found list; the 100 tier is in `requests/dream-100/` and the partner tier in `requests/partners/` |
| 13d | referral-lead | Referral plan, Referral report | A plan file for the referral site in each role agent's `requests/<role>/`; the report's numbers match `rc.py stats`; `team.py list` shows SpeakerAgent as created later and no Speaker desk routine exists |
| 13e | aeo-seo | Weekly AEO read | `aeo.py cost` prints the month's cost; the panel and terms files exist; nothing was bought |
| 13f | All | Conversation log | Every draft of the day is in `conversations/<YYYY-MM>.jsonl`; `convlog/gate.py day` writes the day file and its audit names no line |
| 13g | sales | Referral desk | With the site's key in: new sign-ups read, each real one given a proposed listing and blurb, one pair proposed with its reason, one introduction draft logged; `owner_guard.py check referral-site` prints `live`, so nothing was written to the site |
| 13h | outreach | Referral outreach | Prospects for the launch area (or for the gaps the desk wrote down) in `data/prospects.csv` with a source each; first-touch drafts in `requests/justin/`; nothing sent |
| 13i | aeo-seo | Referral guides | One brief and one guide draft; saved to the site as a draft only if `referral-site: bot`, else kept in `requests/justin/`; nothing public |
| 13j | lead, referral-lead | Two businesses | Each project agent's plan and report cover only its own site; no number is added across the two |
| 13k | lead, referral-lead | The launch | Each site's `LAUNCH.md` L1 has at least one step done as drafts: a calendar, one guide or answer-page brief, ten scored Dream 100 names |
| 14 | lead | Evening report | Every agent has a line; the vault note exists; `beat.py status` shows no SILENT; 0 sent, 0 posted, 0 live-system writes; Grok runs today about 20 |

The day passes when every row passes. Then Justin approves each message type once, and agents go `on` one at a time in the bring-up order.

## Reporting back

| Where | What | Written by |
|---|---|---|
| Slack, the team's own channel | Morning plan, alarms (silent agents, unapproved sends), evening report, Justin's queue | lead |
| Notion | Scoreboard row a day; Drafts waiting on Justin | lead |
| The workspace vault | `vault/Daily/<date>.md`, `People/` (companies, not contact details), `Decisions.md` | lead writes the daily note; each agent adds its section |
| The single brain | A scrubbed status line and the daily summary, no raw transcripts or contact data | lead's Evening report through a deploy key, or Justin's Mac pulls: Justin's pick on NEEDS-JUSTIN |
