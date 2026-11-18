# Dream 500: the process

Version 0.2, 2026-11-17. Version 0.1 was written from the owner's instruction that day; 0.2 takes out every rule he did not state. A spec with one tested script (`dream500.py`). Nothing here has sent a message or run on a bot.

The one rule (the owner, 2026-11-17): "there are no rules unless I tell you there's a rule." What follows is his words, then a description of how the work runs. Where a step is this chat's choice it says so, and it is a default, not a rule.

## What the owner said

All on 2026-11-17 unless marked.

| His words | What it sets |
|---|---|
| "Dream 500 is 100,000 to 1 million subscribers/followers. Dream 100 would be 1 million+. Anything less than 100,000 subscribers is a potential partner, collaborator, or influencer" | The three bands. A row's place comes from its audience number |
| "We're going to build it, and I'll hand it to you, but we'll build it by scraping from different skool groups and social media platforms. We'll also hand you some lists" | The list arrives as files |
| "On this, there's no approval. It's automatic. You'll draft it. We'll send out some. I'll tell you that we'll approve the first 5 or 10. After that, you'll be automatic" | He reads the first 5 or 10, then it sends on its own |
| "First touch is: DM on social. Emails" | Two first-touch channels |
| "Your job is to send 1,000 emails per day" | The daily email number |
| "There's no necessary ask of anything, just more like: here's what we do, here's a recent podcast. Who can I speak to, or how does it work to potentially do some sort of affiliate partnership or giveaway to your group? How can I help support what you're doing by giving you more value?" | The first message |
| "It'll send from my quoted inboxes" | Where email sends from. Read as his cold-email sending inboxes; not confirmed |
| "It's vitally important that we do document all the conversations that we're having" (2026-11-16) | Every draft, send and reply goes in the conversation log |
| "For LinkedIn especially, we're going to have it use our local computer versus the GrokBot computer" (2026-11-16) | LinkedIn DMs go through OutFlo or his own computer |
| No paid enrichment services (standing, 2026-05-25) | Finding an address is done from public pages |
| Packs never hold partner names, contact lists or private figures (standing, 2026-11-12) | Lists and names stay out of this folder |
| Never put a secret in a repo (standing) | The settings check refuses a key-shaped value |

## How the work runs

### 1. Intake

A list file lands as CSV, one row per person or brand. The columns are in [dream500.example.json](dream500.example.json). A row needs a name, an audience number and a way to reach them (an email or a profile URL).

### 2. Place

```
python3 dream500.py place <list.csv> --settings <settings.json> --out <folder>
```

- 1,000,000 or more: `to-dream-100.csv`.
- 100,000 up to 999,999: `dream-500.csv`.
- Under 100,000: `to-partners.csv`.
- No readable audience number: `needs-audience.csv`, because there is nothing to place it by.
- No email and no profile: `no-contact.csv`, because there is nowhere to send.

The script reads the `audience` column as given. Whoever builds the list decides what number goes in it.

### 3. Find an address

A row with no email can be looked up on the person's own public pages (site, channel about page, link in bio). A row with a profile and no email goes by DM.

Three checks sit around this step that are not in the owner's words and were left in for his call (the list at the top of [STATUS.md](STATUS.md)): the kit's opt-out and never-touch check on each row, address verification before an email goes out, and one copy of a row that appears twice.

### 4. Draft

One template per message, in [prompts/](prompts/): the first email, the first DM, and a follow-up. A campaign fills in what we do in one line, the recent episode, and who signs. The rest comes from the row. Every draft goes in the conversation log.

### 5. The first batch, then automatic

The first drafts (5 or 10; `approve_first` in settings, 10 in the example) go to the owner. After his yes, the message sends without one.

### 6. Send email

The sending tool sends, from the owner's inboxes. `dream500.py plan` prints the day's number: the smallest of the 1,000 target, what the inboxes carry, and the rows ready.

A follow-up template and two follow-up days (4 and 10) are in the settings example. The owner has not said whether there are follow-ups; they are there to be kept, changed or deleted.

### 7. Send DMs

| Platform | Path today |
|---|---|
| LinkedIn | OutFlo, or the owner's own computer |
| X | None built |
| Instagram | None built |
| Community groups | None built |

Where no path is built, the drafts are written to a daily file for whoever sends them.

### 8. After a reply

Replies, and the person and conversation, go to the sales agent, which now includes the reply agent (the owner, 2026-11-17: "combine Reply Agent and Sales Agent into one"). A reply that names a partnerships contact becomes a new row for that contact. A yes goes to the owner the same day.

### 9. Numbers

Daily: rows placed in each band, drafted, sent by email, sent by DM, replies, partnership contacts named, yeses. Weekly: reply rate and yes rate by source list and by audience band, so the owner can see which scrape is worth repeating.

## Open items

1. **"My quoted inboxes."** Which inboxes, and whether cold email uses the same ones.
2. **1,000 a day** needs hundreds of new rows a day and inboxes that can carry it. `plan` shows the gap.
3. **DM paths** for X, Instagram and community groups.
4. **Follow-ups:** whether there are any.
5. **The episode** each business points to.

Rules that are not in his words and were left in place for his call are listed at the top of [STATUS.md](STATUS.md).
