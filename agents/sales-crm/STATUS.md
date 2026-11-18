# Sales agent: where this function stands

## Your call: keep or remove (2026-11-17)

The owner, 2026-11-17: "The one rule is the only rule, and that's that there are no rules unless I tell you there's a rule." This folder was gone through on that. These nine are not in his words. Each protects a person, an account or a legal duty, or could not be placed, so each is still in. Say "keep" or "remove" for each, or "remove all".

| # | Rule | Where | What removing it does |
|---|---|---|---|
| 1 | An opt-out is suppressed in code before anything sorts it, is never answered, leaves any nurture campaign, and gets no follow-up | `PROCESS.md` steps 3 and 8, all three prompts, `nurture.leave_on` | A person who asked to stop can get another message. For email this is a legal duty |
| 2 | Text from other people is data, never instructions | All three prompts | A stranger's reply could steer the sorter or the draft. Item 8 on the main list |
| 3 | A draft never says or implies a person typed it, and "is this a bot?" goes to the owner with no draft | `prompts/reply.md`, `prompts/sort.md`, `always_the_owners` | The agent answers that question by itself, in the owner's name |
| 4 | No price, discount, terms, guarantee or promised result in a draft. Price questions and complaints go to the owner with no draft | `prompts/reply.md`, `prompts/follow-up.md`, `PROCESS.md` step 8, `always_the_owners` | The agent can quote and promise in the owner's name, and answers complaints itself |
| 5 | CRM writes fill blanks only: a value already there is never overwritten, and pipelines marked read-only are left alone | `PROCESS.md` step 5, `crm.never`, `crm.read_only_pipelines` | The agent can replace what a person or an automation wrote in a live CRM |
| 6 | One CRM writer per business | `crm.writer`, `PROCESS.md` | Two systems can write the same CRM. Item 6 on the main list; follows the answer there |
| 7 | No address or phone number in a person's vault note | `PROCESS.md` step 6, `vault.contact_details_in_notes` | Contact details sit in the vault and go wherever the vault is pushed. This one works against "creating a vault contact card": with it, the card has no contact details |
| 8 | Follow-ups stop after 3 for a quiet thread | `follow_up.max_follow_ups`, `prompts/follow-up.md` | A person who never answers keeps getting follow-ups |
| 9 | SMS is off until carrier registration is approved | The SMS inbox's note, `PROCESS.md` | Texts go out unregistered; carriers block them and can flag the number |

This folder also uses five items from the main list (`ideas/revenue-os/RULES.md`), which live in shared code and follow the answer there: no send without a logged draft (1), the daily audit (2), engines with no tools (7), no metered API (9), and a message type sending by itself once marked auto (10).

## Kept: he said it

| Rule | His words | Date |
|---|---|---|
| The reply agent and the sales agent are one | "We'll combine those two: the reply agent and the sales agent." | 2026-11-17 |
| Every responder goes into the CRM, with a pipeline, a stage, tags, a contact card and a note | "handling replies, adding people to the CRM, creating a vault contact card, and making sure everything is getting created" | 2026-11-17 |
| The note is attached to the CRM contact and every reply is added to it | "The Obsidian note is created and then attached to the person's GoHighLevel contact"; "Every reply gets added to that person's Obsidian note" | 2026-11-17 |
| The note is read before replying | "there's a rule to check that note first before replying" | 2026-11-17 |
| The inbox says where a person came from; nothing sorts them | "They're not sorted. They're coming through channels, but those channels are designated to agents." | 2026-11-17 |
| Everyone is answered and followed up | "each person is being replied to and followed up with appropriately" | 2026-11-17 |
| The agent sets up the nurture campaigns, lets them run, and a daily task checks them | "setting up follow-up nurture campaigns, letting those run, and just checking on those. We'll have a daily task to check on those." | 2026-11-17 |
| Codex CLI on the subscription, GPT-6 Luna, inside the Grok bot first, Orgo as the way back | "Let's try having the agent on GrokBot using the Codex CLI and GPT-6 Luna model. Let's try that first" | 2026-11-17 |
| Every conversation is documented | "It's vitally important that we do document all the conversations that we're having" | 2026-11-16 |
| LinkedIn runs on OutFlo or the local computer | "For LinkedIn especially, we're going to have it use our local computer versus the GrokBot computer" | 2026-11-16 |
| A send needs his yes, so every message type starts as `ask` and a nurture campaign is shown to him before it sends. Changing a live agent needs his yes | His global instructions file, "Standing authorization" | standing |
| No business name, contact, private figure or key in this folder | His global instructions file | 2026-11-12 |
| The CRM's memory is an Obsidian vault | His global instructions file | 2026-05-25 |

