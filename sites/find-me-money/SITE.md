# Site: Find Me Money (findmemoneyapp.com)

Justin, 2026-11-20: "For Find Me Money, the goal is to disrupt the finance industry (our same Disruptor, right?), research and everything we did before, and generate new leads for people who are looking to get financing the creative alternative ways."

## Who it is for

People and business owners looking for financing: the ones who were denied, the ones buried in pitches, and the ones who want a way other than the usual sales call. Also wholesalers, local businesses, and the funding community as partners.

## What traction means, and where each number comes from

| Measure | Source |
|---|---|
| New leads: a person who gave their contact and their OK | The site's forms through the Lending Hub; the CRM's first pipeline |
| Fresh public asks answered | The Funding Radar, and the conversation log |
| Share of AI answers and front-page terms that name the site | The weekly AEO read (baseline: named on 0 of 15 questions) |
| Views, comments and shares per piece, by pillar and content type | Each outlet, once a brand account exists |

## The message

[MESSAGING.md](MESSAGING.md): the Disruptor position, the eight education pillars, the content types and the voice. The full messaging document, with its proof points, images and claims list, is private. Justin gives it at intake and it lives in `context/messaging/`.

## How each agent works this site

| Agent | What it does here | Settings |
|---|---|---|
| Content | Reactions, talkbacks, breakdowns and UGC prompts on the eight pillars and the eight money hooks. One video per guide question for YouTube | `settings/content.json` |
| AEO and SEO | One answer page and one video brief per pillar question; the weekly read of leads, front-page terms and AI answers | `settings/aeo-seo.json` |
| Lead Radar | Public asks for funding, the creative and alternative routes included (denied for a loan, alternatives to a bank, home equity for a business, card stacking, a cash-advance offer they want checked) | `settings/lead-radar.json` |
| Sales agent | Every reply and every lead, with the person's note read first. On test while the Mac's two agents are live | `settings/sales-crm.json` |
| Dream 100, Dream 500 | People who already have borrowers gathered around them: funding and credit creators, business coaches, community owners, wholesaler communities | `settings/dream-100.json`, `settings/dream-500.json` |
| Partners | Funding companies and affiliates who take a deal for a percentage, and creators who promote | `settings/partners.json` |
| Cold email | Owners of local businesses in the week's metro | `settings/cold-email.json` |
| SpeakerAgent | Shows whose listeners are business owners, with the Disruptor story as the topic | `settings/speaker.json` |

## Not this bot's

The text-back campaign (a reply to every number that texts a funding pitch) runs on Justin's own Mac from the business's private repo. The bot does not send it. A person who answers it and wants funding reaches the sales agent like any other lead.

## Waits on

NEEDS-JUSTIN.md, Tracks B and C, and D1 to D2 (the messaging document and its claims list).
