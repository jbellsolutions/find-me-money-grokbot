---
name: lead-map
description: Find Me Money's map of every niche and every place to mine - who the person is (borrower, partner, affiliate or creator, wholesaler), the words that show they need money, the offer, the route (sales, partners, wholesale) and which worker lane reads it. Use for the weekly niche rotation, picking work orders, a new niche or place, or "where else can we find people who need money".
---

# The lead map

Justin, 2026-11-13: "there are a whole bunch of different types of niches to go after and places to mine... influencers... so many different houses of affiliates... wholesalers, car people who are selling cars, and people on Marketplace... coaches and consultants... thousands of Facebook groups... about coaching of all different types... I really want to go deeper."

This page is the taxonomy and the rules. **The lists themselves (group links, creator handles, coach names, partner names) are private**: Justin gives them at intake into `data/lists/` (mode 600), and the worker builds more. Never paste a list into a report, a skill or the vault.

## Four kinds of person

| Kind | Who | What we offer | Route |
|---|---|---|---|
| **Borrower** | Needs money now for a business or an investment | The funding product that fits (below), always "likely fit, confirm with the lender" | sales |
| **Partner** | Serves owners who need money: CPAs, bookkeepers, brokers, dealers, coaches, agents, ISOs, title firms | Referral or co-marketing, disclosed and verified per profession | partners |
| **Affiliate or creator** | Has an audience that needs money: creators, community owners, coaches with business-owner clients, affiliate houses | An affiliate or partner program for findmemoneyapp.com | partners |
| **Wholesaler or investor** | Needs EMD, transactional, gap, flip or DSCR money, and has deals to pass | Funding through partners, or a deal pass for a percentage | wholesale |

Many people are two kinds at once (a coach is a borrower and a partner). Record both.

## Products (codes the worker and the bot use)

`CS` 0% business cards or credit lines · `LOC` line of credit · `TL` term loan · `MCA` merchant cash advance or revenue-based · `MCA-C` MCA consolidation · `EQ` equipment · `FACT` factoring · `INV` inventory · `SBA` · `CRE` commercial real estate · `DSCR` · `HELOC` (business purpose, licensed partner only) · `HM` hard money · `GAP` · `EMD` · `TXN` transactional (double close) · `FLOOR` floor plan.

## The buckets (14, from the Muse charter; each is a niche family with sub-niches)

| # | Bucket | Sub-niches | Main products | Kind |
|---|---|---|---|---|
| 01 | **Coaches and consultants** | life (transformational, midlife, divorce, grief, recovery), business and executive, sales and marketing, health, fitness, nutrition, hormone, relationship and dating, mindset and spiritual, career, money and investing educators, parenting and family, course creators and community owners (Skool, Circle, masterminds), speakers and authors, specialty (practice growth, RE agents, trucking, lash and barber educators, photo, music, golf, Amazon, AI), agency owners (SMMA, AI, lead-gen), closers and setters | CS first, LOC; MCA once card volume is steady | borrower + partner |
| 02 | **Marketplace dealers and high-ticket sellers** | used-car lots and buy-here-pay-here, car resellers (5+ active listings = dealer sign), powersports, RV, boat and trailer dealers, commercial trucks and heavy equipment, business assets (food trucks, mobile salons, vending, laundromat and restaurant equipment), businesses for sale (the buyer needs money), sellers advertising "financing available" (partners) | FLOOR, INV, EQ, SBA, LOC | borrower + partner |
| 03 | **Creators** | YouTube, short-form, podcast, UGC, streaming, production, creator brands, photo and wedding, music, drone | CS, EQ | borrower + affiliate |
| 04 | **Real-estate capital** | wholesale, fix-and-flip, buy-and-hold and BRRRR, new construction, short-term rental, commercial, multifamily, creative finance, land, mobile-home parks, notes, RE partners (agents, TCs, property managers, title) | EMD, TXN, HM, GAP, DSCR, CRE | borrower + partner + wholesaler |
| 05 | **Starts, buys and launches** | new LLCs, laid-off founders, franchise buyers, business acquisition (ETA), partner buyouts, product launches, crowdfunding, film, music and event producers | CS, SBA, TL | borrower |
| 06 | **Trucking and transport** | owner-operators, box truck and load-board carriers, delivery partners, movers and couriers, dispatchers and authority consultants (partners) | EQ, FACT, MCA, TL | borrower + partner |
| 07 | **Contractors** | HVAC, plumbing, electrical, roofing, general contractors, remodelers, specialty trades | LOC, EQ, FACT, TL | borrower |
| 08 | **Local service and route businesses** | landscaping, pressure washing, pest, junk removal, cleaning, detailing, towing and repair, vending and ATM routes, laundromats, event rentals, childcare, home care | EQ, MCA, TL, SBA | borrower |
| 09 | **Food and hospitality** | restaurants, bars, food trucks, caterers, ghost kitchens | EQ, MCA-C, TL | borrower |
| 10 | **Health, beauty, fitness** | med spas, dental, chiro, PT, vet, salons, barbers, suites, gyms, martial arts | EQ, SBA, CS | borrower |
| 11 | **Ecommerce** | Amazon, Shopify and DTC, TikTok Shop and live selling, Etsy and print-on-demand, resellers, dropshippers | INV, CS, MCA | borrower |
| 12 | **Gig and 1099** | rideshare, delivery, couriers, freelancers | small tools only; careful: consumer loans are out | borrower |
| 13 | **Direct sales and agents** | insurance and financial-services agents (on); general MLM (off) | CS; partner | borrower + partner |
| 14 | **General funding and local** | working capital asks, MCA stacks, 0% lines, equipment, credit repair and education (referral only), local groups (home metro first, then the state, then other metros) | all | borrower + partner |