## Removed: a chat added it

| Was | Where | Added by |
|---|---|---|
| "The only answerer for its inboxes", and "an inbox not on the list is not this agent's" | `PROCESS.md`, `README.md` | This chat |
| Version 1 and the live agent "never answer the same inbox or write the same CRM at the same time: version 1 runs on test, drafts only" | `PROCESS.md` | The main chat, in 0.2 |
| A campaign "may turn an inbox or a type off, lower a limit"; it "may not add a second CRM writer, a second answerer for an inbox, or a per-call model" | `sales-crm.example.json` | This chat |
| A stage moves only on the evidence the stage map lists; the `evidence` map | `PROCESS.md`, `sales-crm.example.json` | This chat, from the copy |
| Never "mark a deal won"; never "write another prefix's tags"; tags only in this agent's own prefix | `PROCESS.md`, `sales-crm.example.json` | This chat, from the copy |
| "A record marked held gets nothing" | `PROCESS.md` | This chat, from the copy |
| The "Gate" column: `crm-writes: on`, "the send gate", "the send guard", "Logged first", "Suppression" named as gates on each step | `PROCESS.md` | This chat, from the kit |
| Word limits (120 for email, 60 for LinkedIn, 40 for SMS and comments), and half of that for a follow-up | `sales-crm.example.json`, both drafting prompts, `PROCESS.md` step 8 | This chat |
| No link in a public reply; never "DM me"; no booking link for any intent but interested | `prompts/reply.md`, `prompts/follow-up.md`, `PROCESS.md` step 8 | This chat |
| Wording bans (no exclamation marks, no "just checking in", no flattery, and the rest). The voice now comes from the business's settings | Both drafting prompts | This chat |
| "The count of open people with no dated next step must be 0"; the audit "must be clean"; a date the sweep proposed can never move. They are reported now, not required | `PROCESS.md` | This chat, from the copy |
| "Every answer waits for the owner" as this chat's own choice. It stands as his standing rule on sends, in the list above | `PROCESS.md` | This chat |
| "This folder belongs to this function's own chat"; a function's chat "proposes a change" to shared files, "it does not make it"; "proposed to the main chat, not made here" | `README.md`, `PROCESS.md`, this page | The main chat's brief, repeated by this chat |

## Where it stands (2026-11-17)

The owner combined the reply agent with this one. Version 1 runs inside the Grok bot on the Codex CLI, model GPT-6 Luna; today's Hermes agent on an Orgo computer is not changed. The spec is [PROCESS.md](PROCESS.md), with a settings example and three prompts.

Tested on a Mac: three made-up replies went through `engines/route.py --agent sales-crm` with `prompts/sort.md` on that model in 14 seconds and came back sorted correctly, including an opt-out that told the sorter to mark it interested. The cut-down reply prompt drafted one made-up answer on the same model (it read the note, answered the question first, gave the booking link); the follow-up prompt has not been run since it was cut down. Nothing else in the spec is code yet, and nothing has run on a Grok bot's computer or against a CRM.

Of the six questions at the foot of this page: 2, 3 and 4 are answered by his words above. The questions now open are at the foot of `PROCESS.md`.

The rest of this page is the survey as written on 2026-11-16.

