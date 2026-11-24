# NEEDS-JUSTIN

Everything only Justin can do, in one list. The bot finds, drafts and files everything else without any of it.

## To hit 100 conversations started a day

The bot finds 100 leads a day and gets 100 first messages ready from day one. A conversation is started only when a message goes out, and each of these is what lets one kind go out.

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 1 | [ ] The opt-out list and the never-touch list | Give the opt-out file when asked; give the names of computers, agents and accounts the bot must never use | Any message addressed to a person; any write to a system |
| 2 | [ ] Public replies to direct leads | Read a day of reply drafts, then say "public_reply: auto" and name the account they go from on each channel, or who posts them | About 30 conversations a day |
| 3 | [ ] First messages to affiliates and referral partners | Read a day of drafts, then say "partner_message: auto" and name the mailbox they go from | One-to-one conversations |
| 4 | [ ] The partnership emails | Say "use the existing domains" or "buy N domains" with a budget; give `INSTANTLY_API_KEY`; then "partner_cold_email: auto" | The bulk of the 100 |
| 5 | [ ] Skool and Whop | Name the groups (or pick from `requests/justin/communities-to-join.md`), say which are ours, sign the bot's browser in to each; then "community_post: auto" if the bot may post | The communities past public pages |

## To run on the CLIs and the tools

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 6 | [ ] Claude Code signed in | On your own computer run `claude setup-token`; tell the bot "Claude token" and paste it at the hidden prompt (saved as `CLAUDE_CODE_OAUTH_TOKEN`). Or sign in from the bot's terminal | Every job on your Claude subscription. Until then each job falls to the bot itself |
| 7 | [ ] Codex signed in | In the bot's terminal run `codex login` and approve the sign-in it shows. Then say "CLI status" | The second engine |
| 8 | [ ] HeyGen | By hidden prompt give `HEYGEN_API_KEY`. Say "show HeyGen avatars and voices", pick one of each (`HEYGEN_AVATAR_ID`, `HEYGEN_VOICE_ID`). Then say "heygen: approved 6" (videos a day; any number) | Talking videos rendered. Until then every script is finished and its render waits |
| 9 | [ ] The other video tools | Say which of Creatomate, Arcads, Higgsfield, Google Flow, InVideo and Max Fusion you use, and give each one's key or sign-in | Captions, cut-downs, b-roll |

## The sales agent and GoHighLevel

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 10 | [ ] GoHighLevel | In the funding sub-account make a Private Integration Token (contacts, opportunities, workflows, conversations, locations). By hidden prompt give `GHL_API_KEY` and `GHL_LOCATION_ID` | The sales agent reading; every write saved as a proposal you can read |
| 11 | [ ] The sales agent writes the CRM | Read a day of `requests/justin/crm-proposals-<date>.md`. If another agent files or answers in that sub-account, switch it off. Then say "gohighlevel: bot", "Sales: on" and "crm-writes: on" | Contacts, notes, stages and next steps written for real |
| 12 | [ ] Replies | Connect the mailbox replies come to, and say "email_reply: auto" once you have read a day of answers | Replies answered without you |
| 13 | [ ] The two pipelines and three workflows | Open `requests/justin/crm-build.md` and make them in GoHighLevel (the API cannot), or say "build them in the browser" once the bot is signed in there | The affiliate and referral pipeline; the follow-up workflows |
| 14 | [ ] The old leads | Say which dashboard you mean: GoHighLevel, the Lead Radar dashboard, or both, and how old is old (built as: no reply and nothing in 14 days). Read `requests/justin/old-leads-<date>.md`, then say "old-leads: clear" | The old leads cleared. In GoHighLevel they move to Not now with a tag; nothing is deleted. The Lead Radar dashboard needs its address and password |

## The message, search and reports

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 15 | [ ] How Find Me Money gets paid | One or two sentences, in your words | The word "free" in public content |
| 16 | [ ] The messaging document and its claims | Attach `04-messaging-document.md` and its covered images; say which claims are cleared ("best rate, best deal" is on that list) | Proof points, counts and screenshots in content |
| 17 | [ ] Outlets | Name the outlets, the brand account on each, and who publishes; then "fmm_content_post: auto" | Content going out |
| 18 | [ ] Search | Verify the site in Google Search Console and Bing. Say yes or no to the tracking tool's cost (`RANKSPOT_API_KEY`) | The Tuesday read from real numbers. Without it the read is done by hand |
| 19 | [ ] Slack and Notion | Connect both; name the channel and the hub page. Say "deploy key" or "Mac pulls" for how `vault/` reaches the single brain | The nightly report; the single brain in sync |
| 20 | [ ] Auto-review lines and a spending cap | Paste the five lines from INSTALL.md into Auto-review → Custom Rules. Set a monthly limit at grok.com/dashboard/billing | The same gates in the app |

## Your call, built with a default

| # | What | Built as | Say |
|---|---|---|---|
| 21 | [ ] The split of the 100 | 30 direct leads, 70 affiliates and referral partners | "as built", or two numbers |
| 22 | [ ] How much content | Six pieces a day | "as built", or a number |
| 23 | [ ] Old bots | The update names any bot left from the earlier install; it deletes none | Delete them, or say which to keep |

These stay yours whatever is on: rates, terms, contracts, a new claim, anyone upset, any account warning.
