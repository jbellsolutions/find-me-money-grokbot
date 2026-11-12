# Find Me Money: the handoff

What Justin does, then what the bot does on its own. Follows the factory PLAYBOOK and the client-build GrokBot standard. Unverified platform facts are flagged *(unverified)*. This pack replaces the v1 pack (never live): one bot, Justin's word 2026-11-12.

## Part 1: Justin

1. **Account.** Sign in at x.ai/bot with the Grok account for **Find Me Money** only, never AI Guy's (one account per business; every bot on it shares one computer, its files and logins). Check the plan covers bots and routines. The bot never buys a plan.
2. **Desktop app.** Open the Grok desktop app. Setup runs in the one-to-one chat there (approval, secret and sign-in requests only show there).
3. **The bot.** Create one bot named **Find Me Money**, pin it, and set Settings → General → Bot → Timezone to **UTC**.
4. **The pack.** The repo is private, so download `find-me-money.zip` from the factory's release `find-me-money-v1` (the factory repo's Releases page), attach it to the first message *(zip route unverified)* and paste:

   > You are Find Me Money. Unpack the attached zip into /workspace/find-me-money/repo/ and follow HANDOFF.md, Part 2, from step 1. Read MASTER-PROMPT.md and CHARTER.md first. Ask me one thing at a time. Nothing sends, posts, spends or writes to a CRM until I say yes in this chat.

5. **Auto-review rules.** At Part 2 step 4, paste the Ask-first lines it shows into Auto-review → Custom Rules.
6. **Sign-ins and keys.** When it asks, sign in through Connect apps, one at a time. Keys go only through a secure secret card or the hidden terminal prompt with **Take over**. Rotate first any key ever pasted in a chat.

## Part 2: the bot

1. **Workspace.** Create `/workspace/find-me-money/` with `context/`, `daily/`, `requests/` (one folder per role: `lead`, `radar`, `muse`, `content`, `outreach`, `sales`, `partners`, `loan-officer`, `wholesale`, plus `justin` and `lead-storm`), `approved/`, `data/` (mode 600), `log/`, `vault/` (Obsidian: `Daily/`, `People/`, `Decisions.md`), `state/` and `state/test/`, `pinnacle-reply/`, `.secrets/` (mode 700). Write:
   - `context/routines-on.md`: every routine in TRIGGER-MAP.md as `<exact name>: off`, plus `crm-writes: off`.
   - `context/owners.md`: one line each, all `live`: `pinnacle-ghl`, `funding-radar`, `radar-cl`, `fbgroups-lane`, `lending-hub`, `muse-app`, `social-sender`, `legacy-agent`, `cold-email-sender`. Check with `python3 repo/guards/scripts/owner_guard.py list`.
   - `context/standing-approvals.md`, `context/spend-approvals.md` (both empty), `context/team-registry.md`, `context/content-log.md`, `context/local-metros.md`.
   - Don't create `context/STOP`. Start `log/setup.md`. Run `python3 repo/tools/check.py` and paste its RESULT line into `log/setup.md`.
