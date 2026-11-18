# The sales agent: replies and the CRM in one

One agent answers people and keeps the CRM. When someone writes back it adds them to the CRM, moves them in the pipeline, makes their contact card and their note in the vault, answers them, and follows up until they book a call or say no.

The owner combined the reply agent with this one on 2026-11-17, and named its engine: the Codex CLI on the ChatGPT subscription, model GPT-6 Luna. Version 1 runs inside the Grok bot; today's sales agent is a Hermes agent on an Orgo computer and is not changed by this. `agents.json` shows the two as one since core 0.6.

| | |
|---|---|
| Engine | codex, model gpt-6-luna; falls back to claude |
| Tier | not a partner tier |
| Channels | crm, email, linkedin, x, instagram, youtube, facebook, skool, sms |
| Message types | crm_opener, crm_follow_up, warm_reconnect, crm_nurture, and the reply types in `PROCESS.md` |

## What it is built from today

In the `revenue-os-max` kit (the product's base, in the same factory):

- Roles: `roles/sales-crm.md`
- Skills: `chief-sales-officer`, `crm-conversations`, `gtm-crm-records`, `gtm-crm-openers`, `gtm-crm-sweep`, `gtm-crm-deals`, `quiet-thread-nudge`, `screenshot-to-crm`
- Worker jobs: none

## Files here

| File | What |
|---|---|
| [PROCESS.md](PROCESS.md) | The loop for one reply, what each intent does, follow-up, where it runs, what is not built |
| [sales-crm.example.json](sales-crm.example.json) | One business's settings: the computer, the engine and model, the CRM and its stage map, the vault, the inboxes, message types |
| [prompts/sort.md](prompts/sort.md) | Codex sorts each reply: one intent, the facts, a dated next step |
| [prompts/reply.md](prompts/reply.md) | Codex drafts one answer from the person's note and the thread |
| [prompts/follow-up.md](prompts/follow-up.md) | Codex drafts one short follow-up for a quiet thread |
| [STATUS.md](STATUS.md) | Every rule in this folder: the keep-or-remove list, what the owner said, what was removed. Then where the function stands |
