# NEEDS-JUSTIN: Find Me Money

Only what Justin can do, in dependency order: nothing on a line can start before the lines it names in "Needs". Each line: what, the exact click or command, what it unblocks. Ticked off in order when he works the list.

"Was" is the item's number in the older list, so notes that say "items 20 to 23" still resolve.

**Checked 2026-11-15, read-only.** Status words: **open** means a check showed it is not done; **unverified** means nothing this pack's owner can read shows it either way (the Grok account, the bot's computer and the Mac are not readable from the factory), so it is treated as not done; **ready** means the pack's side is built and tested and it waits only on the step.

**Version 6 (2026-11-20)** is the combined install: two project agents and one agent per role, both disruptor launches, SpeakerAgent off. It adds Track F at the bottom. **Version 5 (2026-11-20)** made each role its own agent and added Track E: what the team needs from you. **Version 4 (2026-11-20)** added Track D: what the two sites need from you. **Version 3 (2026-11-18)** added Track C: what the Revenue OS needs from you. To start, only B1 and B2 are needed: the lead agent then creates the team, and the team builds everything that needs nothing from you and shows you the rest as one list.

## Track A: the Mac (needs no Grok bot)

The worker install depends on the Orgo key, the Mac's name and the never-touch list. It does not depend on the bot, so it can be done first. Only step A6 needs Track B.

| # | Was | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|---|
| A1 | new | [ ] Let the owner chat read the Mac | Type "yes, read the Mac" in the pack's owner chat. It runs read-only commands on the computer in `MUSE_COMPUTER`, nothing else: is the `find-me-money` Hermes profile there, are its jobs all paused, is `~/fmm-worker` absent, is a permission prompt on screen | Nothing | A true before-picture for A2 to A5 | open: the read was refused by the app's permission check, so every Mac fact below is unverified |
| A2 | 20 | [ ] Install the Hermes worker, paused | Type "yes, install the worker". The chat runs, from a computer with this pack: `MUSE_COMPUTER=<the Mac> bash hermes-worker/install.sh` (dry run, prints only), then the same with `ORGO_API_KEY`, `NEVER_TOUCH` and `--go`. What `--go` changes is listed under this table | A1 | A3, and every work order: groups by theme, Marketplace, Muse, Craigslist, places, wholesalers | ready: dry run clean, install and remove bodies pass in a sandbox; never run on the Mac |
| A3 | 20 | [ ] Turn the worker job on | Type "yes, turn on fmm-worker-inbox". On the Mac: `hermes -p find-me-money cron resume fmm-worker-inbox`. With an empty inbox it only writes a heartbeat every 15 minutes | A2 | The worker answers orders; `hermes_bridge.py status` shows a heartbeat | unverified |
| A4 | 14 | [ ] The System Events "Allow" click on the Mac | On the Mac's own screen, click **Allow** on the prompt that asks to let the Hermes process control System Events (macOS asks once per program that sends the keystrokes, so an Allow given to another program does not cover the worker). If no prompt shows, it appears at the worker's first `muse` order. The bot and the chat never click it | A3 | The `muse` lane, and Marketplace read through Muse. Every other lane works without it | unverified |
| A5 | 23 | [ ] Turn on the Hermes profile's own jobs | One at a time, your yes for each: `hermes -p find-me-money cron resume <job id>` on the Mac (the reply cycle, the sweeps, sorting, the scorecard). First say which computer is the one live reply agent: if a reply agent already runs on another computer, the Mac's reply cycle stays paused, because two writers never write the same thing | A1 | Reply sweeps and sorting with no Grok usage; the `profile/` files in each Pull | unverified |
| A6 | 20 | [ ] Hand the worker to the bot | Say "hermes-worker: bot" in the bot's chat | A3, B2 | Dispatch sends orders to the Mac instead of holding them in `requests/hermes/` | unverified |

**What `--go` changes (A2).** On the computer you run it from: two copied files inside `hermes-worker/` (`lead-map.md`, `lanes/fbgroups_miner.py`), both ignored by git. On the Mac, in this order, stopping at the first failure:

