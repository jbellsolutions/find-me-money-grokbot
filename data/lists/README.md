# data/lists: Justin's private lists

Empty in the pack on purpose. Justin gives these at intake (HANDOFF Part 2 step 3); the bot saves them in `/workspace/find-me-money/data/lists/` (folder mode 700, files mode 600). They never go in a report, a chat, the vault or the pack. The `.gitignore` here keeps every file but this one out of git.

| File | What | Columns | Who reads it |
|---|---|---|---|
| `influencers.csv` | Creators Justin already knows of | `handle, platform, niche, link, note` | partners, radar (Niche rotation) |
| `coaches.csv` | Coaches and consultants | `name, type, link, note` | partners, radar |
| `communities.csv` | Groups and communities, any platform | `name, platform, theme, link, members, note` | radar; the worker's `fbgroups` and `group-discovery` lanes get the Facebook rows |
| `partner-targets.csv` | The partner-target sheet | `company, kind, products, states, link, note` | partners |

Rules:

- Every row carries a `link`. A row with no link is dropped, the same rule the Pull routine uses for research rows.
- One header line, comma-separated, UTF-8. Unknown cells stay empty; nothing is guessed.
- No phone or email unless the person published it for business contact.
- Facebook group links by theme also live on the Mac in `~/.fmm/groups/<theme>.txt` (one link per line), where the worker's `fbgroups` lane reads them. The installer creates that folder; the `group-discovery` lane adds to it.
- A missing file is normal: the lane starts from the lead map and the worker's own research, and says so in its run line.
