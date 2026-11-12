---
name: lead-storm-handoff
description: Feed the social Lead Storm VPS agents - write approved social targets and messages into the Lead Storm queue for the VPS to pick up, and read back what it reports. The bot never posts or DMs on social itself; the VPS agents stay the senders. Use for anything about social outreach, the Lead Storm queue, or what the VPS sent.
---

# Lead Storm handoff

Justin, 2026-11-12: "we have our social lead storm VPS with different agents that'll reach out on social." Decision the same day: "Bot feeds it, VPS sends".

## What is known, and what isn't

- The VPS agents are the social senders (owner `social-sender: live` in `context/owners.md`, always).
- How the VPS takes work (an API, a shared folder, a Slack channel, a repo) is **not in any repo or note**. It is on NEEDS-JUSTIN. Until Justin answers, the queue is a folder in this workspace and Justin (or the VPS operator) carries it over. Don't invent a transport, and never sign in to the VPS.

## The queue

One file per item: `requests/lead-storm/<YYYYMMDD>-<n>.md`

```
platform: facebook | instagram | linkedin | x | tiktok | reddit
target: <public profile or post link>
why: <one line: the signal, quoted from their own post>
message: <the exact text, approved type fmm_social_dm or fmm_social_comment>
approved: <the standing-approvals line, or "waiting on Justin">
source: <radar | craigslist | local | muse | wholesale>
```

## The run (outreach role)

1. Take targets from `requests/outreach/` (radar, local, wholesale) that have a social profile and no email.
2. `suppression.py check "<target>"`. Held means drop.
3. Draft the message in the charter voice (no links, no rate quotes, no guarantees, no "DM me" in a public comment).
4. `send_guard.py fmm_social_dm --routine "Lead Storm feed"` (or `fmm_social_comment`). `draft` means the file says `approved: waiting on Justin` and a copy goes in `requests/justin/`. Only `auto` items are marked ready for the VPS.
5. Read `requests/lead-storm/reports/` (what the VPS writes back, when it does): replies go to `requests/sales/`, opt-outs to `suppression.py add` at once.
6. End with `beat.py write outreach 'lead storm' queued=N ready=N replies=N`.

Counts: an item counts as sent only when the VPS report shows it sent with a link. Queued never counts.
