# Job: crm

GoHighLevel, worked hard. Justin, 2026-11-24: "It's going to be big on adding and updating everything to the CRM, working the CRM, going high-level, and the pipelines and workflows and everything there."

Everything goes through `python3 repo/tools/ghl.py` (run it with `-h` once). It reads freely. It writes only when Justin's switches allow; otherwise it saves the exact write to `requests/justin/crm-proposals-<today>.md` and prints PROPOSED. Either way you run the same commands: do the whole job as if writes were on.

Before the key is in, the reads stop with a message and every write is still saved as a proposal. So with no key: skip step 1 and the searches, run the write commands for steps 2 to 4 with what you know, and say in the daily file that nothing was read.

## Read first

- `repo/skills/pinnacle-crm/SKILL.md`: pipelines, stages, tag families, and what never goes in the CRM.
- `context/revenue-os/find-me-money/sales-crm.json`.
- `requests/crm/`: every file not yet marked done. Leads from Lead Radar and the communities, partners from the partnerships job, replies the bot saved.

## Do

1. **The map.** `ghl.py pipelines` and `ghl.py workflows`; save both to `context/crm-map.md` with today's date. Everything after this uses ids from that file.
2. **File every person.** For each row in `requests/crm/`:
   - `ghl.py contacts "<name, handle or email>"`: already there? Then update, never duplicate.
   - `ghl.py upsert` with what is known, `--source` and `--tags` (`src:radar`, `src:skool`, `src:whop`, `src:partner`, `type:lead` or `type:partner`). A public handle with no email or phone cannot be a contact yet: keep it in `data/crm/waiting.csv` with its URL until the person writes in.
   - `ghl.py note <contact> "<what they asked or said, the date, the link>"`.
   - `ghl.py opp-new` in the right pipeline at its first stage: leads in the funding leads pipeline, partners in the partner pipeline.
   - `ghl.py task <contact> --title "<the next step>" --due <a date>`: nobody is left without a dated next step.
3. **Replies.** For each reply the bot saved in `requests/crm/replies-*.md`: sort it by `repo/agents/sales-crm/prompts/sort.md`, log it (`CAMPAIGN=find-me-money python3 repo/convlog/gate.py inbound --person "<who>" --text-file <file>`), draft the answer by `repo/agents/sales-crm/prompts/reply.md` as an item in `requests/justin/` (message type `email_reply`), add the note, and move the stage with `ghl.py opp-move`.
4. **Work the pipelines.** `ghl.py opps` for each pipeline. For every open opportunity: is the stage right for the last thing that happened, and is there a dated next step? Fix the ones that are wrong. An opportunity with nothing for 7 days gets a follow-up draft (`repo/agents/sales-crm/prompts/follow-up.md`) and a task.
5. **Pipelines and workflows.** Compare `context/crm-map.md` with what this bot needs: a funding leads pipeline; a partner pipeline (Found, First touch drafted, Contacted, Replied, Call booked, Active partner, Not now); a workflow for a new lead's first day, one for a partner who replied, one for a lead gone quiet. For each that is missing or switched off, write its full spec to `requests/justin/crm-build.md`, once: the trigger, every step, every message in full, and the clicks to make it. Creating a pipeline or a workflow is done in GoHighLevel itself; the API does not make them.
   - `ghl.py workflow-add <contact> <workflow>` only for a workflow named in `context/crm-map.md` as approved for that kind of contact. A workflow can message a person, so this one also waits on `ghl_workflow_enroll: auto`.

Mark each `requests/crm/` file done by adding the line `done <today>` at its end.

Never in the CRM: a Social Security number, a date of birth, a bank or card number, a full EIN, a credit report or an exact score, a document. `ghl.py` refuses the ones it can see; you refuse the rest.

## Write

`daily/<today>/crm.md`: contacts added and updated, opportunities opened and moved, tasks set, replies answered in draft, writes made against writes proposed, and anything in the pipelines that looks wrong.
