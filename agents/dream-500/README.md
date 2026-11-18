# Dream 500

The partners where three or four yeses double the business: anyone with an audience of 100,000 up to 1,000,000. One message each, by email and by DM, 1,000 emails a day. The owner reads the first 5 or 10; after that it is automatic.

| | |
|---|---|
| Engine | grokbot |
| Tier | 2 |
| Channels | email, linkedin, x, instagram |
| Message types | dream500_first_touch, dream500_follow_up |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/dream.md`, `roles/partners.md`
- Skills: `dream-partner-portfolio`, `partner-fit-review`, `partner-conversation-drafts`
- Worker jobs: none

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The process, version 0.2: the owner's words, how the work runs, the open items |
| [dream500.example.json](dream500.example.json) | One business's settings: the bands, the first batch, the daily email target, the DM paths |
| [dream500.py](dream500.py) | Places a list by audience size and shows what a day can carry. `python3 dream500.py selftest` |
| [prompts/](prompts/) | The three messages: first email, first DM, follow-up |
| [STATUS.md](STATUS.md) | Where the function stands and what is still open |

The table above still shows the registry's line (`agents.json`), which was written before the owner's instruction. 
