# Lead Radar: where this function stands

## Keep or remove: the owner's call

The owner, 2026-11-17: "The one rule is the only rule, and that's that there are no rules unless I tell you there's a rule." And: "Let me tell you the rule, and if I don't, then don't make it a rule."

This folder was gone through on 2026-11-17. These six are not in the owner's words. Each protects a person, an account or money, or stops the script running on nothing, so they are still in. Say "keep" or "remove" for each, or "remove all".

| # | What | Where | What removing it does |
|---|---|---|---|
| 1 | A kept person is checked against the business's suppression list before the hand-off; held means dropped | `radar.py` (code) | Someone who opted out can be handed to the sales agent again |
| 2 | Post text is marked as data, not instructions, in the scoring prompt and in each hand-off file | `prompts/lead-fit.md`, `radar.py` | A stranger's post could steer the judging or the sales agent (the main chat's list has the same item, number 8) |
| 3 | Spend caps on paid reads: `max_usd_per_call` per source and `daily_cap_usd` per campaign | `lead-radar.example.json` (settings only; no code enforces them here) | Paid reads have no ceiling in a campaign's settings |
| 4 | Skool, Whop and private Facebook groups are read through a browser the owner has signed in to, not with a password the bot holds | `PROCESS.md` (description) | The bot would need the account's password |
| 5 | The script stops when the settings have no offer and buyer, or no channel switched on | `radar.py` (code) | It would judge posts against nothing |
| 6 | A test run's log lines are marked as tests (`--test`) | `radar.py`, passed to the conversation log | Test posts show up as real conversations |

Kept because the owner said them: every decision under "Decided" below, the conversation-log line for each kept lead ("It's vitally important that we do document all the conversations that we're having", 2026-11-16), Codex as the engine ("Our Lead Radar can use our Codex CLI", 2026-11-16), and his standing instructions (his yes for sends, new spend, deletes and remote production writes; no paid enrichment services; no key in a file that ships).

## Removed on 2026-11-17: a chat or a brief added it

| Was | Where |
|---|---|
| "It never contacts anyone", "it does not reply, comment, like, follow, message or join", as rules | `PROCESS.md`, `README.md`, `radar.py` |
| "No lookups": a found post never gets an email or phone; no personal data beyond a handle, link and words | `PROCESS.md`, settings, `radar.py` |
| "No tool id is fixed in the template"; a channel with no read is "blocked, not skipped" | `PROCESS.md`, settings |
| "Every paid read is capped twice"; the sweep stops at the day's cap (the cap settings themselves are item 3 above) | `PROCESS.md` |
| "A pending or uncertain call is never sent again under a new id" | `PROCESS.md` |
| "Public reads only. No sign-in, no cookie, no private group, no CAPTCHA, no way round a block" | `PROCESS.md` |
| A One API gap is "not a reason to hand the bot a second credential" | `PROCESS.md` |
| The "Gate" column on the twelve steps: owner reads the first plan, spend guard, engine gate, one CRM writer, "logged first" | `PROCESS.md` |
| Eight terms at most per channel | `PROCESS.md`, settings |
| "Fresh first": two days read, nothing older than seven kept, "the backlog is never worked" (age is now an optional setting, off when left out) | `PROCESS.md`, `radar.py` (code), settings |
| A person's second post in one run is dropped | `radar.py` (code) |
| Term changes "never applied without the owner's yes" | `PROCESS.md`, settings |
| "It does not think on a metered model" | `PROCESS.md` |
| The owner's yes to each group joined; "never a made-up account"; "the bot never types a password" as a rule | `PROCESS.md`, settings |
| "A member is a lead, an owner is a partner"; a pointer carries "the link and nothing else" | `PROCESS.md` |
| The whole "What a business may change / may not" section, and "What Lead Radar does not do" | `PROCESS.md`, settings |
| The hand-off folder limited to two names | `radar.py` (code) |
| "Names no price and makes no promise" on the reply angle | `prompts/lead-fit.md` |
| The dashboard radar "polled, never rebuilt"; sources "off until the owner says" | `PROCESS.md`, settings |
| "This folder belongs to this function's own chat"; shared files are proposed to the main chat, not edited | `README.md` (from the starting brief) |
| "The owner goes deeper first", "do not build ahead" on the data route | `PROCESS.md`, settings (from the starting brief) |