1. Reads the Mac's home folder, then copies `hermes-worker/` to `~/fmm-worker` (same-named files overwritten, nothing else there touched).
2. Stops with "no find-me-money profile on this computer" if `~/.hermes/profiles/find-me-money/cron/jobs.json` is missing.
3. Runs the worker's offline self-test. A failure stops here, before anything in Hermes is changed.
4. Backs up `jobs.json` to `~/Backups/fmm-worker-<UTC time>/` (mode 700).
5. Creates `~/.fmm/grok/inbox`, `outbox`, `done` and `~/.fmm/groups`.
6. Adds ONE job to that profile's `jobs.json`: `fmm-worker-inbox`, every 15 minutes, no model of its own, `enabled: false`, `state: paused`. A job of the same id is replaced; no other job is touched.
7. Writes `~/.hermes/profiles/find-me-money/scripts/fmm-worker-inbox.sh` (runs `dispatch.py run --max 4`).
8. Checks the job shows in `hermes -p find-me-money cron list --all`; if not, it puts the backup back and fails.

It turns nothing on and touches no other profile, SOUL, config or job. `--remove` backs up `jobs.json`, takes the job, its script and `~/fmm-worker` off, and keeps `~/.fmm`.

**Reinstall note.** The Hermes profile's own installer renders `jobs.json` from its table. A reinstall from there drops `fmm-worker-inbox` unless that table lists it. After any profile reinstall, re-run A2 and A3.

## Track B: the Grok bot

