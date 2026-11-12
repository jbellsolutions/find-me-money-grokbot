---
name: charm-linkedin
description: >
  Writes Charm Offensive LinkedIn connection invites and follow-up messages that get accepted and
  start conversations — personalized with research on the prospect. Use when the user asks to "write
  a LinkedIn invite", "LinkedIn connection request", "LinkedIn message", "LinkedIn outreach", "DM this
  person on LinkedIn", "follow up after they accept", set up a LinkedIn lead-gen sequence (e.g. for
  LinkedHelper), or wants their LinkedIn messaging to sound human and funny instead of salesy.
metadata:
  version: "0.1.0"
---

# Charm Offensive — LinkedIn

Write LinkedIn invites and follow-ups that feel human, get accepted at scale, and open a real
conversation — using disarming honesty and humour, then a soft, gain-framed pitch.

The template library and voice notes are licensed course material, so they never ship in the pack. Justin gives them at intake in `/workspace/find-me-money/.secrets/course/charm/` (mode 600). If a file named below is missing, write from the principles here and say the templates weren't given.

Credit: the approach is adapted from Jon Buchan's Charm Offensive.

## Step 0 — Load the voice and profile (always)

1. Read `/workspace/find-me-money/.secrets/course/charm/voice-and-humour.md` if it was given.
2. Get the user's profile (what they do, who they help, their sign-off): ask for it if it isn't in the workspace.
   You need: what they do / who they help, the sector(s) they love, and their sign-off style.
3. Read `/workspace/find-me-money/.secrets/course/charm/linkedin-templates.md` for the invite and follow-up shapes.

## Step 1 — Scale vs. key prospect

Ask which mode:

- **At scale** (a segment / LinkedHelper campaign): use a light, human, non-personalised invite; a
  human-sounding generic invite still gets plenty of accepts. Then a sector-specific follow-up after they
  connect. Use safe merge fields ({firstname}) only.
- **Key prospect** (someone they *really* want): fully personalise. Research them and reference a
  genuine, specific detail. This is worth the extra effort and always beats the scale template.

## Step 2 — Research

For key prospects (and to sharpen segment messaging): use connected tools / LinkedIn scrapers /
enrichment skills if installed, plus WebSearch, to find role, what they post about, shared interests,
recommendations, the sector they're in. Capture only genuine hooks. For the sector follow-up, you
mainly need to name their sector convincingly and show you love working in it (the Liking principle).

## Step 3 — Draft

**Invite** — keep it short, human, and a little cheeky. Two shapes work (details in the private templates):
a plain human line that admits it isn't a template, or a curiosity hook plus a funny way out that sets
up the follow-up. Character-limit aware.

**Follow-up (after they accept)** — reference the humour in the invite, make light of the sudden
pitch, show you love their sector, and frame it as *them* gaining (ideas they can use), not
a hard sell. Low-pressure CTA to chat.

Keep LinkedIn messages shorter than emails. One hook, one soft ask.

## Step 4 — Self-check and deliver

Run the voice self-check. Then output: the invite text (with character count if near the limit), the
accept-follow-up, and, for a sequence, any second nudge — each labelled. If the user runs LinkedHelper
or similar, format with the right merge fields. Never automate sending without the user's approval;
respect LinkedIn's limits and terms.

## References

- `/workspace/find-me-money/.secrets/course/charm/linkedin-templates.md` (private, given at intake): invite copy, the sector follow-up and the
  post-accept message, with notes.
