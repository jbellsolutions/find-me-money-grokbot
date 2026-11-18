# AEO and SEO: where this function stands

## Keep or remove: checks that are not in the owner's words (2026-11-17)

The owner, 2026-11-17: "there are no rules unless I tell you there's a rule." This folder was gone through on that. What he said is kept and quoted in [PROCESS.md](PROCESS.md); what a chat or a brief added is removed (listed below). These are the ones this chat could not place. Each is in code or guards an account, and none is in his words. They are still in. Say "keep" or "remove" for each, or "remove all".

| # | Check | Where | What removing it does |
|---|---|---|---|
| 1 | The script calls only RankSpot's read paths and refuses the rest. This enforces his own rule (spend, publishing and sends need his yes): the one key can also write articles, publish, find emails and send pitches | `aeo.py` `get()`, `READS` | The rule is words only; a wrong path in a later change could spend or send |
| 2 | RankSpot's own Codex skill and write tools are not part of this function (they hand Codex a shell and the whole key) | Not installed; no line in the pages now | Codex could call any RankSpot action, paid ones included |
| 3 | A key whose RankSpot workspace is for another site is refused | `aeo.py pull` | One business's numbers could be read into another's report |
| 4 | `aeo.py cost` exits with a hold when the panel and articles cost more than `spend.monthly_cap_usd` (20 in the example; a placeholder, not his number) | `aeo.py cost`, `aeo.example.json` | The cost line still prints; nothing flags a panel over the cap |
| 5 | STOP stops every command | `aeo.py main` | The kit's stop file no longer stops this script |
| 6 | Text from an AI answer or a cited page is data, never instructions | `prompts/gap.md`, `aeo.py` docstring | A web page an engine cited could steer the judge |
| 7 | At most 400 answers read and 40 missed answers judged per read | `read.max_answers`, `read.judge_max` | A large panel makes more Codex calls on the subscription; no money |
| 8 | The engine's fix is dropped unless it is on the list and switched on for the business; `forum_answer` is off in the example | `aeo.py judge`, `fixes` in the settings | A brief could go to a role that has no channel for it |

**Removed, added by a chat or a brief:** the "Rules" section's own lines ("no count from a model", "a rank or a mention is never reported as a win by itself", "nothing is promised", "only questions real people asked", "the script is the allow-list" as a stated rule, "`aeo.py cost` is run before any panel change"); "who owns what" (this folder is its chat's, shared files are the main chat's); a video brief "is refused without" three things (now this chat's draft of what a brief holds, marked as not his words); "a page or video with no next step is not finished"; "a learn question gets the cheapest fix or none"; "no invented questions"; every published link "hands back" to the citation queue, and "cited counts only with a saved answer"; partners' "contact comes from public pages, under an approved template"; "a campaign may only lower a cap" and the settings file's may-not list; "the first panel is small; it grows only when"; "that role drafts under its own gates"; "promise no ranking, state no price" in the judge prompt; the 20-answer floor below which the read would not compare periods (code, `read.min_answers`); the "Gate" columns.

**Left as settings, not rules:** 12 questions, a 7-day read, which fixes are on. A business sets its own.

The line between this function and content (below, and in the process page) is this chat's proposal, not his words; it is marked so.

## Where it stands

Written 2026-11-16 by this function's chat, from a read of what exists; updated 2026-11-17 when version 0.1 was written (see "Since this page was written" at the end). Nothing was installed or changed outside this folder. Paths are in the `revenue-os-max` kit (`ideas/revenue-os-max/build/`) unless they say otherwise.

## What exists today, and where