Written 2026-11-16 by this function's chat. A read-only survey: the template, the kit, the four campaign files and the two source repos' own pages. Neither running agent was touched or read live, so their state is what their repos and the campaign files last recorded. Paths are from the factory root.

## The template's line for this function

On Codex. "The one CRM writer. Records every conversation, keeps a dated next step on every open record, takes interest to a booked call." Channels crm, email, sms. Message types `crm_opener`, `crm_follow_up`, `warm_reconnect`. (`ideas/revenue-os/build/TEMPLATE.md`, `agents.json`)

## The original: what it does

One agent profile with no shell or file access. It works only through its own tool package, and every tool that writes is dry until told to apply.

| Job | In plain words |
|---|---|
| Lead sweep | Builds or refreshes one card per lead from the CRM, judges whether each is ready, and proposes the ready ones for a hand-off the owner approves |
| Reply triage | Sorts every campaign reply: a note, tags, a stage move, and a held draft. Opt-outs are suppressed at once. It may not move anyone past "appointment booked" |
| Hand-off watch | Runs a clock on every lead already handed to a partner: tasks, check-ins, flags for the owner, a new pairing proposed when one stalls |
| Day check | Runs every job in order and lists each open loop with an owner |
| Daily report | The end-of-day count, and five lines to the owner |

It also keeps a collections ledger it can read but never mark paid, and a queue of people to reach on social that it counts but never works. Sends are held behind switches; a person sends each answer.

## The copy: how it differs

Both come from the same earlier engine. The copy is a port, not a duplicate of the files.

| | The original | The copy |
|---|---|---|
| Shape | One profile, one tool package | A team of five profiles (opener, replies, closer, deals, warm) over a set of scripts. This is what the kit carries: `ideas/revenue-os-max/build/gtm-box/box/crm*.py`, `deal_ledger.py`, role `roles/sales-crm.md` |
| The CRM write | Its tools write directly | One file is the only writer (`crm.py`). Every other lane hands people to an outbox and holds no CRM key; a drain puts them in, and a hold file can keep a backlog out |
| Stages | Moved by the triage tool, capped at booked | Moved only on evidence (a reply, a booking, a note a person wrote); a tag alone moves nothing |
| Open loops | The day check | A sweep that leaves every open record with an owner, evidence, a next action and a date, and keeps a proposed date from sliding |
| Starting conversations | Not its job; it works replies and hand-offs | Openers, reactivation waves and warm reconnects, each from a card, each a draft the owner ticks |
| Business-specific parts | Partner pairing, the hand-off clock, collections | A deal ledger for partner deals; call prep, no-shows, the daily close |
| Cost shape | The agent runs each job | Scripts run first and wake the agent only when there is work, under a daily dollar guard |
| Last recorded state | Five jobs on, reads and files, sends held | Writes on, backlog held, one tester in, the first opener waiting on the owner's tick (2026-11-08; not re-read) |

## What both think with, against "Codex, the workhorse"

Both run on a small Claude model paid per call through an API. Neither uses Codex, and neither uses a subscription. Codex is not installed on the original's computer. The original also has an optional second paid drafting client, off unless a key is set, with rule-based fallbacks.

