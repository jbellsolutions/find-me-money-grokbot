# AEO and SEO

Get named by AI engines and found in search: the prompt panel, citation tracking, the audit ladder, articles and fixes handed to the role that owns each source.

| | |
|---|---|
| Engine | codex; falls back to claude |
| Tier | not a partner tier |
| Channels | site, medium |
| Message types | medium_post, site_article |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/content-seo.md`
- Skills: `aeo-citations`, `aeo-audit-ladder`, `seo-campaign`, `medium`
- Worker jobs: none

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The goal (inbound leads), the four jobs in the owner's order, the video brief, the setup steps, the weekly read, where each fix goes, the owner's rules that apply |
| [aeo.example.json](aeo.example.json) | One business's settings: the goal, the Google target terms, what a video brief holds, site, panel size, platforms, the month's cap, which fixes are on, how a site change is applied |
| [prompts/gap.md](prompts/gap.md) | The judging prompt: for an answer that did not name the business, the kind of source cited and one fix |
| [aeo.py](aeo.py) | The weekly read: `cost`, `pull` (RankSpot and Search Console, reads only), `judge` (Codex through the router), `read` (leads, Google, AI engines, fixes), `selftest` |
| [STATUS.md](STATUS.md) | Where the function stands, the checks awaiting his keep or remove, and what the owner still needs to say |

Versions 0.1 and 0.2, proposed for the changelog.
