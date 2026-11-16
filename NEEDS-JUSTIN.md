# NEEDS-JUSTIN: Find Me Money

Only what Justin can do, in dependency order: nothing on a line can start before the lines it names in "Needs". Each line: what, the exact click or command, what it unblocks. Ticked off in order when he works the list.

"Was" is the item's number in the older list, so notes that say "items 20 to 23" still resolve.

**Checked 2026-11-15, read-only.** Status words: **open** means a check showed it is not done; **unverified** means nothing this pack's owner can read shows it either way (the Grok account, the bot's computer and the Mac are not readable from the factory), so it is treated as not done; **ready** means the pack's side is built and tested and it waits only on the step.

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
| B2 | 2 | [ ] Create the bot | Grok desktop app: new bot "Find Me Money", pin it, Settings → General → Bot → Timezone **UTC**, then paste the message in HANDOFF.md Part 1 step 4 (it downloads `releases/latest/download/find-me-money.zip`; attach that zip if the download fails) | B1 | Setup | unverified. The link itself works: it returned the zip, logged out |
| B3 | 3 | [ ] Auto-review rules and the spending cap | When the bot shows them (Part 2 step 4): paste the eight Ask-first lines from GATES.md into Auto-review → Custom Rules, one rule each, then the three usage lines from HANDOFF "Usage kit" step 6. Set a monthly additional-usage limit at grok.com/dashboard/billing, or turn Auto top-up off | B2 | Safe routines; no surprise bill | unverified |
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
| B20 | 21 | [ ] Codex CLI on the bot's computer (optional) | Install Codex on the bot's computer and sign it in yourself through the secure path; say "codex-cli: bot" | B2 | Bulk drafts on Codex's subscription instead of Grok's allowance | unverified |
| B21 | 19 | [ ] Archive the v1 pack | "Archive the v1 pack" once this bot is set up | B2 through B13 | One pack, no confusion | open: the v1 repo is not archived |
