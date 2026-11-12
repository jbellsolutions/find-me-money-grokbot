---
name: funding-underwriting
description: Screen a business-funding file and lay out its sequence the way the Lending Hub's Deal Desk does, covering the scorecard, the routing rules, Funding Director's product checks, cited evidence and the next step. Same code as the hub, run from the officer's baked brain. Use for "what does this business qualify for", "what's the plan", "what order", "who do we send it to".
---

# Funding underwriting (the Deal Desk method)

One brain, three surfaces: the hub's Deal Desk, this skill and Funding Director all run the hub's
`underwrite.py` over the same draft Product Cards. Don't re-derive thresholds from memory.

## Inputs

Required: `requested_amount`, `purpose`, `state` (2 letters). Then as many as known: `credit_score`,
`revolving_utilization_percent`, `recent_inquiries`, `recent_derogatories`, `time_in_business_months`,
`monthly_revenue`, `existing_mca_count`, `existing_debt_monthly_payment`, `industry`, `owns_real_estate`,
`has_collateral`, `has_invoices`, `documents`. Hub fields: `use_of_funds_quality` (specific | vague | none),
`has_equity`, `has_investment_property`, `wants_max_capital`, `can_wait_for_cheapest`,
`has_cash_for_paydown`, `tax_liens_or_judgments`, `restricted_industry`, `credit_source`
(self_reported | soft_pull).

## Steps

1. `screen(intake_json)` previews without saving; `hub_create_deal` saves and screens. You get the 0-100
   scorecard and band, the likely-fit sequence, each card's blockers and missing documents, the questions
   and the next step.
2. Ask the screen's questions before anything costs money.
3. Evidence: `kb_cases`, `kb_workflows`, `kb_who`, `kb_search`. Cite title, link, date.
4. `hub_plan(deal_id)` for the cited Funding Plan.
5. `route_pick(deal_id)` to see where each step goes.

## The sequencing rules that matter most

- No use-of-funds plan → don't fund yet; nurture ("come back with a plan").
- Homeowner with equity who wants maximum capital → **non-reporting business HELOC first**, card stack second.
  A HELOC that reports to personal credit kills the later stack; sequence it last.
- 680+ and low utilization → card stack via the fulfillment partner (`FULFILLMENT_PARTNER`, set at intake). Higher
  utilization → only within that partner's own limits (its private terms). Over its ceiling with cash → pay down,
  re-pull, then stack.
- Under 680 with $10K+/month deposits → MCA / revenue-based (check UCC positions; disclose total payback;
  Texas registration).
- 2+ existing MCAs → consolidation, never another position.
- Commercial property and home-secured loans → our licensed partner, through Justin (never named to a client).

Every card is a draft until Justin confirms it, so the screen says "likely fit", never "approved": a lender
approves, the screen doesn't.
