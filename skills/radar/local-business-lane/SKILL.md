---
name: local-business-lane
description: Find Me Money's local lane - build lists of local, owner-run businesses in one metro at a time (Google Maps through Scrapebox places, free rung) in the categories that most often need funding, check each against suppression and the CRM, and hand a short, researched list to the outreach role for drafts. Use for "hit local businesses", a new metro, or refreshing the local list.
---

# Local businesses

Justin, 2026-11-12: "there's also the local aspect of it. I want to hit local companies and businesses."

## One metro at a time

The metro list lives in `context/local-metros.md` (the first one is Justin's pick; until he names it, the default is the metro where the Craigslist lane and the Radar show the most fit asks that week). Work one metro until its list is done.

## Categories that most often need funding

Restaurants and food trucks, contractors and trades (HVAC, roofing, plumbing, landscaping), auto repair and dealers, trucking and logistics, medical and dental practices, salons and gyms, retail with inventory, real-estate investors and wholesalers. Never cannabis (restricted) or crypto (excluded), the same rules as the Radar categories.

## The run

1. **Pull, free:** Scrapebox `places` for `<category> in <metro>`, up to 500 a query (rung 0, free). Fields: name, address, phone, website, category, rating, review count. A paid rung or any other paid source is spend: `spend_guard.py local-<metro>-<date> <usd>` first. **No paid enrichment** (no Clay, Apollo, Hunter, ZoomInfo or the like).
2. **Keep owner-run:** 4+ reviews, a real website or phone, not a national chain or franchise HQ. 1-50 employees by what the site shows.
3. **Check:** `suppression.py check "<business>"` (held means drop) and look the business up in Pinnacle read-only (already a contact means drop; the sales role owns it).
4. **Research one line per business** from its own site: what they sell, a growth or cash signal (hiring, a new location, seasonal, new equipment). No signal, no draft.
5. **Hand off:** write `requests/outreach/local-<metro>-<date>.csv` (business, site, phone, category, the signal line). The outreach role drafts; nothing goes to a person from here.
6. End with `beat.py write radar 'local <metro>' found=N kept=N held=N`.

Emails are not guessed or bought. If the site lists one, record it; otherwise the business goes to the phone and social lists for Justin or the Lead Storm queue.