2. **Memory and skills.** Save MASTER-PROMPT.md to memory word for word, then each role's "System prompt section" from `roles/`. Save `guards/SKILL.md` and every `skills/<role>/<skill>/SKILL.md` as a private skill ([SKILLS-MAP.md](SKILLS-MAP.md) says which role uses which). Install the engine: `pip install httpx` and `pip install -e repo/engine/pinnacle-reply-agent`; run `python3 -m py_compile` over `repo/engine` and `python3 repo/skills/radar/craigslist-lane/scripts/scrape.py selftest`. Put each key name in `.env.example` into `.secrets/fmm.env` by hidden prompt, one at a time. The non-secret intake values (ids, service URLs, `FMM_HOSTS`, `MUSE_COMPUTER`) go in the same file; Justin pastes them from his private intake list. Write the never-touch names he gives to `.secrets/never-touch.txt` (mode 600), one per line: without that list `preflight`, `owner_guard.py`, `orgo.py` and `muse.py` refuse every guarded write. Leave `REPLY_WRITE`, `REPLY_GHL` and every `FCM_SEND_*` switch off.
3. **Intake.** Ask Justin, one at a time: the Slack channel for this bot (default `#find-me-money-bot`, not the live Hermes orchestrator's channel), the Notion page for the scoreboard and drafts, the suppression list file, the first local metro, the partner list with each partner's products, states and pay, and which templates are already approved. Write `context/owner.md`; save the suppression list as `context/suppression.csv`; mark approved templates in `standing-approvals.md`.
4. **Approval rules.** Show Justin the Ask-first lines from GATES.md to paste.
5. **Connect, read-only, one at a time.** Each gets a Check that reads one real record into `log/setup.md`.

   | App | Roles | Check |
   |---|---|---|
   | Slack, the bot's channel | lead, content | Read the last message |
   | Notion | lead | Read today's scoreboard row (or the page title) |
   | The Funding Radar | radar, wholesale | `GET /api/replies`: today's ask count |
   | treg, One API | radar | Account status and today's read cap |
   | Scrapebox | radar | `status`: which rungs run here |
   | browser-box | radar | `status` |
   | Orgo, the Mac in `MUSE_COMPUTER` only | muse | `owner_guard.py target "$MUSE_COMPUTER"` prints `ok`, then a screenshot shows Muse. Never any other computer |
   | GoHighLevel, Pinnacle Funding Group (read-only key first) | sales | P1 · Funding Leads stage counts |
   | The Lending Hub | sales, partners, loan-officer | `GET /api/deals`: count; `GET /api/distribution/open` |
   | Gmail | sales | Newest thread subject |
   | Instantly (read-only key first) | outreach | Campaign count and last week's reply rate |
   | Reacher (email verifier) | outreach | Verify one known address |

6. **Old agents.** Some of this work may already run live in other agents and services (each one is a system in `context/owners.md`). Two writers never write the same thing: every one of those systems stays `live` in `context/owners.md`, and the bot reads and drafts. Justin moves a system to `bot` only after he pauses its live writer. Record this in `log/setup.md`.
7. **Routines, switched off.** Create all 29 routines in TRIGGER-MAP.md, paused, with the exact names. Each prompt starts `Role: <role>.` and names the script or skill it runs. Record each in `team-registry.md` with role, cron, time zone and next run. A next run an hour or more off means the time zone isn't set.
8. **Report.** Read back every routine and connection into `team-registry.md`, and send Justin the list plus what isn't done and why.

## Usage kit (usage-mastery v1.0.0)

From `grokbot-usage-mastery`. Do these right after the workspace and memory steps.

1. Run `bash repo/usage/scripts/install.sh` (free, pinned, no keys) and paste its last line into `log/setup.md`.
2. Save `repo/usage/SKILL.md` as a private skill named usage-saver.
3. Copy `repo/usage/LEDGER.md` to `log/usage-ledger.md`. Ask Justin for the baseline reading (Settings → Usage: % used and reset date) before the first test day, and again after it.
4. The weekly audit (`repo/usage/AUDIT.md`) runs inside the Monday evening report; it adds no routine and changes nothing.
5. Check: `bash repo/usage/scripts/grep_lines.sh 'usage-mastery v' repo/usage/.. 3` prints at least one line (the rules are in place and the scripts run).
6. Show Justin the two owner-only steps, once per Grok account, and record the answers in `log/setup.md`:
   - A spending cap: grok.com/dashboard/billing → a monthly additional-usage limit, or Auto top-up off. The bot never changes billing.
   - Three lines for Auto-review → Custom Rules (chat only; routines never wait on approvals):

     ```
     Ask first before opening more than 5 web pages for one task.
     Ask first before starting a sub-agent or a second bot on a job.
     Ask first before re-running a step that has already failed twice.
     ```
## Bring-up order

| # | Role | Why this order | Turned on first |
|---|---|---|---|
| 1 | lead | Plans, watchdog, scoreboard; reads only | Morning plan, Watchdog, Scorecard, Evening report |
| 2 | radar | Reads and sorts; nothing reaches a person | Pick today's queue, Craigslist read, Local businesses |
| 3 | wholesale | Reads radar-cl's output; call cards and drafts only | Wholesaler sweep, Wholesale match |
| 4 | content | Drafts only; first post per channel is Justin's | Daily content |
| 5 | muse | Screenshots and reads until `muse-app: bot` | Muse collect, then Muse morning session |
| 6 | sales | Drafts first; CRM writes only after `pinnacle-ghl: bot` (Hermes Reply Agent paused first) | File and draft, Read answers, Sort replies |
| 7 | partners | Proposals only | Partner match, Handoff watch, Affiliate replies |
| 8 | outreach | Deliverability and send volume; the senders stay live systems | Deliverability check, then Cold email drafts, Lead Storm feed |
| 9 | loan-officer | Parked until a verified lender | In-house desk |

## The first-day test run

Every routine is `test` in `context/routines-on.md` and every system is `live` in `context/owners.md`, so nothing reaches a person or a live system. **Test on a routine does real work**: the `test` line goes in before every Test press.

| Step | Role | Do | Pass when |
|---|---|---|---|
| 1 | lead | Morning plan | A plan for every role in `daily/<date>/lead.md` and in the bot's Slack channel |
| 2 | radar | Pick today's queue | Up to 10 drafts from the last 2 days, high tier first, in `requests/justin/`; nothing older than 7 days |
| 3 | radar | Craigslist read (5 sites) | `state/craigslist/posts-<date>.jsonl` written; fit rows in `requests/sales/`; 0 paid calls |
| 4 | radar | Local businesses (one metro, one category) | `requests/outreach/local-<metro>-<date>.csv`; every row checked against suppression |
| 5 | wholesale | Wholesaler sweep | Call cards in `requests/wholesale/`; no contract, no message sent |
| 6 | content | Daily content | Three pieces on three different hooks, each scored 4+ on funny, simple, relatable, in `requests/justin/` |
| 7 | muse | Muse collect | A screenshot of Muse and today's Muse file; nothing typed (owner is `live`) |
| 8 | sales | File and draft, then Read answers, then Sort replies | Cycle runs, the beat says `CRM held (live owns pinnacle-ghl)`; fcm runs `dry`; any answer sorted with the next message drafted |
| 9 | partners | Partner match | Each applicant with a partner OK gets "in-house" or one partner and a reason, as a proposal only |
| 10 | outreach | Cold email drafts, Lead Storm feed | Verified list and copy in `requests/justin/`; queue items say `approved: waiting on Justin` |
| 11 | All | Suppression test | Add a known name with `suppression.py add`; radar, sales, outreach and wholesale all hold it |
| 12 | All | Owner test | `owner_guard.py check pinnacle-ghl --routine "File and draft"` prints `live`; set the routine to `on` and the system to `bot` in a scratch copy only: prints `bot`; restore |
| 13 | All | STOP test | Create `context/STOP`; the next run of every role says stopped and does nothing; remove it |
| 14 | lead | Evening report | Every role has a line; today's vault note exists; `beat.py status` shows no SILENT; 0 sent, 0 posted, 0 live-system writes |

The day passes when every row passes. Then Justin approves each message type once, and roles go `on` one at a time in the bring-up order.

## Reporting back

| Where | What | Written by |
|---|---|---|
| Slack, the bot's own channel | Morning plan, alarms (silent roles, unapproved sends), evening report, Justin's queue | lead |
| Notion | Scoreboard row a day; Drafts waiting on Justin | lead |
| The workspace vault | `vault/Daily/<date>.md`, `People/` (companies, not contact details), `Decisions.md` | lead writes the daily note; each role adds its section |
| The single brain | A scrubbed status line and the daily summary, no raw transcripts or contact data | lead's Evening report through a deploy key, or Justin's Mac pulls: Justin's pick on NEEDS-JUSTIN |
