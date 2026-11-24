# The Referral Connection: launching the disruptor campaign

The Referral Connection main agent works down this page. Each morning's plan comes from the next open step, and each step names the agent that does it. A step that waits on Justin goes to his queue once, and the next step that needs nothing from him starts. Steps are milestones, not dates.

The message is [MESSAGING.md](MESSAGING.md), a draft until Justin confirms it (NEEDS-JUSTIN 19). Everything made from it stays a draft until he does.

## L1. The library: all drafts, nothing needed from Justin

| Step | Agent | Done when |
|---|---|---|
| A guide per pillar, eight in all, each answering one question an owner asks | AEO and SEO | Drafts in the queue (on the site as drafts once `referral-site: bot`) |
| A two-week calendar: one piece a day, each on one pillar and one content type, pointing to the sign-up page | Content | `content/referral-connection-calendar.md`; each piece logged and in the queue |
| The panel of 10 questions and the baseline read | AEO and SEO | The baseline written down |
| The audience holders: chambers, associations, networking groups, local newsletters and podcasts, coworking spaces, organisers who sell sponsorships | Dream 100, Dream 500 | `data/referral/dream100.csv`; the placed list; first touches in the queue |
| Prospects, each with a public source; first-touch and follow-up drafts, each link tagged | Cold Email | `data/prospects.csv`; drafts in the queue. Before the launch area is named (22) it works a sample metro and says so |
| The public-ask terms: owners asking for a partner, a sponsor, a collaboration or a deal; the Skool and Whop communities worth reading | Lead Radar | Fresh asks a day with a draft each |
| Local business shows found and scored | SpeakerAgent | A scored list. Pitches wait on the speaker profile |
| The brief for the site's pages and form to cover all four | Referral Connection | One file in the queue (23) |

Before the site's key is in (20), the Sales and CRM agent builds its desk against made-up rows and says so.

## L2. Go live, one channel at a time

Each line is one yes from Justin, asked once, with the piece in front of him.

| Step | Agent | The yes |
|---|---|---|
| The team reads the site | Sales and CRM | The admin key (20) |
| The team writes the site's records | Sales and CRM | "referral-site: bot" (21) |
| The first guides published | AEO and SEO | `rc_guide` |
| Outreach to the launch area | Cold Email | The area and the sender (22); `rc_outreach_first`, `rc_outreach_followup` |
| Replies answered | Reply | `rc_reply` |
| The first post on each outlet | Content | The outlet's account and who publishes; `rc_group_post` |
| Introductions | Sales and CRM | `rc_introduction`, `rc_match_followup` |

## L3. Run it as a business

| Each | What the main agent does |
|---|---|
| Day | Sign-ups by source, listings, connection requests, pairs by stage; every real sign-up listed and looked at for a match; tomorrow's plan from the weakest number |
| Week | Which source brought sign-ups that became listed and matched; which pillar brought them. Next week doubles the best and drops the worst. One decision, with its number, in `vault/Decisions.md` |
| Area | An area is full enough when a new sign-up there can be matched the same day. Then the main agent proposes the next area to Justin, once |

## The switches that make it run without Justin

Each is his, said once to the Referral Connection agent. Until a switch is on, that step is a draft in his queue and the rest still runs.

| Switch | File in `context/` | Takes him out of |
|---|---|---|
| `referral-site: bot` | `owners.md` | Listing sign-ups and recording matches |
| `rc_guide: auto` | `standing-approvals.md` | Approving each guide |
| `rc_outreach_first`, `rc_outreach_followup`, `rc_reply: auto` | same | Approving each message |
| `rc_introduction`, `rc_match_followup: auto` | same | Approving each introduction |
| `rc_group_post: auto` | same | Approving each post |
| `<routine>: on` | `routines-on.md` | That routine's test mode |

These stay his whatever is on: the site's code and pages, a price or a fee if the site ever charges one, terms between two owners, anyone upset, any account warning.
