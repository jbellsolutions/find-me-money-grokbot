# Job: lead-radar

People asking in public for funding. Find them, keep the real ones, draft a helpful first answer, hand each to the crm job.

## Read first

- `context/revenue-os/find-me-money/lead-radar.json`: the offer, the buyer, the leave-outs, the channels that are on, how old a post may be.
- `repo/agents/lead-radar/PROCESS.md` and `repo/agents/lead-radar/prompts/lead-fit.md`: how a post is scored 1 to 5.
- `state/lead-radar/terms.md`: the search terms. If it is not there, write it first: 20 ways an owner asks for funding in their own words, the creative routes included (equipment, a build-out, payroll, a first property, bad credit, denied by the bank).

## Do

1. Search the public web for posts from the last 7 days on the channels that are on (Reddit, public Facebook groups and pages, TikTok and YouTube comments, X), with WebSearch and WebFetch. Public pages only. A page that asks for a sign-in is skipped and named in the daily file.
2. Write what you found to `state/lead-radar/found-<today>.json`: a list of `{"id": "<channel>:<post id>", "channel", "url", "author": "<public handle>", "text", "posted_at", "source": "web"}`.
3. Score them: `CAMPAIGN=find-me-money python3 repo/agents/lead-radar/radar.py score --items state/lead-radar/found-<today>.json --settings context/revenue-os/find-me-money/lead-radar.json --test`. If the script cannot reach an engine, score them yourself by the prompt file: you are the engine.
4. For each post kept at 4 or 5:
   - Check `python3 repo/guards/scripts/suppression.py check "<handle>"`. `held` means skip.
   - Draft a public reply: it answers the question, teaches one thing, asks for nothing, has no link and no "DM me". Item file `requests/justin/reply-<today>-<n>.md` (ITEM, ROLE, ---PAYLOAD---, TO: the post's URL, SUBJECT: the need, TEXT, ---END---), logged with `CAMPAIGN=find-me-money python3 repo/convlog/gate.py drafted <file> --agent lead-radar`. Message type: `public_reply`.
   - Add the person to `requests/crm/leads-<today>.md`: handle, channel, URL, the need in their words, the score. The crm job files them.
5. Anyone found who has an audience of owners (a creator, a coach, a group owner) is not a lead: add them to `requests/partnerships/found-<today>.md` with the public source.
6. Add each real question, without the person, to `content/ideas.md`. The afternoon content run answers them.

## Write

`daily/<today>/lead-radar.md`: posts read, kept, drafted; pages skipped for a sign-in; the three questions asked most.
