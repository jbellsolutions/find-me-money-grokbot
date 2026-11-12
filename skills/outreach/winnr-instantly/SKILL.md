---
name: winnr-instantly
description: >-
  Connect Hermes mailboxes (Winnr pre-warmed or AgentMail) to Instantly for warmup, manage
  Instantly accounts/tags, and handle Winnr mailbox credentials. Use the repo's own CLI —
  NEVER ad-hoc curl, which gets blocked and loses the work. Covers password rotation, IMAP
  verification, encrypted secret storage, and the API gotchas that cost hours to rediscover.
  Triggers: "add mailboxes to Instantly", "add the winnr accounts to instantly", "tag accounts
  in Instantly", "winnr password", "winnr credentials", "Instantly warmup", "Instantly API",
  "connect inboxes to Instantly", "import inboxes into Instantly".
---

# Winnr ↔ Instantly mailbox operations

Repo: the owner's private cold-email infrastructure repo (Hermes).

## THE RULE — use the repo CLI, never ad-hoc curl

This integration is **real, tested code in the repo**. Do not rewrite it as shell one-liners.

```bash
npm run dev -- winnr-instantly-sync --dry-run
```

Two independent reasons, both learned the hard way:

1. **Ad-hoc curl gets blocked.** A shell loop that rotates credentials and POSTs them to an
   external API is indistinguishable from a credential-exfiltration script, and Claude Code's
   permission classifier denies it — including one mailbox at a time, not just in bulk. The repo's
   own CLI is routine dev work and runs without friction.
2. **Scratch scripts evaporate.** Two full Instantly rollouts (149 AgentMail inboxes, then 20 Winnr
   mailboxes) were originally done as `.scratch-*.ts` files that were deleted afterwards. The result
   was a repo with *zero* Instantly code despite the integration being live twice — every task
   restarted from raw API research. If you find yourself writing a scratch script for this, extend
   the adapter instead.

## Commands

```bash
# ALWAYS dry-run first — this rotates passwords, which is irreversible.
npm run dev -- winnr-instantly-sync --dry-run

# Prove one mailbox end-to-end before a batch.
npm run dev -- winnr-instantly-sync --address someone@example.com

# The batch. Idempotent: anything already in Instantly is skipped, never re-rotated.
npm run dev -- winnr-instantly-sync
```

Flags: `--dry-run`, `--address <email>`, `--limit <n>`, `--route <route>` (default `winnr`).

Refuses to run without `HERMES_SECRET_KEY` — it will not rotate a password with nowhere durable
to store it.

## The code

| File | Role |
|---|---|
| `src/providers/instantly.ts` | Instantly v2 client — accounts, pagination, tags |
| `src/providers/winnr.ts` | Winnr client — `getEmailUser`, `setPassword` |
| `src/core/imapVerify.ts` | Proves a password authenticates, with propagation retry |
| `src/core/mailboxSecrets.ts` | AES-256-GCM storage in `mailbox_secrets` |
| `src/orchestrator/winnrToInstantly.ts` | The orchestration + idempotency |
| `test/instantly.test.ts`, `test/winnrToInstantly.test.ts` | Mocked-fetch coverage |

## API gotchas — each of these cost real debugging time

**Instantly** (`https://api.instantly.ai/api/v2`, `INSTANTLY_API_KEY`, Bearer):
- **A recognizable `User-Agent` header is required.** Requests without one 403. Node's and Python
  urllib's defaults are not enough.
- **The `next_starting_after` cursor must be URL-encoded** before going back on the query string.
  It is base64-ish and contains `/`, `+`, `=`. An unencoded cursor 403s.
- `daily_limit: 1` on every account we create — a deliberate backstop so Instantly can never become
  a second real-sending lane invisible to Hermes' own per-mailbox tracking. Do not "fix" this.
- Tagging is `POST /custom-tags/toggle-resource` with `resource_type: 1` (Account) and email
  addresses as `resource_ids`.

**Winnr** (`https://api.winnr.app`, `WINNR_API_KEY`, Bearer; spec at
`https://app.winnr.app/openapi.yaml?v=<hash>` — every guessable `/openapi.json` path 404s):
- **Winnr never returns an existing mailbox password.** `EmailUser` has no password field, on
  `GET /v1/email-users/{id}` *or* the documented `?filter[domain]=` list path. Don't go looking again.
- **`WINNR_API_KEY` is NOT a shared IMAP password.** (AgentMail's org key *is*, which makes this an
  easy wrong assumption. Verified: raw IMAP auth with the API key returns `AUTHENTICATIONFAILED`.)
- So connecting a mailbox anywhere external **requires** `PATCH /v1/email-users/{user_id}`
  `{password}` — a normal partial update. **This is irreversible**: the old password is gone.
- **NEVER `POST /v1/email-users/replace`.** It DELETES and recreates the mailbox — all mail and all
  warmed reputation permanently lost. It is never the right tool.
- IMAP/SMTP hosts are **resolved per mailbox** (Winnr spreads domains across mail servers). They all
  return `inbound.mywinnr.com` today; never hardcode that across a batch.

**Timing:** a freshly-set password takes ~5s to reach the mail backend. Verifying immediately fails
with `AUTHENTICATIONFAILED` *even when the password is correct*. `imapVerify.ts` sleeps before the
first attempt and retries 3×. This exact race broke a mailbox on the first rollout.

## Credentials

Rotated passwords are stored AES-256-GCM encrypted in `mailbox_secrets`, keyed by address, under
`HERMES_SECRET_KEY` in the gitignored `.env`.

**For Winnr mailboxes this is the only copy** — Winnr won't show it again, so losing the key means
re-rotating every mailbox. The key must be mirrored to Railway for the secrets to be usable there.

## Verifying

Never trust the command's own log — read the state back independently:

```bash
# All winnr-tagged accounts: expect status 1, warmup_status 0, daily_limit 1, setup_pending false
curl -s "https://api.instantly.ai/api/v2/accounts?tag_ids=<TAG_ID>&limit=100" \
  -H "Authorization: Bearer $INSTANTLY_API_KEY" -H "User-Agent: curl/8.0" \
  | jq '{n:(.items|length), status:[.items[].status]|unique, warmup:[.items[].warmup_status]|unique}'
```

Then re-run the sync — a fully-synced fleet reports every mailbox as `skipped_existing` and rotates
nothing. That is the idempotency proof.

## Current state (2026-07-31)

All 20 `route='winnr'` mailboxes are live in Instantly, tagged `winnr`
(tag id `INSTANTLY_WINNR_TAG_ID`, set at intake), **warmup deliberately OFF** — they are pre-warmed
(`warmup_stage=99`), so Instantly's synthetic warmup would spend their daily volume for nothing.
The 149 AgentMail inboxes have warmup **ON**. That asymmetry is intentional; don't reconcile it.

## Related

`hermes-fleet` skill — operates the *deployed* fleet (leads, campaigns, sending) via the hosted
agent. It cannot reach Instantly or Winnr APIs. Different tool; don't reach for it here.
