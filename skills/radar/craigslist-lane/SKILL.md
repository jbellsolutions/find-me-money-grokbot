---
name: craigslist-lane
description: Find Me Money's Craigslist lane - read Craigslist business-for-sale, financial-services and skilled-trade-services posts across US sites for business owners who may need funding (and for possible partners), cheapest read first (the free scraper, then One API, then browser-box), and hand fit rows to the Radar. Reading only - never posts, logs in or contacts anyone. Use for the daily Craigslist run, adding a city, or a blocked read.
---

# Craigslist lane

Justin, 2026-11-12: "a Craigslist scraping agent too, that uses our one API and Browserbox potentially to bring in Craigslist scraping."

## Who reads what (no double reads)

| Lists | Reader | Why |
|---|---|---|
| Real estate: `rea-owner`, `rea-broker`, `rew`, `rts` | The live Craigslist reader (owner `radar-cl` in `context/owners.md`) | Already live, about 400-500 rows a day in Florida. The bot **reads its output** (wholesale role) and never re-scrapes these lists |
| Business: `bfs` (business for sale), `fns` (financial services), `sks` (skilled trade services) | **This lane** (`--cats biz`) | New on 2026-11-12. Owners selling, buying or running a trade business are funding asks in waiting |

## The read ladder (cheapest first, climb only when blocked)

1. **Rung 0, free:** `python3 repo/skills/radar/craigslist-lane/scripts/scrape.py run --cats biz --sites <list> --max-age-hours 36 --out state/craigslist/posts-<date>.jsonl`. Needs `pip install httpx` once. One honest user agent, one request every 2.5 s, a hard request cap. Exit 3 means Craigslist blocked the run: stop that site for the day, never retry around it.
2. **Rung 1, One API** (`one-api` skill): only for a site rung 0 can't read, and only inside an approved plan: `spend_guard.py craigslist-oneapi-<date> <usd>` first.
3. **Rung 2, browser-box** (`read` or `fetch`): a page that needs a real browser. Same spend rule. Never a CAPTCHA, never a login, never a changed address to get past a block.
4. **Fallback:** `scrape.py google --max-credits 8` (site: search). Credits are spend: same rule.

Start with the 20 biggest metro sites in `sites.json`; add cities only after the first 100 rows show fit.

## Lead fit (the judgment; the script's signals are tuned for real estate)

Most business rows come back `kind: other`. You sort them:

| Keep as | When the post shows | Goes to |
|---|---|---|
| **Funding ask** | An owner running or buying a business who mentions growth, equipment, inventory, a slow season, "seller financing", "need capital", or a sale that needs a buyer with money | The Radar as `lane-craigslist` (sales role's queue) |
| **Partner** | A broker, lender, bookkeeper, CPA, business broker or merchant-services seller (most `fns` posts) | `requests/partners/` with the post link |
| **Skip** | Scams, MLM, crypto, cannabis (restricted), no business, or anything over 7 days old | Nothing; one line in the run log |

Record only what the post itself prints: post link, title, city, category, price if shown, and a phone only if printed in the post. Craigslist hides emails behind its relay; never try to reveal one.

## Hand-off

- Fit rows go to the Radar import (`RADAR_IMPORT_URL`, `RADAR_IMPORT_TOKEN`) with `lane-craigslist` **only when `owner_guard.py check funding-radar --routine "Craigslist read"` says `bot`**. Otherwise they wait as a file in `requests/sales/craigslist-<date>.jsonl` for the sales role's drafts.
- Never reply to a post, never post an ad (automated Craigslist posting is banned; ads stay by hand and are Justin's call).
- End with `beat.py write radar 'craigslist <sites> sites' found=N kept=N partners=N blocked=N`.