| # | Was | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|---|
| B1 | 1 | [ ] Grok account for Find Me Money | Sign in at x.ai/bot with a Find Me Money account (never AI Guy's); check the plan includes bots and routines | Nothing | Everything in Track B | unverified |
| B2 | 2 | [ ] Create the lead agent | Grok desktop app: new bot "Find Me Money", pin it, Settings → General → Bot → Timezone **UTC**, then paste the message in HANDOFF.md Part 1 step 4 (it downloads `releases/latest/download/find-me-money.zip`; attach that zip if the download fails) | B1 | Setup, and the lead creating the other eleven agents (Track E) | unverified. The link itself works: it returned the zip, logged out |
| B3 | 3 | [ ] Auto-review rules and the spending cap | When the bot shows them (Part 2 step 4): paste the Ask-first lines from GATES.md into Auto-review → Custom Rules, one rule each, then the three usage lines from HANDOFF "Usage kit" step 6. Set a monthly additional-usage limit at grok.com/dashboard/billing, or turn Auto top-up off | B2 | Safe routines; no surprise bill | unverified |
| B4 | 6 | [ ] Intake values (not secrets) | Paste the private intake values into `.secrets/fmm.env` when the bot asks: `GHL_LOCATION_ID`, `PINNACLE_GHL_LOCATION_ID`, `FM_GHL_LOCATION_ID`, `FM_GHL_CALENDARS`, `REPLY_NEVER_LOCATIONS`, `FCM_NEVER_SAY`, `FMG_NURTURE_WORKFLOW_ID`, `FMG_REACTIVATION_WORKFLOW_ID`, `FMG_SALES_CONTENT_WORKFLOW_ID`, `FMG_NEWSLETTER_WORKFLOW_ID`, `RADAR_URL`, `RADAR_IMPORT_URL`, `HUB_URL`, `REACHER_URL`, `ONE_API_URL`, `ONE_API_HUB_URL`, `FMM_HOSTS`, `MUSE_COMPUTER`, `INSTANTLY_WINNR_TAG_ID`, `GHL_COMPANY_ID`, `GHL_MCP_HOME`, `SUPER_BROWSER_URL`, `FULFILLMENT_PARTNER`, `FMM_MAILING_ADDRESS`, and `REPLY_GHL_TARGET=pinnacle-funding-group` (the code default is the other funding location, which is never written). The never-touch names go into `.secrets/never-touch.txt`, one per line; the persona names into `.secrets/personas.json`; the wholesaling method notes into `.secrets/course/method.md`; the Charm Offensive templates into `.secrets/course/charm/` | B2 | Preflight, the owner guard, Orgo and Muse (all refuse until the never-touch list and `FMM_HOSTS` exist), the scorecard and every CRM write | ready: every name above has a value in your private intake file; pasted into the bot is unverified |
| B5 | 5 | [ ] Keys, by hidden prompt (names only) | One at a time when the bot asks, through a secure secret card or the hidden terminal prompt with **Take over**: `SLACK_BOT_TOKEN`, `NOTION_TOKEN`; `RADAR_PASSWORD`, `RADAR_IMPORT_TOKEN`; `TREG_API_KEY`; `ONE_API_TOKEN` (a revocable agent key); `SCRAPEBOX_URL`, `SCRAPEBOX_TOKEN`; `BROWSER_BOX_URL`, `BROWSER_BOX_TOKEN`; `ORGO_API_KEY`; `GHL_API_KEY` (read-only first); `ANTHROPIC_API_KEY`; `HUB_PASSWORD`; `INSTANTLY_API_KEY` (read-only first). Rotate first any key ever pasted in a chat | B4 | The tools each role uses | unverified |
| B6 | 7 | [ ] Slack channel and Notion page | Create the bot's own channel (default `#find-me-money-bot`) and name the Notion page; invite the bot to both | B5 | The daily report and alarms | open: no Slack channel with "find-me-money" in its name exists. Notion page unverified |
| B7 | 4 | [ ] Sign-ins | Gmail and Slack through Connect apps when the bot asks, one at a time. InvestorLift (wholesale inventory). The Lender portal of a verified lender only when you name one | B2 | Sales inbox, the report, wholesale inventory, the loan officer | unverified |
| B8 | 8 | [ ] Suppression list | Give the bot the opt-out file when it asks (never in the repo) | B2 | Any draft to a person | unverified |
| B9 | 22 | [ ] The private lists | Give the bot your lists at intake: `influencers.csv`, `coaches.csv`, `communities.csv`, `partner-targets.csv` (columns in `data/lists/README.md`). On the Mac, put Facebook group links by theme into `~/.fmm/groups/<theme>.txt`, one per line, or let the worker's `group-discovery` lane build them | B2; the Mac part needs A2 | Theme lanes start from what you already have, not from zero | ready: the folder and its format are in the pack; lists given is unverified |
| B10 | 10 | [ ] First local metro | Name it, or "use the default" (the metro with the most fit asks that week) | B2 | Local businesses | unverified |
| B11 | 9 | [ ] Lead Storm VPS | Say where it runs, which agents and platforms, and how it takes work: a folder, an API, a Slack channel or a repo | B2 | The bot's social queue reaching the VPS | open: decided that the bot feeds it and the VPS sends; how it takes work is not recorded anywhere |
| B12 | 17 | [ ] Spend caps | A daily cap for Radar credits, One API and paid scrape rungs, written as `<plan-id>: approved <usd>` | B2 | Anything past the free rungs | unverified |
| B13 | 11 | [ ] Approve each message type once | After the first-day test passes: reply yes to each draft type in Notion Drafts (public reply, email reply, cold email, social DM, content post, wholesaler first touch, deal pass, partner message). Say "auto" for a type once its replies look right | B6, B8, the first-day test | Sends | unverified |
| B14 | 12 | [ ] First post per channel | Approve the first viral piece for each channel, and say who posts (you, a poster, or a scheduler) | B13 | Content going live | unverified |
| B15 | 13 | [ ] Which system the bot takes over first | Pause the live writer for one system, then say "<system>: bot" (for the CRM also "crm-writes: on"). The other systems the same way, one at a time | B13 | CRM writes, Radar imports, Muse typing | unverified |
| B16 | 14 | [ ] Muse | Say "muse-app: bot" once the Mac's Muse is free of any other driver, and say whether Muse's past finds move to the home CRM | A4, A6, B15 | Muse as a lane | unverified |
| B17 | 15 | [ ] One active partner and the split | Name one partner with products, states and pay, set the commission rate (`[RATE]` is still open), then "yes, deploy Hub distribution" | B15 | Any lead or deal reaching a partner | unverified |
| B18 | 16 | [ ] Cold email domains | "Buy N domains" with a budget, or "use the existing Instantly domains" | B13 | Cold email going out | unverified |
| B19 | 18 | [ ] Single brain path | "Deploy key" (the bot pushes its daily note) or "Mac pulls" | B2 | Reports reach the single brain | unverified |
| B20 | 21 | [ ] Codex CLI on the bot's computer | Now part of the Revenue OS: Track C, items C1 and C2 | B2 | See C1, C2 | unverified |
| B21 | 19 | [ ] Archive the v1 pack | "Archive the v1 pack" once this bot is set up | B2 through B13 | One pack, no confusion | open: the v1 repo is not archived |

## Track C: the Revenue OS (version 3)

The bot builds all nine agents on test without any of these. Each line is what one agent, or the engines, needs from you to go past drafts. Nothing here has been done by anyone.

| # | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|
| C1 | [ ] Yes to the two CLIs on the bot's computer | Say "yes, install the CLIs" in the bot's chat. It runs `npm install -g @anthropic-ai/claude-code @openai/codex` on its own computer, then `python3 repo/engines/route.py --check`. No cost beyond the two subscriptions | B2 | C2 | open |
| C2 | [ ] Sign the two CLIs in | **Claude Code CLI:** on your Mac run `claude setup-token`, then give the token to the bot by hidden prompt as `CLAUDE_CODE_OAUTH_TOKEN` (never in chat). **Codex CLI:** turn on device sign-in in ChatGPT's security settings, then use **Take over** on the bot's computer and run `codex login --device-auth` as the user the routines run as. Then say "check the engines", and again the next day | C1 | Content on Claude Code; the sales agent, Lead Radar, SpeakerAgent, AEO and SEO on Codex. Until then the bot does that thinking itself, on the Grok plan | open: neither CLI has run on a Grok bot's computer |
| C3 | [ ] Where the engines run: confirm or reverse | This pack puts Claude Code and Codex on the bot's computer, from your words on 2026-11-18 ("give it to GrokBot... have it go build it"). The older open question was keeping them on the Mac, where every funding agent runs today. Say "bot computer is right" or "keep it on the Mac" | Nothing | If "keep it on the Mac": the engines move there in the next pack version; the bot still orchestrates | open: built as "bot computer" |
| C4 | [ ] The CRM field for a person's note | Name the contact field in Pinnacle that holds the link to a person's vault note, or say "make one" (a new custom field is a CRM write: your yes) | B5 | The sales agent attaching each person's note to their contact | open |
| C5 | [ ] One sales agent: which live agent is the base | Two agents on the Mac do this job today: the CRM manager (reads and files, sends held) and the reply agent (drafts only). Say "CRM manager is the base" or "reply agent is the base"; when the bot's sales agent has passed its test day, say "yes, switch the other off", then "pinnacle-ghl: bot" and "crm-writes: on" | C2, the first-day test | The bot's sales agent answering and writing the CRM. Until then it drafts and logs only, so nothing double-writes | open |
| C6 | [ ] Dream 100 and Dream 500: the offer to a partner's audience, and the lists | In your words: what Find Me Money gives a partner's audience at no cost, and what their audience gets from it. For the lists: give them (B9), or say "build them from the rubric" | B2 | First-touch drafts for both Dream tiers | open: `sites/find-me-money/settings/dream-100.json` has both lines empty |
| C7 | [ ] Content: the outlets, the accounts, who publishes | Name the outlets (set now: YouTube, newsletter, Instagram, Facebook; LinkedIn off), create or name a brand account for each, and say who publishes on each. Your content setup (workflows, where recordings live) when you have it. Any video tool is its own plan or credits: say which, if any | B2 | Content leaving the draft queue. YouTube is the strongest lever on record: AI answers cite YouTube on most funding questions and the site on none | open: no brand account is on record for any outlet |
| C8 | [ ] AEO and SEO: the verifications and the tracking tool | Verify the site in Google Search Console and Bing (your sign-ins). For the tracking tool (RankSpot): a key by hidden prompt as `RANKSPOT_API_KEY`, and "yes" to its daily run: 15 questions on 4 platforms is about $7.20 a month at the prices read 2026-11-16, under a $20 monthly cap in the settings | B2 | The weekly read with real numbers: leads, front-page terms, the share of AI answers that name the site | open |
| C9 | [ ] The domain decision | This is B18: "buy N domains" with a budget, or "use the existing Instantly domains". It now also carries Dream 500 and partner email at volume | B13 | Cold email, Dream 500 waves and partner email going out | open |
| C10 | [ ] The cold email charter | In your words: who to prospect, how, and what a first line may say | B2 | Cold email lists and first lines | open: `sites/find-me-money/settings/cold-email.json` has it empty and the daily number at 0 |
| C11 | [ ] SpeakerAgent: now off for both sites (version 6, your words). Only if you turn it back on: do you want shows for funding, and the speaker profile | "Yes" or "no shows". If yes: the speaker's name and title, the talk topics, the claims you approve word for word, and the proof that may be named | B2 | Pitches. Finding and scoring shows runs without it | open |

## Track D: the two sites (version 4)

The bot builds and tests every agent for both sites without any of these. Each line is what a site needs from you to go past drafts. Nothing here has been done by anyone.

### Find Me Money: the Disruptor

| # | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|
| D1 | [ ] Give the bot the messaging document | When the bot asks: attach `04-messaging-document.md` from the business's private repo (`research/messaging/`), and the covered images you want used. It is private, so it is not in the pack | B2 | Content, outreach and guides that use your words, the proof points, the counts and the images. Until then the bot drafts from the public outline only (`sites/find-me-money/MESSAGING.md`) | open |
| D2 | [ ] Clear the claims list | Section 9 of that document, 18 items. Three need your decision before any content: claims 1 to 3 ("fraudulent industry", "the lies, the deceit": your opinion, or narrowed to what is documented), claim 9 (tell the lead-buying as the insider story), claim 8 (who reviews pillars 6 and 7, the creative routes, before they are taught). Say each in the bot's chat | D1 | Each piece that leans on a cleared claim. Pillars 6 and 8 are the "creative alternative ways", and pillar 6 waits on the review in claim 8 | open |

### The referral connection site

| # | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|
| D3 | [ ] The site's admin key | By hidden prompt when the bot asks: `RC_ADMIN_KEY` (the `ADMIN_KEY` variable on the site's Railway service). `RC_SITE` is `https://findreferralpartners.com` | B2 | Every read of the site: sign-ups, listings, connection requests, matches | open |
| D4 | [ ] Let the bot write the site's records | After its test day: say "referral-site: bot" | D3 | Listings, matches and guide drafts saved on the site. Until then each is a proposal in your queue | open |
| D5 | [ ] Removals | Say whether the bot may apply a removal request itself (`rc.py remove <email>` deletes that member's records) or queues each one for you. The pack's gate says the bot never deletes data; the site's privacy page promises removal | D3 | Removal requests being honoured | open |
| D6 | [ ] The launch area | Tell the bot the first city or metro, and trades if any | B2 | Prospects, outreach and the first matches | open |
| D7 | [ ] A sender address for member email | Name the address introductions and outreach go from, and connect it through Connect apps | B2 | Introductions and outreach leaving the draft queue. No email leaves the site today | open |
| D8 | [ ] Approve each message type once | After the test day: yes to each draft type (`rc_outreach_first`, `rc_outreach_followup`, `rc_reply`, `rc_group_post`, `rc_introduction`, `rc_match_followup`, `rc_guide`); "auto" for a type once its replies look right | D4, D7 | Sends and published guides | open |
| D9 | [ ] Google Search Console for the site | Verify findreferralpartners.com in Google Search Console and Bing (your sign-ins) | Nothing | The weekly read with real search numbers | open |
| D10 | [ ] The site's pages and form for all four | The site's pages and sign-up form are written for commission referral campaigns. Your words on 2026-11-20 add collaborations, partnerships and sponsorships. The bot writes the brief; say "yes, change the site" in the site's own chat, where its code lives | Nothing | A visitor who wants a sponsor or a collaboration seeing themselves on the page | open |
| D11 | [ ] One team for the referral site: confirm | This pack has the Find Me Money team run the referral site. The site also has its own pack (`referral-connection` v1.0.0), not installed. Say "this bot runs it" or "its own bot": two bots on the same records would double-write | Nothing | If "its own bot": set `referral-connection: off` in `context/sites.md` here | open: built as "this bot runs it" |

## Track E: the team, one agent per role (version 5)

Your words, 2026-11-20: "it should be in grokbot with each role being its own agent", and "nine functions = 9 agents". The pack sets up 12 agents at install (the two project agents, eight of the nine functions, the worker and wholesale). SpeakerAgent and the loan officer are created later, on your word. [TEAM.md](TEAM.md) has the list. Whether a bot can create another bot is not known, so E1 may or may not come up.

| # | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|
| E1 | [ ] Create the eleven agents, only if the lead cannot | If the lead says the app will not let it create a bot: open `requests/justin/create-the-team.md`. For each of the eleven names in it, create a bot with that exact name, set Settings → General → Bot → Timezone **UTC**, and paste its message. Each answers "ready" | B2 | Every agent but the lead | unverified: nobody has tried a bot creating a bot |
| E2 | [ ] UTC on each agent, only if the lead cannot set it | Settings → General → Bot → Timezone **UTC** on each agent the lead names | E1 or the lead's own creation | Routines that fire at the right hour | unverified |
| E3 | [ ] Auto-review rules on each agent, only if they are per bot | The lead says which after the first agent's test. If per bot: paste the same lines from B3 into each agent's Auto-review → Custom Rules | B3 | The same Ask-first gates on every agent | unknown |
| E4 | [ ] The plan covers twelve bots | Check at x.ai/bot how many bots the Find Me Money plan allows. If fewer than twelve, say which agents wait | B1 | The full team | unknown |
| E5 | [ ] One agent per role, as built: confirm the cut | Built as: the nine Revenue OS functions each an agent, plus the two project agents, and the worker, wholesale and loan officer as their own agents (14, 12 at install). Say "as built", or name roles to fold together | Nothing | Nothing waits on it | open: built as 13 |

## Track F: two autonomous businesses (version 6)

Your words, 2026-11-20: "one-click install that combines the Referral Connection site and Find Me Money... two separate project agents... the goal is for those two to be autonomous businesses... They're both disruptor campaigns." The team builds everything and drafts both campaigns' libraries without any of these.

| # | What | The exact step | Needs | Unblocks | Status |
|---|---|---|---|---|---|
| F1 | [ ] Content and SpeakerAgent: confirm the reading | You said: "I wouldn't do any content. I wouldn't do SpeakerAgent for Find Me Money, but I would do content, and that's the disruptor campaign." Built as: SpeakerAgent off for both sites, content on for both. Say "as built", or say which site gets no content | Nothing | Nothing waits on it | open: built as read |
| F2 | [ ] The Referral Connection's disruptor message | Read `sites/referral-connection/MESSAGING.md`. It is a draft written from the site's own words, with no research behind it. Say "use it", give your own position, or say "research it first" | Nothing | Anything for the referral site going public. Drafts are made from it meanwhile | open: draft |
| F3 | [ ] The switches that make Find Me Money autonomous | The table at the end of `sites/find-me-money/LAUNCH.md`. Turn on the ones you want, one at a time, after you have seen that type's drafts: say "<type>: auto" or "<system>: bot" in the Find Me Money agent's chat | B13, the test day | Find Me Money running without you in the daily loop | open: every switch is off |
| F4 | [ ] The switches that make The Referral Connection autonomous | The table at the end of `sites/referral-connection/LAUNCH.md`, the same way, in the Referral Connection agent's chat | D3, D4, the test day | The Referral Connection running without you in the daily loop | open: every switch is off |
| F5 | [ ] One pack or two: confirm | This combined install replaced version 5 at the same link, so there is one Find Me Money link. The referral site's own pack (`referral-connection-grokbot`) is still published and must not be installed beside this one (D11). Say "one link", or "give the combined pack its own name" | Nothing | Nothing waits on it | open: built as one link |
