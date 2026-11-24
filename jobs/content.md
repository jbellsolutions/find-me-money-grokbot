# Job: content

Justin, 2026-11-24: "creating content, really more so than anything else." And: "We want to make sure we have a hard and fast rule on content. We're using HeyGen and different tools, and we're also using Claude Code CLI."

**The rule** (`repo/skills/content-tools/SKILL.md`): you, the CLI, write every word. Every piece meant to be said to camera is rendered in HeyGen with `python3 repo/tools/heygen.py render`. The other video tools in `repo/agents/content/skills/` are for what HeyGen does not do.

## Read first

- `repo/campaigns/find-me-money/MESSAGING.md`: the position, what it stands for, the eight pillars, the content types, the voice.
- `repo/skills/fmm-viral-content/SKILL.md`: the eight money hooks, word for word.
- `repo/agents/content/prompts/`: one page per format (reaction, talkback, breakdown, ugc).
- `context/revenue-os/find-me-money/content.json`: outlets, pieces a day.
- `daily/<today>/plan.md` if it is there; `content/calendar.md`; `content/ideas.md` (what Lead Radar and the communities found); `requests/content/` (video briefs from the AEO and SEO job: these come first).
- `context/messaging/messaging-document.md` if it is there: the private proof points and the claims Justin has cleared.

## Make

Three pieces this run (the note says morning or afternoon; half of `pieces_a_day`).

- Morning: the next three open rows of `content/calendar.md`. If there is no calendar, or fewer than three open rows, first write the next two weeks of it: six rows a day, each with a pillar, a content type and a hook, no pillar twice in a row.
- Afternoon: three pieces that answer real questions from today, taken from `content/ideas.md` and `daily/<today>/lead-radar.md`. Use the question, never the person: no name, handle, group name or quote that could be searched.

For each piece write `content/drafts/<today>-<type>-<n>.md` with: the hook (first two seconds), the script or post in full, the on-screen text, the caption, one version for each outlet that is on in the settings, and the one thing the viewer learns. 

Then the video. For each piece said to camera, save the spoken words alone to `content/drafts/<today>-<type>-<n>.script.txt` and run `python3 repo/tools/heygen.py render --script-file <that file> --portrait`. It renders, or prints RENDER HELD and queues the command for Justin; go on either way. A render started on an earlier run: `heygen.py status <id>`, and when it is done `heygen.py fetch <id> --out content/video/<name>.mp4`. Captions, cut-downs and b-roll: the tool its page in `repo/agents/content/skills/` says fits, after `python3 repo/guards/scripts/spend_guard.py <tool> <usd>`.

End each piece's file with three lines: `words by: <engine>`, `video by: <HeyGen and the video id, another tool, or held: why>`, `points to: findmemoneyapp.com`.

Then for each piece write its item file `requests/justin/content-<today>-<n>.md`:

```
ITEM: content-<today>-<n>
ROLE: find-me-money
---PAYLOAD---
TO: <outlet>
SUBJECT: <the hook>
TEXT: <the piece for that outlet>
---END---
```

and log it: `CAMPAIGN=find-me-money python3 repo/convlog/gate.py drafted requests/justin/content-<today>-<n>.md --agent content`.

## Hold to

- The position is Justin's, in his words: free to the owner; not a lender, not a broker; the best rate and the best deal. How Find Me Money gets paid is said plainly wherever "free" is said. If `context/messaging/how-we-get-paid.md` is not there, write the piece without the word "free" and add one line to `requests/justin/open-questions.md`, once.
- No proof point, count, screenshot or line about a named company unless the private messaging document is in and that claim is cleared there.
- Never promise approval, an amount or a timeline. Never "guaranteed", "pre-approved", "instant", "no risk".
- A piece teaches one thing the viewer can use that day.
- You never post. Message type: `fmm_content_post`.

## Write

`daily/<today>/content.md`: the three pieces (file, pillar, type, hook, video rendered or held), and which calendar rows are now done. Mark those rows done in `content/calendar.md`.
