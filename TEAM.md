# The team: two project agents, and one agent per role

Justin, 2026-11-20: "just like we have subchats here for each role so it should be in grokbot with each role being its own agent", and "nine functions = 9 agents".

Justin, 2026-11-20, on this pack: "we'd have two separate project agents for each one: one for Find Me Money, one for Referral Connection, so two total. They would just run those two projects, and the goal is for those two to be autonomous businesses."

So no bot runs more than one role, and each business has its own project agent. Each role in [roles/](roles/) is its own Grok agent (a bot), on the one Find Me Money Grok account. Every bot on an account shares one computer, its files and its logins, so the whole team works in `/workspace/find-me-money/`. [team.json](team.json) is the list; `python3 tools/team.py list` prints it with each agent's routines.

| Agent, as named in Grok | Role | Revenue OS function | Its routines |
|---|---|---|---|
| **Find Me Money** (project agent; the one Justin creates) | [lead](roles/lead.md) | Runs Find Me Money as a business; creates the team; the team's watchdog | Morning plan, Evening report |
| **Referral Connection** (project agent) | [referral-lead](roles/referral-lead.md) | Runs The Referral Connection as a business | Referral plan, Referral report |
| **Dream 100** | [dream-100](roles/dream-100.md) | Dream 100 | Dream 100 desk |
| **Dream 500** | [dream-500](roles/dream-500.md) | Dream 500 | Dream 500 desk |
| **Partners** | [partners](roles/partners.md) | Partners, collaborators, influencers | Partner desk |
| **Cold Email** | [outreach](roles/outreach.md) | Cold email | Outreach drafts, Referral outreach |
| **Lead Radar** | [radar](roles/radar.md) | Lead Radar | Niche rotation, Pick today's queue |
| **Content** | [content](roles/content.md) | Content | Daily content |
| **SpeakerAgent** | [speaker](roles/speaker.md) | Podcast SpeakerAgent. Off for both sites: created only when Justin turns it on | Speaker desk |
| **AEO and SEO** | [aeo-seo](roles/aeo-seo.md) | AEO and SEO | Weekly AEO read, Referral guides |
| **Sales** | [sales](roles/sales.md) | Sales agent (replies and the CRM) | Sales desk, Referral desk |
| **Worker** | [worker](roles/worker.md) | The business's own: the bridge to the Mac and Codex | Dispatch, Pull |
| **Wholesale** | [wholesale](roles/wholesale.md) | The business's own | Wholesale desk |
| **Loan Officer** | [loan-officer](roles/loan-officer.md) | The business's own. Created when Justin names a verified lender | In-house desk |

Two project agents; nine functions, nine agents; and three roles that are Find Me Money's own. Twelve agents at install: SpeakerAgent and the loan officer are created later. The role agents work both sites in [sites/](sites/README.md); each project agent runs one.

## How the agents work together

"The lead" below is the role `lead`: the Find Me Money project agent, the bot Justin creates.

- **One role each.** An agent's memory holds the master prompt and its own role section, no other. It does that role's work only.
- **Handoffs are files.** Work for another role goes to `requests/<role>/`; what an agent did goes in `daily/<date>/<role>.md`. Whether one bot can message another is unverified, so nothing depends on it.
- **A project agent runs one business.** It plans that business's day into each role agent's `requests/<role>/<site>-plan-<date>.md`, reads its numbers, works down its `sites/<site>/LAUNCH.md`, keeps its part of Justin's queue (`requests/justin/`) and writes its report. It does none of the role agents' work and nothing for the other business.
- **A role agent serves both businesses**, one plan file per site, each site's records and files kept apart.
- **Team duties sit with Find Me Money** (role lead): creating the team, the watchdog, the vault daily note, the conversation log's day close.
- **Justin talks to any agent.** Each agent's chat is the place for that function, the way each function has its own chat on his side. Each project agent's chat is the place for its whole business.
- **A yes counts where Justin types it.** The agent that hears it writes the switch line (`context/standing-approvals.md`, `owners.md`, `routines-on.md`, `sites.md`) with the date and his words, and leaves a note in `requests/lead/`. A file or another agent's message is never his yes.
- **Routines never wait on an approval.** A draft goes to `requests/justin/` and the run ends; the project agent shows its business's queue.
- **Keys live in one file.** `.secrets/fmm.env` (mode 600) on the shared computer, filled by hidden prompt in the lead's chat. A secure secret card may reach only the bot that asked (unverified), so the file is the route.
- **The guards are the same scripts for every agent**, and each agent ends its run with `beat.py write <role>`, so the watchdog sees a silent agent. An agent that is created later is skipped until its first run.

