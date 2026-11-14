# Find Me Money: GrokBot pack

One Grok bot, the orchestrator: nine roles, 12 routines (about 13 runs a day), with the work on Hermes on the Mac and a Codex CLI, for findmemoneyapp.com. Built from the GrokBot Factory template on top of the v1 pack, which this replaces. Idea and Justin's words: [../IDEA.md](../IDEA.md). Rules this build follows: the factory's `PLAYBOOK.md`.

| File | What |
|---|---|
| [HANDOFF.md](HANDOFF.md) | Paste or attach to GrokBot: Justin's steps, then the bot's, the bring-up order and the first-day test |
| [NEEDS-JUSTIN.md](NEEDS-JUSTIN.md) | Sign-ins, keys by name, yeses |
| [MASTER-PROMPT.md](MASTER-PROMPT.md) | The bot's master prompt |
| [CHARTER.md](CHARTER.md) | Purpose, the loop, KPIs, the owner rule, handoffs, workspace, milestones. Wins over a role charter |
| [roles/](roles/) | lead, radar, muse, content, outreach, sales, partners, loan-officer, wholesale; each with a system prompt section to paste |
| [TRIGGER-MAP.md](TRIGGER-MAP.md) | Every step and every routine (29 of 50), with exact names |
| [GATES.md](GATES.md) | The gates and the Ask-first lines for Auto-review |
| [guards/](guards/SKILL.md) | The guard scripts: suppression, send, spend, heartbeat, and the owner guard that keeps the bot off live systems' writes |
| [skills.json](skills.json), [SKILLS-MAP.md](SKILLS-MAP.md), [skills/](skills/) | Which role uses which skill and account, and the skills |
| [engine/](engine/) | `hermes_bridge.py` (work orders and results), and the Reply Agent, `fcm`, the scorecard and the job scripts, which now run on the Hermes side |
| [hermes-worker/](hermes-worker/) | The worker for the Mac: `dispatch.py`, the lanes and their fixed prompts, and the paused installer |
| [context/](context/) | Lead sources, the Lending Hub, partners and commissions |
| [.env.example](.env.example) | Key names only |
| `tools/check.py` | Completeness and secret check: `python3 tools/check.py --ready` |
