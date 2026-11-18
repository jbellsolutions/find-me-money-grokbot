# The sales agent: the process

One agent answers people and keeps the CRM. When someone writes back, it adds them to the CRM, moves them in the pipeline, writes it down, makes their contact card and their note in the vault, answers them, and follows up until they book a call or say no.

The owner, 2026-11-17: "I'm realizing that this actually is a reply agent as well, right? This will be combined with the reply agent." "We want to make sure that agent is also the CRM sales agent, handling replies, adding people to the CRM, creating a vault contact card, and making sure everything is getting created. We also want to make sure that each person is being replied to and followed up with appropriately." "We want to make sure that happens on its own computer, on the Orgo computer." "Yes, we'll use the Codex subscription and the ChatGPT CLI. GPT-6 Luna is the model."

The owner to the main chat, later the same day: "They're not sorted. They're coming through channels, but those channels are designated to agents. The Dream 100 will be through my personal email. Dream 500, partner collabs, and cold leads will be through cold email inboxes, so it'll know based off of channel where the leads are coming from." "The Obsidian note is created and then attached to the person's GoHighLevel contact, and then it's updated as the conversation is being had and progresses. Every reply gets added to that person's Obsidian note, a record of note, and there's a rule to check that note first before replying." "The agent is responsible for nurturing follow-up. That's setting up follow-up nurture campaigns, letting those run, and just checking on those. We'll have a daily task to check on those." "This agent now is a Hermes agent on Orgo AI computer. This agent here, though, is a V1 of the sales agent inside of GrokBot."

## Rules

The only rules here are the ones the owner stated. They are listed with his words in [STATUS.md](STATUS.md), with the ones this page had that he never stated (now removed), and nine that are still in and waiting on his keep or remove. Below, "(list N)" marks one of those nine.

## What his words settle

| Point | Settled as |
|---|---|
| Reply and the CRM sales agent | One agent. It answers the replies and keeps the CRM, so a reply is not filed by one system and answered by another |
| Where it runs | Version 1 runs inside the Grok bot, thinking on the Codex CLI. Today's sales agent is a Hermes agent on an Orgo computer; that one is not changed by this spec |
| Where a person comes from | Nothing sorts a person into lead or partner. Each inbox belongs to one outreach agent, so the inbox a reply arrives in says who they are: Dream 100 through the owner's personal email; Dream 500, partners and collaborators, and cold leads through the cold email inboxes |
| The person's note | Made in the vault, attached to the person's contact in the CRM, and added to on every reply for as long as the conversation runs. The note is read before any answer is drafted, so each message is written for that person |
| Nurture and follow-up | This agent's job: it sets up the follow-up and nurture campaigns in the CRM, lets them run, and checks on them in a daily task |
| What it thinks with | The Codex CLI on the ChatGPT subscription, model GPT-6 Luna, for sorting and for drafting |
| The vault | An Obsidian vault is the CRM's memory: one note per person, the pipeline, the day. If the owner cannot open it in Obsidian and see the person, the step is not done |

## How it is built

These are this chat's design, not rules. Any of them can change.

- **Scripts do the work and Codex judges.** Code reads the inbox, writes the CRM and the vault, and sends. Codex gets one batch of replies or one draft at a time through the router. This is what keeps a prompt-in, answer-out CLI enough.
- **The CRM gets one note per conversation per day** with a link to the vault note; the full text stays in the log and the vault.
- **Claude Code is the fallback** when Codex gives no usable answer, as the router already does.

## The loop for one reply

