---
name: outreach-drafts
description: Draft the messages that get a local business to sign up at findreferralpartners.com, and handle the replies. Use for the Referral outreach run, or when Justin asks for outreach copy, a post for a local group, or a reply to someone who answered.
---

# Outreach drafts

What is being offered: a free listing in a directory of local businesses that swap referral campaigns. "You send to my list. I send to yours." Each partner emails their own list about the other, once, and they pay each other commission on the sales. Nobody shares a list; nobody connects an inbox.

## Message types

Each is its own type for `send_guard.py`, so Justin can turn them on one at a time.

| Type | To | Says |
|---|---|---|
| `rc_outreach_first` | A business in `data/prospects.csv` with status `found` | Who is writing and why them: the specific partner or category nearby that shares their customers. What a referral campaign is, in two lines. That it is free and they keep their list. The link. How to say no. |
| `rc_outreach_followup` | A `sent` row with no reply | One short note with one new fact: a business that has since been listed in their area, or a new guide. |
| `rc_reply` | Anyone who answered | A yes: the link again and what happens after they sign up. A question: the answer, from the site's FAQ. A no: thanks, then `suppression.py add`. Price, terms, a complaint: `requests/justin/`. |
| `rc_group_post` | A local business group or forum | What the directory is, who is already listed in that town (only businesses that are on the site), the link. The group's own posting rules decide whether it can go there at all. |

## Writing one

- Open with their business and the reason it is them: "You do roofs in Round Rock; a gutter company two miles from you just listed and is looking for a roofer."  Only say that when the listing is on the site. With nobody listed yet, the honest opener is that the area is opening and the first in a category gets first pick of partners.
- Plain words, short. Four or five sentences. No income claims and no made-up numbers.
- The link is `https://findreferralpartners.com/join?utm_source=<channel>-<area>` (for example `email-austin`, `fb-roundrock`). The site stores that tag on the sign-up as `source`, and `rc.py stats` shows sign-ups `by_source`, which is how this role knows what worked. Link to their city page (`/directory/<state>/<city>`) instead when it exists.
- Last line: how to opt out ("reply no and I won't write again").

## Sending and after

`suppression.py check "<business>"`, then `send_guard.py <type>`. Not `auto` means the draft goes to `requests/justin/` with the prospect row. In `test` it is always a draft. After a send, set the row's `status` and count it only with the sent message as proof. A yes-reply goes to `requests/sales-crm/<date>-<business>.md` so sales can match them the moment they sign up.

Each Friday read `rc.py stats` → `by_source` and write to `daily/<date>/outreach.md` which tags produced sign-ups.
