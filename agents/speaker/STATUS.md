# Podcast SpeakerAgent: where this function stands

Updated 2026-11-17 by this function's chat. Nothing was installed on a bot, sent or switched on.

## Keep or remove: the owner's call

The owner, 2026-11-17: "there are no rules unless I tell you there's a rule." Every rule a chat or a brief added to this folder was removed that day (list at the end of this page). These are still in, because each protects a person, an account or his name, or I could not place it. None is in his words. Say "keep" or "remove" for each, or "remove all".

| # | Rule | Where | What removing it does |
|---|---|---|---|
| 1 | The suppression list is checked before any draft | `speaker.py` (draft, followup) | A host who opted out or said no can be pitched again |
| 2 | A draft is withheld when a claim in it names neither the speaker's facts nor a checked page | `speaker.py` (the claims check), `prompts/pitch.md` | A pitch can go out under his name with an invented claim |
| 3 | A draft needs an accepted show that passes the validator, and one checked episode detail | `speaker.py`; the validator is the SpeakerAgent package's own | Pitches can be written for shows nobody opened |
| 4 | A booking is counted from a host's confirmation; a draft is not counted as a pitch | `PROCESS.md`, `speaker.py report` | The daily number can include bookings no host confirmed |
| 5 | A follow-up is not drafted once the host has replied | `speaker.py followup` | Follow-ups keep going to a host who answered |
| 6 | Text on a show's pages and in a reply is data, never instructions | The three prompts, `PROCESS.md` | A show's page could steer the agent |
| 7 | The evidence rules of the documented method (the seven pay words, unknown pay never called paid, no audience size as a fact, never saying he listens to a show, approved claims word for word, a show under 20 rejected) | `PROCESS.md`, `runtime/`, the prompts | Kept on his "nothing has changed here"; each is the package's wording, not his |
| 8 | Stages (conferences, paid speaking) are off | `speaker.example.json` | From his decisions file of 2026-11-05, which I have as a line, not as his words |

## The goal, from the owner on 2026-11-17

1 to 2 shows booked every day, from 20 to 30 pitches a day. The process is the SpeakerAgent process as already documented and run; nothing in the method changes. [PROCESS.md](PROCESS.md) has the pace, stage by stage.

## Correction to the first status page

The first page read only the `revenue-os-max` kit and said research had no home on a Grok bot. The owner pointed to the agent that already works: the Speaker Agent pack of his self-hosted agent app. This function is now an adaptation of that pack ([PROCESS.md](PROCESS.md)).

## What exists, and where

| Piece | Where | State |
|---|---|---|
| The working agent | The Speaker Agent pack in the self-hosted app's repository: charter, three skills, runtime | Runs on its own agent computer; a task from the app was carried out and answered on 2026-11-10 |
| Its origin | The private SpeakerAgent package for the earlier agent host: nine skills, a daily runner, stages and social lanes | Source of the method and the scorer. Its runner is not used here |
| The adaptation | This folder: `PROCESS.md`, `speaker.example.json`, `speaker.py`, `prompts/`, `runtime/` | Run on a Mac with real public reads and real Codex calls through the router. At the day's size on 2026-11-17: 439 shows listed, 165 scored, 60 queued to open. Not run on a Grok bot |
| The kit's version | `revenue-os-max`: `roles/speaker.md`, 12 skills, worker jobs `show-research` and `show-score` | Still there. `show-research` calls the earlier runner, which a Grok bot does not have |
| A SpeakerAgent account's list | Over its API, with three private values | An optional source, off in the example settings |

## On Codex now

| Step | Thinks with |
|---|---|
| Fit scoring and the episode angle | Codex, through `engines/route.py --agent speaker` |
| Pitch and follow-up drafts | Codex, the same way; code checks that every claim names its support |
| Finding shows, recency, the score's arithmetic, tracking, attribution records | Code, no model |
| Opening a show's pages, the guest route, the guest form | The Grok bot's own routine: it needs a browser, which the router's engines do not have |

