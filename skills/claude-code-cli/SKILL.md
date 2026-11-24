---
name: claude-code-cli
description: Use for every task. The bot orchestrates; the Claude Code CLI does the work, with the Codex CLI as the second engine. Covers how to hand over a job or any task, how to install and sign in both CLIs, what to do when one does not answer, and how the daily report proves the rule was kept.
---

# The Claude Code CLI: every task goes through it

Justin, 2026-11-24: "There needs to be a hard-baked-in rule that it's using the Claude Code CLI skill. I'll get it logged in, and it's using that tool for every task and everything it does. It's just an orchestrator." And: "we're going to install the Codex CLI as well... We're just using those unless it just makes sense or is cheaper, because we're trying to keep our usage down and primarily use Grok Bot as an orchestrator."

## Hand over a task

```
python3 repo/tools/job.py run <job>                     a job with a file in repo/jobs/
python3 repo/tools/job.py run <job> --note "<words>"    the same, with what Justin or the plan asked for
python3 repo/tools/job.py ask "<any task>"              anything else
python3 repo/tools/job.py list                          the jobs
```

`job.py` starts Claude Code headless in the workspace with the job's brief. Claude Code reads and writes the workspace's files, searches and reads the public web, and runs the pack's Python scripts. If it gives no answer, the same brief goes to Codex. The CLI's last message is printed and saved in `log/jobs/`. Wait for it; a job can take several minutes.

## What is the bot's own

Only what a CLI cannot reach:

- the browser Justin signed in (Skool, Whop, anything members-only): read it, save the text to a file, then hand the job over;
- connected apps (Slack, Notion): post the file the job wrote, as it is;
- creating and changing routines;
- talking with Justin, and writing his yes into a switch file.

## When the CLI does not answer

`job.py` exits 3 and says so. Then, and only then, do the job yourself from `repo/jobs/<job>.md` and record it:

```
python3 repo/tools/job.py grok <job> "no CLI answered"
```

Tell Justin once that a CLI needs signing in. Do not tell him again until it has answered and failed again.

## Install and sign in

```
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex
python3 repo/tools/job.py status
```

If `npm` is missing, Claude Code's own installer is `curl -fsSL https://claude.ai/install.sh | bash`.

Sign-in is Justin's. Claude Code: he runs `claude setup-token` on his own computer and gives the token by hidden prompt; it is saved as `CLAUDE_CODE_OAUTH_TOKEN` in `.secrets/find-me-money.env`, where `job.py` reads it. Or he opens the bot's terminal, runs `claude` and signs in there. Codex: he runs `codex login` in the bot's terminal and approves the sign-in it shows. `job.py status` makes one tiny real call to each and says which answer.

## Proof

Every hand-over is one line in `log/engine-<month>.jsonl`. `python3 repo/tools/job.py audit` counts the day's jobs by engine and exits 1 if the bot carried one without a recorded reason. The nightly report prints that count.
