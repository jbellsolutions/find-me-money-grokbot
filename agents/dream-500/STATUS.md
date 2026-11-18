# Dream 500: where this function stands

Updated 2026-11-17 after the one-rule cleanup. The owner that day: "there are no rules unless I tell you there's a rule... Go through and remove every rule that I didn't explicitly tell you."

## Keep or remove: the owner's call

None of these is in his words. Each protects a person, an account or a legal duty, so it was left in place. Say "keep" or "remove" for each, or "remove all".

| # | Rule | Where | What removing it does |
|---|---|---|---|
| 1 | Each row is checked against the opt-out and never-touch lists before a draft, and a "no" or "stop" reply adds the person to the opt-out list | The kit's `suppression.py` and `never_touch.py`; one line in `PROCESS.md` step 3 | Someone who asked not to be written to can be written to again |
| 2 | Every email carries an unsubscribe line and the sender's name; the settings check flags an empty one | `prompts/first-touch-email.md`, `prompts/follow-up.md`, `dream500.py check` | Cold email with no way to opt out, which the anti-spam laws require |
| 3 | An email address is verified before it is sent to | One line in `PROCESS.md` step 3; no code here | Bounces rise, which puts the sending inboxes at risk at 1,000 a day |
| 4 | A row that appears twice in a list (same email or same profile) is kept once | `dream500.py place` | The same person gets the same message twice |
| 5 | The bot does not message on X through a browser | The kit's `GATES.md` (an account was locked on 2026-09-25); not restated in this folder | The X account can be locked again |

The shared ones this function runs under (the draft in the log before a send, the LinkedIn caps and stop rule, the kit's other gates) are on the main chat's list in `ideas/revenue-os/RULES.md`, not repeated here.

## Kept: he said it

| Rule | His words | Date |
|---|---|---|
| The three bands by audience | "Dream 500 is 100,000 to 1 million subscribers/followers. Dream 100 would be 1 million+. Anything less than 100,000 subscribers is a potential partner, collaborator, or influencer" | 2026-11-17 |
| The first 5 or 10 are read, then automatic | "On this, there's no approval. It's automatic... I'll tell you that we'll approve the first 5 or 10. After that, you'll be automatic" | 2026-11-17 |
| First touch is a DM and an email | "First touch is: DM on social. Emails" | 2026-11-17 |
| 1,000 emails a day | "Your job is to send 1,000 emails per day" | 2026-11-17 |
| The first message has no hard ask | "There's no necessary ask of anything" | 2026-11-17 |
| Email sends from his inboxes | "It'll send from my quoted inboxes" | 2026-11-17 |
| The list is handed in | "We're going to build it, and I'll hand it to you" | 2026-11-17 |
| Every conversation is documented | "It's vitally important that we do document all the conversations that we're having" | 2026-11-16 |
| LinkedIn on OutFlo or the local computer | "For LinkedIn especially, we're going to have it use our local computer versus the GrokBot computer" | 2026-11-16 |
| No paid enrichment; no partner names, contact lists or private figures in a pack; no secret in a repo | His global instructions file | standing |

## Removed: a chat added it

All added by this function's chat in version 0.1 unless marked.

| Was | Where |
|---|---|
| This function's chat owns only this folder and proposes changes to shared files | `README.md` (from the main chat's brief) |
| The audience number is the largest single count, never a sum, and needs a source or the row is not placed | `PROCESS.md`, `dream500.py` (code), the settings example |
| This function never scrapes and never buys a list | `PROCESS.md` |
| A name never moves down a tier by the agent's choice | `PROCESS.md` |
| One first touch ever, across the three tiers and cold email | `PROCESS.md` |
| An address is looked up once only | `PROCESS.md` |
| A draft is refused for an empty field, a price, a call link or a promise of money | `PROCESS.md` |
| A separate first batch for each channel and for each follow-up | `PROCESS.md`, the prompts |
| A changed template drops back to ask-first, by its hash | `PROCESS.md`, the prompts |
| Follow-ups count inside the 1,000 and go before first touches | `PROCESS.md`, `dream500.py plan` (code) |
| Two follow-ups at most, then stop | `PROCESS.md`, the prompts, `dream500.py check` (code) |
| A bounce or complaint spike pauses the campaign | `PROCESS.md` |
| This function never sends from a mailbox directly | `PROCESS.md` |
| DMs outside LinkedIn are drafts a person sends; a daily cap per DM platform | `PROCESS.md`, the settings example |
| One first touch per channel, and days between an email and a DM to the same person | `PROCESS.md`, the settings example |
| Terms, fees and dates are the owner's | `PROCESS.md` |
| The "gates that do not move" section; "nothing in this folder turns a send on" | `PROCESS.md` |
| Word limits, no link in a first DM, no attachment, plain text, one link, never "just bumping" | The three prompts |
| A campaign may not skip the first batch, drop the unsubscribe line or raise a cap | The settings example |
| An email address in a settings file is refused | `dream500.py check` (code) |
| The example starts on `test` | The settings example |

