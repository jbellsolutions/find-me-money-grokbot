# The sites this Revenue OS incubates

Justin, 2026-11-20: "we're going to have the Revenue OS, and we're going to have it be an incubator for a few different sites: the referral site, the Find Me Money site. We're looking to have a Revenue OS that's all about getting those sites traction."

Nine functions, each its own Grok agent ([TEAM.md](../TEAM.md)), and one folder here per site. Every agent does its job once per site, with that site's settings. A site's page says what traction means for it and how each agent serves it.

| Site | Folder | What traction means |
|---|---|---|
| Find Me Money, findmemoneyapp.com | [find-me-money/](find-me-money/SITE.md) | New leads from people looking for financing, the creative and alternative ways included, won with the Disruptor message |
| The Referral Connection, findreferralpartners.com | [referral-connection/](referral-connection/SITE.md) | Businesses signing up who want collaborations, partnerships, sponsorships and deals with others, then listed and matched |

## What a site folder holds

| File | What |
|---|---|
| `SITE.md` | The goal in Justin's words, who the site is for, what counts as traction and where the number comes from, how each of the nine agents works it, what it waits on |
| `campaign.json` | The site's Revenue OS settings: which agents are on, the records it keeps, the sending tools. Checked with `python3 tools/check_campaign.py sites/<site>/campaign.json` |
| `settings/<agent>.json` | One file per agent |

In the bot's workspace the live copies are `context/revenue-os/<site>/`. Justin's answers go there, never into `repo/`.

## How the team works two sites

- **The list of sites** is `context/sites.md`, one line per site: `<site>: on`, `test` or `off`. A routine works each site that is `on` or `test`, in that order, and writes a line per site.
- **Each site keeps its own records.** Find Me Money: the CRM. The referral site: the site itself, through `tools/rc.py`. A person from one site is never filed in the other's records.
- **The conversation log is one log with a site on every line.** Run the gate with `CAMPAIGN=<site>` for a site's work, so the day file and the audit can be read per site.
- **Private files are kept apart:** `data/` and `context/` for Find Me Money as before, `data/referral/` and `context/referral/` for the referral site (its prospect list is `data/prospects.csv`, where its skill writes it).
- **The scoreboard has a block per site.** A number is never added across sites.

## Adding a site

Copy a site folder, fill `SITE.md` and `campaign.json`, run the check, add the line to `context/sites.md`. No new routine is needed unless the site has records of its own to work, as the referral site does.
