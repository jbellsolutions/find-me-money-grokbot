# Lead sources

What each source is and how the bot uses it. Hosts and ids are set at intake (`.env.example`); none ship here.

**The one rule:** every source produces signals, not leads. A signal is a public post with a handle and a link. A lead has a name, a phone or email, and the person's own OK. The bot turns signals into leads by answering them, never by guessing contact details.

| Source | What it is | How the bot uses it |
|---|---|---|
| The Funding Radar (`RADAR_URL`) | The main source: graded funding asks from public posts across Facebook groups, Reddit, TikTok, LinkedIn and the web, refreshed by its own daily sweep | radar reads `GET /api/replies` (fresh first: the last 2 days, never older than 7); sales drafts answers. Imports (`RADAR_IMPORT_URL`) only when `owner_guard.py check funding-radar` says `bot` |
| The Radar's lanes | Creators, gig workers, discovery and a Craigslist reader, each feeding the Radar | Read through the Radar. The bot never writes a lane's tables |
| Prospects | Cold names from public records and Craigslist, not asks | outreach and wholesale only, after suppression; never treated as a person who asked |
| Facebook asks | Found by the Radar; answered by people, not the bot | The Reply Agent files them in their own pipeline with a checked draft; a person posts |
| Craigslist | Ads we post by hand (bot checks), and the reader's rows | radar reads; ad posting is a person's job |
| The site and app | Forms on findmemoneyapp.com that post to the Lending Hub (`HUB_URL`) | The only source where people give contact details and consent themselves. sales works them first |
| Email lists | Research-intent lists, never opt-in | Email only, never text or call, and only after Justin approves the sender, copy and postal address |
| Muse | Funding asks and partner openings Muse finds | muse collects them into one daily file; radar imports when the owner guard allows |

## Gaps the bot reports, never works around

- Nobody posts replies yet: drafts wait in `requests/justin/` until a message type is approved.
- Credits are spend: any top-up is Justin's yes (`spend_guard.py`).
- No source records consent to a call, a text or a partner share; the bot never assumes it.
- Stale signals convert badly: the 7-day rule holds.
