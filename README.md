# Find Me Money: GrokBot pack

A team of Grok agents, one per role, whose Revenue OS is an incubator for two sites: **Find Me Money** (findmemoneyapp.com: disrupt the finance industry and bring in new leads from people looking for financing, the creative and alternative ways included) and **The Referral Connection** (findreferralpartners.com: attract businesses that want collaborations, partnerships, sponsorships and deals, list them and match them). Nine functions, nine agents (Dream 100, Dream 500, partners, cold email, Lead Radar, content, SpeakerAgent, AEO and SEO, the sales agent), plus the lead agent and three of the business's own (worker, wholesale, loan officer): 13 agents, 19 routines, about 18 runs a day, each function once per site. Justin, 2026-11-20: "it should be in grokbot with each role being its own agent". The team orchestrates; Claude Code and Codex do the thinking on their own subscriptions; browser lanes and high-frequency sweeps stay on Hermes on the Mac.

**One-click install.** Paste this into a new Grok bot named Find Me Money. It becomes the lead and creates the rest of the team ([TEAM.md](TEAM.md)):

> You are Find Me Money, the lead agent of a team. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, unpack it into /workspace/find-me-money/repo/ and follow HANDOFF.md: Part 2 from step 1, which has you create the team from TEAM.md (one agent per role, each its own bot on this account), then Part 3, where each agent builds its own part of the Revenue OS from REVENUE-OS.md for both sites in sites/ (Find Me Money and the referral connection site). Read MASTER-PROMPT.md, CHARTER.md, TEAM.md and sites/README.md first. Do every step that needs nothing from me without stopping. Keep one list of what only I can do and show it to me once, at the end. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

Version 5.0.0. Version 2 was the orchestrator and the Hermes worker; version 3 added the Revenue OS template; version 4 made it an incubator for the two sites; version 5 makes each role its own agent.

| File | What |
|---|---|
| [TEAM.md](TEAM.md), [team.json](team.json), `tools/team.py` | The team: one agent per role, how the lead creates it, how an agent sets itself up, each agent's setup message |
| [REVENUE-OS.md](REVENUE-OS.md) | The build list: which agent is which of the nine functions, what each builds, the check that shows it |
| [TEMPLATE.md](TEMPLATE.md), [agents/](agents/README.md), [agents.json](agents.json) | The Revenue OS spec, one folder per agent (process, status, prompts, script), and the engine each thinks with |
| [sites/](sites/README.md) | One folder per site: `SITE.md` (the goal, what traction means, how each agent works it), `campaign.json`, `settings/` (one file per agent). [The Disruptor message outline](sites/find-me-money/MESSAGING.md) |
| `tools/rc.py` | The referral site's admin API: sign-ups, listings, connection requests, matches, removals, guides |
| [engines/route.py](engines/route.py) | The engine router: every Claude Code and Codex call goes through it and is recorded |
| [convlog/](convlog/), [CONVERSATION-LOG.md](CONVERSATION-LOG.md) | The one log every agent writes every draft, send and reply to |
| [HANDOFF.md](HANDOFF.md) | Justin's steps, then the lead's and the team's, the bring-up order and the first-day test |
| [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md) | Sign-ins, keys by name, yeses |
| [MASTER-PROMPT.md](MASTER-PROMPT.md) | The master prompt every agent saves, above its own role section |
| [CHARTER.md](CHARTER.md) | Purpose, the loop, KPIs, the owner rule, handoffs, workspace, milestones. Wins over a role charter |
| [roles/](roles/) | One charter per agent: lead, dream-100, dream-500, partners, outreach, radar, content, speaker, aeo-seo, sales, worker, wholesale, loan-officer; each with the system prompt section its agent saves |
| [TRIGGER-MAP.md](TRIGGER-MAP.md) | Every step and every routine by agent (19 in all), with exact names |
| [GATES.md](GATES.md) | The gates and the Ask-first lines for Auto-review |
| [guards/](guards/SKILL.md) | The guard scripts: suppression, send, spend, heartbeat, and the owner guard that keeps the bot off live systems' writes |
| [skills.json](skills.json), [SKILLS-MAP.md](SKILLS-MAP.md), [skills/](skills/) | Which role uses which skill and account, and the skills |
| [engine/](engine/) | `hermes_bridge.py` (work orders and results), and the Reply Agent, `fcm`, the scorecard and the job scripts, which now run on the Hermes side |
| [hermes-worker/](hermes-worker/) | The worker for the Mac: `dispatch.py`, the lanes and their fixed prompts, and the paused installer |
| [data/lists/](data/lists/README.md) | Where Justin's private lists go at intake: file names and columns only, never a list |
| [context/](context/) | Lead sources, the Lending Hub, partners and commissions |
| [.env.example](.env.example) | Key names only |
| `tools/check.py` | Completeness and secret check: `python3 tools/check.py --ready` |
| `tools/selftest.py`, `tools/check_campaign.py` | Offline checks of the router, the log and the agents' scripts; the campaign file's check and gap list |
