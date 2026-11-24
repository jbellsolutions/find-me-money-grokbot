# NEEDS-JUSTIN

Everything only Justin can do, in one list. The team builds and drafts everything else without any of it. Each line: what, the exact step, what it unblocks.

## To install

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 1 | [ ] A Grok account for these two campaigns | Sign in at x.ai/bot. Check the plan covers eleven bots and routines | Everything |
| 2 | [ ] One bot, one line | Create one new bot, set Settings → General → Bot → Timezone to **UTC**, paste the line from INSTALL.md | The install |
| 3 | [ ] The other ten bots, only if the first one cannot create them | Open `requests/justin/create-the-team.md`. For each of the ten names: create a bot with that name, set UTC, paste its line | The rest of the team |
| 4 | [ ] The screenshot of where the earlier install stopped | Drop it in the Find Me Money on GrokBot chat | Confirms what stopped it. This pack was rebuilt without it |

## To keep the cost down

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 5 | [ ] Claude Code and Codex on the team's computer | Say "yes, install the CLIs" to a main agent. Then sign in: on your Mac run `claude setup-token` and give the token by hidden prompt as `CLAUDE_CODE_OAUTH_TOKEN`; for Codex, approve the device sign-in it shows | The agents' thinking runs on your subscriptions and not on Grok usage. Until then each agent thinks on Grok |

## To connect

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 6 | [ ] Slack | Connect Slack in Connect apps and name the channel for each campaign | Plans, reports and alarms |
| 7 | [ ] Notion and the single brain | Connect Notion and name the hub page; say "deploy key" or "Mac pulls" for how the vault's daily note reaches the single brain | Reports in Notion; the single brain in sync |
| 8 | [ ] Auto-review lines and a spending cap | Paste the five lines from INSTALL.md into Auto-review → Custom Rules. Set a monthly limit at grok.com/dashboard/billing | The same gates in the app; no surprise bill |
| 9 | [ ] The opt-out list and the never-touch list | Give the opt-out file when asked; give the names of computers, agents and accounts the team must never use | Any draft to a person; any write to a system |

## Your call, built with a default

| # | What | Built as | Say |
|---|---|---|---|
| 10 | [ ] SpeakerAgent | On for both campaigns. On 2026-11-20 you said "I wouldn't do SpeakerAgent for Find Me Money"; on 2026-11-24 you listed it in the Revenue OS | "as built", or "speaker off for Find Me Money" |
| 11 | [ ] A partners agent | Not installed: it was not in your list. Dream 500 keeps the partner tier | "as built", or "add partners" |
| 12 | [ ] The older packs | The old Find Me Money link now serves this pack. The referral site's own pack is still published and must not be installed beside this one | "as built", or "take the old ones down" |

## Find Me Money campaign

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 13 | [ ] The messaging document | Attach `04-messaging-document.md` and its covered images to the Find Me Money agent | Pieces that use a proof point, a count or a screenshot |
| 14 | [ ] Its claims, cleared one by one | Say which claims are cleared, in your words | Those claims in public |
| 15 | [ ] The CRM | Give `GHL_API_KEY` (read-only first) by hidden prompt. Say which agent files and answers there today, switch it off, then say "pinnacle-ghl: bot" and "crm-writes: on" | Sales and CRM writing records |
| 16 | [ ] Outlets | Name the outlets, the brand account on each, and who publishes | Content going out |
| 17 | [ ] Cold email | Give `INSTANTLY_API_KEY` (read-only first); say "buy N domains" with a budget or "use the existing domains"; say who to prospect and what a first line may say | Cold email and Dream 500 waves |
| 18 | [ ] Search | Verify the site in Google Search Console and Bing. Say yes or no to the tracking tool's cost (`RANKSPOT_API_KEY`) | The weekly read |

## Referral Connection campaign

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 19 | [ ] Its disruptor message | Read `campaigns/referral-connection/MESSAGING.md`: a draft from the site's own words, no research behind it. Say "use it", give your own, or "research it first" | Anything public for this campaign |
| 20 | [ ] The site's admin key | By hidden prompt: `RC_ADMIN_KEY` (the `ADMIN_KEY` variable on the site's service). `RC_SITE` is already set | Reading sign-ups, listings and matches |
| 21 | [ ] The team writes the site's records | Say "referral-site: bot", and whether removal requests are applied or queued for you | Listings, matches, guide drafts on the site |
| 22 | [ ] The launch area and a sender | Name the first city or metro, and the address introductions and outreach go from | Prospects, outreach, introductions |
| 23 | [ ] The site's pages | Say "yes, change the site" in the site's own chat, so the pages and the form cover collaborations, partnerships, sponsorships and deals | The site matching what the campaign says |
| 24 | [ ] Search | Verify the site in Google Search Console and Bing | The weekly read |

## Both campaigns

| # | What | The exact step | Unblocks |
|---|---|---|---|
| 25 | [ ] Skool and Whop | Name the communities to read. Sign the Lead Radar agent in to any that are members-only | Lead Radar past public pages |
| 26 | [ ] The speaker profile | Name, title, talk topics, proof | SpeakerAgent pitches |
| 27 | [ ] The switches that make each campaign run without you | The table at the end of each campaign's `LAUNCH.md`. After you have seen a type's drafts, say "<type>: auto" to that campaign's main agent | Each campaign running on its own |
