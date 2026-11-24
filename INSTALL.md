# Install

One line, pasted into the Find Me Money bot (a new one, or the one already in use):

> Install Find Me Money. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, unpack it into /workspace/find-me-money/repo/, run python3 /workspace/find-me-money/repo/tools/install.py and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

That is the whole install for Justin. The rest of this page is what the bot does.

## What the bot does

1. **Unpack and run the installer.** It makes the workspace, the switch files, the settings and the setup page, runs the checks and prints the next steps. It asks nothing and can be run again. An older install in the same folder is unpacked over; the answers Justin already gave in `context/` are kept.
2. **Set itself up.** `python3 /workspace/find-me-money/repo/tools/team.py setup` prints four things: the memory to save, the `claude-code-cli` skill to save, the eight routines to create, and one command to run.
3. **Install the two CLIs** and run `python3 /workspace/find-me-money/repo/tools/job.py status`.
4. **Send Justin one message**: what is set up, what `job.py status` said, any failed check, then the whole checklist from `requests/justin/CHECKLIST.md`, starting `NEEDS-JUSTIN:`. Then stop.

## The rule this bot is built on

The bot orchestrates. Every task is handed to the Claude Code CLI with `tools/job.py`; the Codex CLI is the second engine. The bot's own part is only what a CLI cannot reach: its signed-in browser, its connected apps, its routines and the chat with Justin. `job.py audit` counts each day's jobs by engine, and the nightly report prints the count. The whole rule is in [skills/claude-code-cli/SKILL.md](skills/claude-code-cli/SKILL.md).

## What can go wrong, and what to do

| If | Then |
|---|---|
| The download fails | Ask Justin once to attach `find-me-money.zip` from the release, then carry on from step 1 |
| `npm` is missing or an install fails | Try Claude Code's own installer (in the skill). If that fails too, say so in the one message and carry on |
| A CLI is installed and not answering | Expected until Justin signs it in (checklist 1). Each job then falls to the bot itself and is recorded as such |
| A check fails | Carry on, and put the failed line in the one message |

## What is on after the install

Every routine runs on **test**: its job runs and makes drafts. Nothing reaches a person or the CRM, and nothing is spent, until Justin turns that switch on. The switches are four small files in `context/`: `routines-on.md`, `standing-approvals.md`, `owners.md`, `spend-approvals.md`. He changes one by saying it in the bot's chat.

## Lines for Auto-review

Justin pastes these into Auto-review → Custom Rules:

- Ask first before sending any email, DM, comment, reply, form or message to a person outside the team.
- Ask first before posting anything public, on any channel or in any community.
- Ask first before any payment, purchase, plan change, credit top-up or paid API or scrape run.
- Ask first before creating, updating or deleting a record in a CRM, or putting a contact in a workflow.
- Ask first before changing DNS, billing or any account setting.