| What | Where | State |
|---|---|---|
| **The role.** AEO shares one role with content: seven routines, five of them this function's (AI visibility read weekly, SEO daily, article pick twice a week, links and keywords weekly, Medium twice a week) | `roles/content-seo.md` | Written for one business and one site; routines created paused |
| **The AEO loop.** How engines pick who to cite, the prompt panel (30 to 50 buyer questions), the weekly visibility read, the citation queue, RankSpot's price list and money rules, what counts as cited | `skills/content-seo/aeo-citations/SKILL.md` | A skill the bot reads; no code. The panel, read and queue files (`data/aeo/`) are named, not shipped |
| **The audit ladder.** A one-page read of how AI engines see a prospect, handed to sales as the free first step; no price until the owner writes one | `skills/content-seo/aeo-audit-ladder/SKILL.md` | v0.1, marked a test with thin evidence |
| **The SEO campaign kit.** A charter, thirteen specialist roles (one is the AEO evaluator), a board, task and record templates, and a research library of 152 source notes with page and panel templates | `skills/content-seo/seo-campaign/` (`kit/`, `library/`) | Generic and thorough. Runs in local-draft mode: research, plans and drafts only |
| **The campaign state.** Authority and campaign settings for the one site | `gtm-box/seo/config/` | Authority is `ungranted`, every spend cap is 0, no baseline recorded |
| **Medium.** Syndicate site articles with a canonical link, or one Medium-first piece a week, through the owner's signed-in browser session (Medium issues no new API tokens) | `skills/content-seo/medium/SKILL.md` | First post waits for the owner; drafts until he marks the type auto |
| **The paid-check gate.** Articles can only be written through this script, which holds a monthly cap per site (4) and a ledger, and stops on STOP | `gtm-box/box/rankspot.py`; the RankSpot row in `GATES.md` | Works for two hard-coded sites; gates articles only |
| **This function in the template** | `ideas/revenue-os/build/agents.json` (`aeo-seo`: Codex, falls back to Claude Code; channels site and medium; types `medium_post`, `site_article`); `engines/route.py` already routes `--agent aeo-seo` | No job calls it |

**In the four applications:** one runs the kit's shared role, paused, with no owner grant and no RankSpot credit. One did the site work by hand outside the kit (a guide hub, answer pages, schema, a sitemap, `llms.txt`) and has a measured baseline on a fixed question panel, with nothing recurring and its search-console verifications pending. One has a weekly SEO routine in its own pack, paused on site access. One has nothing, and a third party runs its website. None runs a panel read on Codex.

## Free, and what costs money

