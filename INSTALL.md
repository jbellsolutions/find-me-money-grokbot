# Install

One line, pasted into the Find Me Money bot (a new one, or the one already in use):

> Install Find Me Money. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, unpack it into /workspace/find-me-money/repo/, run python3 /workspace/find-me-money/repo/tools/install.py and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

That is the whole install for a bot that never had it.

## Update: for the bot that already has an older install

One line:

> Update Find Me Money. Download https://github.com/jbellsolutions/find-me-money-grokbot/releases/latest/download/find-me-money.zip, delete /workspace/find-me-money/repo/ and unpack the zip there, run python3 /workspace/find-me-money/repo/tools/update.py and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

`update.py` deletes the referral site's files, switch lines and keys from the workspace and lists each in `log/update-<date>.md`; keeps every answer Justin already gave; then runs the installer. It tells the bot to replace its memory, delete its old routines and name any leftover bots for Justin to delete.

The rest of this page is what the bot does.

## What the bot does

1. **Unpack and run the installer.** It makes the workspace, the switch files, the settings and the setup page, runs the checks and prints the next steps. It asks nothing and can be run again.
2. **Set itself up.** `python3 /workspace/find-me-money/repo/tools/team.py setup` prints four things: the memory to save, the two skills to save (`claude-code-cli`, `content-tools`), the nine routines to create, and one command to run.
3. **Install the two CLIs** and run `python3 /workspace/find-me-money/repo/tools/job.py status`.
4. **Send Justin one message**: what is set up, what `job.py status` said, any failed check, then the whole checklist from `requests/justin/CHECKLIST.md`, starting `NEEDS-JUSTIN:`. Then stop.

## The rule this bot is built on

The bot orchestrates. Every task is handed to the Claude Code CLI with `tools/job.py`; the Codex CLI is the second engine. The bot's own part is only what a CLI cannot reach: its signed-in browser, its connected apps, its routines and the chat with Justin. `job.py audit` counts each day's jobs by engine, and the nightly report prints the count. The whole rule is in [skills/claude-code-cli/SKILL.md](skills/claude-code-cli/SKILL.md). Content has its own: words by the Claude Code CLI, talking videos by HeyGen ([skills/content-tools/SKILL.md](skills/content-tools/SKILL.md)).

## The two numbers

100 leads and 100 conversations started a day, in `context/targets.md`. Direct leads come from Lead Radar; the rest are affiliates and referral partners. A conversation is counted only when a first message has reached a person, so until Justin has approved a message type the report shows them as ready, not started.

## What can go wrong, and what to do

| If | Then |
|---|---|
| The download fails | Ask Justin once to attach `find-me-money.zip` from the release, then carry on from step 1 |
| A CLI will not install or does not answer | Carry on. Each job falls to the bot itself and is recorded as such, until Justin signs it in |
| A check fails | Carry on, and put the failed line in the one message |

## What is on after the install

Every routine runs on **test**: its job runs and makes drafts. Nothing reaches a person or the CRM, and nothing is spent, until Justin turns that switch on. The switches are four small files in `context/`: `routines-on.md`, `standing-approvals.md`, `owners.md`, `spend-approvals.md`. He changes one by saying it in the bot's chat.

## Lines for Auto-review

Justin pastes these into Auto-review → Custom Rules:

- Ask first before sending any email, DM, comment, reply, form or message to a person outside the team.
- Ask first before posting anything public, on any channel or in any community.
- Ask first before any payment, purchase, plan change, credit top-up, video render or paid API or scrape run.
- Ask first before creating, updating or deleting a record in a CRM, or putting a contact in a workflow.
- Ask first before changing DNS, billing or any account setting.
