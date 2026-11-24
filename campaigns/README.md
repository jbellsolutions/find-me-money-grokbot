# The two campaigns

Justin, 2026-11-24: "Both those are disruptor campaigns. It's just two separate campaigns."

| Campaign | Main agent | Folder |
|---|---|---|
| Find Me Money, findmemoneyapp.com | **Find Me Money** | [find-me-money/](find-me-money/CAMPAIGN.md) |
| The Referral Connection, findreferralpartners.com | **Referral Connection** | [referral-connection/](referral-connection/CAMPAIGN.md) |

Each folder holds `CAMPAIGN.md` (the goal, the numbers, what each agent does for it), `MESSAGING.md` (the disruptor message), `LAUNCH.md` (the launch plan and the switches that make it run on its own), `campaign.json` and `settings/` (one file per function). `tools/install.py` copies the settings to `context/revenue-os/<campaign>/`, where Justin's answers go.

The two are kept apart: their own records, their own plan and report, their own files (`data/referral/` and `context/referral/` for the referral campaign), and a campaign name on every line of the conversation log. To add a third campaign: copy a folder, add its name to `team.json` with a main agent, and run the installer again.
