# Job: aeo-seo

Get Find Me Money found: on the front page of Google and named in AI answers. Justin, 2026-11-24: "we still want to keep AEO SEO. In fact, that's a big part of it." The measure is inbound leads from search, AI engines and video, not rank.

## Read first

- `repo/agents/aeo-seo/PROCESS.md`: the four jobs in the owner's order, the video brief, the weekly read.
- `context/revenue-os/find-me-money/aeo-seo.json`; `repo/campaigns/find-me-money/MESSAGING.md` (the eight pillars are where the questions come from).
- `data/aeo/terms.json` and `data/aeo/prompts.md`. If they are not there, write them first: 15 questions a buyer asks an AI, and the buying terms behind them, each marked buy, compare or learn.

## Do

**Tuesday: the read.**
1. `python3 repo/agents/aeo-seo/aeo.py cost --settings context/revenue-os/find-me-money/aeo-seo.json`. If the tracking tool's key is in and its cost is approved, `aeo.py pull`, `judge` and `read`.
2. Without the key, do the read by hand: for each of the 15 questions, search the public web and note whether findmemoneyapp.com is named, who is named instead, and which page was cited. Write `data/aeo/visibility-<today>.md`: named on N of 15, the three closest to a win, the one fix for each.
3. Each fix goes to the job that owns it: a page or a video brief to `requests/content/`, a partner page that should name the site to `requests/partnerships/`.

**Friday: one page and one video brief**, buying terms first. The page opens with the direct answer in its first lines, carries the video, and ends on one next step. The brief has the buyer's question as the title and the answer in the first 30 seconds. Both go to `content/aeo/<slug>/`. The page is an item in `requests/justin/` logged with `CAMPAIGN=find-me-money python3 repo/convlog/gate.py drafted <file> --agent aeo-seo`; the brief goes to `requests/content/`, where the content job scripts it and renders it in HeyGen.

A change to the site is a pull request in the site's own repo, or a brief in `requests/justin/` if the bot has no access. Never a deploy.

Every lead whose source is search, an AI answer or a video is a row in `requests/sales/` with `src:search`.

## Write

`daily/<today>/aeo-seo.md`: named on N of 15 (and against last week), pages and briefs drafted, fixes handed over, leads from search this week.
