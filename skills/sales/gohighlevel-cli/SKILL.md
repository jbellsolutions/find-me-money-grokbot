---
name: "gohighlevel-cli"
description: "Control GoHighLevel (GHL) CRM/Marketing across a multi-tenant agency — contacts, opportunities, calendars, workflows, conversations, emails, payments, forms, social, locations, documents, plus a named credential profile per business/client (Revenue Partners, Client A, funding) and sub-account provisioning. Use the `ghl` CLI or the `gohighlevel` MCP tools. Triggers: gohighlevel, ghl, GHL contacts/workflows/opportunities/calendars/profiles."
triggers:
  - gohighlevel
  - ghl
  - ghl cli
  - ghl contacts
  - ghl workflows
  - ghl calendars
  - ghl opportunities
  - ghl profiles
  - revenue partners
---

# gohighlevel-cli

Control the GoHighLevel (GHL) CRM and Marketing API from any Claude Code session — across
**one agency with multiple businesses**, each with its own sub-accounts (see
[Multi-tenant: profiles](#multi-tenant-profiles) below). Two interchangeable interfaces are
installed **globally** on this machine:

1. **MCP server `gohighlevel`** (user scope, in the user's Claude Code config) — native tools in
   every session after a Claude Code restart:
   - `ghl(args=[...], json_output=true, experimental=false, profile=None)` — run ANY GHL command.
   - `ghl_profiles(business=None)` — list configured businesses/sub-accounts. **Call this
     before targeting a specific client** — never guess a profile name from a display name.
   - `ghl_help(command=[...])` — discover exact flags for a command.
   - `ghl_catalog()` — list all command groups/commands.
2. **CLI `ghl`** on PATH (`~/.local/bin/ghl`) — one-shot commands or the REPL.

**Install location: `$GHL_MCP_HOME`** (repo + venv + `.env` + `ghl_mcp_server.py`; set at intake).
This is the single install. Any separate vanilla upstream checkout is
superseded, do not run it.

## Credentials (single source of truth: `$GHL_MCP_HOME/.env`)

| Var | Required | What it is |
|-----|----------|------------|
| `GHL_API_KEY` | **Yes** | Private Integration Token (`pit-…`), scoped + revocable |
| `GHL_LOCATION_ID` | **Yes** | Sub-account ID (the long ID in the GHL URL) |
| `GHL_FIREBASE_REFRESH_TOKEN` | No | ONLY for workflow *creation* via the unofficial internal API |

Both the CLI and the MCP server read this same `.env`. To rotate a key, edit one file.

`GHL_LOCATION_ID` has **no default** — commands fail loudly if it is unset. (It
previously fell back to the upstream author's own location ID, which silently pointed
every command at a stranger's sub-account. That default was removed.)

## Multi-tenant: profiles

One GHL agency (`<GHL_COMPANY_ID>`, set at intake) runs **multiple businesses**, each with its own
sub-accounts. GHL's API has **no concept of grouping sub-accounts** (confirmed: `/locations/search`
accepts only `companyId`/`skip`/`limit`/`order`/`email` — a `group` param 422s,
`/locations/tags/search` 404s). `profiles/registry.json` (chmod 600, gitignored) is where
we invent that grouping ourselves — one entry per sub-account, tagged with a `business`
bucket, plus one `_agency` entry for the agency-level token.

**Businesses:** each profile is tagged with a business bucket (for example the agency's own business,
a client project, the funding business). The real profile names are in `profiles/registry.json`.

**Never assume a bare command (no profile) targets the client you mean.** Without
`--profile`/`profile=`, commands fall back to `.env`'s default — currently
`revenue-partners`. Always resolve the right profile first:

```bash
ghl --json profiles list                       # all profiles
ghl --json profiles list --business client-a # just one business's clients
```
```
ghl_profiles()                    # MCP: same thing
ghl_profiles(business="client-a")
```

Then target it:
```bash
ghl --profile client-a-acme contacts list
```
```
ghl(["contacts","list"], profile="client-a-acme")
```

**Adding a profile** (after a sub-account + its Private Integration Token already exist):
```bash
ghl profiles add client-a-acme --business client-a \
  --location-id <id> --label "Client A — Acme Dental"
# prompts for the token (hidden input) if --api-key is omitted
ghl profiles remove client-a-acme
```

Check the install with `verify.sh --profile <name>` (location-scoped endpoints) and, for agency-only
resources (`locations get/search`, snapshots, `POST /locations/` provisioning), the `_agency` profile.

### Agency vs location tokens — two different scope lists

GHL has two kinds of Private Integration with **two different scope lists**. The agency
list (~24 scopes: snapshots, custom-menus, locations, saas, oauth, companies) **does not
contain** `contacts.readonly`, `opportunities.readonly`, etc. Those exist only on an
integration created from **inside a sub-account**. So "tick every scope" on an agency
integration cannot unlock contacts — the checkboxes aren't on that screen. Every profile
except `_agency` needs a **location-level** token.

Diagnose any token with:
```bash
$GHL_MCP_HOME/.venv/bin/python $GHL_MCP_HOME/scope-probe.py --profile <name>
```
`users` returning *"Token's user type mismatch!"* = agency token on a location endpoint.

### Provisioning a new sub-account (Client A clients, future Revenue Partners clients, the funding business)

```bash
.venv/bin/python provision-location.py --business client-a \
  --label "Client A — Acme Dental" --phone "+18135551234" [--snapshot-id <id>]
```

**Dry-run by default** — prints the request and exits without calling the API. Add
`--confirm` to actually create the sub-account. **This is a real, possibly billable write
against production GHL — always confirm with the user before passing `--confirm`, never
infer it from context.** GHL's create-sub-account API reportedly needs an agency plan that allows it; a 401/403 here
usually means the plan tier.

A freshly created location has **no Private Integration Token yet** — it exists in GHL
but nothing can authenticate to it until the manual UI step below happens.
Such a profile shows in `ghl profiles list` but has no `api_key`, so any command against it fails
with `ProfileError: Profile '<name>' has no api_key set.` — that's expected, not a bug. `rollup` (below) skips such profiles gracefully instead of
erroring.

GHL's API **cannot mint a Private Integration Token for a location it just created** —
PITs exist only via the GHL UI. So provisioning is two steps: the script creates the
Location and prints its ID; a human then creates the PIT in GHL UI → Settings → Private
Integrations, and runs `ghl profiles add` with it. Don't skip this and don't try to
automate around it — there is no API for it.

### Cross-client rollups

Opportunities/Pipelines are inherently **location-scoped** in GHL — there is no
agency-level pipeline. `ghl rollup opportunities --business client-a` answers "all open
Client A opportunities" by looping every profile tagged with that business bucket and
merging — the same aggregation `profiles/registry.json` exists to make possible.

```bash
ghl rollup opportunities --business client-a [--status open] [--limit 100]
```

Each returned opportunity gets a `_profile` field naming which sub-account it came from.
A profile in the bucket with no `api_key` yet (e.g. right after `provision-location.py`,
before the manual PIT step) is skipped, not fatal — check the `skipped` list in the output
for the reason. Only `opportunities` is rolled up today; extend the same pattern
(`list_profiles(business=)` → per-profile env swap → merge, restoring `os.environ`
afterward) for other location-scoped resources if asked.

## Verifying the install

```bash
$GHL_MCP_HOME/verify.sh            # read-only, one command per group
$GHL_MCP_HOME/verify.sh --verbose  # also show sample output
```

Exit codes: `0` all pass · `1` real failure · `2` credentials missing ·
`3` token valid but missing scopes.
`SCOPE` = token valid, scope not ticked at creation (fix in GHL UI).
`SKIP (HTTP 403/404)` = that GHL product isn't enabled on the sub-account.
Neither is a CLI bug.

## Output contract (important for agents)

- `--json` / `json_output=true` returns JSON on **both** success and failure.
- Failures emit `{"ok": false, "error": {"message": ..., "status": ..., "type": ...}}`
  on **stderr** and exit **non-zero**.
- Without `--json`, errors are prose (`API Error (401): ...`).
- `error.type` is `"api_error"` (with an HTTP `status`) for API failures, or
  `"GHLConfigError"` when credentials are missing/placeholder — check this to tell
  "not configured" apart from "the call failed".
- **Always check the exit code.** Exit `0` = success, non-zero = failure.

## Usage — CLI

```bash
ghl --profile revenue-partners --json contacts list --limit 50
ghl contacts search "john"
ghl contacts create --email lead@co.com --first-name Jane --last-name Smith --tag hot-lead
ghl --json opportunities list --status open
ghl opportunities pipelines
ghl calendars slots <calendar_id> --start 2026-03-25 --end 2026-03-30
ghl conversations send <conversation_id> --type SMS --message "Thanks!"
ghl workflows list
ghl workflows enroll --contact-id <id> --workflow-id <id>
ghl locations get
ghl                       # no args → interactive REPL with autocomplete
```

`--json` is recommended for programmatic/agent use and pipes cleanly into `jq`. Omit
`--profile` to use `.env`'s default (currently `revenue-partners`).

## Usage — MCP tools

```
ghl_profiles()                                          # see what businesses/clients exist
ghl_catalog()                                            # see what's available
ghl_help(["contacts","create"])                         # exact flags
ghl(["contacts","list","--limit","5"], profile="revenue-partners")
ghl(["conversations","send","<id>","--type","SMS","--message","hi"], profile="client-a-acme")
```

**Note:** as of 2026-08-22 this MCP surface (`profile=` on `ghl()`, the `ghl_profiles()`
and `rollup` tools/commands, the updated `ghl_catalog()`) is **built and unit-tested but
not yet verified end-to-end through a live MCP session** — the running server process
loads `ghl_mcp_server.py` once at Claude Code startup and doesn't hot-reload, so it needs
a session restart (or MCP reconnect) before treating it as proven. Until then: `ghl()`'s
generic passthrough still works for *any* CLI subcommand including `rollup` (it just
forwards argv), but `profile=` on that call and the discovery tools (`ghl_profiles()`,
`ghl_catalog()` showing the new groups) will not work until restarted. The CLI
(`ghl --profile ...` / `ghl rollup ...` directly) always has current behavior since it
re-execs fresh on every call — prefer it if you're unsure whether a restart has happened
yet.

## Command groups

| Group | Key commands |
|-------|--------------|
| `contacts` | list, get, create, update, delete, search, add-tag, remove-tag |
| `opportunities` | list, get, create, update, delete, pipelines |
| `calendars` | list, get, slots, appointments, book, groups |
| `workflows` | list, enroll, remove, create\*, create-n8n\*, create-step |
| `conversations` | list, get, get-email, messages, send |
| `emails` | list-campaigns |
| `payments` | transactions, orders, invoices, create-invoice |
| `forms` | list, submissions |
| `social` | accounts, posts, create-post |
| `locations` | get, search, tags, custom-fields, custom-values |
| `documents` | list, templates, send, send-template |
| `profiles` | list, get, add, remove |
| `rollup` | opportunities (aggregate across every profile in a `--business` bucket) |

\* See the workflow-creation section below — needs `--experimental`.

## Commands that WRITE (confirm with the user first)

`contacts create/update/delete`, `contacts add-tag/remove-tag`,
`opportunities create/update/delete`, `calendars book`, `conversations send`
(**sends a real SMS/email to a real person**), `payments create-invoice`,
`social create-post` (**publishes publicly**), `workflows enroll/remove`,
`workflows create/create-n8n`, `documents send` / `send-template` (**sends a real
contract to a real recipient**).

Everything else in the table is read-only and safe to run freely.

## Workflow creation (experimental — unofficial internal API)

The public API is read-only for workflows (`workflows list`, plus `enroll`/`remove`).
Creating/updating workflows requires `--experimental`, which uses GHL's **unofficial**
internal API (`backend.leadconnectorhq.com`) authenticated with
`GHL_FIREBASE_REFRESH_TOKEN`.

**Surface this to the user before using it:**
- That Firebase token is the user's **entire GHL login** (full account access), not a
  scoped key. Use it **only on the user's own agency account — never a client's**.
- To provision workflows for client sub-accounts, prefer **Snapshots** (build once in
  the UI, sub-accounts inherit it) — no token, no internal API.
- The internal API has no SLA and may change/break without notice. Workflows are
  created as draft. The CLI prints a one-time warning on use
  (`GHL_SUPPRESS_INTERNAL_WARNING=1` to silence).

The scripts in `builders/` write live workflows through this internal API. Do not run
them casually — only on explicit request, and only against the user's own account.

## Agent notes

- Public API base: `https://services.leadconnectorhq.com`; version header auto-routed
  per endpoint by the CLI (`2021-07-28` default, `2021-04-15` for conversations and
  calendars).
- For name search use `contacts search <query>`.
- Precedence for which sub-account a command hits: `--profile`/`profile=` >
  `--location-id`/`GHL_LOCATION_ID` env var > `.env` default. Env vars set on the command
  line override `.env` (`GHL_LOCATION_ID=x ghl ...`).
- **Always resolve a profile explicitly for multi-client work.** Call `ghl_profiles()` /
  `ghl profiles list` first; never infer a profile name from a client's display name, and
  never assume the default (`.env`) profile is the client the user means.
- A 401 means the Private Integration Token is invalid/expired; a 403 usually means
  the token is missing that **scope** — scopes are chosen when the token is created,
  so a missing scope requires making a new token (see Agency vs location tokens, above).
- `/opportunities/search` is the one GHL endpoint that wants snake_case `location_id`
  instead of `locationId` — the CLI already handles this; only relevant if calling the
  raw API directly.
- `provision-location.py --confirm` creates a real, possibly billable GHL sub-account.
  Treat it like any other destructive/hard-to-reverse action: confirm with the user
  first, never run `--confirm` speculatively.
