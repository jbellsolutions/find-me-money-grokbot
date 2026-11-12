---
name: fmm-guards
description: The checks the Find Me Money agent runs in code before it drafts, sends or spends. Load on every run.
---

# Find Me Money guards

These are code, not advice. Run them; don't reason around them. `G=python3 /workspace/find-me-money/repo/skills/lead/fmm-guards/guards.py`

| Before you | Run | It answers |
|---|---|---|
| Start any run | `$G preflight` | `ok`, `STOP`, `refused` (no never-touch list, or `FMM_HOSTS` not set at intake), or which address doesn't resolve. Anything but `ok`: stop |
| Touch any computer, agent or account | `$G target "<name>"` | `ok` or `refused`. Refused when the name is on the private never-touch list, or when there is no list |
| Draft to anyone | `$G suppress check "<handle, email or url>"` | `clear` or `held`. Held means stop on that person |
| Read an opt-out | `$G suppress add "<who>" --why "<their words>"` | Always allowed, and it comes before anything else |
| Send or post anything | `$G send <type> --to "<who>" --text "<the message>"` | `allowed`, `queued <id>` (it waits for Justin) or `held <why>`. Only `allowed` may go out |
| Spend credits | `$G spend <pool> <amount> --balance <n>` | `allowed` or `refused`. A pool with no cap is refused: new spend is Justin's yes |
| End a run | `$G beat '<line>' found=N drafted=N queued=N sent=N answers=N leads=N` | Your heartbeat. The health check alarms when it goes quiet |

Message types: `public_reply`, `public_followup`, `email_first_touch`, `email_reply`, `partner_handoff`, `partner_message`.

Never edit `gates.json`, `spend.json` or a guard, and never run `guards.py decide`: that's a person's answer.
The only CRM writer is the cycle's outbox (`pinnacle_reply`); don't call GoHighLevel directly.
