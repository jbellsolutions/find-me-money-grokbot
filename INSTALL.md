# Install

One line, pasted into one new Grok bot:

> Install the Disruptor Revenue OS. Download https://github.com/jbellsolutions/disruptor-revenue-os-grokbot/releases/latest/download/disruptor-revenue-os.zip, unpack it into /workspace/revenue-os/repo/, run python3 /workspace/revenue-os/repo/tools/install.py and do what it prints, in order. Ask me nothing until it is all done, then send me one message that ends with the checklist. Nothing sends, posts, spends or writes to a CRM or a site until I say yes.

That is the whole install for Justin. The rest of this page is what the bot that got the line does.

## What the first agent does

1. **Unpack and run the installer.** `python3 /workspace/revenue-os/repo/tools/install.py`. It makes the workspace, the switch files, each campaign's settings and each agent's setup page, runs the checks and prints the next steps. It asks nothing and can be run again.
2. **Set yourself up as a main agent.** `python3 /workspace/revenue-os/repo/tools/team.py setup <your role>` prints three things: your memory block to save, your two routines to create, and one command to run. Your role is `find-me-money`, or `referral-connection` if that is your name.
3. **Create the other ten bots**, one at a time: the second main agent and the nine Revenue OS agents. `python3 /workspace/revenue-os/repo/tools/team.py line <role>` gives each one's name and its one line. Each sets itself up the same way.
4. **Send Justin one message**: who is set up, any failed check, then the whole checklist from `requests/justin/CHECKLIST.md`, starting `NEEDS-JUSTIN:`. Then stop.

## What can go wrong, and what to do

| If | Then |
|---|---|
| The download fails | Ask Justin once to attach `disruptor-revenue-os.zip` from the release, then carry on from step 1 |
| You cannot create a bot, or cannot message one | Stop trying after the first failure. Every line is already in `requests/justin/create-the-team.md`. Say so in your one message |
| A new bot does not find `/workspace/revenue-os/repo/` on its computer | Its line tells it to download the pack and run the installer itself. It then says in its "ready" that it is on its own computer |
| Claude Code or Codex is not installed or signed in | Carry on. Each agent does its own thinking until Justin signs them in (checklist 3) |
| A check fails | Carry on, and put the failed line in your one message |

## What is on after the install

Every routine runs on **test**: it does its work and makes drafts. Nothing reaches a person, a CRM or a site, and nothing is spent, until Justin turns that switch on. The switches are four small files in `context/`: `routines-on.md`, `standing-approvals.md`, `owners.md`, `spend-approvals.md`. He changes one by saying it in an agent's chat.

## Lines for Auto-review

Justin pastes these into Auto-review → Custom Rules:

- Ask first before sending any email, DM, comment, reply, form or message to a person outside the team.
- Ask first before posting anything public, on any channel.
- Ask first before any payment, purchase, plan change, credit top-up or paid API or scrape run.
- Ask first before creating, updating or deleting a record in a CRM or in the referral site's admin API.
- Ask first before changing DNS, billing or any account setting.
