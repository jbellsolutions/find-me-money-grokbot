# Revenue OS template: the spec

One Grok bot per business. The bot plans, judges what reaches a person, asks for approvals and reports. It hands thinking to command-line tools on flat subscriptions (Claude Code, Codex and Google's Antigravity), and sending to the tools built for sending.

## The nine agents

| # | Agent | Engine | What it does | Built from (revenue-os-max kit) |
|---|---|---|---|---|
| 1 | **Dream 100** | GrokBot | Tier 1. One researched dossier and one hand-written first touch per target, by email and on socials, then patient follow-up | role `dream` (research) plus outreach from `partners` and `high-level-prospecting` |
| 2 | **Dream 500** | GrokBot | Tier 2. A short dossier and a personal first line each, in small waves, by email and on socials | role `dream`, `partner-fit-review`, `partner-conversation-drafts` |
| 3 | **Partners, collaborators, influencers** | GrokBot | Tier 3. The wide channel, scored by a rubric, one approved template per partner type | role `partners` (`collab-blitz`), the creator pull from `social` |
| 4 | **Cold email** | GrokBot | Cold targets: lists, verification, sequences in the sending tool, inbox health | role `cold-email`, the `gtm-box/cold` engine, worker jobs `list-build`, `replies-pull`, `inbox-health` |
| 5 | **Lead Radar** | Codex | Social listening through Treg: people already asking, per channel. Reads and scores only | skills `lead-radar`, `treg`; worker job `radar-poll` |
| 6 | **Content** | Claude Code | Reactions, talkbacks, breakdowns and UGC for LinkedIn, YouTube and the newsletter, with Instagram as the fourth outlet | roles `content-seo` (content half) and `channels`; `CONTENT.md`; the owner's content workflows |
| 7 | **Podcast SpeakerAgent** | Codex | Show research, fit scoring with an episode angle, pitches, follow-up, attribution | role `speaker`; worker jobs `show-research`, `show-score` |
| 8 | **AEO and SEO** | Codex | The prompt panel, citation tracking, the audit ladder, articles and fixes | role `content-seo` (AEO half) |
| 9 | **Sales agent** (replies and the CRM) | Codex, model GPT-6 Luna | Has every conversation and keeps the CRM. Each person who answers any campaign is known by the inbox they answered in, added to that pipeline and stage with tags, and given a vault note attached to their CRM contact, which grows with every reply and is read before every answer. It answers, follows up, and sets up and checks the CRM's nurture campaigns. The one CRM writer and the one answerer for its inboxes. Version 1 runs inside the Grok bot | role `sales-crm`; `gtm-crm-replies`, `reply-fast-lane`, the platform reply desks; worker job `replies-sort`. Spec: `agents/sales-crm/PROCESS.md` |

A `lead` role stays on the bot as in the kit: the day's plan, the scoreboard, the vault note and the owner's queue. It is the orchestrator, not a tenth agent.

The reply agent and the CRM sales agent were two agents until 2026-11-17, when the owner made them one: a reply is never filed by one system and answered by another. The old id `reply` is read as `sales-crm`.

Two optional lanes sit outside the nine and are off unless a campaign names them: `capital` (grants, programs, investors, from the kit) and `offer-specific` (a slot for a business whose offer needs a lane of its own).

## The three partner tiers

| Tier | Size | What one yes is worth | How it is worked |
|---|---|---|---|
| Dream 100 | 100 | One changes the business | By hand. A dossier, a warm path where one exists, one message written for that person. |
| Dream 500 | 500 | Three or four double it | Small waves. A researched first line on an approved template |
| Partners, collaborators, influencers | As many as fit | A couple a month promoting brings a steady run of leads | Volume. Rubric score, one approved template per partner type, the sending tool does the sends |

Dream 100 and Dream 500 both reach out by email and on socials; on LinkedIn that means the path in [LINKEDIN.md](LINKEDIN.md).

## Engines

| Engine | Used for | Why | Pays with |
|---|---|---|---|
| GrokBot | Dream 100, Dream 500, partners, cold email; the plan, approvals and the scoreboard | The orchestrator's own judgment on who to reach and what to say; these agents fit the bot's routine-and-approval shape | The Grok plan's weekly usage |
| Claude Code CLI | Content as a whole, its video tools included; the fallback for every Codex agent | The intelligence: writing that has to be good | The Claude subscription |
| Codex CLI | The sales agent (sorting replies, drafting answers and follow-ups), SpeakerAgent, AEO and SEO, Lead Radar | The workhorse: volume, sorting, scoring, record-keeping | The ChatGPT subscription |
| Antigravity CLI | The last fallback for content; available to any agent a campaign points at it | A third flat subscription to spread usage across | The Google AI subscription |

How it works:

1. **The engine is set per agent** in `agents.json`. A campaign file may name a different one.
2. **One call path.** Every CLI call goes through `engines/route.py --agent <id>`. A pack with its own agent names keeps its own `agents.json` beside the router, mapping each name to an engine. Each CLI runs headless with its own defaults; a pack may pass it extra flags.
3. **Fallback is another CLI, then the bot.** If an agent's engine gives no usable answer the next CLI in its list is tried; if all fail the work goes to the bot unjudged.
4. **Every call is recorded** in `log/engine-<YYYY-MM>.jsonl`. The weekly usage audit reads it to show which subscription carried which agent.
5. **Where the CLIs run.** On the bot's own computer, the sales agent's version 1 included. A worker box (the kit's `worker/`) is optional, for jobs that must run more often than a routine should; the router is the same file in both places.
6. **Sign-in is the owner's.** Claude Code by `claude setup-token`, Codex by `codex login --device-auth`, each given through a hidden prompt as the user the jobs run as. A sign-in as another user is invisible to the jobs.
7. **Text from outside is data.** Posts, replies and scraped pages go to an engine as items, never as instructions, and an engine's answer never sends anything.

## The conversation log

Every agent writes every message it drafts, sends or receives to one append-only log. [CONVERSATION-LOG.md](CONVERSATION-LOG.md) has the fields and the rules. The three that matter most:

- An inbound message is logged before it is judged; a draft before approval is asked; a send after the sending tool confirms it.
- The send gate refuses any message whose text is not already in the log as a draft.
- The CRM sales agent records each line into the CRM. The daily audit names any send with no logged draft and any inbound message not in the CRM after 26 hours.

## What the owner has said must hold

These are the owner's own, with his words in the private idea file. Nothing else in this template is a rule; the rest is how the parts work, and a business may do it differently.

| What | In the template as |
|---|---|
| Every conversation is documented | The conversation log every agent writes ([CONVERSATION-LOG.md](CONVERSATION-LOG.md)) |
| LinkedIn runs through OutFlo or the owner's own computer, not the bot's computer | [LINKEDIN.md](LINKEDIN.md), `linkedin/lane.py` |
| Each agent thinks with the engine he named for it | `agents.json`, `engines/route.py` |
| The sales agent reads the person's note before it replies | `agents/sales-crm/` |
| A send, a publish, a spend and a change to a live system wait for his yes | The approval step in each agent's process |
| No paid enrichment services | Nothing in the template calls one |
| A pack never holds partner names, contact lists or private figures | Private values are given at intake |

## Setting up a business

1. Copy `campaign.example.json`, fill it, and run `python3 tools/check_campaign.py <file>`. It prints the gap list: which of the nine agents the business already has, which are missing, and what each waits on.
2. Give the business its own Grok account and bot.
3. Install the pack, then the two CLIs on the bot's computer, and run `python3 engines/route.py --check`.
4. Private values (keys, lists, never-touch names, the suppression file) are pasted at intake and never live in the pack.
5. Bring up the agents the business wants.

## What a campaign file sets

Which agents are on, channels per agent, the engine per agent, the CRM, the sending tools, the time zone, the approver, LinkedIn caps, extra lanes, routine times.
