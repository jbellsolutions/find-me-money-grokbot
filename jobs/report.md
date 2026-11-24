# Job: report

The nightly report. The bot posts the file you write, as it is, to Slack and Notion.

## Run and read

- `python3 repo/tools/job.py audit --days 1`: how many jobs each engine carried today.
- `python3 repo/guards/scripts/beat.py status`: any job that did not run.
- `CAMPAIGN=find-me-money python3 repo/convlog/gate.py day`: closes the conversation log's day and audits it.
- Today's `daily/<today>/*.md`; `requests/justin/` (what is waiting, oldest first); `context/` (the switches).

## Write `daily/<today>/report.md`, under 300 words

```
Find Me Money, <date>
Leads: N of 100 (direct N; affiliates and referral partners N). Conversations started: N of 100 (first messages ready, not sent: N).
Content: N drafted, N posted. Lead Radar: N asks, N answered. Communities: N groups read, N partners found.
Affiliates and referrals: N first touches, N emails, N replies; pipeline N found, N replied, N agreed, N sending leads. Sales: N replies in, N answered; N contacts, N opportunities, N next steps set (N written, N proposed).
AEO and SEO: named on N of 15; N leads from search this week.
Engines: Claude Code N jobs, Codex N, the bot itself N (why).
Did not run: <jobs, or none>
Waiting on you: <the three oldest items, one line each, with the file>
Tomorrow: <one line>
```

A number you cannot read is "?". A draft is never counted as posted, sent or a conversation started. The two numbers come from `context/targets.md`; if either was missed, the Tomorrow line says what changes.

## Also write

- `vault/Daily/<today>.md`: the report, then one line per person heard from today linking `vault/People/<name>.md`. No secret, no private figure.
- `vault/status.md`: one scrubbed status line for the single brain, replacing the last.
- On Mondays, `vault/Decisions.md`: the week's one decision with the number behind it (which pillar and content type did best, which source brought the most; next week doubles the best and drops the worst).