Still in the folder as defaults, not rules: the wording of the three messages, and two follow-up days (4 and 10). The owner has not said whether there are follow-ups.

## Where it stands

[PROCESS.md](PROCESS.md) is version 0.2: his words, then how the work runs. Built: the process, a settings example, three message drafts, and a script that places a list by audience and shows what a day can carry (14 of 14 self-test checks pass). Not built: the role page and routines for a bot, any DM path outside LinkedIn, the loader into the sending tool. Nothing has sent, and nothing runs on a bot.

## Still open

1. Which inboxes "my quoted inboxes" are, and whether cold email uses the same ones.
2. 1,000 a day needs hundreds of new rows a day and inboxes that can carry it. Neither is measured.
3. DM paths for X, Instagram and community groups.
4. Whether there are follow-ups.
5. Which episode each business points to.

## What existed before this function's own work (surveyed 2026-11-16)

| What | Where | What it does |
|---|---|---|
| The registry entry | `agents.json`, id `dream-500` | Tier 2, engine `grokbot`, channels email, LinkedIn, X and Instagram, message types `dream500_first_touch` and `dream500_follow_up` |
| A research-only role, shared with Dream 100 | kit `roles/dream.md` (`ideas/revenue-os-max/build/`) | One daily dossier routine for both tiers. It hands the warm path to another role and never reaches out |
| Dossier and tier advice | kit `skills/dream/dream-partner-portfolio` | A sourced dossier and a recommended tier. It says the owner assigns the tier and the owner writes Dream outreach |
| Target research | kit `skills/dream/partner-opportunity-research` | Finds and cites real targets for a partner type |
| Fit review | kit `skills/partners/partner-fit-review` | Qualify, research more, defer or exclude. A reasoned call, not a number |
| Drafts | kit `skills/partners/partner-conversation-drafts` | Drafts outreach and replies into an outbox. It has no sender |
| Guards | kit `guards/scripts/` | Suppression, never-touch, the send guard, the spend guard, STOP |
| A version that sends in approved waves | One client pack in this factory. Its path is the `dream-500.source` line in that campaign's private settings file | Email only. A scored list per partner segment, waves of 25 to 50, a personal first line per row, one first email and two follow-ups per wave. The approver says yes to the wave (the list file by its hash, five sample rows, the exact text), then to each day's batch of 10. Sends happen in chat, never inside a routine. A changed list is a new wave |
| A second wave version | Another client pack, same pointer | An agent page and a wave-prep routine, built and never switched on |
| The shared gates this function would use | `convlog/gate.py`, `linkedin/lane.py` | A send needs its draft in the conversation log first. LinkedIn goes through the lane, capped at 20 connection requests and 50 messages a day across every function |

Across the four businesses that apply the product: one has research only, one has nothing, two have the wave version built and paused. None is running. They wait on a Dream 500 list (two), on which inboxes send (one), and on the client's own answers (one).
