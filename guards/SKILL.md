---
name: bot-guards
description: The checks every role runs in code before it drafts, sends or spends, and the heartbeat it writes at the end. Load on every run.
---

# Guards

These are code, not advice. Run them; don't reason around them. Paths are relative to the workspace.

| Before you | Run | It answers |
|---|---|---|
| Draft to anyone | `python3 repo/guards/scripts/suppression.py check "<name, business, email or url>"` | `clear` or `held`. Held means stop on that person |
| Someone says no | `python3 repo/guards/scripts/suppression.py add "<who>" "<reason>"` | Done for every role |
| Send anything | `python3 repo/guards/scripts/send_guard.py <message-type> --routine <NAME>` | `auto`, `draft` or `stopped`. Draft means it goes to `requests/justin/` |
| Spend anything | `python3 repo/guards/scripts/spend_guard.py <plan-id> <usd>` | `approved` or `held`. Held means the plan and its cost go to `requests/justin/` |
| End a run | `python3 repo/guards/scripts/beat.py write <role> '<line>' found=N drafted=N sent=N` | Your heartbeat. The watchdog alarms on a silent role |
| Watchdog | `python3 repo/guards/scripts/beat.py status --hours 26` | `SILENT <role>` lines to alarm on |

Never print the suppression list, read `.secrets/`, or edit a guard or a switch file to get past it.
| Write to a live system | `python3 repo/guards/scripts/owner_guard.py check <system> --routine "<NAME>"` | `bot`, `live` or `stopped`. Anything but `bot` means read and draft only; the live system keeps the writes |

The engine's own guard, `repo/skills/lead/fmm-guards/guards.py` (preflight, gates and daily caps, the approval queue), reads the same `context/STOP`, `context/suppression.csv` and `context/standing-approvals.md`, so the two never disagree.