| # | Step | Who |
|---|---|---|
| 1 | **Read.** Each inbox in the settings is read by its own path. Every new message becomes `{id, channel, person, thread, text, received_at, inbox, from_agent}`. `from_agent` is the outreach agent the inbox belongs to in the settings. An inbox with no reader is reported as blocked | Code |
| 2 | **Log.** `convlog.py add --agent sales-crm --direction in`. Every conversation is documented (his words, 2026-11-16) | Code |
| 3 | **Opt-outs, bounces, automatic replies.** An opt-out in any wording the list knows goes to suppression and is not answered (list 1). Bounces and automatic replies are set aside | Code |
| 4 | **Sort.** `route.py --agent sales-crm --prompt prompts/sort.md --in replies.json`: one intent, the facts they stated, a dated next step, and whether an answer is wanted. A reply no engine sorted goes to the owner's queue unsorted | Codex |
| 5 | **The CRM.** Find the person or add them. The pipeline and the source tag come from `from_agent` (the inbox), the other tags and the stage from the intent (table below). Blank fields are filled; a value already there is left (list 5). One note for the day's conversation, one dated task for the next step. Then `convlog.py mark-crm <id> <crm-ref>` | Code |
| 6 | **The person's note.** `People/<person>.md` is made on the first reply and attached to the person's CRM contact (the contact carries the note's link and the day's summary). Every later reply and every answer is added to the same note, in order. It holds: who they are, where they came from, the facts so far, the stage, the next step and its date, every message in order. Address and phone number stay in the CRM, not the note (list 7). `Pipeline/` and `Daily/<date>.md` are rewritten from the same data | Code |
| 7 | **Read the note first, then draft**, where the intent wants an answer (his rule, 2026-11-17). The script loads the person's note and does not ask for a draft without it; a person with no note goes back to step 6. `route.py --agent sales-crm --mode write --prompt prompts/reply.md` with the note and the thread as context | Codex |
| 8 | **Check the draft** in code, for the listed items only: not addressed to an opted-out person (list 1), no price, terms or promise (list 4). A failed draft is redone once, then goes to the owner as it is, marked | Code |
| 9 | **Log the draft**, then put it in the owner's queue with the person's note beside it. A send needs his yes (his standing rule) | Code |
| 10 | **Send** through the channel's own sending path once he says yes, or at once where he has marked that message type auto. LinkedIn goes by OutFlo or the local computer (his words, 2026-11-16). `sent` is logged after the tool confirms it. The CRM note and the vault note get the answer | Code |

## What each intent does

| Intent | Pipeline | Next step | Answer |
|---|---|---|---|
| `interested` | To the first stage | Answer today | Yes: `reply_book_call` |
| `question` | No move | Answer today | Yes: answer what they asked |
| `referral` | No move; the named person is added as a new lead with the source | Reach the new person; thank the sender | Yes: a thank-you. The first touch to the new person is an opener |
| `not_now` | Tagged later | The date they gave, or the settings' default | A one-line acknowledgement, if the settings say so |
| `not_interested` | Closed as lost, reason in the note | None | No |
| `opt_out` | Suppressed in step 3 (list 1) | None | No |
| `wrong_person` | Closed; a named right person is added like a referral | As referral | Optional thank-you |
| `auto_reply`, `bounce` | No move | Out-of-office: the return date. Bounce: marked bad address | No |
| `complaint`, `identity_question`, `price_or_terms` | No move, flagged | The owner, today | No draft: the owner's (list 3 and 4) |
| `other` | No move | The owner reads it | No |

## Follow-up

"Each person is being replied to and followed up with appropriately."

- **The sweep**, twice a day: for every open person it fills in a next action and a date where one is missing, and lists what is overdue, worst first.
- **Quiet threads.** Where our message was the last one and the thread has been quiet for `quiet_business_days`, one short follow-up is drafted (`prompts/follow-up.md`). The settings stop this at `max_follow_ups` a thread (list 8); after the last one the person is tagged later with a date.
- **Nurture campaigns.** The agent sets up the follow-up and nurture email campaigns in the CRM, puts people in by stage and tag, and lets them run. A campaign's emails go to the owner once, as a whole, before it sends (a send needs his yes). A person who replies leaves the campaign and comes back to the loop above.
- **The daily nurture check**, one task a day: each campaign is running, who entered and left, replies it produced, bounces and opt-outs, and anyone stuck in a campaign past its last email. Anything wrong goes to the owner's queue. It checks; it does not change a campaign.
- **Dated returns.** A "not now" or an out-of-office comes back on its date as a draft.
- **A booking** moves the stage, writes a call brief from the person's note, and stops follow-ups. A no-show gets a dated next step the same day.
- **The day close.** `convlog.py audit` runs (a send without a logged draft, an inbound message not in the CRM after 26 hours), and the scoreboard gets its result with the day's replies, answers, bookings, open people with no dated next step, and what is waiting on the owner.

## The CRM and the inboxes

