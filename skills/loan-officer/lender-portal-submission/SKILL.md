---
name: lender-portal-submission
description: How the Loan Processing Officer submits a file in a partner's portal on its own computer (a fulfillment partner, a HELOC partner, a lender), with Hermes' browser driving its one signed-in Chrome profile and Jev choosing each element. It runs only after Funding Director has consumed a one-time human approval for the exact payload. Use for "submit this to the fulfillment partner", "upload it to the lender portal", "check the status in the portal".
---

# Portal submission (heavy browser work)

## Where it runs

On **the officer's own Orgo computer**, in its one Chrome profile, which Justin signed into every
portal from once on the Orgo desktop. Hermes' `browser` tool drives that profile
(`browser.use_real_profile: true` and `real_profile_pin` in config.yaml on the Orgo computer). Hermes pins one
profile, so every portal shares it: confirm the account name the playbook names before you submit. The officer never types a
password, never creates an account, and never solves a CAPTCHA. A sign-in page or 2FA prompt means it stops
and asks a human to sign in on the desktop.

Don't use browser-box for this. Its browsers are fresh and logged out, so it can't reach a signed-in portal.
browser-box `fetch`/`read`/`act` are for logged-out research only: a funder's public program page, a
business's own website, reviews.

## The contract (all of it, every time)

1. `funding_submission_begin_browser(submission_id)` returns `authorized: true` and the destination's
   `playbook_ref`. No authorization, no browser.
2. `route_get(<destination>)` gives the playbook text. If its status is draft or any field is
   `TODO(Justin)`, **stop**: report that the playbook isn't reviewed.
3. Open the portal in that destination's profile and confirm the signed-in account name.
4. Do the playbook's steps **once**, in order: one action per step. Use `browser_snapshot` to read the page and
   pick the element. For a hard call (two similar buttons, an ambiguous dropdown), use `jev_choose` with the
   element labels as options and accept only `accepted`.
5. Every value you type comes from the frozen payload. If the portal asks for anything not in the field map,
   stop.
6. On the review page, compare every value to the payload. Any difference → stop.
7. Submit once. Capture the confirmation (number, page text, screenshot).
8. `funding_submission_record_receipt(submission_id, receipt_id, verification)`.
9. If the result is unclear (spinner, error, timeout, no confirmation): `funding_submission_mark_unknown`,
   tell Justin with what you saw, and **never resubmit**. Someone checks the portal by hand first.

## Uploads

Upload documents from `$OFFICER_STATE/deals/<deal-id>/docs/` by file name. Never upload anything that isn't
on the deal's checklist. Never paste document contents into a free-text field.

## Status checks

Reading a submitted file's status in the portal is a read: open, read, close. Record what it says on the hub
deal with `hub_stage` only when it is a real stage change (offers in, approved, declined).
