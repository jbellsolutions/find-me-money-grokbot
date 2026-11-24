# Campaign: The Referral Connection (findreferralpartners.com)

Justin, 2026-11-20: "building out that site to attract clients who want to do collaborations, partnerships, sponsorships, and deals with others." And 2026-11-24: "the Referral Connection site (which is a disruptor product in and of itself)."

Main agent: **Referral Connection**. The message: [MESSAGING.md](MESSAGING.md), a draft until Justin confirms it. The launch plan: [LAUNCH.md](LAUNCH.md).

## Who it is for

Business owners who want a partner: someone to collaborate with, sponsor or be sponsored by, do a deal with, or swap commission referral campaigns with.

## The site, and what the team does not do

A directory on its own server. People sign up, real sign-ups get a listing, and a visitor can ask to be connected to a listed business. The team reaches it only through its admin API (`tools/rc.py`). The site's code is Justin's private repo: the team never builds or deploys it. A fault, or a page the site needs, is a brief in `requests/justin/`. Its pages today say commission referral campaigns only; the brief for all four is NEEDS-JUSTIN 23.

## The numbers, and where each comes from

| Number | Source |
|---|---|
| Sign-ups, by source and by area | `python3 repo/tools/rc.py stats` |
| Listings, and areas with a listing | `rc.py listings` |
| Matches by stage: proposed, introduced, agreed, sent, paid | `rc.py matches` |
| Guides published and reachable | `rc.py pages`, the site check |
| Whether search and AI answers name the site | The weekly AEO read (a panel of 10 questions) |

## What each agent does for it

| Agent | Here |
|---|---|
| Sales and CRM | Sign-ups, connection requests and removals read; a listing for each real sign-up; pairs matched; introductions drafted; each pair followed to a paid campaign |
| AEO and SEO | A guide per pillar, saved to the site as a draft; the site check; the weekly read |
| Cold Email | Local businesses in the launch area from public sources, and the messages that get them to sign up, each link tagged with its source |
| Dream 100, Dream 500 | Chambers, associations, networking groups, local newsletters and podcasts, coworking spaces, organisers who sell sponsorships |
| Lead Radar | Owners asking in public for a partner, a sponsor, a collaboration or a deal, on social, Skool and Whop |
| Content | One piece a day on one pillar, pointing to the sign-up page |
| SpeakerAgent | Local business shows and podcasts, once there is a speaker profile |
| Reply | Every reply to outreach, a guide or a post |

Message types: `rc_outreach_first`, `rc_outreach_followup`, `rc_reply`, `rc_group_post`, `rc_introduction`, `rc_match_followup`, `rc_guide`.

## One writer

The site's own pack is published separately. If it is ever installed on another bot, both would write the same records: one of the two is switched off first.
