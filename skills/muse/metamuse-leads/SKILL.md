---
name: metamuse-leads
description: Use Meta's Muse app (MetaMuse, on the Find Me Money Orgo Mac) to find funding leads and opportunities on Facebook first, Instagram second, TikTok later - the prompts, the daily routine, how to pull Muse's results out as rows, hand them to the Funding Radar (lane-metamuse) so the Reply Agent and the Pinnacle CRM pick them up, and how to prove it. Use when asked to "get leads from Muse", "run the Muse sweep", "mine Facebook groups / Marketplace / Instagram with Muse", or "what did Muse find". Operating the app itself is the metamuse-operator skill.
---

# MetaMuse leads

Muse reads Facebook (the groups its account is in, posts, comments, Marketplace) and Instagram through Meta's own connectors. That is the reach the scrapers don't have: member-only groups and the comment threads under them. This skill turns that into rows the Find Me Money pipeline already takes.

**Operate the app with `metamuse-operator`** (`muse.py`). Prompts are in `references/prompts.md`. Rows go to the Radar through `scripts/muse_to_radar.py`.

```bash
M="python3 /workspace/find-me-money/repo/skills/muse/metamuse-operator/scripts/muse.py"
R="python3 /workspace/find-me-money/repo/skills/muse/metamuse-leads/scripts/muse_to_radar.py"
```

## Who does what (rulings that stand)

- **Muse finds and drafts. It never sends.** On 2026-11-07 Justin ruled that hired posters answer Facebook and Instagram asks from their own accounts, not Muse. Facebook comments and Instagram posts are "Ask" in Muse's connectors, and agents never click an approval.
- **The Radar is the handoff.** Rows → `POST /api/leads/import` with `lane: metamuse` → Radar campaign `lane-metamuse` → the Reply Agent drafts and files to **Pinnacle Funding Group** (Facebook Leads or Lead Radar Leads pipeline, New Lead) → the posters' list. LOW-fit rows go to the Radar's Prospects. The Radar dedupes by URL.
- **Posting to the live Radar is a production write.** The first `--post` needs Justin's yes. After that, follow the standing charter Justin gives.
- **Don't route Muse into a CRM yourself.** Check which connector scopes are allowed before acting, and ask Justin. Prompts here say "do not write to the CRM" until he says otherwise.

## The run (one sweep, about 10 minutes of Muse time)

