# The Lending Hub

The record for applications, deals and handoffs. Live at `HUB_URL` (set at intake), signed in with `HUB_PASSWORD`.

## What the bot uses

| Part | How |
|---|---|
| Deals and applications | `GET /api/deals`: the site's forms land here and in Pinnacle Funding Group's P1 · Funding Leads |
| Deal Desk | Talk a deal in, screen it, get a plan (loan-officer, through `funding-underwriting`) |
| Handoffs | One open handoff per contact; states proposed, approved (a person only), sent, accepted, funded, paid |
| Distribution | `GET /api/distribution/open`: partner proposals (partners role). Sending is off until Justin's switch |
| The reply desk proxy | The Funding Radar's desk, read through the hub |

## Rules the bot follows

- It reads and writes Pinnacle Funding Group, the home CRM; the bot writes the hub only when `owner_guard.py check lending-hub` says `bot`.
- Every new hub lane (distribution sends, partner and poster links, payments, Craigslist-to-CRM) is off until Justin sets its switch.
- Only Justin or a verified payment marks Funded or Paid. An agent token can't.
- A slow page or a rate limit is reported, not retried in a loop.
