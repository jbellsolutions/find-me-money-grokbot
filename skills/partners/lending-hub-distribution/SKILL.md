---
name: lending-hub-distribution
description: Route an applicant through the Lending Hub: keep the deal in-house or propose one partner, with a one-line reason, then run the Hub's 7-day partner clock. Use for "who should this lead go to", "propose the handoff", "chase the partner", "what did the partner say", or any applicant with a partner OK.
---

# Lending Hub distribution

The Hub (live at `HUB_URL`, set at intake) is the record for applications, deals and handoffs. Scripts sign in with `Authorization: Bearer $HUB_PASSWORD`. Our own GoHighLevel (Pinnacle Funding Group, pipeline `P4 · Partner Handoffs`) mirrors it.

## The calls

| Need | Call |
|---|---|
| See which partner fits, without saving | `POST /api/distribution/preview` with the lead (product, state, amount, lane, the person's OK) |
| Propose a handoff | `POST /api/distribution/handoffs` with `{"lead": {...}, "partner_id": "<id or empty for the Hub's pick>"}` |
| Read handoffs | `GET /api/distribution/handoffs`, `GET /api/distribution/handoffs/{id}` |
| Chase list (the 7-day clock) | `GET /api/distribution/open`, `GET /api/distribution/quiet` |
| Record a partner's answer | `POST /api/distribution/handoffs/{id}/report` with `{"status": "...", "note": "..."}` |
| Applications and stage moves | `GET /api/deals`, `GET /api/deals/{id}` |

**Person-only actions, never the bot:** `approve` a handoff, `sent` with `via: manual`, and `report` with status `funded` or `paid`. The Hub refuses them from a script on purpose. Propose, then queue the approval for Justin.

## The rules

1. A lead goes to a partner only with the lead's own OK, in their words. Consent to text never travels to a partner.
2. One partner at a time, at most `max_partners` (3) before the lead goes back to Justin.
3. Only an **active** partner can receive. Every partner starts as draft, and only Justin makes one active. Today none is active, so every proposal is "in-house, waiting on Justin's first partner".
4. Home-secured asks are commission only, and go to a licensed partner on Justin's routing.
5. Never route from the Funding Machine account. Partner names never go in public copy.
6. Distribution sending (`HUB_DISTRIBUTION_SEND`) is off until Justin deploys it. Until then a handoff is a proposal and a card for Justin.

## Output

For each applicant: `in-house` or `partner <id>`, one line of reason, and the handoff id. Counts only in reports; no names, phones or emails.
