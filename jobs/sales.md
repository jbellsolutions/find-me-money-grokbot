# Job: sales

The sales agent: it answers every reply and it works GoHighLevel. Justin, 2026-11-24: "We want to have a sales agent that works the go high level and takes care of replies, and that's a big part of what we're doing." And: "building affiliates and referrals, maintaining a pipeline for them."

It runs four times a day so no reply waits long. Everything in GoHighLevel goes through `python3 repo/tools/ghl.py` (run it with `-h` once). It reads freely. It writes only when Justin's switches allow; otherwise it saves the exact write to `requests/justin/crm-proposals-<today>.md` and prints PROPOSED. Either way you run the same commands: do the whole job as if writes were on. Before the key is in, the reads stop with a message and the writes are still saved as proposals: skip the reads and say so in the daily file.

## Read first

- `repo/agents/sales-crm/PROCESS.md` and its `prompts/` (sort, reply, follow-up).
- `repo/skills/pinnacle-crm/SKILL.md`: stages, tag families, and what never goes in the CRM.
- `context/revenue-os/find-me-money/sales-crm.json`; `context/targets.md`; `context/crm-map.md` if it is there.
- `requests/sales/`: every file not marked done. New replies the bot saved; leads from Lead Radar and the communities; affiliates and referral partners from the partnerships job; inbound leads from search.

## Do, in this order

1. **Replies first.** For each reply in `requests/sales/replies-*.md`: sort it (`prompts/sort.md`); log it (`CAMPAIGN=find-me-money python3 repo/convlog/gate.py inbound --person "<who>" --text-file <file>`); read the person's note in `vault/People/` and their contact in the CRM; draft the answer (`prompts/reply.md`) as an item in `requests/justin/` (ITEM, ROLE: find-me-money, ---PAYLOAD---, TO, SUBJECT, TEXT, ---END---) logged with `gate.py drafted <file> --agent sales-crm`. Message type `email_reply`. Then the note, the stage move (`ghl.py opp-move`) and the next dated task. Someone ready to talk gets the booking step; anyone upset goes to Justin and gets no draft.
2. **File every new person.** For each row handed over: `ghl.py contacts "<name, handle or email>"` (update, never duplicate); `ghl.py upsert` with `--source` and `--tags` (`src:radar`, `src:skool`, `src:whop`, `src:partner`, `src:search`; `type:lead`, `type:affiliate` or `type:referral-partner`); `ghl.py note`; `ghl.py opp-new` at the first stage of the right pipeline; `ghl.py task` with the next step and a date. A public handle with no email or phone cannot be a contact yet: keep it in `data/crm/waiting.csv` with its URL.
3. **The two pipelines, worked every run.** `ghl.py opps` for each.
   - **Direct leads** (from Lead Radar and search): New, Answered, Replied, Call booked, Application, Funded, Not now.
   - **Affiliates and referral partners**: Found, First touch sent, Replied, Call booked, Agreed, Sending leads, Not now. A partner who has sent a lead gets the tag `partner:active` and a note of each lead they sent.
   For every open opportunity: is the stage right for the last thing that happened, and is there a dated next step? Fix what is wrong. Nothing for 7 days gets a follow-up draft (`prompts/follow-up.md`) and a task.
4. **The map, pipelines and workflows.** Once a day (the first run): `ghl.py pipelines` and `ghl.py workflows` into `context/crm-map.md`. For each pipeline above that is missing, and for three workflows (a new lead's first day; an affiliate or partner who replied; a lead gone quiet), write the full spec to `requests/justin/crm-build.md`, once: the trigger, every step, every message in full, the clicks to make it. Pipelines and workflows are made in GoHighLevel itself. `ghl.py workflow-add` only for a workflow that `context/crm-map.md` marks approved; it also waits on `ghl_workflow_enroll: auto`.
5. **Old leads.** Justin, 2026-11-24: "We need to clear out the old leads from the dashboard." Once a day list every open direct lead with no reply and nothing in 14 days in `requests/justin/old-leads-<today>.md` (counts by source and age; the contacts stay in `data/crm/`). While `context/routines-on.md` says `old-leads: keep`, only list them. When it says `old-leads: clear`, move each to Not now with `ghl.py opp-move <id> --status abandoned` and the tag `old:cleared-<today>`. Nothing is deleted.

Mark each `requests/sales/` file done by adding the line `done <today>` at its end.

Never in the CRM: a Social Security number, a date of birth, a bank or card number, a full EIN, a credit report or an exact score, a document.

## Write

`daily/<today>/sales.md` (add to it on later runs): replies in and answered in draft; contacts added and updated; opportunities opened and moved, by pipeline; affiliates and partners by stage; tasks set; old leads listed or cleared; writes made against writes proposed.
