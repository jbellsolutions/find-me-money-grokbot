# Content

UGC, viral and storytelling content made to be shared: reactions, talkbacks, breakdowns, UGC. LinkedIn, YouTube and the newsletter first; Instagram as the fourth outlet. Runs the owner's content workflows (handed over at intake).

| | |
|---|---|
| Engine | claude; falls back to codex |
| Tier | not a partner tier |
| Channels | linkedin, youtube, newsletter, instagram |
| Message types | linkedin_post, youtube_publish, newsletter_issue, instagram_post |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/content-seo.md`, `roles/channels.md`
- Skills: `content-engine`, `charm-social-content`, `linkedin-ghostwriter`, `youtube-channel`, `youtube-brief-loop`, `channel-weekly-read`
- Worker jobs: none

## Files here

[PROCESS.md](PROCESS.md), [STATUS.md](STATUS.md), `content.py`, `prompts/`, `content.example.json`, [TOOLS.md](TOOLS.md) and `skills/`. Version 0.4; earlier versions are in the changelog.

## Toolset

[TOOLS.md](TOOLS.md): the video and posting tools, which engine operates them, the call path that needs, and what is not built. Claude Code runs the agent as a whole, the video tools included.

One skill per video tool, each written from the tool's public pages and not yet run:

| Skill | For |
|---|---|
| [skills/higgsfield/](skills/higgsfield/SKILL.md) | A generated clip, by API |
| [skills/invideo/](skills/invideo/SKILL.md) | Generated clips and an edited cut, by its CLI |
| [skills/max-fusion/](skills/max-fusion/SKILL.md) | An AI-actor or product ad, by its MCP server. Which tool the owner meant is not confirmed |
| [skills/arcads/](skills/arcads/SKILL.md) | A talking AI actor, by API |
| [skills/creatomate/](skills/creatomate/SKILL.md) | A templated cut, by API |
| [skills/google-flow/](skills/google-flow/SKILL.md) | A generated clip on Google's models, by the Gemini API |

## Rules

The owner's rules here are two: new spend needs the owner's yes (every render and every sign-up is spend), and nothing is published without the owner's yes. Every other rule in this folder that is not in the owner's words is on the keep-or-remove list at the top of [STATUS.md](STATUS.md).
