# Find Me Money (findmemoneyapp.com)

Justin, 2026-11-24: "it's just a funding Grok Bot. I want to keep it super focused... and I also wanted to really double down on content."

The message: [MESSAGING.md](MESSAGING.md). The plan: [LAUNCH.md](LAUNCH.md).

## Who it is for

People and business owners looking for funding: the ones who were denied, the ones buried in pitches, and the ones who want a way other than the usual sales call. And the partners who already have those owners gathered: funding and credit creators, business coaches, community owners.

## What the bot does, in the order it matters

| Job | Here |
|---|---|
| Content | Six pieces a day on the eight pillars and the eight money hooks: reactions, talkbacks, breakdowns, UGC prompts. The afternoon three answer what people asked that day |
| Lead Radar | Public asks for funding, the creative routes included; a helpful draft answer for each |
| Communities | The Skool and Whop groups: partners worth approaching, asks, and what the group talks about |
| Partnerships | The Dream 100 and Dream 500 partner lists; one-to-one first touches; the partnership email sequence |
| CRM | GoHighLevel: every person a contact with tags, a note, a stage and a dated next step; pipelines and workflows checked and specified |

## The numbers, and where each comes from

| Number | Source |
|---|---|
| Pieces drafted and posted; views, comments and shares by pillar and type | `content/drafts/`; each outlet, once it has a brand account |
| Public asks found and answered | The conversation log |
| Partners found, contacted, replied, active | `data/partners/`; the CRM's partner pipeline |
| Leads: a person who gave their contact and their OK | The CRM's funding leads pipeline |
| Jobs carried by Claude Code, Codex and the bot | `python3 repo/tools/job.py audit` |

## Not this bot's

- Cold email to a direct lead. Cold email is for partnerships only (Justin, 2026-11-24).
- The Referral Connection site, SpeakerAgent, AEO and SEO.
- A reply-to-every-pitch text campaign runs on Justin's own computer. The bot does not send it.