- **The other agents hand over.** Cold email, Lead Radar, the partner tiers, content and SpeakerAgent pass a reply that reaches them, and every new person they want in the CRM, to this agent as a hand-over row; it enters at step 2. This agent is the one that writes the CRM (list 6).
- **Each inbox is in the settings** with the outreach agent it belongs to, how it is read and how it is answered.
- **Forms and CRM automations** may still add people. This agent fills blanks and leaves pipelines marked read-only alone (list 5).
- **Where the CRM is not the bot's to write** (`crm.writer: none` in the campaign file), steps 5 and 10's CRM part are replaced by the day file (`convlog.py daily --mark`), handed to whoever keeps that CRM. The vault, the answers and the follow-up still run.
- **A business that already has a live reply agent or CRM agent:** changing or switching off a live agent needs the owner's yes (his standing rule).

## Where it runs

Version 1 runs inside the Grok bot: the bot's routines start the scripts, the scripts call the Codex CLI through the router, and the owner's queue is the bot's. The conversation log and the vault sit in the bot's workspace with every other agent's lines, so no line has to cross between computers.

Today's sales agent is a Hermes agent on an Orgo computer. This spec does not change it. Where a business has both, which one holds each inbox is the owner's to say (question 1 below).

## The engine

`engines/route.py --agent sales-crm`. The router asks Codex for the model in `agents.json` (`gpt-6-luna`) itself. Checked 2026-11-17 on a Mac: three made-up replies sorted correctly in one call. Not checked on a Grok bot's computer.

The owner, 2026-11-17: Codex is the engine "if it uses the Codex CLI and is reliable there, and we can keep usage down". And: "Let's try that first, and then, if the usage isn't working well or the system isn't working well, we can always publish the agent on Orgo like how it is now." So this is a trial with a way back, on two conditions, and each has a measure:

| Condition | How it is kept | How it is measured |
|---|---|---|
| Reliable | Code does every read, write and send; Codex only judges one batch of replies or writes one draft. An answer that does not parse is retried on Claude Code, then goes to the owner unsorted | `log/engine-<YYYY-MM>.jsonl`: the share of `sales-crm` calls with `ok: true`, and how often the fallback carried the work |
| Usage down | The reply check is a script; Codex is called only when there is a new reply, replies are sorted in one batch per run, and a draft is written only for an intent that wants one | The same file: calls a day and characters in and out, read in the weekly usage audit |

The way back, if either measure is bad: the same scripts, prompts and settings run as an agent on an Orgo computer, as the sales agent does today. Nothing in this spec depends on the bot's computer except where the routines start.

Not proven yet: whether a Grok bot's computer keeps the Codex CLI signed in between runs. That is the first thing the test day shows.

## Message types

Every type starts as `ask`: a send needs the owner's yes. From the CRM agent: `crm_opener`, `crm_follow_up`, `warm_reconnect`, `crm_nurture` (a nurture campaign, shown once as a whole). From the reply agent: `email_reply`, `reply_book_call`, `linkedin_reply`, `linkedin_comment`, `x_reply`, `instagram_reply`, `youtube_reply`, `skool_reply`, `sms_reply`. A type can run only where its channel has an inbox in the settings with both a reader and a sending path. SMS is off until carrier registration is approved (list 9).

## Not built yet

1. The code for steps 1, 5, 6 and 8 as one runner. The kit's CRM scripts do most of 5 and part of 6 for one CRM product; the original's package does the same for its business. Neither calls the log or the router.
2. The line from a logged message to a CRM note (`pending-crm` to the CRM to `mark-crm`).
3. Readers for X, Instagram, YouTube and Facebook comments and DMs, and for SMS.
4. Opt-out words outside email (a "stop" in a DM or a comment).
5. Setting up a nurture campaign in the CRM from code, and the daily check's read of it.
6. Attaching the note to the CRM contact (the link field and the summary).
7. The stage map, tag prefix and owner as settings in the kit's scripts; today they are one business's file.

## Still the owner's to say

1. **Where the Hermes agent is live**, per business: when version 1 takes an inbox over from it, or whether it stays the answerer and version 1 only drafts.
2. **Dream 500, partners and cold leads share the cold email inboxes.** Built as: each cold email inbox, or each campaign in the sending tool, belongs to one of the three, so the reply still says which. Say if they share inboxes with no such split.
3. **The first public answer to a stranger** Lead Radar found: this agent's job too, or does that stay with the business that already does it.
4. **Calls, meetings and messages typed by hand**: recorded by this agent from recordings and screenshots, or outside its job.
5. **Which types go auto.** The booking answer on approved words is the usual first.
6. **Who it answers as**: the owner in the first person, or a named persona where a business uses one.
7. **The nine rules on the keep-or-remove list** at the top of `STATUS.md`.