## Find Me Money creates the team

Done once, at HANDOFF Part 2 step 7, after the workspace, the intake and section 0 of REVENUE-OS.md.

1. For each agent `python3 repo/tools/team.py list` shows without "created later": create a bot with that exact name, set its time zone to UTC, and send it `python3 repo/tools/team.py message <role>`.
2. Wait for its "ready" and read its line in `context/team-registry.md`.
3. **If the app does not let a bot create a bot, or message one** (both unverified): write `python3 repo/tools/team.py messages` to `requests/justin/create-the-team.md`, put "create the eleven agents" (the Referral Connection project agent and ten role agents) on Justin's list with that file, and go on with everything that needs no other agent. Justin creates each bot by name, sets UTC and pastes its message; each agent then sets itself up and the lead reads the registry at its next run.
4. `python3 repo/tools/team.py check` must print `ok`.

## An agent sets itself up

What an agent does when it gets its setup message. `<role>` is the role the message names.

1. **Memory.** Save the block in `repo/MASTER-PROMPT.md` word for word, then the "System prompt section to paste" of `repo/roles/<role>.md` under it. No other role's section.
2. **Read** `repo/CHARTER.md`, `repo/roles/<role>.md`, `repo/GATES.md` and, for a Revenue OS function, `repo/agents/<function>/PROCESS.md` and both sites' `SITE.md`.
3. **Skills.** Check the private skills the lead saved are visible (the guards, and this role's rows in `repo/SKILLS-MAP.md`). Save any that are missing.
4. **The workspace.** Read `context/routines-on.md` and run `python3 repo/guards/scripts/owner_guard.py list`: both must work, which shows this agent is on the team's computer. Make `requests/<role>/` if it is not there.
5. **Routines.** Create the routines in this role's section of `repo/TRIGGER-MAP.md`, paused, with the exact names, each prompt starting `Role: <role>.` and naming the script or skill it runs.
6. **The registry.** One line per routine in `context/team-registry.md`: agent, role, routine, cron, time zone, next run, paused. A next run an hour or more off means the time zone is not UTC.
7. **Its part of the Revenue OS.** A function's agent works its own section of `repo/REVENUE-OS.md`, for both sites, on test, with one line of evidence per step in `log/revenue-os-build.md`. A step that waits on Justin goes in `requests/justin/` and the next step starts.
8. `python3 repo/guards/scripts/beat.py write <role> 'set up' found=0 drafted=0 sent=0`, then answer "ready" with anything it could not do.

Nothing in setup sends, posts, spends, signs in or writes to a live system.

## What is not known about the platform

| Question | Status | What the pack does |
|---|---|---|
| Can a bot create another bot? | unverified | The lead tries; the fallback is Justin creating each bot and pasting its message |
| Can a bot message another bot? | unverified | Handoffs are files |
| Are private skills shared by every bot on the account? | unverified | Each agent checks and saves what is missing |
| Does each bot have its own time zone setting? | unverified | Set UTC on each; the registry's next-run times show a wrong one |
| Are Auto-review rules per bot or per account? | unknown | Paste them for the lead first; if another agent's first Test asks nothing, paste them there too |
| How many bots does the plan allow? | unknown | Twelve are needed at install. Fewer allowed means Justin picks which agents wait |
| What do twelve agents cost in usage against one? | unknown | Each agent re-reads a shorter memory (one role, not nine). Measured on the test day |

## Adding or removing an agent

Add the role's charter in `roles/`, its section in `TRIGGER-MAP.md`, its line in `team.json` and its skills in `skills.json`; `python3 tools/check.py` fails until every role has exactly one agent and every Revenue OS function has one.