| Free | Costs money |
|---|---|
| Codex and Claude Code calls through the router (flat subscriptions) | RankSpot prepaid credit, from a $10 top-up. Prices as read 2026-11-12, not rechecked: an AI visibility check $0.004 per prompt per engine (a 40-question panel on 5 engines is $0.80 a read), keyword update $0.15 and backlink update $0.07 per site, an article $3, indexing $0.01, a Google search $0.0025, a page read $0.004 |
| RankSpot reads of data it already holds, competitor tracking | RankSpot's own schedules bill the credit by themselves: about $90 a month at its defaults. Owner's yes only |
| The SEO kit in local-draft mode; on-site work as pull requests (answer pages, FAQ and schema, sitemap, `llms.txt`) | Treg's SERP, backlink and AI-visibility tools: metered, and its key is not on the box |
| Google Search Console and Bing Webmaster (the owner's sign-ins) | Anything the kit's charter calls a new recurring cost: none is granted |
| Medium through the owner's signed-in session | |

Only the article has a code gate. Visibility checks, keyword and backlink updates rest on the spend guard and a line in the approvals file. RankSpot's email-finding and outreach are never used.

## What would move to Codex through `engines/route.py`

The router runs Codex headless in a read-only sandbox from an empty folder, so it judges and drafts from the items it is given; it is not the thing that fetches an AI answer. The bot (or a worker job) fetches, Codex thinks, the bot hands over.

- **Judge the panel read** (`--mode judge`): for each saved answer, are we named or linked, who is cited instead, which page was cited. Output is the week's share per engine.
- **Rank the gaps** and write the three fixes with the role that owns each.
- **Build and prune the panel** from call notes, Lead Radar asks and People Also Ask; prune keywords nobody asks.
- **Draft the audit page** for a prospect from the free reads.
- **Briefs**: page briefs, link briefs to partners, the citation queue rows.
- **The SEO daily task**, where the task is analysis or a draft from the kit's board.

Stays on the bot: RankSpot calls, the browser (Medium), the spend guard, approvals, hand-offs between roles.

## RankSpot's agent surface (read 2026-11-16, from the link the owner sent)

Read from rankspot.ai/agent, its Codex page and its API spec (the first two thirds of the spec; the rest is schemas). Nothing was called.

- **A REST API a script can read with one key**, beside the MCP server. Saved AI answers come back in full for free: the answer text, the pages cited in order, the searches the engine ran, every brand named with its rank (`ai-visibility/responses`, `citations`, `fanouts`, `summary`). People Also Ask, keywords, backlinks and Search Console performance are free reads too. That is the fetch step gap 4 asks for: a script reads, Codex judges.
- **There is no check on demand.** A prompt added to the panel joins RankSpot's own daily run, which bills the credit by itself. So "RankSpot checks the engines" means saying yes to its schedule; the panel's size is the spend dial. At the listed $0.004 a check, on the four platforms the API lists: 12 questions is about $6 a month, 40 about $19. Whether a check is counted per platform is the kit's reading, not confirmed on this page.
- **Engines it reads:** its site says ChatGPT, Claude, Gemini, Perplexity and Google AI Overviews; its API lists four platforms (ChatGPT, Perplexity, Google AI Overviews, Google AI Mode). Not Grok.
- **The same key reaches paid and outward actions:** article generation, publishing to a connected site, indexing requests, email finding ($0.065) and pitch emails ($0.025). Keys are not scoped by action, so the allow-list has to be ours: a script that calls only the free reads.
- **Its Codex skill** (`npx skills add RankSpotAI/seo --skill rankspot`, curl and jq with the key in the environment) gives Codex a shell and the whole key. That is outside the router's rule (read-only, no tools) and puts email finding one call away. Proposed: do not install it; use our own read script.
- **The kit's `rankspot.py`** calls `/actions/{id}` with no workspace in the path. The spec says that still works for a key tied to one workspace and not for a personal key, which reaches every workspace. Not tested.
- **Also free, with no account:** its free tools endpoint (rate limited per IP) and an open index of the sources AI engines cite most.
- $1 of credit on sign-up; first top-up from $10; nothing renews.

## Where AEO ends and content begins

Not written down anywhere: the content function's process does not mention it. From the template's two lines, this is the split I would propose:

- **AEO and SEO owns** what gets us cited and found: the panel, the reads, the citation queue, the audit, on-site structure, and pieces written to answer one panel question (site articles, their Medium copies).
- **Content owns** what is made to be shared: reactions, talkbacks, breakdowns and UGC on LinkedIn, YouTube, the newsletter and Instagram.
- **The seam:** AEO hands content a brief when the fix is a video or a post; content hands AEO every published link for the citation queue. Speaker and partners feed the queue the same way (show notes, guest posts).

## Missing against the template's line

The line: "The prompt panel, citation tracking, the audit ladder, articles and fixes", on Codex.

1. **Its own role.** AEO is half of `content-seo`; the split is not made, and the role file names one business, one site and one owner.
2. **Any job on Codex.** No worker job, no prompt file, no script calls the router for this function. The kit lists no worker jobs for it.
3. **The panel as a file with a shape.** Questions, engines, locale, version; and a saved-answer record that makes "cited" checkable.
4. **A fetch step that is not the bot reading a dashboard.** Something has to put answers in front of Codex: RankSpot's API, Treg, or a signed-in browser. None is wired.
5. **Per-business settings.** `rankspot.py` hard-codes two sites and their key names; the skills name one site. Needs a settings example: site, engines, panel size, read cadence, article cap, the month's spend cap, who merges site changes.
6. **A gate on paid checks other than articles.**
7. **The fix hand-off.** No file shape for a fix going to content, partners, speaker or the site's owner, and none for links coming back into the citation queue.
8. **The site with no write access.** Two applications cannot change their site; "fixes handed over, not made" needs a release-package format a third party can apply.
9. **Message types.** `site_article` is in `agents.json` but not in the kit's gate list; `aeo_audit_offer` is in the kit's list but in no function here.
10. **A baseline step.** Only one application has one. The kit says never invent it, and has no first-run step that measures it.

## Questions for the owner

1. **Who checks the engines?** RankSpot's paid checks, Treg, or the bot asking each engine itself through a signed-in browser (free, slower, fewer prompts)? This decides the cost and what Codex is handed.
2. **Who writes the articles?** `agents.json` gives this function `site_article` and `medium_post` on Codex, but the engine rule says writing that has to be good is Claude Code. Codex for the brief and Claude Code for the draft, or all Codex?
3. **Is the split above right,** and does the audit ladder (a sales offer to prospects) belong here or with the CRM sales agent?
4. **The spend line.** A monthly cap per business for checks and articles, on the business's own RankSpot account? And may RankSpot's own schedules ever be on?
5. **How often is the panel read,** and how big is the panel: the kit says 30 to 50 questions weekly; the SEO kit's first-run limit is 12.
6. **When the business cannot edit its site,** does this function stop at a package for the site's owner, or is getting site access a setup requirement?
7. **Is the full SEO kit (thirteen roles, a board) the method,** or a library this function draws from while running a smaller loop?

## Since this page was written

The owner chose RankSpot as the engine checker, read by our own script and judged on Codex (2026-11-17). Versions 0.1 and 0.2 are in this folder: [PROCESS.md](PROCESS.md), `aeo.py`, `prompts/gap.md`, `aeo.example.json`.

| Gap above | Now |
|---|---|
| 2 Any job on Codex | Closed: `aeo.py judge` |
| 3 The panel as a file with a shape | Part: size, platforms and sources are settings; the saved answer is the evidence. The panel file itself is still free text |
| 4 A fetch step | Closed: `aeo.py pull`, not yet run against RankSpot |
| 5 Per-business settings | Closed for the read: `aeo.example.json`. The kit's article script still names two sites |
| 6 A gate on paid checks other than articles | Part: `aeo.py cost` holds a panel over the cap. Turning the daily run on is still the owner's own switch |
| 7 The fix hand-off | Closed one way: a file per owner role. Links coming back to the citation queue are a rule, not code |
| 8 A site with no write access | Part: `site_changes.mode: package` is a setting; the package format is not written |
| 10 A baseline step | Closed: setup step 7 |
| 1 Its own role, 9 message types | Open: both are shared files, proposed to the main chat |

**The goal, in the owner's words (2026-11-17):** "the goal here is generating as many inbound leads as possible from search engines and AI engines. Your Google answers are your best spots. Rank it on the front page of Google, especially using video, but stuff that's going to convert, not just any video. Then get it seeded in ChatGPT and Google, get those going, and make sure that we're ranking. RankSpot's a great tool. It's not our only function." His message ended mid-sentence at "At the end of the day, AEO SEO".

Version 0.2 turns the function to that: leads are the score, Google's front page comes first with video for buying terms, the AI engines are seeded from the same answers, and the weekly read measures all three. New gaps it opens: no lead carries a source yet (search, AI engine, video); the video brief's must-haves are a rule, not a check; nothing here makes or uploads a video.

Still open from the questions: 2 (who writes the piece), 3 (the audit ladder's home), 4 (the cap's amount and whose RankSpot account), 6 (site access as a setup requirement), 7 (the full SEO kit as method or library). Question 5 has a default: 12 questions, read weekly.