## How this page was written

Written 2026-11-16 by this function's chat, from a read of what exists. Nothing was run, installed or changed.

## What exists today, and where

"Lead Radar" is the name of three different things. The template's line does not yet say which one it means.

| # | What | Where | Reads through | Judges with |
|---|---|---|---|---|
| 1 | **The dashboard radar.** A hosted service the business runs: campaigns of first-person asks, a daily run, a credit cap, its own classifier. The kit drives it over its API | Skill `revenue-os-max/build/skills/social/lead-radar`; worker job `worker/jobs/radar_poll.py` (every 4 hours) with prompt `worker/prompts/lead-fit.md` | ScrapeCreators, on the service's own balance | Its own classifier (metered), then the worker's `think.py`: Codex first, then Hermes, then a metered endpoint |
| 2 | **The Treg radar and the Lead Radar agent.** A search, grade and opener engine on Treg, wrapped in a Hermes agent on its own computer that also replies on approval, reads inboxes, writes the CRM, nurtures and reports bookings | Private repo `lead-radar-agent` (engine pinned from `treg-lead-radar`); not in this factory. The kit's `skills/content-seo/treg` is only the general Treg catalog skill | Treg (ScrapeCreators underneath) | A metered model through the owner's own key |
| 3 | **Radar roles inside two businesses' packs.** One plans where to look each week and picks the day's queue of fresh asks for sales. The other reads local Facebook groups through the owner's own sign-in and drafts replies the owner posts himself | Each pack's `roles/radar.md` (paths are in the private campaign files) | A signed-in browser, or the pack's other finders | The bot's own run |

Two more listeners sit beside these in the kit: `skills/social/x-intent-search` (Grok's own X search, scored in the bot's run) and `skills/social/skool-inbound` (a signed-in browser read on a host the owner picks, then worker job `skool-score` with the same `lead-fit` prompt). The kit's role for all of it is `roles/social.md`, routine "Radar and Skool askers from the worker".

## Channels

| Channel | Can listen today | Through |
|---|---|---|
| Reddit, YouTube, TikTok, Instagram, LinkedIn, public Facebook groups | Yes | 1 or 2 |
| Threads, Google, job boards | Yes, in 1 only; not in the template's channel list | 1 |
| X | Only through Google in 1; directly through Grok's X search | `x-intent-search` |
| Skool, private Facebook groups | Only with the owner's signed-in browser | `skool-inbound`, a pack's own role |

**In use:** one application runs it live: a hosted radar of kind 1 on its own ScrapeCreators balance, plus a nightly Facebook-groups lane through Treg under a daily read cap. For the other three it is built and never switched on, or said to be set up with no first run seen. No application scores through the template's router, and none runs it on a Grok bot.

## How a kept lead moves today

- **Kit:** `radar-poll` keeps 4s and 5s (and anything unjudged) and writes them to the worker's digest with the link, the need and a reply angle. The `social` role's routine reads the digest, checks suppression, and hands each one to the CRM agent as a row in `requests/sales-crm/` with the post as evidence; reply drafts go to the owner's queue.
- **Template:** says "every kept lead goes to the reply agent with its evidence", and the conversation log says an inbound message is logged before it is judged, then the CRM sales agent records it from `convlog.py pending-crm`. Nothing implements that path for Lead Radar yet.
- **The Lead Radar agent (2):** does its own replies, inbox and CRM writes, which the template gives to the reply agent and the one CRM writer.

## Missing against the template's line

