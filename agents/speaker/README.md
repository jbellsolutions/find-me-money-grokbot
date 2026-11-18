# Podcast SpeakerAgent

Shows and stages: SpeakerAgent research cycles, fit scoring with an episode angle, pitches, follow-up on day 4 and day 10, and attribution for every appearance.

| | |
|---|---|
| Engine | codex; falls back to claude |
| Tier | not a partner tier |
| Channels | email, forms |
| Message types | podcast_pitch, podcast_follow_up |

## What it is built from

Adapted from the Speaker Agent pack of the owner's self-hosted agent app, where it already runs: its charter and three skills (podcast research, pitch writing, booking follow-up) became [PROCESS.md](PROCESS.md), and its runtime is in `runtime/`, unchanged.

Also in the `revenue-os-max` kit (the product's base, in the same factory), for a pack that already carries them:

- Roles: `roles/speaker.md`
- Skills: `speakeragent`, `speakeragent-podcasts`, `speakeragent-pitches`, `show-rss-research`, `charm-podcast-pitch`, `podcast-follow-up-and-attribution`
- Worker jobs: `show-research`, `show-score`

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The process: what changed in the move to a Grok bot, the pace, the fifteen steps, the rules and whose each one is |
| [speaker.example.json](speaker.example.json) | One business's settings: the speaker, topics and approved claims, leave-outs, sources and search words, the daily pace, the route order, follow-up days, attribution |
| [speaker.py](speaker.py) | Find shows (free reads), score them on Codex, draft a pitch or a follow-up on Codex, track every show to a booking, report against the daily pace, carry an existing SpeakerAgent persona and cases over |
| [prompts/](prompts/) | `show-fit.md` (the four judgments), `pitch.md` (three parts, every claim with its support), `follow-up.md` |
| [runtime/](runtime/) | From the source pack, unchanged: `research.py` (scorer, case validator), `speaker_cases.py` (case repair), the case contract, the scoring anchors, example files with made-up values |
| [STATUS.md](STATUS.md) | Where the function stands and what the owner still needs to say |
