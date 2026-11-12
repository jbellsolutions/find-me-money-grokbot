---
name: sales-replies
description: Work campaign replies: sort, note, move the stage, draft the answer, get the details and their OK for a partner.
---

# Sales replies

Read `knowledge/lending/03-campaign-rules.md` and `04-funding-map.md`.

- `fcm_replies_triage` handles each new reply once. Drafts stay held for a person, who sends them the same day.
- **The map is the promise.** Every cold email offers it, and it's theirs either way. Don't ask for a partner OK before they've had it.
- Questions get no canned draft. Answer what they asked with `fcm_reply_draft`, then ask one thing.
- `fcm_reply_draft` saves better wording. It refuses anything that crosses a line, and so does `fcm_reply_check`.
- `fcm_stage_move` goes forward only, with one line of why. Talking once they've given details, Qualified once you have all
  six things, Booked once a time is set.
- `fcm_partner_ok` needs their exact words from a reply. "Sounds good" to a question about a partner counts. A vague yes to
  something else doesn't.
- Keep answers short and in Justin's voice: plain, warm, one question at a time. Answer what they asked first.
- Never ask for a document. Partners do that.
