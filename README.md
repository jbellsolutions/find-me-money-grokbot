# Find Me Money: GrokBot pack

One Grok bot that builds and runs the Revenue OS for findmemoneyapp.com: nine agents (Dream 100, Dream 500, partners, cold email, Lead Radar, content, SpeakerAgent, AEO and SEO, the sales agent) worked by nine roles in 15 routines, about 14 runs a day. The bot orchestrates; Claude Code and Codex do the thinking on their own subscriptions; browser lanes and high-frequency sweeps stay on Hermes on the Mac.

**One-click install.** Paste this into a new Grok bot named Find Me Money:

> You are Find Me Money. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, unpack it into /workspace/find-me-money/repo/ and follow HANDOFF.md: Part 2 from step 1, then Part 3, which builds the Revenue OS from REVENUE-OS.md. Read MASTER-PROMPT.md and CHARTER.md first. Do every step that needs nothing from me without stopping. Keep one list of what only I can do and show it to me once, at the end. Nothing sends, posts, spends or writes to a CRM until I say yes in this chat.

Version 3.0.0. Version 2 was the orchestrator and the Hermes worker; version 3 adds the Revenue OS template.

| File | What |
|---|---|
| [REVENUE-OS.md](REVENUE-OS.md) | The bot's build list: which role works which of the nine agents, what to build for each, the check that shows it |
| [TEMPLATE.md](TEMPLATE.md), [agents/](agents/README.md), [agents.json](agents.json) | The Revenue OS spec, one folder per agent (process, status, prompts, script), and the engine each thinks with |
| [campaign.json](campaign.json), [settings/](settings/) | Find Me Money's Revenue OS settings: one file for the business, one per agent |
| [engines/route.py](engines/route.py) | The engine router: every Claude Code and Codex call goes through it and is recorded |
| [convlog/](convlog/), [CONVERSATION-LOG.md](CONVERSATION-LOG.md) | The one log every agent writes every draft, send and reply to |
| [HANDOFF.md](HANDOFF.md) | Paste or attach to GrokBot: Justin's steps, then the bot's, the bring-up order and the first-day test |
| [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md) | Sign-ins, keys by name, yeses |
| [MASTER-PROMPT.md](MASTER-PROMPT.md) | The bot's master prompt |
| [CHARTER.md](CHARTER.md) | Purpose, the loop, KPIs, the owner rule, handoffs, workspace, milestones. Wins over a role charter |
| [roles/](roles/) | lead, worker, radar, content, outreach, sales, partners, loan-officer, wholesale; each with a system prompt section to paste |
| [TRIGGER-MAP.md](TRIGGER-MAP.md) | Every step and every routine (15 of 50), with exact names |
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
