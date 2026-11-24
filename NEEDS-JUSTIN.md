# NEEDS-JUSTIN

Everything only Justin can do, in one list. The bot drafts everything else without any of it. Each line: what, the exact step, what it unblocks.

## To run on the CLIs

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 1 | [ ] Claude Code signed in | On your own computer run `claude setup-token`; tell the bot "Claude token" and paste it at the hidden prompt (it is saved as `CLAUDE_CODE_OAUTH_TOKEN`). Or open the bot's terminal, run `claude` and sign in there | Every job running on your Claude subscription. Until then each job falls to the bot itself |
| 2 | [ ] Codex signed in | In the bot's terminal run `codex login` and approve the sign-in it shows | The second engine |
| 3 | [ ] Check it | Say "CLI status". The bot runs `job.py status`: both should say "installed and answering" | Proof the rule is live |

## To connect

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 4 | [ ] GoHighLevel | In the funding sub-account make a Private Integration Token (contacts, opportunities, workflows, conversations, locations). By hidden prompt give `GHL_API_KEY` and `GHL_LOCATION_ID` | The CRM job reading; every write saved as a proposal you can read |
| 5 | [ ] The bot writes the CRM | Read a day of `requests/justin/crm-proposals-<date>.md`. If another agent files or answers in that sub-account, switch it off. Then say "gohighlevel: bot", "CRM: on" and "crm-writes: on" | Contacts, notes, stages and next steps written for real |
| 6 | [ ] Skool and Whop | Name the groups (or pick from `requests/justin/communities-to-join.md`), say which are ours, and sign the bot's browser in to each | The communities job past public pages |
| 7 | [ ] Slack and Notion | Connect both in Connect apps; name the Slack channel and the Notion hub page. Say "deploy key" or "Mac pulls" for how `vault/` reaches the single brain | The nightly report; the single brain in sync |
| 8 | [ ] Auto-review lines and a spending cap | Paste the five lines from INSTALL.md into Auto-review → Custom Rules. Set a monthly limit at grok.com/dashboard/billing | The same gates in the app; no surprise bill |
| 9 | [ ] The opt-out list and the never-touch list | Give the opt-out file when asked; give the names of computers, agents and accounts the bot must never use | Any draft addressed to a person; any write to a system |

## The message

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 10 | [ ] How Find Me Money gets paid | One or two sentences, in your words. You said the owner pays nothing; the content has to say who does | The word "free" in public content |
| 11 | [ ] The messaging document | Attach `04-messaging-document.md` and its covered images | Pieces that use a proof point, a count or a screenshot |
| 12 | [ ] Its claims, cleared one by one | Say which claims are cleared. "Best rate, best deal" is on that list | Those claims in public |
| 13 | [ ] Outlets | Name the outlets, the brand account on each, and who publishes | Content going out |

## Your call, built with a default

| # | What | Built as | Say |
|---|---|---|---|
| 14 | [ ] One bot or a bot per job | One bot that orchestrates, from "it's just an orchestrator". On 2026-11-20 you said each role is its own agent | "as built", or "one agent per job" |
| 15 | [ ] How much content | Six pieces a day: three in the morning, three in the afternoon | "as built", or a number |
| 16 | [ ] The partnership emails | Drafted from day one; nothing sends. Sending needs a tool and domains | "use the existing domains" or "buy N domains" with a budget; give `INSTANTLY_API_KEY`; then "partner_cold_email: auto" |
| 17 | [ ] The older links | The combined pack (disruptor-revenue-os) is still published and still installs both businesses on one bot | "leave it", or "take it down" |

## The switches that make it run without you

After you have seen a type's drafts, say "<type>: auto": `fmm_content_post`, `public_reply`, `community_post`, `partner_message`, `partner_cold_email`, `email_reply`, `ghl_workflow_enroll`. Say "<routine>: on" to take a routine off test. These stay yours whatever is on: rates, terms, contracts, a new claim, anyone upset, any account warning.
