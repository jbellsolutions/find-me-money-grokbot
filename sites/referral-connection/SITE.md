# Site: The Referral Connection (findreferralpartners.com)

Justin, 2026-11-20: "that's all about building out that site to attract clients who want to do collaborations, partnerships, sponsorships, and deals with others."

And 2026-11-18: "They sign up to get connected to others in the area that want to do referral relationships that pay on commission. You send to my list, I send to your list." "Give it to GrokBot, and let GrokBot go promote the crap out of it."

## Who it is for

Business owners who want a partner: someone to collaborate with, sponsor or be sponsored by, do a deal with, or swap commission referral campaigns with.

## What the site is today, and what the bot does not do

A directory on its own server. People sign up, real sign-ups get a listing, and a visitor can ask to be connected to a listed business. The bot reaches it only through the site's admin API (`tools/rc.py`): sign-ups, listings, connection requests, removals, matches and guide pages. The site's code is Justin's private repo: the bot never builds or deploys it. A fault, or a page the site needs, goes to `requests/justin/` as a brief.

The site's own pages and sign-up form are written for commission referral campaigns between local businesses. Collaborations, partnerships, sponsorships and deals are covered from now in guides, outreach and matching; the first brief the bot writes for the site's repo is what the pages and the form need to say for all four.

## What traction means, and where each number comes from

| Measure | Source |
|---|---|
| Sign-ups, by source and by area | `python3 repo/tools/rc.py stats` |
| Listings, and areas with a listing | `rc.py listings` |
| Matches by stage: proposed, introduced, agreed, sent, paid | `rc.py matches` |
| Guides published and reachable; pages in the sitemap | `rc.py pages`, the site check |
| Whether search and AI answers name the site | The weekly AEO read (a panel of 10 questions) |

## How each agent works this site

| Agent | What it does here | Starts from | Settings |
|---|---|---|---|
| Sales agent | Intake of sign-ups, connection requests and removals; a listing for each real sign-up; pairs matched; introductions drafted; each pair followed to a paid campaign | `skills/sales/directory-desk`, `skills/sales/matchmaker` | `settings/sales-crm.json` |
| AEO and SEO | Guides that answer what an owner looking for a partner, a sponsor or a collaboration asks, saved to the site as drafts; the site check; the weekly read | `skills/aeo-seo/guide-publisher`, `skills/aeo-seo/site-check` | `settings/aeo-seo.json` |
| Cold email | Local businesses in the launch area, from public sources, and the messages that get them to sign up, each link tagged with its source | `skills/outreach/prospect-finder`, `skills/outreach/outreach-drafts` | `settings/cold-email.json` |
| Dream 100, Dream 500 | People who already have business owners gathered: chambers, associations, networking groups, local newsletters and podcasts, coworking spaces, event organisers who sell sponsorships | `agents/dream-100/`, `agents/dream-500/` | `settings/dream-100.json`, `settings/dream-500.json` |
| Partners | The wide tier of the same: anyone who would tell their members about a free listing | `agents/partners/` | `settings/partners.json` |
| Lead Radar | Owners asking in public for a partner, a sponsor, a collaboration or a deal | `agents/lead-radar/` | `settings/lead-radar.json` |
| Content | One piece a day pointing to the sign-up page: a pairing that makes sense, a sponsorship that worked, a new area on the directory | `agents/content/` | `settings/content.json` |
| SpeakerAgent | Off for this site | | `settings/speaker.json` |

Message types, each approved once before it sends: `rc_outreach_first`, `rc_outreach_followup`, `rc_reply`, `rc_group_post`, `rc_introduction`, `rc_match_followup`, `rc_guide`.

## One writer

No other system writes the site's records today. The site also has its own pack (`referral-connection` v1.0.0), not installed on any bot. If that pack is ever installed on another bot, both would write the same records: one of the two is switched off first.

## Waits on

NEEDS-JUSTIN.md, Track D (D3 to D10).