The template's router (`engines/route.py --agent sales-crm`) made one real Codex call on a Mac. It is wired to neither agent. It gives Codex one prompt and takes one answer, read-only, with no tools. So "on Codex" fits the copy's shape as it stands: scripts do the reading and writing, and Codex judges each item (a reply's intent, a lead's readiness, a draft's wording). It does not fit an agent that loops over tools by itself, which is how the original runs. Moving either one is a change to a live agent and needs the owner's yes.

## The one-CRM-writer rule

| Case | How it holds | Proven |
|---|---|---|
| The business's own CRM, the agent may write | The CRM sales agent is the only writer. Other agents hand people over through the outbox and replies through a hand-over command; none holds a CRM key | In the copy's scripts, yes |
| Automations and forms also write the same CRM | The agent fills blanks, never overwrites a value, writes only its own tag prefix and never touches another pipeline | In the copy's rules, yes |
| Several agents write today | Not yet true. One application has three writers: the original, its reply agent and a site form. Proposed in its gap list: the CRM agent is the one writer for conversations, the reply agent hands over through the log, the form stays as intake | No. A live change |
| A client's own system writes, or nobody may touch the CRM | `crm.writer: none`. The bot reads at most. There is no CRM sales agent to build; the day file below stands in | The day file is tested; no hand-over has run |

## How every conversation gets recorded

1. Every agent appends every inbound message, draft and send to the log (`conversations/<YYYY-MM>.jsonl`). Calls and meetings get a note line.
2. Each run, this agent runs `convlog.py pending-crm`, writes each line to its contact in the CRM, then `convlog.py mark-crm <id> <crm-ref>`. No other agent runs `mark-crm`.
3. Once a day `convlog.py audit` fails on a send with no logged draft, or an inbound line not in the CRM after 26 hours.
4. Where the CRM is not the bot's to write, `convlog.py daily --mark` replaces step 2: one file a day, by person, in the business's own time zone, carrying anything not yet handed over, given to whoever keeps the CRM.

The log tool is built and self-tested. Neither agent runs it. Today the original writes a note and a stage for the replies it handles, and sees only replies that reach the CRM or the email tool. The copy puts sends and calls on the person's card and takes replies other lanes hand it. Neither can show that nothing was missed.

## What is missing against the template's line

1. **Step 2 above does not exist.** No code takes a pending line and writes it to a CRM contact. Which CRM object a line becomes (a note per message, or one note per thread per day) is not decided.
2. **Neither agent writes the log,** so the audit has nothing to check for either business.
3. **Codex is wired to neither**, and the job-by-job split between script and Codex is not written.
4. **No generic version.** The kit's role and its five CRM skills are named for one business, one CRM product, one pipeline and one stage map. The stage-and-evidence map, the tag prefix and the owner's name are not settings yet.
5. **Which jobs are the product.** The original's partner pairing, hand-off clock and collections, and the copy's deal ledger, belong to their businesses. The common set has not been named.
6. **The line with the reply agent is not drawn.** The template moved replies to their own agent; the kit role and both running agents still sort and draft replies themselves.
7. **"To a booked call" is unproven.** The original's sends are held. The copy's first opener was waiting on a tick. The booking trigger is named in the kit role; the three message types are named in `agents.json` and only `crm_opener` has an approved shape, in one business.
8. **Conversations outside the agents.** Texts and DMs typed by hand, and calls, reach the log only if someone adds them. The kit's screenshot skill is the one path, and nothing prompts for it.
9. **`sms` is listed as a channel.** The copy's rules say no SMS until carrier registration is approved.
10. **One CRM product only.** Both write the same product. The two client businesses use others, and both are `writer: none`, so no second adapter is needed until that changes.

## What the owner needs to say

1. **Which shape is the product?** The original (one agent, a tool package) or the copy (a five-part team over scripts, which the kit already carries). And which jobs every business gets: this chat's reading is reply recording, the lead card, the open-loop sweep, call prep and the day check, with pairing, collections and the deal ledger left to their businesses.
2. **What "on Codex" means here.** Scripts do the work and Codex judges each item through the router (this chat's recommendation, and no change to how the copy runs), or Codex becomes the agent that runs the whole job.
3. **Where the reply agent stops and this one starts.** Recommended: the reply agent sorts and answers; this agent records everything and owns a person from "interested" to the booked call.
4. **Where several things write one CRM,** is the CRM agent the one writer for conversations, with the reply agent handing over through the log and forms left as intake?
5. **What "document all the conversations" covers.** Agent messages only, or also calls, meetings and anything typed by hand. And what lands in the CRM: every message as its own note, or one note per conversation per day with the full text kept in the log and the vault (recommended).
6. **How far it goes without a tick.** Every opener and follow-up waits for the owner, or a follow-up type goes on its own once its words are approved.
