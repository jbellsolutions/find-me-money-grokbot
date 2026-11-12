---
name: pinnacle-crm
description: How the officers use GoHighLevel for the funding business. The pipelines (P1 Funding Leads, P2 Funding Deals, P3 Rehab), how each GHL stage maps to the hub's stage, the tag families (src, radar, consent, fi, prod, route, flag), the fi_ custom fields, and what may never go in GHL. Use with the gohighlevel skills whenever a contact, tag, note, opportunity or stage changes.
---

# The funding CRM (spec 19)

GHL is the lead inbox and the humans' pipeline view. **The hub is the source of truth for a deal** once it
exists. GHL mirrors it.

**The other funding location, never written, is on Funding Machine** (`FM_GHL_LOCATION_ID`, set at intake). Its
pipelines are FM's own (1. FM Applicants, 2. FM Clients, 3. FM Marketing Pipeline), not the P1/P2/P3 below:
work them with the `funding-machine-operator` skill. P1–P3 describe the older Pinnacle Funding Group account
and the hub's stage names. The `ghl` tool refuses to run until `GHL_PROFILE` names the funding account (a
profile name, or a tenant file on the Orgo computer).
Never write a funding contact into another business's sub-account (the names in `REPLY_NEVER_LOCATIONS`, set at intake); the tool blocks it.

## Using GHL here

Run everything through the pinnacle-officer `ghl` tool: `ghl(["contacts", "search", "--query", "Acme"])`.
It pins the profile. It allows reads and CRM writes (contacts, tags, notes, opportunities, stage moves). It
refuses sends, deletes and workflow enrollment, which reach a person: draft those for a human. The
gohighlevel skills (`ghl-operator`, `ghl-api`, `ghl-workflows`…) explain the product; their `ghl hub …`
commands work through the same tool on the officer's computer.

## Pipelines and stages

**P1 · Funding Leads** (GHL owns it until the deal exists): New → Attempting Contact → Engaged → Prequal
Submitted (hub `received`) → Plan v1 Ready (`underwriting_review`) → Plan Call Booked → Plan Call Held →
Soft Pull Link Sent → Soft Pull Done → **move to P2**. Lost: No Contact · Not a Fit · Not Now → P3 · DNC.

**P2 · Funding Deals** (the hub owns it; GHL mirrors): Plan v2 Ready (`strategy_ready`) → Fee Agreement
Signed → Docs Requested (`documents_needed`) → Docs Complete (`submission_ready`) → Awaiting Submission
Approval (`approval_requested`) → Submitted · <FULFILLMENT_PARTNER> / Submitted · Lender (`submitted`) → Offers In
(`offers_received`) → Client Deciding (`client_decision`) → Lender Approved (`approved`) → **Funded**
(`funded`, Justin only) → Commission Invoiced → Commission Collected (money is human-only).

**P3 · Rehab / Re-Try** (`nurture`): Prep Plan Sent → Paydown In Progress → Re-Check Due → Re-Qualified.

## Tags

`<FULFILLMENT_PARTNER>` is the fulfillment partner's short id, set at intake; the stage and tag use it exactly as
they are named in the CRM.


- Source: `src:radar` `src:craigslist` `src:referral` `src:partner` `src:website` `src:setter`… plus
  `radar:<campaign>` `geo:<metro>` `cl:<category>` `partner:<id>`
- Hub status: `fi:new` `fi:in-hub` `fi:needs-info` `fi:plan-v1` `fi:plan-v2` `fi:tier-a..d` `fi:pursue`
  `fi:after-prep` `fi:not-now` `fi:not-fit`
- Product / route: `prod:card-stack` `prod:biz-heloc` `prod:term-loan` `prod:loc` `prod:mca` `prod:sba`
  `prod:equipment` `prod:factoring` `prod:dscr` `prod:fix-flip` `prod:cre` `prod:debt-consol` · `route:<FULFILLMENT_PARTNER>`
  `route:lender` `route:re-lender`
- Flags: `flag:util-over-ceiling` `flag:inquiries-high` `flag:mca-positions` `flag:no-plan` `flag:homeowner`
- **`consent:*` tags are set only by a form submission or provider evidence, never by an officer.**

## Fields

`fi_` custom fields: ask (`fi_amount_requested`, `fi_use_of_funds`), business (`fi_state`, `fi_industry`,
`fi_monthly_revenue`…), plan (`fi_case_id`, `fi_tier`, `fi_recommended_path`, `fi_next_action`), routing
(`fi_partner`, `fi_route`). Credit goes in as **bands only** after a pull.

## Never in GHL

SSN, DOB, bank account or routing numbers, card numbers, full EIN, credit reports, exact credit scores,
statement contents, documents, who-to-call contacts, case-study text. Documents stay in the officer's secure
store.