**Out:** cannabis (restricted), crypto, day traders and prop firms (excluded), consumer loans, personal debt consolidation, student, auto and mortgage refi. Competitors (other funding educators and card-stack sellers) are watch-only.

## Places, and which worker lane reads each

| Place | Lane (`hermes_bridge.py lanes`) | Executor | Notes |
|---|---|---|---|
| Facebook groups, newest posts, by theme | `fbgroups` | Hermes on the Mac (One API) | Theme lists in `~/.fmm/groups/<theme>.txt`. The live nightly lane keeps its own list; themes here are new ones |
| Facebook groups we don't know yet | `group-discovery` | Hermes | Google `site:facebook.com/groups` plus Muse; outputs a theme registry with member counts. **Build this first: no coaching, health, fitness, ecommerce, contractor or creator group list exists yet** |
| Member-only groups, comment threads, Instagram | `muse` | Hermes, typing only when `muse-app: bot` | Muse sees what APIs can't: private groups as Justin, comments, Marketplace, IG accounts |
| Facebook Marketplace | `marketplace` | Hermes (Muse or the Mac's own signed-in browser, whichever reads better; Justin: "we don't have to use MetaMuse") | Record the **seller**, never consumer buyers; skip scams, parts-only, salvage, no-title |
| Craigslist business boards | `craigslist` | Hermes or any computer (rung 0 free) | `fns` sellers of funding and bookkeepers are partners, not borrowers; `sks`, `hss` trades are borrowers; `ctd` dealer autos are borrowers (floor plan); owner autos are consumers (off) |
| Local businesses on Google Maps | `places` | Hermes (Scrapebox places, free) | One metro at a time |
| Creators and influencers | `influencers` | Codex or Hermes | Partner and affiliate candidates; their comment sections are borrower places |
| Affiliate houses, ISO and broker networks, referral programs | `affiliate-houses` | Codex or Hermes | No named list exists yet: the worker builds it from published programs |
| Coaches and consultants, and their communities | `coaches` | Codex or Hermes | Coaches are borrowers and partners; their groups are places |
| Wholesalers | `wholesalers` | Hermes | See `wholesaler-system` |
| Skool, forums, Reddit, YouTube and TikTok comments, public records | the live Radar | not the worker | 221 Radar campaigns already read these; the bot reads the Radar, never re-mines it |

## Signals (the words that mean money is needed)

- **Borrower, any niche:** "looking for a business loan", "bank turned me down", "denied", "need working capital", "how do I get an SBA loan", "recommend a lender", "stuck in MCA", "daily payments are killing me", "need to make payroll", "slow season".
- **Coaches and creators:** "need ad budget", "Stripe is holding my payouts", "hire a closer", "launch budget", "event deposit", "can't scale ads".
- **Marketplace and dealers:** "need capital for auction", "floor plan", "second lot", "can't restock", "do you work with financing", "how do people finance these".
- **Ecommerce:** "Shopify Capital declined", "Q4 inventory", "reorder", "supplier wants payment upfront".
- **Trucking:** "truck financing", "new authority", "can't get approved", "factoring company".
- **Real estate and wholesale:** "assignment available", "JV this deal", "need a cash buyer", "EMD due", "inspection ends", "double close", "transactional funding", "gap funding", "hard money down payment", "rehab capital", "DSCR lender".
- **Partner signals:** offers financing themselves, serves business owners (CPA, broker, coach whose clients are owners), runs an audience of owners or investors.

A comment or a post is a signal, **never consent**. Consent to contact or to share comes only in the person's own words in a reply.

## Scoring (for the weekly rotation)

Per lane and niche, from last week: **answers per 100 finds** first, then fit finds per run, then cost (Hermes and Codex minutes, credits). Keep the top lanes, try two new niches a week, drop a niche after three weeks with no answer. A lane that failed is a coverage gap, never zero.

## The week plan (what the Niche rotation routine writes)

`context/week-plan.md`, one line per work order the Dispatch routine sends each day:

```
<lane> | {"arg": "value"} | why (one line: last week's answers, or "new niche trial")
```

At most 12 orders a day to start (the Mac runs four at a time every 15 minutes). Justin's caps win.

## Rules that never move

Read only on every place. No automated DMs, comments or group joins. No paid enrichment. DSCR and home-secured money only through a licensed partner. Splits and referral fees follow the partner rules Justin set (RESPA and state broker rules apply to real estate). Say "likely fit", never "approved".