1. `$M pin` → `$M state` (Muse running, frontmost, RAM OK).
2. Open the lead side chat: `$M open-chat "<FUND-xx or your sweep chat>"`, or start fresh with `ask --new-side-chat`. **Never use Main chat.**
3. `$M ask "$(cat prompt.txt)" --marker FB$(date +%m%d%H%M%S) --yes-send-to-muse`. Use **FB-1** for the core sweep. Ask for at most 40 rows per prompt; one prompt per bucket keeps answers under the context limit.
4. `$M wait-marker FB… --timeout 1200 > rows.txt`. Use a new marker for every send: `wait-marker` returns the last block with that ID, so a reused ID returns the old answer. **No Esc while it runs**: Esc stops Muse.
5. `$R rows.txt -o batch.json`. Check the counts and the skipped lines. Open 3 URLs at random in the Mac's Safari (read only) to check they land on the post.
6. `$R rows.txt --post --yes` (with `RADAR_IMPORT_TOKEN` in env, after Justin's yes). Log the 200 body: `imported / known / skipped / by_category`.
7. Proof: `$M shot` of the answer, the import response, and a line in the run log (`REPORT.md` format). Delete captured text from the Mac's `/tmp` and from the local scratch folder: rows hold people's names.

## Daily routine

Muse may already run scheduled tasks of its own. Prompt "list every scheduled task (cron.list include_disabled) with its exact prompt" to see them, and never message, post or follow from them. The routine reads them out and adds what they miss:

| When (ET) | Who | What |
|---|---|---|
| ~9:15 AM | agent | **REPORT** prompt in the sweep side chat: "list every lead your scheduled tasks found since yesterday 9 AM" → rows → Radar |
| ~9:30 AM | agent | **FB-1** core sweep (48 h) in the sweep side chat → Radar |
| ~1:00 PM | agent | **FB-3** comment mining on the 5 hottest posts from the morning → Radar |
| ~5:00 PM | agent | **FB-1** again (since 9 AM) → Radar. **IG-1** once a day → Radar |
| Mon 8 AM | agent | **FB-4** Marketplace dealers and **FB-5** partners → Prospects |
| any time | posters | answer the HIGH/MEDIUM leads from the posters' list (drafts from **REPLY-DRAFT**) |

Schedule it in the founder (GrokBot) or as a Hermes cron that shells `muse.py`. Don't add scheduled tasks inside Muse without Justin's yes: each one spends the plan's allowance.

## Facebook playbook (go deep here)

- **Groups are the gold.** Funding-ask groups (BUSINESS FUNDING AND INVESTMENT, Business Funding for Small Businesses, Small Business Funding And Resources), deal groups (Subto and the like), and trade groups (contractors, trucking, cleaning, lawn). Muse reads member-only groups only where its account is a member. If its group search misses a group, paste the group's link (**FB-2**).
- **Comments beat posts.** The person asking "who funds this?" under someone else's deal post is often the hottest lead (**FB-3**).
- **Marketplace = prospects.** Dealers and high-ticket sellers whose buyers need financing (**FB-4**). Business sellers only, never consumer car buyers.
- **Partners.** Lenders, brokers, coaches and agencies who post deals (**FB-5**) go to Prospects with category `…/partner`.
- **Proven 2026-11-11:** FB-1 style read, 5 real funding asks from 3 groups in the last 72 hours with permalinks and fit. Tools: `facebook-cli` (group posts and post read). No approval was asked.

## Instagram playbook (bonus)

What Muse's `instagram-cli` can and can't do (asked and confirmed 2026-11-11):
- **Can:** search accounts; read posts by username (with since/until); read the following feed and favorites; read a post by id or URL; **read a post's comments**; read saved posts, stories, followers and following.
- **Can't:** search hashtags or keywords. There's no hashtag feed. `social.search` returned topic posts, and the 7-day test found 5 funding-topic posts, mostly lenders and educators *offering* money, not asking.
- **So on Instagram, work a watchlist, not a search.** (1) Build a list of creator, lender and educator accounts whose comment sections fill with "how do I get funded?" (**IG-2**). (2) Each day, read their newest posts' **comments** and pull the askers (**IG-1**). (3) Read comments on the brand's own posts.
- Lenders and educators found this way are **partners**: fit low, category `credit/partner`.

## TikTok (later)

There's no TikTok connector in Muse. Muse's built-in Browser connector can open public web pages; **TK-1** tests whether it can read TikTok tag pages without a sign-in. It's untested, and TikTok often walls logged-out views. If it fails, use the Super Browser or Scrapebox lanes, not Muse.

## DMs

Check whether Muse has a messaging connection before relying on DMs; it may not. Turning one on is a sign-in in Muse → Settings → Connectors, which is Justin's to do (`NEEDS-JUSTIN.md`). Even then: read and draft only, never send.

## Getting results out

- **As text (main path):** the BEGIN/END marker block via `wait-marker` → pipe rows → `muse_to_radar.py`.
- **As a file:** Muse writes files on its own cloud VM, not on the Mac's disk (they show under Library → System files). To get one out, ask Muse to print it inside a marker block (`cat` it), or connect Google Drive in Muse (Justin's sign-in) and have Muse save there.
- **The whole chat:** `$M read -o chat.txt` gives the full chat as text.

## Failure modes seen

- Message landed in Main chat: Esc or ⇧Esc discarded the empty new side chat. Fixed in `ask` (it clicks the composer).
- Run "Interrupted": Esc sent while Muse worked. Never press Esc during a run.
- `read` returned empty: the composer had focus. `read` now clicks an empty strip first.
- Group search by name can miss: paste the group link (Muse's own notes say the same).
- Facebook comment reads return **no author names** (`facebook-cli` gives only text and `comment_id`). Use the comment permalink as the lead URL; the poster sees the name on the page.
- Many "funding" comments are brokers pitching. Mark them partner or competitor, never borrower.
- Instagram has no hashtag search (see above).
- The plan's allowance is unpublished: check Settings → General after big sweeps.

## Proof standard

A run counts when it has all three: (1) the screenshot of Muse's answer in its side chat, (2) the parsed rows count from `muse_to_radar.py`, and (3) the Radar's 200 response or Pinnacle rows for those URLs. Keep screenshots with names in `proof/private/`, which git ignores.
