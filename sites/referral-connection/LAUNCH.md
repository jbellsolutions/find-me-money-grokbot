# The Referral Connection: launching the disruptor campaign

Justin, 2026-11-20: "they need to be autonomous businesses. That's the whole point... with charters and instructions on launching both those disruptor campaigns." And of this site: "building out that site to attract clients who want to do collaborations, partnerships, sponsorships, and deals with others."

This page is the Referral Connection project agent's launch plan. It works down it: each morning the plan comes from the next open step, and each step names the agent that does it. A step that waits on Justin goes to his queue once and the next step that needs nothing from him starts. Steps are milestones, not dates.

The message is [MESSAGING.md](MESSAGING.md), a draft until Justin confirms it (NEEDS-JUSTIN F3). SpeakerAgent is off for this site.

## L0. Ground

| Step | Agent | Done when |
|---|---|---|
| The team is set up and the Revenue OS is built on test | Find Me Money creates the team; Referral Connection (project agent) reads it back for this site | HANDOFF test day passes: 0 sent, 0 posted, 0 site writes |
| The site's admin key is in | Justin (D3) | `rc.py stats` reads one real record |
| The launch area is named | Justin (D6) | One city or metro in `context/referral/launch-area.md`. Until then prospects come from the gaps the desk wrote down |
| The message is confirmed or replaced | Justin (F3) | His words in `context/referral/messaging-confirmed.md` |
| The site says all four: collaborations, partnerships, sponsorships, deals | A brief for the site's repo (D10) | The pages and the sign-up form changed by the site's own chat |

## L1. The library (drafts only)

| Step | Agent | Done when |
|---|---|---|
| A guide per pillar, eight in all, each answering one question an owner asks | AEO and SEO | Drafts on the site (once `referral-site: bot`) or in the queue |
| A two-week calendar: one piece a day, each on one pillar and one content type, pointing to the sign-up page | Content | `content/referral-calendar.md`; pieces logged and in the queue |
| The panel of 10 questions and the baseline read | AEO and SEO | The baseline is written down |
| The Dream 100 for the area: chambers, associations, networking groups, local newsletters and podcasts, coworking spaces, organisers who sell sponsorships | Dream 100 | `data/referral/dream100.csv`, a dossier for the first ten |
| The Dream 500 placed; the partner tier | Dream 500, Partners | The placed list; first lines in the queue |
| Prospects in the launch area, each with a source; the first-touch and follow-up drafts, each link tagged | Cold Email | `data/prospects.csv`; drafts in the queue |
| The public-ask terms: owners asking for a partner, a sponsor, a collaboration or a deal | Lead Radar | Fresh asks a day with a draft each |

## L2. Go live, one channel at a time

Each line is one yes from Justin, asked once, with the piece in front of him.

| Step | Agent | The yes |
|---|---|---|
| The team writes the site's records | Sales | "referral-site: bot" (D4), and how removals are handled (D5) |
| The first guides published | AEO and SEO | `rc_guide` approved |
| Outreach to the launch area | Cold Email | The sender address (D7); `rc_outreach_first`, `rc_outreach_followup`, `rc_reply` approved |
| The first post on each outlet | Content | The outlet's account and who publishes |
| Introductions | Sales | `rc_introduction`, `rc_match_followup` approved |

## L3. Run it as a business

| Each | What the project agent does |
|---|---|
| Day | Sign-ups by source, listings, connection requests, pairs by stage; every real sign-up listed and looked at for a match; tomorrow's plan from the weakest number |
| Week | Which source brought sign-ups that became listed and matched; which pillar's guide and pieces brought them. Next week doubles the best source and drops the worst. One decision, with its number, in `vault/Decisions.md` |
| Area | An area is full enough when a new sign-up there can be matched the same day. Then the project agent proposes the next area to Justin, once |

## What makes it autonomous

The business runs without Justin in the daily loop once these switches are on. Each is his, said once. Until a switch is on, that step is a draft in his queue and the rest still runs.

| Switch | Where | What it takes him out of |
|---|---|---|
| `referral-site: bot` | `context/owners.md` | Listing sign-ups and recording matches by hand |
| `rc_guide: auto` | `context/standing-approvals.md` | Approving each guide |
| `rc_outreach_first`, `rc_outreach_followup`, `rc_reply: auto` | same | Approving each outreach message |
| `rc_introduction`, `rc_match_followup: auto` | same | Approving each introduction |
| `rc_group_post: auto` and the content post type | same | Approving each post |

These stay his whatever is switched on: the site's code and its pages, a price or a fee if the site ever charges one, terms between two owners, a removal he wants to see, anyone upset, any account warning.
