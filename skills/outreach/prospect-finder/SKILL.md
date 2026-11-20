---
name: prospect-finder
description: Find local businesses in the launch area that would want a commission referral partner, using public sources only. Use for the Referral outreach run, a gap handed over by sales, or when Justin names an area or a trade to fill.
---

# Prospect finder

The directory is worth something to a member when there is a partner for them nearby. So it fills one area at a time, and inside the area it fills pairs: for every category that has a listing, the categories that share its customers.

## What to fill today

1. `context/launch-area.md` names the area (and trades, if Justin gave any).
2. `python3 repo/tools/rc.py signups --area "<city>"` shows who is already in, by category. `requests/outreach/` holds the gaps sales wrote down.
3. Pick the partner categories that are missing. Pairs that share customers: roofing, gutters, windows, solar, HVAC, plumbing, electrical, pest control, landscaping, cleaning, painting; realtors, mortgage brokers, home inspectors, movers, stagers; gyms, physiotherapists, chiropractors, nutrition, massage; wedding venues, photographers, caterers, florists, DJs; accountants, bookkeepers, insurance agents, financial planners, business attorneys; vets, groomers, trainers, pet sitters.

## Where to look (all public, all free)

- Google Maps and the business's own website, for name, category, town and the contact route the business itself publishes.
- The local chamber of commerce member directory and trade association directories.
- Public posts where an owner asks for referral partners or says they already send customers to other businesses.

Read pages with the usage scripts (`clean_page.py`, `pick.py`), not whole.

## Who is a fit

A business that keeps customers and can email them: it has a newsletter sign-up, a "past customers" or "members" offer, reviews that go back years, or a maintenance or membership plan. A business that is a franchise location with no local control of its email, or that has no website, is a weak fit; record it and move on.

## What to record

`data/prospects.csv` (mode 600), one row per business: `found` (date), `business`, `category`, `city`, `region`, `website`, `contact_route` (the public form, email or profile the business publishes for business enquiries), `fit` (one line: why they would want a partner, and which listed member they would pair with, if any), `status` (found, drafted, sent, replied-yes, replied-no, signed-up), `source_tag` (the `utm_source` used on their link).

Before adding a row run `python3 repo/guards/scripts/suppression.py check "<business or website>"`. End the run with the count found, by category, in `daily/<date>/outreach.md`.
