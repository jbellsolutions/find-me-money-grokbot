---
name: orgo-computer
description: "Use your own Orgo cloud computer (a full Linux desktop with Chrome logged into GoHighLevel, LinkedIn, and Skool): take screenshots, click, type, scroll. Use for anything the APIs can't do — building/editing GHL workflows, funnels, and snapshots in the UI, LinkedIn research and DMs, Skool posts — and to prove work with screenshots."
---

# Your Orgo computer

- It is **yours**: the "Funding Affiliate Manager" workspace on Orgo, one always-on Linux desktop. The `orgo` MCP key is scoped to that workspace — you cannot see or touch other computers.
- You run on this computer, and its desktop is where you work: no second computer, no second browser. Hermes' local `computer_use` is off; the `orgo` MCP is how you drive the desktop.
- Never open a terminal, a file manager or a text editor on the desktop, and never touch `~/.fcm`, your settings or the approvals. Never sign in to Slack here, and stop and tell the manager if you see a Slack session open: approvals count only from the approver's own Slack account.
- For anything the GoHighLevel API token can't do, follow skill `ghl-dashboard`: it has the step-by-step workflows and the fallback for new roadblocks.
- Logged-in sessions (set up once by Justin over VNC): GoHighLevel (demo location), LinkedIn, Skool. If a site shows a login page, stop and ask the manager — never type passwords.

## Pattern
1. Screenshot first. Describe what you see before acting.
2. Act in small steps (click → screenshot → verify). Prefer keyboard shortcuts and URL navigation over hunting for buttons.
3. There is no shell, Python or file tool in the `orgo` MCP, on purpose. Work through the UI.
4. Finish with a screenshot as proof and log it in the daily note.

## Approval rules (same as everything outbound)
- Reading, researching, building drafts in GHL (unpublished workflows/funnels): allowed.
- Publishing a workflow, sending a LinkedIn DM, posting in Skool, publishing a funnel, or anything visible to others: draft → approval card to the manager → do it only after a clear yes.
- Never create, delete, resize, or clone computers or workspaces (those tools are excluded anyway).

## Common jobs
- Build W-1…W-9 from `config/workflows.json` in GHL's workflow builder, leave them in **draft**, screenshot each, ask the manager to publish.
- Build the Affiliate Lifecycle and Growth Services pipelines from `config/pipelines.json` (exact names), then tell the manager to run `fcm ghl bootstrap --apply` (or ask to run it).
- LinkedIn: research an affiliate's profile for intake; draft DMs for approval.
- Skool: draft the weekly coaching-call announcement and event posts for approval, then post.