1. **Scoring on Codex through the router.** `radar-poll` and `skool-score` call the kit's `think.py`, whose chain can end at a metered endpoint. The template wants `engines/route.py --agent lead-radar` (Codex, then Claude Code, then the bot unjudged, never metered). The router and its self-test already cover the `lead-radar` agent; no job calls it.
2. **A prompt per business.** `lead-fit.md` is written for one business's offer and names its owner. The function needs the offer, the buyer, the leave-outs and the keep line from the campaign's settings.
3. **A Treg listening job.** The template names Treg, but no job in the kit or the template searches through Treg: the kit polls the dashboard radar, and the Treg engine lives only in the separate agent's repo.
4. **The hand-off.** No file shape for "kept lead plus evidence" to the reply agent, no conversation-log line for a found post, and no rule for when a found person goes to the CRM (at once, or only when they engage).
5. **One list across sources.** No dedupe between the dashboard radar, Treg, the X search and Skool, and no suppression check inside the worker job (it happens later, in the role).
6. **A settings example** for this function: channels on or off, search terms, look-back window, keep line, daily read or credit cap per source, whose account pays.
7. **Reply coverage.** The reply agent's channels and message types have no Reddit or TikTok, and no Facebook reply type, so a kept lead on those channels has nowhere to go.
8. **Two models outside the engine rule.** The dashboard radar's own classifier and the Lead Radar agent both think on a metered model.

## Decided

- **2026-11-16, which radar:** "both but we want to build the agent with treg, and One api as the main one here for the grokbot". The function's main build on a Grok bot reads through One API and Treg and scores on Codex; a dashboard radar a business already runs stays as one more source. Written up in `PROCESS.md`.

- **2026-11-16, who reads through what:** "Treg for clients is going to be the appropriate way, because I don't think I can give them access to One API while also not shouldering some of the cost." The owner's own businesses read through One API (free reads first, saved scrapers, then Treg inside it); a client reads through their own Treg team. `account` in the settings picks.

- **2026-11-16, the scope:** "lead radar is for social media. Same tools though for data sourcing and enrichment". Widened by the owner on 2026-11-17 (the four routes, below).

- **2026-11-16, where a kept lead goes:** asked whether a kept lead goes to the reply side and the CRM at once, the owner said "Yes, both at once".

- **2026-11-16, Skool and Facebook groups:** "Facebook and Skool as well, correct? Skool is also for the influencers as well, though." And: "We'll message all the group owners as influencers to do collaborations, and then we'll also scrape all the Skool groups, the posts, and the comments for potential leads." Both are Lead Radar channels; group owners go on the partner list.

- **2026-11-16, the standalone agent:** asked whether it is kept out of a Revenue OS business, the owner said "No, it stays"; asked whether it hands its leads over, "Yes, hand them over".

- **2026-11-16, who starts the conversation:** "need to start a convo - thats CRM sales agent. reply agent makes sure all replies are taken care of and leads are moved to the next stage. crm sales agent does the work to move them through the pipeline and cover as well". And: "maybe they are the same agent?" A kept lead now goes to the CRM sales agent, who sends the first message through the send gate; the reply agent sees that replies are answered and stages moved. `radar.py` writes the hand-off to `requests/sales-crm/` (was `requests/reply/`).

- **2026-11-17, one agent:** asked whether to make the reply agent and the CRM sales agent one agent, the owner said "Yes, one agent". In the template that agent is `sales-crm`, and Lead Radar hands to it.

- **2026-11-17, the four routes:** the owner called Lead Radar "the star of the show, the quarterback" and set its routes. Social media: Facebook, Instagram and Reddit to start. Community leads: Skool and Whop groups, joined on his account, posts and comments. Partnerships: a list of possible influencers and partners from Skool and Whop. Data: Treg and Consulti, with Lead Radar "in control of the data for the different email campaigns". This widens the 2026-11-16 "social media only" line. Kept leads go to the CRM sales agent, who starts and carries the conversation and writes the CRM.

## Built since

`PROCESS.md`, `lead-radar.example.json`, `prompts/lead-fit.md` and `radar.py`. They close gaps 1, 2, 4, 5 and 6 above for the judging step (router, a prompt per business, the hand-off, seen-once and suppression, a settings example). Gap 3 (the reads as code), 7 and 8 stay open. Nothing has run against a live One API, Treg or Codex.

## Questions for the owner

1. **The data route.** Which email campaigns ask Lead Radar for lists first, and does it hold the lists itself or fill the lists those functions already keep?
2. **Groups.** Which Skool and Whop groups to join first, and on which account.
3. **One API gaps.** Keyword search on Reddit, TikTok, X, Threads and YouTube is in Treg but not in One API. Should the One API chat add those, or may the owner's bots call Treg directly meanwhile?
