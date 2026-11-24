# The function folders the jobs work from

Each folder holds `PROCESS.md` (how the function works, step by step), `STATUS.md` (what was built and tested), a settings example, prompts and any script. The filled settings are in [../campaigns/find-me-money/settings/](../campaigns/find-me-money/settings/). None of these is its own bot here: one bot orchestrates, and each [job](../jobs/) hands the work to the Claude Code CLI, which reads these folders.

| Folder | Used by the job |
|---|---|
| [content/](content/README.md) | content |
| [lead-radar/](lead-radar/README.md) | lead-radar, communities |
| [dream-100/](dream-100/README.md), [dream-500/](dream-500/README.md), [partners/](partners/README.md) | partnerships |
| [cold-email/](cold-email/README.md) | partnerships (partner emails only; no direct lead) |
| [sales-crm/](sales-crm/README.md) | crm |
