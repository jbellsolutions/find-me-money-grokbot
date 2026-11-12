# Hermes on Orgo: how the boxes are laid out and how to drive them

Learned from running a fleet of Hermes agents on Orgo since 2026-10 (Hermes v0.16 to v0.22). Orgo's own guide: `docs/site/guides/hermes.md`.

## Shapes you will meet

| Shape | How to recognise it | Runs as |
|---|---|---|
| Host install, root | `hermes` on root's PATH, `~/.hermes` = `/root/.hermes`, one gateway for every profile | root |
| Host install, own user | gateway process owned by `hermes` (or another user); root has no `hermes` on PATH | that user (`runuser -u hermes`) |
| Docker container | `docker ps` shows a container with `hermes` inside | the uid that owns its `HERMES_HOME` |
| macOS (Orgo Mac) | `uname` = Darwin, Hermes in `~/hermes-agent`, gateway under launchd | the logged-in user (often `admin`) |
| Orgo template `system/hermes-agent@x` | gateway under `supervisorctl` (`hermes-gateway`); no systemd on Orgo | root |

`orgo.py hermes agents <computer>` finds all of them each run. Always run Hermes **as the owner of that HERMES_HOME**, or root-owned files end up where the gateway must write.

## Profiles

One Hermes install holds many profiles under `$HERMES_HOME/profiles/<name>/`, each with its own `SOUL.md`/config, memory, skills (`skills/`), logs (`logs/gateway.log`, `errors.log`, `agent.log`) and cron jobs. One gateway serves them all. A profile is a worker: opener, closer, cold-email, podcast, and so on. The default profile has a ◆ in `hermes profile list`.

## Talking to a profile

- One-shot: `hermes -p <profile> chat -q "<msg>" -Q --source tool --max-turns N`. Present on every version since v0.16. `--source tool` keeps it out of the user's chat threads.
- Continue a thread: add `--resume <session-id>`.
- Newer-only flags (`--query-file`, `--run-budget`, `--create-if-missing`) exist from v0.21; don't rely on them across a fleet.
- Other channels that exist on some boxes: A2A (`:9900`), an OpenAI-style API (`:8642`, needs a key read off the box). The CLI one-shot is the one path on every box.

## Long work

The Orgo bash API stops at 300 s per call. `orgo.py hermes start` writes the task to `$HERMES_HOME/.orgo-jobs/<job>/task.md`, launches a detached runner as the owner, and returns the job id. `orgo.py hermes result` reads `out.txt` and `exit`. Some boxes have their own dispatcher (`box/dispatch.py start|result|status`) with a concurrency cap and STOP check: prefer it where it exists.

## Cron

`hermes [-p P] cron list`. Jobs are shown `[active]` or `[paused]` with schedule, skills and delivery. Pausing and resuming change a live agent: do them only with authority.

## Skills

A Hermes skill is a folder with `SKILL.md` (agentskills format: YAML front matter `name`, `description`, then instructions) plus any scripts. Profile skills live in `$HERMES_HOME/profiles/<p>/skills/<name>/`. `orgo.py hermes skill-install` moves an existing version to `skills/.backup/<name>-<timestamp>` before installing, and `skill-rollback` restores the newest backup. Hermes also writes skills itself from experience; never overwrite one of those without a backup.

## Health signals

- `hermes profile list`: the Gateway column (running/stopped) is the truth, not `pgrep`.
- `logs/errors.log` per profile.
- RAM: past ~85% the box needs a resize or fewer screens. GrokBot-style screens (Chrome per agent) cost the most memory.
- Disk: a full disk silently breaks Hermes' session store.
- A gateway reads its config at start: after `hermes gateway setup` it needs one restart (`supervisorctl restart hermes-gateway` on the template).

## Gateways need outbound mode

Orgo computers have no public inbound hostname. Run Slack in Socket Mode and Telegram in long polling. Webhooks can't reach the box (unless you open a public URL: `docs/site/guides/public-urls.md`).
