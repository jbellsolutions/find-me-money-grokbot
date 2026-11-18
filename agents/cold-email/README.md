# Cold email

Traditional cold targets: lists, verification, sequences in the sending tool, inbox health. The sending tool sends; code builds the lists; the bot owns copy and the daily read.

| | |
|---|---|
| Engine | grokbot |
| Tier | not a partner tier |
| Channels | email |
| Message types | cold_email |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/cold-email.md`
- Skills: `cold-email-master`, `cold-copy`, `cold-campaigns`, `verify-leads`, `scraper-forge`
- Worker jobs: `list-build`, `list-load`, `replies-pull`, `inbox-health`, `campaign-stats`, `blocklist`

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The process: the numbers (1,000 a day at 10 an inbox), what is and is not this function's, the eleven steps |
| [cold-email.example.json](cold-email.example.json) | One business's settings: the daily number, targets, the charter, the list's columns, first lines, campaigns |
| [prompts/first-line.md](prompts/first-line.md) | The first-line prompt; the charter's personalization words are added from the settings |
| [cold.py](cold.py) | The volume plan, the list-against-campaign check, a first line per person on Codex, the daily read against the targets |
| [test_cold.py](test_cold.py) | Offline test for `cold.py`: `python3 agents/cold-email/test_cold.py` |
| [STATUS.md](STATUS.md) | Where the function stands and what the owner still needs to say |
