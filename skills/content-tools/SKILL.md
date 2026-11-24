---
name: content-tools
description: Use for every piece of content. The hard rule on how Find Me Money content is made - every script, post and caption is written by the Claude Code CLI, every talking video is rendered in HeyGen, and the other video tools are used only for what HeyGen does not do. Covers the commands, what a render costs and who approves it, and what the bot never does itself.
---

# Content: the hard rule

Justin, 2026-11-24: "We want to make sure we have a hard and fast rule on content. We're using HeyGen and different tools, and we're also using Claude Code CLI."

1. **Words are the Claude Code CLI's.** Every script, post, caption, carousel and video brief is written by the content job: `python3 repo/tools/job.py run content`. The bot never writes a piece itself.
2. **Talking videos are HeyGen's.** A script that is meant to be said to camera is rendered with `python3 repo/tools/heygen.py render --script-file <file>`. The content job runs it; the bot does not open HeyGen in a browser to do the same thing by hand.
3. **The other tools do what HeyGen does not.** Each has a page in `repo/agents/content/skills/`: Creatomate (templates, captions, cut-downs), Arcads (ad actors), Higgsfield and Google Flow (b-roll and motion), InVideo, Max Fusion. `repo/agents/content/TOOLS.md` says how each is reached and how it charges. The content job picks by that page and says which tool it used in the piece's file.
4. **A render is spend.** HeyGen renders run up to the number in `heygen: approved <videos a day>` (context/spend-approvals.md). Past it, or before Justin has said it, the script is finished and the exact render command waits in `requests/justin/video-renders-<date>.md`. Any other tool's paid run asks `python3 repo/guards/scripts/spend_guard.py <tool> <usd>` first.
5. **Nothing is posted by this rule.** A finished piece is a draft until its type is `auto` and the outlet has a brand account.

## The commands

```
python3 repo/tools/job.py run content --note "<what is wanted>"
python3 repo/tools/heygen.py check | avatars | voices
python3 repo/tools/heygen.py render --script-file content/drafts/<file>.script.txt --portrait
python3 repo/tools/heygen.py status <video_id>
python3 repo/tools/heygen.py fetch <video_id> --out content/video/<file>.mp4
```

Each piece's file ends with three lines: `words by:` (the engine that wrote it), `video by:` (HeyGen and the video id, another tool, or "held: <why>"), and `points to: findmemoneyapp.com`.