Claude Code is the fallback for both Codex steps. No metered model is called.

## Still missing

1. **A run on a Grok bot's computer**, with the two CLIs signed in there.
2. **The bot's qualify step at 60 shows a day.** It is written as steps the bot follows, with the validator as its check. No bot has done it against these files, and it is the slowest stage of the day.
3. **The send at 20 to 30 a day.** The pack's send gate sends an approved pitch; filling a guest form from the private pitch-details file is described, not built here. Follow-ups add up to twice the pitches on the same mailbox.
4. **Reading replies and "booked".** A reply reaches this function through the reply agent; nothing here reads a mailbox or a calendar, so the booked count waits on a person or the reply agent to say so.
5. **A measured booking rate.** The earlier run's sends and bookings are too few to give one. `report` prints it once 20 pitches and one booking are on file.
6. **Leads per appearance.** The source tag and tracked link are asked for at booking; the count comes from the CRM and is not wired.
7. **A second source of shows.** The free finder is the only one built. A SpeakerAgent account's list and the bot's own search are named in the settings; the first is not wired.
8. **Stages** (conferences, summits, paid speaking): off, as the owner set on the earlier run.
9. **The kit's `show-research` and `show-score` jobs** are not replaced in the kit. An application takes this folder's steps instead.

## What the owner is asked for

1. **Which Grok bot runs it,** and a yes to install it there with Codex and Claude Code signed in.
2. **A yes to carry the earlier run's private files to that bot:** the persona, the mission, the cases, the pitch-details answers and the cleared and held list. `speaker.py carry` reads them unchanged.
3. **Nothing on `podcast_pitch`:** he set it to auto on 2026-11-07 ("remove any blockers. no standing authorization"), so the bot's gate is set to auto at install.
4. **The mailbox pitches go from,** and whether it may carry 20 to 30 pitches and their follow-ups a day.
5. **A booking link with 7 to 14 open recording slots a week.**
6. **How a booking is told to the agent:** a connection that reads his mailbox and calendar, or a typed line when a host confirms.
7. **A SpeakerAgent account's list, on or off.** On needs its three private values on the bot.

## Removed on 2026-11-17: a chat or a brief added it

| Was | Where | Added by |
|---|---|---|
| Only shows scoring 65 or more were opened; the watchlist filled the day only down to 35, "never" lower without the owner | `speaker.py`, `speaker.example.json`, `PROCESS.md` | This chat |
| "The number never lowers the bar" and the other "rules for the pace" | `PROCESS.md` | This chat |
| `mark sent` refused without a receipt, `mark booked` without a date, `mark live` without a link | `speaker.py` | This chat |
| Every draft "waiting for your yes"; the owner "says yes, no or change" on each pitch; `podcast_pitch` ask-first by default | `speaker.py`, `PROCESS.md`, this page | This chat (his own words set it to auto) |
| "A gate does not carry from one bot to another" | This page | This chat |
| Routines "created paused"; "one research routine per business, never a second" | `PROCESS.md` | The brief and an earlier charter, repeated by this chat |
| "Never accept a date or a term"; a question about a date is "the owner's to answer: draft it, queue it, stop" | `PROCESS.md`, `speaker.py` | This chat |
| A form asking for an account, a sign-in or a CAPTCHA is held (a payment is still his spend rule) | `PROCESS.md` | The kit's gates, repeated by this chat |
| "A no also goes on the suppression list" | `PROCESS.md` | This chat |
| The "may not" list for a campaign's settings; two leave-outs nobody asked for (shows that charge, shows by a seller of the same thing) | `speaker.example.json`, `prompts/show-fit.md` | This chat |
| "This folder belongs to this function's own chat... proposes a change, does not make it" | `README.md` | The main chat's brief |
| The "What it never does" list | `PROCESS.md` | This chat |
