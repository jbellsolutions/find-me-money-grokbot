---
name: partner-handoffs
description: Pair a qualified lead with a partner, make the intro, run the 7-day clock and re-pair when it stalls.
---

# Partner handoffs

Read `knowledge/lending/02-partners-and-handoffs.md`.

- `fcm_handoffs_propose` sends qualified leads to the hub. Justin approves each.
- After Justin approves, the intro goes to both sides. Then the partner owns the conversation.
- `fcm_handoffs_watch` runs the clock. Don't send your own nudges on top of it.
- A partner who says they can't help triggers a re-pair right away: `fcm_handoff_repair` with their reason.
- Funded and Paid are Justin's. Report what partners tell you, and let him mark it.
