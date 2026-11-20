---
name: directory-desk
description: Run the directory's front desk on findreferralpartners.com. Use for the sales intake run or when Justin asks about sign-ups, listings, connection requests or removal requests - reading new sign-ups, marking spam, listing a business with a blurb, answering a request to be connected, and handling a removal.
---

# Directory desk

Everything goes through `python3 repo/tools/rc.py` (needs `RC_SITE` and `RC_ADMIN_KEY` from `.secrets/site.env`). Reading is free; a write needs `crm-writes: on`.

## Intake, in this order

1. `rc.py stats` gives the counts: `signups_new`, `connections_new`, `removals_open`. All zero means nothing to do.
2. `rc.py removals` lists removal requests; ones with no `done_at` are open. `rc.py remove <email>` deletes that person's sign-up, listing, matches and connection requests and marks the request done. The factory gate says the bot never deletes data, so an open removal goes to `requests/justin/` with that exact command, unless Justin has told this bot it may apply removals itself (see NEEDS-JUSTIN). Either way add the email to suppression: `suppression.py add "<email>" "asked to be removed"`.
3. `rc.py signups --status new` lists new sign-ups. For each one decide: real business or spam. Signs of spam: no real business name, a category that doesn't fit the words, a link stuffed into a text field, the same text many times. `rc.py signup-set <id> --status spam` hides it from every later step. A name starting "TEST" is a test: leave it.
4. For each real sign-up with `show_in_directory` 1: `rc.py list <id> --blurb "<one line>"`. The blurb is one plain sentence built from their own `customers` and `wants` answers and their category and city. If they gave nothing to build from, list with no blurb. The site then shows the business on `/business/<slug>` and on its state, city, city-plus-category and category pages, and adds them to the sitemap.
5. A sign-up with `show_in_directory` 0 is never listed; it is still matched.
6. `rc.py connections` lists requests from visitors who asked to be connected to a listed business (`listing_business`, `listing_signup_id`). Each one is a warm match: the visitor has picked their partner. Hand it to the matchmaker skill, then `rc.py connection-set <id> --status introduced` once the introduction has gone out, or `declined` / `spam`.

## What to write down

`daily/<date>/sales.md`: counts only (new sign-ups, listed, spam, removals, connection requests), by area. Names, emails and businesses of members stay on the site and in `data/`; the scoreboard and the vault get numbers.

## Gaps to pass on

After listing, look at the area: `rc.py signups --area "<city>"`. A city with listings in one category and nobody in the categories that pair with it is a gap: write it to `requests/outreach/<date>-<city>.md` (the city, who is listed by category, which partner categories are missing). A question three members have asked goes to `requests/content/`.
