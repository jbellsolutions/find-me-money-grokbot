# Lead Radar

Brings the leads and opportunities in the door: reads social media, Skool and Whop for people talking about the offer, judges each post, hands the kept ones to the sales agent, lists possible influencers and partners, and holds the data for the email campaigns.

| | |
|---|---|
| Engine | codex; falls back to claude |
| Tier | not a partner tier |
| Channels, to start | facebook, instagram, reddit, skool, whop |
| Channels, switched off to start | linkedin, tiktok, youtube, x |
| Message types | none: the sales agent starts the conversation |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/social.md`
- Skills: `lead-radar`, `treg`, `x-intent-search`, `skool-inbound`
- Worker jobs: `radar-poll`, `skool-score`

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The four routes, the tools, who does what with a kept lead, the twelve steps, what is not built |
| [lead-radar.example.json](lead-radar.example.json) | One business's settings: offer, buyer, leave-outs, routes, channels, sources, the keep line |
| [prompts/lead-fit.md](prompts/lead-fit.md) | The scoring prompt, 1 to 5; the business's offer and buyer are added from its settings |
| [radar.py](radar.py) | The judging step: found posts in, kept leads logged and handed to the sales agent |
| [STATUS.md](STATUS.md) | The keep-or-remove list, what was decided, what is open |
