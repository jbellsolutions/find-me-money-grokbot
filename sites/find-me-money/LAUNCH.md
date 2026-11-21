# Find Me Money: launching the disruptor campaign

Justin, 2026-11-20: "they need to be autonomous businesses. That's the whole point... with charters and instructions on launching both those disruptor campaigns." And of this site: "the goal is to disrupt the finance industry... and generate new leads for people who are looking to get financing the creative alternative ways."

This page is the Find Me Money project agent's launch plan. It works down it: each morning the plan comes from the next open step, and each step names the agent that does it. A step that waits on Justin goes to his queue once and the next step that needs nothing from him starts. Steps are milestones, not dates.

The message is [MESSAGING.md](MESSAGING.md): the position, the six commitments, the eight pillars, the content types, the voice. SpeakerAgent is off for this site.

## L0. Ground

| Step | Agent | Done when |
|---|---|---|
| The team is set up and the Revenue OS is built on test | Find Me Money (project agent) | HANDOFF test day passes: 0 sent, 0 posted, 0 live writes |
| The messaging document is in `context/messaging/` | Project agent asks once (NEEDS-JUSTIN D1) | The file is there, mode 600 |
| The claims list is cleared, claim by claim | Justin (D2) | `context/messaging/claims-cleared.md` lists each cleared claim with his words. An uncleared claim is never used |

Without the document the campaign still starts: L1 to L3 run from the public outline, on pillars 1 to 5 and 8, with no proof point, count or screenshot.

## L1. The library (drafts only)

| Step | Agent | Done when |
|---|---|---|
| A two-week calendar: three pieces a day, each on one pillar and one content type, the eight money hooks rotated | Content | `content/calendar.md`; every piece in Justin's queue is logged |
| One answer page and one video brief per pillar question (15 questions) | AEO and SEO | Briefs in `requests/justin/`; page changes are pull-request briefs for the site's repo |
| The panel and the buying terms from the pillars; the baseline read | AEO and SEO | `data/aeo/prompts.md`, `terms.json`; the baseline is written down |
| The Dream 100 for the campaign: funding and credit creators, business coaches, community owners, wholesaler communities | Dream 100 | 100 scored names, a dossier for the first ten |
| The Dream 500 placed; first lines for wave one | Dream 500 | The placed list; drafts in the queue |
| Partner types and one first email per type | Partners | Drafts in the queue |
| The first metro's local list, verified; the cold email sequence on the campaign's angle | Cold Email | List and copy in the queue |
| The public-ask terms, the creative routes included | Lead Radar | Ten fresh asks a day with a draft each |

## L2. Go live, one channel at a time

Each line is one yes from Justin, asked once, with the piece in front of him.

| Step | Agent | The yes |
|---|---|---|
| First post on each outlet | Content | The outlet's brand account, who publishes, and the first piece (C7, B14) |
| Public replies to fresh asks | Lead Radar | `public_reply` approved |
| The first answer pages live | AEO and SEO | The pull request merged by him |
| Dream 100 first touches | Dream 100 | The offer to a partner's audience (C6) and the first-touch type |
| Dream 500 and cold email waves | Dream 500, Cold Email | The domain decision (C9), the cold email charter (C10), the types |
| Replies answered and filed by the team | Sales | Which live agent is the base, then `pinnacle-ghl: bot` and `crm-writes: on` (C5) |

## L3. Run it as a business

Every day the project agent reads the numbers and moves the work to what is producing leads.

| Each | What the project agent does |
|---|---|
| Day | Leads (a contact and an OK), asks answered, pieces out, replies waiting; tomorrow's plan from the weakest number |
| Week | Views, comments and shares by pillar and by content type; leads by source. Next week's calendar doubles the best pillar and drops the worst. One decision, with its number, in `vault/Decisions.md` |
| Month | The AEO read against the baseline; funded deals and partner fees against the revenue target Justin set |

## What makes it autonomous

The business runs without Justin in the daily loop once these switches are on. Each is his, said once. Until a switch is on, that step is a draft in his queue and the rest still runs.

| Switch | Where | What it takes him out of |
|---|---|---|
| `fmm_content_post: auto` | `context/standing-approvals.md` | Approving each post |
| `public_reply: auto`, `public_followup: auto` | same | Approving each public reply |
| `email_first_touch`, `email_reply`, `fmm_cold_email: auto` | same | Approving each email |
| `partner_message: auto` | same | Approving each partner note |
| `pinnacle-ghl: bot`, `crm-writes: on` | `context/owners.md`, `routines-on.md` | Filing and answering replies himself or on the Mac |
| `cold-email-sender: bot`, `social-sender: bot` | `context/owners.md` | Launching each wave |
| A spend line per plan | `context/spend-approvals.md` | Approving each paid run |

These stay his whatever is switched on: price, rates, terms, contracts, a partner's activation, marking a deal Funded or Paid, a new claim, anyone upset, any account warning.
