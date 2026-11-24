# Find Me Money: launching the disruptor campaign

The Find Me Money main agent works down this page. Each morning's plan comes from the next open step, and each step names the agent that does it. A step that waits on Justin goes to his queue once, and the next step that needs nothing from him starts. Steps are milestones, not dates.

The message is [MESSAGING.md](MESSAGING.md): the position, the six commitments, the eight pillars, the content types, the voice.

## L1. The library: all drafts, nothing needed from Justin

| Step | Agent | Done when |
|---|---|---|
| A two-week calendar: three pieces a day, each on one pillar and one content type, the eight money hooks rotated | Content | `content/find-me-money-calendar.md`; each piece logged and in the queue |
| The panel of 15 questions and the buying terms, from the pillars; the baseline read | AEO and SEO | `data/aeo/prompts.md`, `terms.json`; the baseline written down |
| One answer page and one video brief per pillar question | AEO and SEO | Briefs in the queue |
| 100 scored names; a dossier and a first touch for the first ten | Dream 100 | `data/dream100.csv` |
| The wider list placed; first lines for wave one | Dream 500 | The placed list; drafts in the queue |
| The first metro's local list; the cold email sequence on the campaign's angle | Cold Email | List and copy in the queue |
| The public-ask terms, the creative routes included; the Skool and Whop communities worth reading | Lead Radar | Fresh asks a day with a draft each |
| Shows found and scored | SpeakerAgent | A scored list. Pitches wait on the speaker profile |
| One note per person who has written in | Reply | `vault/People/` |
| The stage map; every open lead with a dated next step, as proposals | Sales and CRM | A proposals file in the queue |

Without the private messaging document (NEEDS-JUSTIN 13, 14) the library is drafted from the public outline, on pillars 1 to 5 and 8, with no proof point, count or screenshot.

## L2. Go live, one channel at a time

Each line is one yes from Justin, asked once, with the piece in front of him.

| Step | Agent | The yes |
|---|---|---|
| First post on each outlet | Content | The outlet's account and who publishes (16); `fmm_content_post` |
| Public replies to fresh asks | Lead Radar, Reply | `public_reply`, `public_followup` |
| The first answer pages live | AEO and SEO | His merge of the site's pull request |
| Dream 100 first touches | Dream 100 | `partner_message` |
| Dream 500 and cold email waves | Dream 500, Cold Email | The sender and domains (17); `fmm_cold_email` |
| Replies answered and leads filed by the team | Reply, Sales and CRM | `email_reply`; `pinnacle-ghl: bot` and `crm-writes: on` (15) |
| Show pitches | SpeakerAgent | The speaker profile (26); `speaker_pitch` |

## L3. Run it as a business

| Each | What the main agent does |
|---|---|
| Day | Leads, asks answered, pieces out, replies waiting; tomorrow's plan from the weakest number |
| Week | Views, comments and shares by pillar and content type; leads by source. Next week doubles the best and drops the worst. One decision, with its number, in `vault/Decisions.md` |
| Month | The AEO read against the baseline; funded deals and partner fees against the target Justin sets |

## The switches that make it run without Justin

Each is his, said once to the Find Me Money agent. Until a switch is on, that step is a draft in his queue and the rest still runs.

| Switch | File in `context/` | Takes him out of |
|---|---|---|
| `fmm_content_post: auto` | `standing-approvals.md` | Approving each post |
| `public_reply: auto`, `public_followup: auto` | same | Approving each public reply |
| `email_first_touch`, `email_reply`, `fmm_cold_email`, `partner_message`, `speaker_pitch: auto` | same | Approving each message |
| `pinnacle-ghl: bot`, `crm-writes: on` | `owners.md`, `routines-on.md` | Filing and answering leads |
| `cold-email-sender: bot` | `owners.md` | Launching each wave |
| `<routine>: on` | `routines-on.md` | That routine's test mode |
| `<plan-id>: approved <usd>` | `spend-approvals.md` | Approving each paid run |

These stay his whatever is on: price, rates, terms, contracts, a new claim, anyone upset, any account warning.
