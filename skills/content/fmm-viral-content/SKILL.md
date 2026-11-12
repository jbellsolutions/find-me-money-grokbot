---
name: fmm-viral-content
description: Make Find Me Money's simple viral content - short, funny, relatable posts, captions and video scripts built on Justin's eight money hooks ("Where's my money at?" and the rest) that get a laugh or stop the scroll and point to findmemoneyapp.com. Use for the daily content drafts, the weekly batch, picking which hook to run, or scoring a draft.
---

# Find Me Money: simple viral content

Justin, 2026-11-12: "The major thing here is we need simple viral content that is simple but works to get people to laugh or pay attention." And: "Funny, Simple and relatable."

## The eight hooks (his words, keep them exactly)

| # | Hook |
|---|---|
| H1 | Find Me Money app |
| H2 | Wherever money at |
| H3 | How do I get the money? |
| H4 | Where's the money? |
| H5 | Find me money |
| H6 | Where's my money at? |
| H7 | Where's my money? |
| H8 | My go-to for getting money |

Every piece uses one hook word for word, said or on screen in the first two seconds. The brand line is always **Find Me Money** and the place is **findmemoneyapp.com**.

## The one test

Would a business owner laugh, nod, or stop scrolling? If not, it's not done. Score each draft 1-5 on **funny**, **simple** (one idea, under 15 seconds to get), **relatable** (a money moment every owner has had). Ship to Justin's queue only at 4+ on all three.

## Formats that fit the hooks

| Format | Shape | Example skeleton (write fresh ones; never reuse a creator's bit) |
|---|---|---|
| Skit, 7-15 s | Setup of a money pain, beat, the hook as the punchline | Owner checks the bank app, long stare, says H6 to the camera. Cut to the Find Me Money app. |
| POV text-on-screen | "POV:" + a situation, the hook as the payoff line | "POV: payroll is Friday and it's Wednesday" + H4 |
| Search parody | Typing the hook into a search bar, then the app | Types H3, deletes, types H5, cut to findmemoneyapp.com |
| Reply bait | One line + a question that begs a comment | H8 + "What's yours? Wrong answers only." |
| Street-style ask | "What's your go-to for getting money?" answers, last one is the app | H8 |
| Still meme | One image idea + caption, described for a designer or an image tool | H2 under a picture idea of a detective with a magnifying glass over a wallet |

## Rules (they never move)

1. **No rate, approval or amount promises.** No "guaranteed", "instant approval", "no credit check", "get $50K today". Funny never means misleading. Business funding ads are regulated: a claim we can't prove is a no.
2. **No real people, brands, songs or creators' bits** without rights. Describe the audio ("trending sound, upbeat"), never name a copyrighted track to rip.
3. **Punch at the situation, never at the viewer.** No shaming debt, credit or being broke.
4. **Each channel's first post waits for Justin.** Every piece is a draft in `requests/justin/content-<date>-<n>.md` until `fmm_content_post` is `auto` in `context/standing-approvals.md`. The bot never posts; a person or the approved scheduler does.
5. **Count only what's live:** a post counts with its live link. Views and comments come from the platform, never estimated.

## The daily run (content role)

1. `python3 repo/guards/scripts/send_guard.py fmm_content_post --routine "Daily content"`: `draft` means queue for Justin.
2. Read `vault/Daily/` for yesterday's winners (posts with the most comments per view) and `context/content-log.md`.
3. Draft 3 pieces on 3 different hooks, rotating so each hook runs at least once a week; one of them in the format that won last week.
4. For each: hook #, format, the script or caption, the on-screen text, the shot list, the call to action ("findmemoneyapp.com" or "comment H8"), and the three scores.
5. Write them to `requests/justin/`, add a line to `context/content-log.md`, and end with `beat.py write content ...`.

## The weekly batch

Mondays: 10 pieces across all eight hooks, plus a one-line read on last week (which hook and format got the most comments per view, with the links). Fewer, better: drop any hook that lost three weeks running and say so.
