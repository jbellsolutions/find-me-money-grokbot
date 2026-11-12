# Orgo docs mirror: INDEX

Captured 2026-11-11 from https://docs.orgo.ai (llms-full.txt split per page). REST base: https://www.orgo.ai/api . Auth: `Authorization: Bearer $ORGO_API_KEY` (keys start sk_live_).

## Top-level files

| File | Covers |
| --- | --- |
| mcp.md | Official MCP server (hosted https://www.orgo.ai/mcp + npm orgo-mcp-server): install for Claude Code/Desktop/Codex/Cursor, config env vars, every tool with params |
| sdk-python.md | Python SDK `orgo` 0.0.47 API surface |
| sdk-typescript.md | TypeScript SDK (orgo@1.0.22; orgo@2+ is the CLI) plus orgo-vnc, orgo-convex |
| openapi.json | Full OpenAPI 2.0.0 spec (113 operations) from docs.orgo.ai/api-reference/openapi.json |
| cli-manifest.json | Pre-existing manifest of local orgo CLI v2.3.0 (untouched) |
| site/llms.txt | Page index as published |

## Site pages (one file per docs page)

| File | Page title |
| --- | --- |
| site/general/introduction.md | Introduction (/introduction) |
| site/general/quickstart.md | Quickstart (/quickstart) |
| site/guides/get-started-dashboard.md | Dashboard (/guides/get-started-dashboard) |
| site/general/for-agents.md | For agents (/for-agents) |
| site/guides/agent-signup.md | Agent signups (/guides/agent-signup) |
| site/guides/cli.md | CLI (/guides/cli) |
| site/guides/mcp.md | MCP (/guides/mcp) |
| site/guides/skill.md | Claude Code skill (/guides/skill) |
| site/guides/troubleshooting.md | Troubleshooting (/guides/troubleshooting) |
| site/guides/computer-settings.md | Computer settings (/guides/computer-settings) |
| site/guides/ssh.md | SSH (/guides/ssh) |
| site/guides/public-urls.md | Public URLs (/guides/public-urls) |
| site/guides/connectors.md | Connectors (/guides/connectors) |
| site/guides/workflows.md | Workflows (/guides/workflows) |
| site/guides/workspaces-and-clients.md | Workspaces and clients (/guides/workspaces-and-clients) |
| site/guides/computer-ends.md | End times (/guides/computer-ends) |
| site/guides/models.md | Models (/guides/models) |
| site/guides/bring-your-own-key.md | Bring your own key (/guides/bring-your-own-key) |
| site/guides/browser-networking.md | Browser networking (/guides/browser-networking) |
| site/guides/residential-blocked-sites.md | Sites blocked on a residential IP (/guides/residential-blocked-sites) |
| site/guides/instance-identity.md | Identity tokens (/guides/instance-identity) |
| site/guides/embed-vms.md | Embedding (/guides/embed-vms) |
| site/guides/memory.md | Memory (/guides/memory) |
| site/guides/invoicing.md | Invoicing (/guides/invoicing) |
| site/guides/billing.md | Billing (/guides/billing) |
| site/guides/pricing.md | Pricing (/guides/pricing) |
| site/guides/instance-types.md | Computer sizes (/guides/instance-types) |
| site/guides/account-limits.md | Limits (/guides/account-limits) |
| site/guides/scaling.md | Scaling (/guides/scaling) |
| site/guides/templates/introduction.md | Templates (/guides/templates/introduction) |
| site/guides/templates/quickstart.md | Templates quickstart (/guides/templates/quickstart) |
| site/guides/templates/schema.md | Template schema (/guides/templates/schema) |
| site/guides/templates/secrets.md | Secrets (/guides/templates/secrets) |
| site/guides/templates/triggers.md | Triggers (/guides/templates/triggers) |
| site/guides/templates/examples.md | Examples (/guides/templates/examples) |
| site/guides/openclaw.md | OpenClaw (/guides/openclaw) |
| site/guides/hermes.md | Hermes Agent (/guides/hermes) |
| site/guides/latitude.md | Latitude (/guides/latitude) |
| site/guides/claude-computer-use.md | Claude Computer Use (/guides/claude-computer-use) |
| site/guides/openai-computer-use.md | OpenAI Computer Use (/guides/openai-computer-use) |
| site/guides/gemini-computer-use.md | Gemini Computer Use (/guides/gemini-computer-use) |
| site/guides/agent-s2.md | Agent S3 (/guides/agent-s2) |
| site/guides/migrations/overview.md | Compare platforms (/guides/migrations/overview) |
| site/guides/migrations/fly-io.md | Migrate from Fly.io (/guides/migrations/fly-io) |
| site/guides/migrations/digitalocean.md | Migrate from DigitalOcean (/guides/migrations/digitalocean) |
| site/guides/migrations/hetzner.md | Migrate from Hetzner (/guides/migrations/hetzner) |
| site/guides/migrate.md | Migrate from a VPS (/guides/migrate) |
| site/api-reference/introduction.md | API reference (/api-reference/introduction) |
| site/api-reference/authentication.md | Authentication (/api-reference/authentication) |
| site/api-reference/api-keys/permissions.md | Key permissions (/api-reference/api-keys/permissions) |
| site/api-reference/api-keys/manage.md | Manage keys (/api-reference/api-keys/manage) |
| site/api-reference/api-keys/expiry-and-rotation.md | Expiry and rotation (/api-reference/api-keys/expiry-and-rotation) |
| site/api-reference/api-keys/computer-keys.md | Computer keys (/api-reference/api-keys/computer-keys) |
| site/api-reference/support/ask.md | Ask support (/api-reference/support/ask) |
| site/api-reference/account/capacity.md | Get capacity (/api-reference/account/capacity) |
| site/api-reference/account/add-capacity.md | Add capacity (/api-reference/account/add-capacity) |
| site/api-reference/account/reduce-capacity.md | Reduce capacity (/api-reference/account/reduce-capacity) |
| site/api-reference/account/residential-data.md | Get residential data (/api-reference/account/residential-data) |
| site/api-reference/account/buy-residential-data.md | Buy residential data (/api-reference/account/buy-residential-data) |
| site/api-reference/agents/signup.md | Sign up an agent (/api-reference/agents/signup) |
| site/api-reference/agents/get-claim.md | Get claim status (/api-reference/agents/get-claim) |
| site/api-reference/agents/refresh-claim.md | Refresh claim link (/api-reference/agents/refresh-claim) |
| site/api-reference/clients/list.md | List clients (/api-reference/clients/list) |
| site/api-reference/clients/create.md | Add client (/api-reference/clients/create) |
| site/api-reference/clients/get.md | Get client (/api-reference/clients/get) |
| site/api-reference/clients/update.md | Update client (/api-reference/clients/update) |
| site/api-reference/clients/close.md | Close client (/api-reference/clients/close) |
| site/api-reference/clients/replace-key.md | Replace client key (/api-reference/clients/replace-key) |
| site/api-reference/clients/transfer.md | Transfer client (/api-reference/clients/transfer) |
| site/api-reference/clients/withdraw-transfer.md | Withdraw transfer (/api-reference/clients/withdraw-transfer) |
| site/api-reference/clients/get-billing.md | Get billing (/api-reference/clients/get-billing) |
| site/api-reference/clients/send-payment-link.md | Bill a client (/api-reference/clients/send-payment-link) |
| site/api-reference/clients/update-billing.md | Change price (/api-reference/clients/update-billing) |
| site/api-reference/clients/stop-billing.md | Stop billing (/api-reference/clients/stop-billing) |
| site/api-reference/clients/resend-payment-link.md | Resend payment link (/api-reference/clients/resend-payment-link) |
| site/api-reference/clients/list-payments.md | List payments (/api-reference/clients/list-payments) |
| site/api-reference/clients/refund-payment.md | Refund payment (/api-reference/clients/refund-payment) |
| site/api-reference/chat/completions.md | Create chat completion (/api-reference/chat/completions) |
| site/api-reference/chat/threads.md | Threads (/api-reference/chat/threads) |
| site/api-reference/workspaces/create.md | Create workspace (/api-reference/workspaces/create) |
| site/api-reference/workspaces/list.md | List workspaces (/api-reference/workspaces/list) |
| site/api-reference/workspaces/get.md | Get workspace (/api-reference/workspaces/get) |
| site/api-reference/workspaces/delete.md | Delete workspace (/api-reference/workspaces/delete) |
| site/api-reference/computers/create.md | Create computer (/api-reference/computers/create) |
| site/api-reference/computers/get.md | Get computer (/api-reference/computers/get) |
| site/api-reference/computers/update.md | Update computer (/api-reference/computers/update) |
| site/api-reference/computers/extend.md | Extend computer (/api-reference/computers/extend) |
| site/api-reference/computers/clone.md | Clone computer (/api-reference/computers/clone) |
| site/api-reference/computers/fork.md | Fork computer (/api-reference/computers/fork) |
| site/api-reference/computers/move.md | Move computer (/api-reference/computers/move) |
| site/api-reference/computers/resize.md | Resize computer (/api-reference/computers/resize) |
| site/api-reference/computers/delete.md | Delete computer (/api-reference/computers/delete) |
| site/api-reference/computers/vnc-password.md | Get VNC password (/api-reference/computers/vnc-password) |
| site/api-reference/computers/ssh-get.md | Get SSH settings (/api-reference/computers/ssh-get) |
| site/api-reference/computers/ssh-enable.md | Turn on SSH (/api-reference/computers/ssh-enable) |
| site/api-reference/computers/ssh-disable.md | Turn off SSH (/api-reference/computers/ssh-disable) |
| site/api-reference/computers/residential-proxy-get.md | Get residential proxy (/api-reference/computers/residential-proxy-get) |
| site/api-reference/computers/residential-proxy.md | Set residential proxy (/api-reference/computers/residential-proxy) |
| site/api-reference/computers/webrtc.md | Set UDP video streaming (/api-reference/computers/webrtc) |
| site/api-reference/computers/auto-stop-get.md | Get sleep when idle (/api-reference/computers/auto-stop-get) |
| site/api-reference/computers/auto-stop.md | Set sleep when idle (/api-reference/computers/auto-stop) |
| site/api-reference/computers/health.md | Check health (/api-reference/computers/health) |
| site/api-reference/computers/heal.md | Heal computer (/api-reference/computers/heal) |
| site/api-reference/computers/sync-secrets.md | Apply secrets (/api-reference/computers/sync-secrets) |
| site/api-reference/secrets/create.md | Save secret (/api-reference/secrets/create) |
| site/api-reference/secrets/apply.md | Apply secrets in bulk (/api-reference/secrets/apply) |
| site/api-reference/public-urls/list.md | List public URLs (/api-reference/public-urls/list) |
| site/api-reference/public-urls/create.md | Create public URL (/api-reference/public-urls/create) |
| site/api-reference/public-urls/update.md | Update public URL (/api-reference/public-urls/update) |
| site/api-reference/public-urls/delete.md | Delete public URL (/api-reference/public-urls/delete) |
| site/api-reference/public-urls/password.md | Get public URL password (/api-reference/public-urls/password) |
| site/api-reference/computers/start.md | Start computer (/api-reference/computers/start) |
| site/api-reference/computers/stop.md | Stop computer (/api-reference/computers/stop) |
| site/api-reference/computers/restart.md | Restart computer (/api-reference/computers/restart) |
| site/api-reference/computers/suspend.md | Suspend computer (/api-reference/computers/suspend) |
| site/api-reference/computers/resume.md | Resume computer (/api-reference/computers/resume) |
| site/api-reference/computers/suspension.md | Get suspension (/api-reference/computers/suspension) |
| site/api-reference/computers/operation.md | Get operation (/api-reference/computers/operation) |
| site/api-reference/computers/screenshot.md | Take screenshot (/api-reference/computers/screenshot) |
| site/api-reference/computers/click.md | Click mouse (/api-reference/computers/click) |
| site/api-reference/computers/mouse-move.md | Move mouse (/api-reference/computers/mouse-move) |
| site/api-reference/computers/drag.md | Drag mouse (/api-reference/computers/drag) |
| site/api-reference/computers/type.md | Type text (/api-reference/computers/type) |
| site/api-reference/computers/key.md | Press key (/api-reference/computers/key) |
| site/api-reference/computers/scroll.md | Scroll (/api-reference/computers/scroll) |
| site/api-reference/computers/wait.md | Wait (/api-reference/computers/wait) |
| site/api-reference/computers/bash.md | Execute bash (/api-reference/computers/bash) |
| site/api-reference/computers/exec.md | Execute Python (/api-reference/computers/exec) |
| site/api-reference/computers/terminal.md | Terminal WebSocket (/api-reference/computers/terminal) |
| site/api-reference/computers/audio.md | Audio WebSocket (/api-reference/computers/audio) |
| site/api-reference/computers/events.md | Events WebSocket (/api-reference/computers/events) |
| site/api-reference/screens/list.md | List screens (/api-reference/screens/list) |
| site/api-reference/screens/create.md | Create screen (/api-reference/screens/create) |
| site/api-reference/screens/get.md | Get screen (/api-reference/screens/get) |
| site/api-reference/screens/resize.md | Resize screen (/api-reference/screens/resize) |
| site/api-reference/screens/delete.md | Destroy screen (/api-reference/screens/delete) |
| site/api-reference/files/upload.md | Upload file (/api-reference/files/upload) |
| site/api-reference/files/start-upload.md | Start large upload (/api-reference/files/start-upload) |
| site/api-reference/files/complete-upload.md | Complete large upload (/api-reference/files/complete-upload) |
| site/api-reference/files/export.md | Export file (/api-reference/files/export) |
| site/api-reference/files/list.md | List files (/api-reference/files/list) |
| site/api-reference/files/download.md | Download file (/api-reference/files/download) |
| site/api-reference/files/delete.md | Delete file (/api-reference/files/delete) |
| site/api-reference/templates/schema.md | Get template schema (/api-reference/templates/schema) |
| site/api-reference/templates/list.md | List templates (/api-reference/templates/list) |
| site/api-reference/templates/publish.md | Publish template (/api-reference/templates/publish) |
| site/api-reference/templates/validate.md | Validate template (/api-reference/templates/validate) |
| site/api-reference/templates/list-versions.md | List template versions (/api-reference/templates/list-versions) |
| site/api-reference/templates/get.md | Get template (/api-reference/templates/get) |
| site/api-reference/templates/delete.md | Delete template version (/api-reference/templates/delete) |
| site/api-reference/templates/build.md | Build template (/api-reference/templates/build) |
| site/api-reference/templates/build-status.md | Get build status (/api-reference/templates/build-status) |
| site/api-reference/templates/build-events.md | Stream build logs (/api-reference/templates/build-events) |
| site/api-reference/templates/list-curated.md | List curated templates (/api-reference/templates/list-curated) |
| site/api-reference/templates/test-run.md | Test-run template (/api-reference/templates/test-run) |
| site/api-reference/workflows/list.md | List workflows (/api-reference/workflows/list) |
| site/api-reference/workflows/create.md | Create workflow (/api-reference/workflows/create) |
| site/api-reference/workflows/get.md | Get workflow (/api-reference/workflows/get) |
| site/api-reference/workflows/replace.md | Replace steps (/api-reference/workflows/replace) |
| site/api-reference/workflows/update.md | Update workflow (/api-reference/workflows/update) |
| site/api-reference/workflows/delete.md | Delete workflow (/api-reference/workflows/delete) |
| site/api-reference/workflows/validate.md | Validate workflow (/api-reference/workflows/validate) |
| site/api-reference/workflows/start-run.md | Start run (/api-reference/workflows/start-run) |
| site/api-reference/workflows/list-runs.md | List runs (/api-reference/workflows/list-runs) |
| site/api-reference/workflows/get-run.md | Get run (/api-reference/workflows/get-run) |
| site/api-reference/workflows/stop-run.md | Stop run (/api-reference/workflows/stop-run) |
| site/api-reference/workflows/answer-run.md | Answer run (/api-reference/workflows/answer-run) |
| site/api-reference/workflows/events.md | Follow workflow (/api-reference/workflows/events) |

## Gaps

- Source repos for the Python SDK, orgo CLI/TS v1 SDK and orgo-mcp (OrgoAI/orgo-mcp, spencerkinney/orgo-cli) returned 404 via gh (private or moved). SDK/MCP references were derived from the published npm/PyPI artifacts, not GitHub source. Public OrgoAI repos exist: orgo-vnc, orgo-convex, orgo-hermes-connect, orgo-cua, bops; only READMEs of the first three were skimmed (summarized in sdk-typescript.md).
- No current official TypeScript REST SDK exists (orgo@2+ is CLI only); Python SDK 0.0.47 covers only a subset of the API (no start/stop/resize/clone/files/secrets). Use REST, CLI or MCP for the rest.
- Hermes-specific MCP config: no dedicated page; inferred from the Hermes guide and orgo-hermes-connect README.
- Workflow MCP tools are hosted-only, hand-written, and not in openapi.json; extra detail lives at https://www.orgo.ai/workflows.md (not fetched).
- Pages outside docs.orgo.ai (orgo.ai pricing page, dashboard, YouTube video) were not mirrored; pricing is covered by site/guides/pricing.md and billing.md. Images/screenshots in docs are not saved.
- Nothing behind sign-in was accessed; no API key was used, so live responses were not verified.
