---
name: wholesaler-system
description: The Find Me Money wholesaler and investor system - daily active-wholesaler discovery with evidence, the score and the active gate, the deal state machine, the funding and acquisition workflows, the three separate permissions, and the launch order by market. Use with wholesale-funding for the daily queue, scoring a wholesaler signal, a deal's next state, or anything about the wholesaler system's milestones.
---

# Wholesaler system

Justin's private wholesaler spec (2026-11-13) is the full specification: a system map, workflow maps, the data model, integrations and 12 build issues across four milestones. Status there: **specification only, collection and outreach inactive.** This skill is how the bot runs it, with the Hermes worker doing the collecting.

## Three business lines

| Line | What | Bot's part |
|---|---|---|
| **A. Funding** | Funding conversations with wholesalers and investors: operating capital, EMD, transactional, flip, rental money for their buyers | Find, card, first-touch draft, hand to sales once they say yes |
| **B. Acquisition partnerships** | We source; investors who use our financing buy; we take a small acquisition split. Financing pay is separate | Match and draft; terms and agreements are Justin's |
| **C. Wholesale operation** | JV inventory, buyer feedback, closing | Buyer match, feedback capture, deal state; never contracts |

Direct-to-seller comes only after the first market works.

## Daily discovery (worker lane `wholesalers`, then the Wholesale desk)

1. Hermes collects from the enabled sources (newest first, 72-hour overlap so nothing falls between runs).
2. Each find is classified: role (wholesaler, investor, agent, title, other) and the specific activity (assignment, JV ask, cash-buyer ask, funding ask).
3. Identity: merge two finds into one person or company only on corroborated evidence (same phone printed by them, same company site, same handle). When unsure, keep them apart.
4. Dedupe reposts.
5. Score (below). Publish the whole delta plus the top 25 to `requests/wholesale/`.
6. A source that failed is listed as a **coverage gap**, never as zero finds.

## The score (0-100) and the active gate

| Part | Points |
|---|---|
| Wholesale evidence: specific (assignment, JV, EMD due, double close) / general / weak / none | 30 / 15 / 5 / 0 |
| Recency of the event: 72 hours / 7 days / 30 days / older | 20 / 15 / 8 / 0 |
| Detail (address or area, price, deadline, access) | up to 20 |
| Identity confidence | up to 15 |
| Market and activity fit | up to 15 |

Priority **A** at 75+, **B** at 55+. **Active gate:** a specific wholesale signal AND an event 7 days old or less AND identity at least medium AND not known expired. The score is relevance, never consent and never creditworthiness.

## Signal phrases

"assignment available", "assignable contract", "JV this deal", "co-wholesale", "need a cash buyer", "investor special", "off market", "price reduction", "inspection ends", "EMD due", "double close", "transactional funding", "funder for A-B, B-C closings".

## Deal states

Sourced → ControlVerified → MarketingAuthorized → BuyerMatched → FeedbackReceived → Negotiating → Agreed → Closing → Closed, or DeadOrExpired at any point. The bot may move a deal only through FeedbackReceived; Negotiating and later are Justin's.

## Three separate permissions

1. **Collection**: may we read this source? (public, or a source Justin enabled)
2. **Contact**: may we message this person? (only through a reviewed draft Justin approved, and never someone suppressed)
3. **Transaction authority**: does this person control the deal and may we market it? (verified, in writing, before any deal pass)

One never implies another.

## Money

Keep forecast, earned and collected apart, and keep acquisition money apart from financing money. Amounts in whole cents. A fee counts only with a title or settlement confirmation. No default split rate exists: Justin sets it per deal.

## Launch order

Home metro first (three counties), then the next two metros in the state, then the rest of the state, then selected states, then national. Each new market turns on per source, channel, structure and product, on Justin's word. National starts research-only.

## Milestones (the repo's 12 issues)

| Milestone | Issues | Bot's part now |
|---|---|---|
| 1 Discovery pilot (home state) | reconcile existing systems; configure sources and product routes; evidence records and identity; first permitted source adapters; the daily ranked queue | The worker lane and the Wholesale desk do this today, read only |
| 2 Funding conversion | contact policy and reviewed drafts; funding intake, CRM and partner attribution | Drafts only; sales hands to Pinnacle once `pinnacle-ghl: bot` |
| 3 Acquisition partnerships | deal control, buyer match and feedback; acquisition splits and reconciliation; direct-seller packets | Match and feedback capture; splits are Justin's |
| 4 Nationwide | source health, recovery, spend controls, owner reporting; launch checks and expansion | Source health in the Pull routine's alarms |

Exit gates before a market expands: a 50-record labelled check at 90% precision for "active wholesaler", under 2% duplicate people, and the daily report on time on 95% of days across 14 days.

## Compliance

Referral fees and splits on real estate follow RESPA section 8 and the state's broker rules; commercial-financing broker rules apply to funding referrals; texting and calling follow TCPA (no automated calls or texts); DSCR and home-secured money only through a licensed partner; always "likely fit, confirm with the lender".
