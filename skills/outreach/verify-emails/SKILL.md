---
name: verify-emails
description: >-
  Verify email addresses and clean lead lists for deliverability before sending —
  catches invalid/bouncing addresses, catch-all domains, role accounts, and
  disposables using the self-hosted Reacher stack (droplet + Proxy4Smtp). Use when
  asked to verify an email, validate/clean/scrub an email or lead list, check if an
  address is deliverable or real, reduce bounce rate, or decide whether it's safe to
  email someone. Triggers: "verify this email", "is this email valid/real",
  "clean my list", "check deliverability", "will this bounce", "validate these leads".
---

> **Retired 2026-10-07:** the original self-hosted Reacher droplet was deleted to cut cost; the owner keeps an archive. Use the backend in `REACHER_URL` (set at intake). If it is unset or unreachable, tell the user verification is offline instead of retrying.

# Verify Emails (self-hosted Reacher)

Verifies email deliverability **without sending mail** — SMTP-probes each address
through the Reacher backend at `REACHER_URL` (which routes via the Proxy4Smtp
SOCKS5 proxy, so Gmail/Yahoo/Outlook verify correctly). Two tools:

- **`reacher` CLI** — single checks and raw API access (agent-native: `--json`, `--agent`, `--select`).
- **`tools/reacher_verify.py`** (bundled) — takes a CSV/TXT list → returns it sorted into **SEND / DROP / REVIEW / RETRY** with a clean CSV. This is the canonical workflow for lists.

Credentials are saved in the CLI config. The endpoint is `REACHER_URL`, set at intake.
If commands fail with a DNS/connection error, the endpoint's DNS record may not be live yet —
override with `REACHER_URL` (e.g. an SSH tunnel to the droplet) or tell the user.

## Verify ONE address

```bash
reacher check-email post-v1 --to-email someone@example.com --json
```

The verdict is at `.data.is_reachable` (one of `safe` / `risky` / `invalid` / `unknown`).
Extract just that:

```bash
reacher check-email post-v1 --to-email someone@example.com --json | jq -r '.data.is_reachable'
```

Health check anytime: `reacher doctor`. Introspect all commands: `reacher agent-context`.

## Verify a LIST (the main job)

Use the bundled Python tool — it uploads the whole list, polls to completion, and
writes an annotated CSV plus per-bucket files. Stdlib-only, no install.

```bash
python3 repo/skills/outreach/verify-emails/tools/reacher_verify.py leads.csv -o out
```

It auto-detects the email column and reuses the same droplet endpoint + saved credential
as the `reacher` CLI (no flags needed). Output in `out/`:
- `results.csv` — every row + bucket + plain-English reason + flags
- `send.csv` / `drop.csv` / `review.csv` / `retry.csv`

Override the target if needed: `--backend <url> --secret <val>` (or `REACHER_BACKEND` / `REACHER_SECRET`).

## Enrich REVIEW leads (recover real emails from catch-all / role-account domains)

REVIEW leads (catch-all domains, `info@`/`support@` role accounts) are mostly unusable as-is.
Enrichment finds the **real named person** for those companies:

```bash
python3 repo/skills/outreach/verify-emails/tools/enrich.py review.csv -o enriched
```

Per unique domain it scrapes the public site (contact/about/team pages) for real on-domain
emails, infers the address pattern, optionally Google-dorks LinkedIn via Bright Data, then
**re-verifies every candidate through Reacher**. Output tiers (in `enriched_all.csv`, with the
mailable set in `enriched_mailable.csv`):
- **SEND** — SMTP-confirmed deliverable (usually from non-catch-all domains).
- **LIKELY** — a real email published on the company's *own website*; the domain is catch-all so
  SMTP can't confirm it, but the company published it → real and mailable.
- **SPECULATIVE** — pattern-guessed (not published), unconfirmed — use with caution.

No paid enrichment SaaS. To add the LinkedIn/SERP layer (finds named people even when a site
publishes no emails), set `BRIGHTDATA_API_KEY` + `BRIGHTDATA_SERP_ZONE`. Uses the same Reacher
credential as the CLI/list tool.

## What the buckets mean (how to act)

| Bucket | `is_reachable` | Meaning | Action |
|--------|----------------|---------|--------|
| **SEND** | `safe` | Mailbox exists, accepts mail | Mail them |
| **DROP** | `invalid` | Dead mailbox/domain, or disposable/blocklisted | Remove — these **hard-bounce** |
| **REVIEW** | `risky` | Accepted but unconfirmable: catch-all domain, role account (`info@`), full inbox, disposable | Send with care / segment |
| **RETRY** | `unknown` | Provider blocked the probe (greylisting/rate-limit) | Re-run the RETRY file later |

**Honest limits (don't over-promise):**
- **Catch-all domains** accept every address, so no probe can confirm an individual mailbox → they land in REVIEW, never SEND.
- **`unknown` ≠ bad** — it means "no straight answer this time." Re-running usually resolves it.
- SMTP verification removes the *guaranteed* bounces (DROP) and is the strongest non-sending signal; it does not guarantee zero bounces on REVIEW.

## Non-technical option

For a human who just wants to drag-and-drop a CSV: the dashboard at
the owner's hosted verifier dashboard (password-gated; ask the owner for the link) does the
same upload → buckets → download in the browser.

## Anti-triggers (do NOT use this skill for)

- Sending emails / running campaigns (this only *verifies*, never sends).
- Finding or guessing email addresses (no enrichment/discovery here).
- Bulk-verifying someone else's list you don't have permission to process.
