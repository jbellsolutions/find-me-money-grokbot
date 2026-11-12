# orgo-computer-use

Connect to, run and control [Orgo.ai](https://orgo.ai) cloud computers remotely, and drive the [Hermes](https://github.com/NousResearch/hermes-agent) agents that live on them. One skill that works in Claude Code, Hermes, GrokBot or any shell.

- **`SKILL.md`**: the skill. Connect, computers, computer use (screen, mouse, keyboard), shell and Python, Hermes (ask, long jobs, logs, cron, skills), rules.
- **`scripts/orgo.py`**: one dependency-free Python 3 client for Orgo's REST API plus the Hermes patterns. Linux and macOS computers.
- **`references/`**: the computer-use loop, Hermes on Orgo, safety.
- **`docs/`**: an offline copy of Orgo's documentation, captured 2026-11-11: 168 pages, the OpenAPI spec (113 operations), the MCP server (108 tools), the Python and TypeScript SDKs, and the CLI manifest. Start at `docs/INDEX.md`.

## Install

```bash
./install.sh claude              # Claude Code
./install.sh hermes [profile]    # a Hermes agent
./install.sh /workspace          # a GrokBot bot's computer, or any folder
export ORGO_API_KEY=sk_live_...  # a workspace-scoped key; never commit it
python3 scripts/orgo.py list
```

## Quick tour

```bash
O="python3 scripts/orgo.py"
$O list
$O status "<computer>"
$O screenshot "<computer>" -o now.png --scale 0.5
$O bash "<computer>" "df -h /"
$O hermes ask "<computer>" "What did you do today? One line." --profile <profile>
$O hermes start "<computer>" --profile <profile> --file task.md && $O hermes result "<computer>" <job>
```

## Status

Proven 2026-11-11 on live computers, read-only: `list`, `status` (Linux root, Linux 2-profile, macOS), `screenshot`, `bash`, `exec`, `hermes logs`, `hermes cron`. `ask`, `start`/`result`, `skill-install`/`skill-rollback` were proven against a stub Hermes locally; the first live run is a test.

Used by an orchestrator as every founder agent's way into its business's computer.
