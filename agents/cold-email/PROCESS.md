# Cold email: the process

Cold email reaches cold prospects who could buy directly, by email only, at a fixed daily number. Its job is that cold email goes out every day, each one with some personalization, and that the data and the campaigns match.

The owner, 2026-11-17:

- "We want to be sending 10 per inbox per day. On this cold leads portion of it, it's probably 1,000 per day." The sending tool is PlusVibe.
- "Cold leads is different from Dream 500... These are just cold prospects that are potential direct prospects."
- "Data stays with the data lane... You're just on the cold email."
- "First lines at volume through the Codex subscription is correct." "We'll use the GPT-6 Luna with Codex."
- "Create some simple first lines and a little bit of personalization. For the most part, we're not going to overcomplicate it, and we want to make sure we hit our volume quota. As long as the data is good, then we'll do good."
- "You should be getting a 10% response rate and a 1% booking rate."
- "You'll be given a charter on who and how to prospect, templates, and what to say as far as personalization."

## The numbers

| | | Where it comes from |
|---|---|---|
| Sends a day | 1,000 | The owner |
| Sends per inbox a day | 10 | The owner |
| Warmed inboxes needed | 100 | 1,000 divided by 10 |
| Domains | About 34 | The kit's 3 inboxes a domain |
| New verified contacts a day | About 334 | A three-step sequence; changes with the charter's sequence length |
| Reply rate | 10% | The owner's target |
| Booking rate | 1% | The owner's target |
| At those targets | About 33 replies and 3 bookings a day | Arithmetic, not a measurement |

The script counts both rates per person contacted, not per email sent. `python3 cold.py plan --settings <file>` prints this table for a business's own numbers.

## What is this function's and what is not

| This function | Not this function |
|---|---|
| Checking that a list fits its campaign before it loads | Finding, scraping, enriching or verifying the list: the data lane (the owner: "Data stays with the data lane") |
| A first line for every person | Dream 500 and the other partner tiers (the owner: "Cold leads is different from Dream 500") |
| The campaign in the sending tool matching the templates | |
| Cold email going out every day, and the daily read against the targets | |

## The steps

| # | Step | Who |
|---|---|---|
| 1 | **Charter.** The owner's words on who to prospect, how, the templates and what a first line says go into the business's copy of `cold-email.example.json` (`charter`, each campaign's `audience`, `must`, `contains`, `steps`, `merge_fields`) and its sequence file | The bot, from the owner's words |
| 2 | **Plan.** `cold.py plan`: inboxes, domains and new contacts a day the number needs, against the warmed inboxes there are | `cold.py` |
| 3 | **Order the list.** The bot asks the data lane for the audience and the day's count, with the columns the templates use | The bot; the data lane builds and verifies |
| 4 | **Match.** `cold.py match`: every row is kept or counted under one reason (bad address, not verified, seen before, a blank the template needs, off audience, suppressed). A list missing a column the templates use cannot be matched and is sent back. The share that fits is printed | `cold.py` |
| 5 | **First lines.** `cold.py first-lines`: company, title, industry, city and a note go to Codex through `engines/route.py`. A row the engine gives no line for gets the fallback line built from the row, so every email has some personalization and volume does not wait | Codex; the fallback line if it gives nothing |
| 6 | **Log the templates.** Each step of the sequence is logged once in the conversation log, under the campaign's name (the owner, 2026-11-16: "It's vitally important that we do document all the conversations that we're having") | The bot |
| 7 | **Load.** The ready rows go into the campaign in the sending tool, the day's count | The kit's `list-load` job |
| 8 | **Send.** The sending tool sends on its own schedule, 10 an inbox a day. Turning sending on is the owner's yes (his standing rule on sends) | PlusVibe |
| 9 | **Replies.** Pulled and handed to the sales agent | The kit's `replies-pull` |
| 10 | **Daily read.** `cold.py read`: today's sends against the number, bounces, and replies and bookings against the targets | `cold.py`, then the bot |
| 11 | **Report.** Sent, new contacts loaded, days of ready rows left, reply and booking rates, lines by source (Codex or fallback), in the day's note | The bot |

Steps 2, 4, 5 and 10 are one script, built and tested here. Steps 7 to 9 are the kit's engine and worker jobs, not yet run against a live account. The join between them is not built: the kit's load reads its own list file, not this script's ready file.

## Rules

Only the owner's. They are listed with his words and dates at the top of [STATUS.md](STATUS.md), with a short list of checks in the code that are not his and wait on his keep or remove.
