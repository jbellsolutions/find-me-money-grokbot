Source: https://docs.orgo.ai/guides/mcp ; npm package `orgo-mcp-server` 1.1.1 (repo git+https://github.com/OrgoAI/orgo-mcp.git, not publicly readable via gh at time of capture; contents read from the npm tarball)

# Orgo MCP server

Official Orgo MCP. Two forms: hosted remote server (`https://www.orgo.ai/mcp`, OAuth or API key) and local stdio server (`npx -y orgo-mcp-server`, API key or `orgo login` credentials). Tools are generated from the OpenAPI spec (`https://docs.orgo.ai/api-reference/openapi.json`) at startup, one tool per operationId, named `orgo_<snake_case_operationId>` (e.g. createComputer -> `orgo_create_computer`). Path/query/body params are flattened into one argument list, e.g. `orgo_resize_computer({ id, ... })`.

Do not confuse with unrelated npm `orgo-mcp` (orgo-space, community management) or third-party repos (nickvasilescu/orgo-mcp, orgo-chrome-mcp).

## Install

Claude Code, hosted with OAuth (no key; browser consent, pick a workspace):
```bash
claude mcp add --transport http orgo https://www.orgo.ai/mcp
```
Claude Code, local with API key:
```bash
claude mcp add orgo -e ORGO_API_KEY=sk_live_... -- npx -y orgo-mcp-server
```
Hosted with an API key (clients that can set headers): URL `https://www.orgo.ai/mcp`, header `Authorization: Bearer $ORGO_API_KEY`. Optional pinning: header `X-Orgo-Default-Computer-Id`, or `?computer_id=` on the URL.

Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`; fully quit and relaunch):
```json
{ "mcpServers": { "orgo": { "command": "npx", "args": ["-y", "orgo-mcp-server"], "env": { "ORGO_API_KEY": "sk_live_..." } } } }
```
Codex: `codex mcp add orgo --url https://www.orgo.ai/mcp && codex mcp login orgo` (hosted) or `codex mcp add orgo --env ORGO_API_KEY=sk_live_... -- npx -y orgo-mcp-server` (local).
Cursor `~/.cursor/mcp.json` and VS Code `.vscode/mcp.json` (top-level key `servers`, `type: stdio`): same command/args/env; see site/guides/mcp.md.
Windows: wrap as `"command":"cmd","args":["/c","npx","-y","orgo-mcp-server"]`.

Hermes: no Hermes-specific MCP page was found in the docs. Hermes Agent reads MCP servers from its `config.yaml`; Orgo's Hermes template wires an `orgo.ai/mcp/computers/<id>` MCP entry there (per the OrgoAI/orgo-hermes-connect README). Use the same stdio command or the hosted URL. See site/guides/hermes.md.

If you have run `orgo login` (CLI), the server reads `~/.orgo/credentials.json` and the `env` block can be dropped.

## Config (local server env vars)

`ORGO_API_KEY` (falls back to ~/.orgo/credentials.json), `ORGO_READ_ONLY` (register only GET tools), `ORGO_TAGS` (comma list of spec tags, e.g. "Computers,Computer Actions"), `ORGO_DEFAULT_COMPUTER_ID` (lets action tools omit `id`), `ORGO_PROFILE`, `ORGO_API_BASE_URL` (default https://www.orgo.ai), `ORGO_TIMEOUT_MS` (120000), `ORGO_RETRIES` (2; only idempotent GET/PUT/DELETE retry), `ORGO_RAW`, `ORGO_SPEC_URL`, `ORGO_SPEC_MAX_AGE_MS`, `XDG_CACHE_HOME`.

## Notes

- Screenshot: `orgo_get_screenshot` returns a link by default; pass `response_format: "base64"` for an image (hosted OAuth always returns an image).
- OAuth sign-in sees a reviewed subset only: workspace read, computers create/manage, screenshot/mouse/keyboard/bash/python, screens, file list/export/download/delete and `orgo_start_file_upload`/`orgo_complete_file_upload`. NOT offered: Templates, Clients, Account, Chat, Support, workspace create/update/delete, suspend/resume, `orgo_upload_file`, `orgo_get_vnc_password`, `orgo_apply_computer_secrets`, `orgo_move_computer`. Use an API key for those.
- With an API key over the hosted URL, `orgo_upload_file` (reads a local file) and `orgo_agent_signup` are refused.
- `orgo_execute_bash`/`orgo_mouse_click` are never retried. Keep client tool confirmation on; consider a workspace-scoped key or `ORGO_READ_ONLY=true`.
- Bundled npm 1.1.1 snapshot has only 43 tools (older spec); the live spec has 113 operations (workflow operations have no operationId in the spec; the hosted server serves hand-written `orgo_*_workflow*` tools, listed below).
- Revoke OAuth grants at https://www.orgo.ai/settings/security#connected-apps.
- Diagnostic: `ORGO_API_KEY=... npx -y orgo-mcp-server` prints `[orgo-mcp] <n> tools from Orgo API 2.0.0 ... -> https://www.orgo.ai/api` on stderr.

## Tools (generated from live spec 2.0.0)

Every tool below maps to the REST call shown; see site/api-reference/ for response schemas. Body fields of YAML endpoints appear as `<application/yaml>`.

### Templates

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_get_template_schema` | GET /template-schema | - | Get template schema |
| `orgo_list_templates` | GET /templates | namespace | List templates |
| `orgo_publish_template` | POST /templates | auto_build, force, <application/yaml> | Publish template |
| `orgo_validate_template` | POST /templates/validate | <application/yaml> | Validate template |
| `orgo_list_curated_templates` | GET /templates/global | - | List curated templates |
| `orgo_list_curated_template_versions` | GET /templates/global/{namespace}/{name} | namespace*, name* | List curated template versions |
| `orgo_list_template_versions` | GET /templates/{namespace}/{name} | namespace*, name* | List template versions |
| `orgo_get_template` | GET /templates/{namespace}/{name}/{version} | namespace*, name*, version* | Get template |
| `orgo_delete_template` | DELETE /templates/{namespace}/{name}/{version} | namespace*, name*, version* | Delete template version |
| `orgo_build_template` | POST /templates/{namespace}/{name}/{version}/build | namespace*, name*, version*, tier, launch, project | Build template |
| `orgo_get_build_status` | GET /templates/{namespace}/{name}/{version}/build | namespace*, name*, version* | Get build status |
| `orgo_cancel_build` | DELETE /templates/{namespace}/{name}/{version}/build | namespace*, name*, version* | Cancel build |
| `orgo_stream_build_events` | GET /templates/{namespace}/{name}/{version}/build/events | namespace*, name*, version* | Stream build logs |
| `orgo_test_run_template` | POST /templates/run | ref* | Test-run a template |
| `orgo_stop_template_run` | DELETE /templates/run | id* | Stop a test-run |

### Workspaces

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_list_workspaces` | GET /workspaces | - | List workspaces |
| `orgo_create_workspace` | POST /workspaces | name*, icon_url, status | Create workspace |
| `orgo_get_workspace` | GET /workspaces/{id} | id* | Get workspace |
| `orgo_update_workspace` | PATCH /workspaces/{id} | id*, name, icon_url, status | Update workspace |
| `orgo_delete_workspace` | POST /workspaces/{id}/delete | id* | Delete workspace |

### Computers

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_create_computer` | POST /computers | Idempotency-Key, workspace_id*, name*, os, cpu, ram, disk_size_gb, resolution, gpu, template_ref, billing_mode, ends_in_hours, on_end, compute_quote_id, compute_request_id | Create computer |
| `orgo_get_computer` | GET /computers/{id} | id* | Get computer |
| `orgo_delete_computer` | DELETE /computers/{id} | id* | Delete computer |
| `orgo_update_computer` | PATCH /computers/{id} | id*, name, bot_mascot, on_end, ends_at, ends_in_hours | Update computer |
| `orgo_extend_computer` | POST /computers/{id}/extend | id*, Idempotency-Key, hours*, idempotency_key | Extend computer |
| `orgo_clone_computer` | POST /computers/{id}/clone | id*, name | Clone computer |
| `orgo_fork_computer` | POST /computers/{id}/fork | id* | Fork computer |
| `orgo_resize_computer` | PATCH /computers/{id}/resize | id*, vcpus, mem_gb, disk_size_gb, bandwidth_limit_mbps, auto_stop_minutes, size | Resize computer |
| `orgo_get_resize_limits` | GET /computers/{id}/resize | id* | Get resize limits |
| `orgo_move_computer` | PATCH /computers/{id}/move | id*, workspace_id* | Move computer to another workspace |
| `orgo_get_vnc_password` | GET /computers/{id}/vnc-password | id* | Get VNC password |
| `orgo_apply_computer_secrets` | POST /computers/{id}/secrets/sync | id*, names*, wake, remove, dry_run | Apply secrets to a computer |
| `orgo_apply_secrets_to_computers` | POST /secrets/apply | names*, computer_ids, workspace_id, remove, dry_run | Apply secrets to many computers |
| `orgo_get_computer_ssh` | GET /computers/{id}/ssh | id* | Get SSH settings |
| `orgo_enable_computer_ssh` | POST /computers/{id}/ssh | id*, public_key* | Turn on SSH |
| `orgo_disable_computer_ssh` | DELETE /computers/{id}/ssh | id* | Turn off SSH |
| `orgo_get_residential_proxy` | GET /computers/{id}/residential-proxy | id*, check | Get residential proxy |
| `orgo_set_residential_proxy` | POST /computers/{id}/residential-proxy | id*, enabled*, new_ip, country | Set residential proxy |
| `orgo_set_computer_udp_streaming` | POST /computers/{id}/webrtc | id*, enabled* | Set UDP video streaming |
| `orgo_get_computer_auto_stop` | GET /computers/{id}/auto-stop | id* | Get sleep when idle |
| `orgo_set_computer_auto_stop` | PATCH /computers/{id}/auto-stop | id*, auto_stop_minutes* | Set sleep when idle |

### Computer Lifecycle

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_start_computer` | POST /computers/{id}/start | id*, async, Prefer, async, on_end, ends_in_hours, ends_at, billing_mode | Start computer |
| `orgo_stop_computer` | POST /computers/{id}/stop | id*, async, Prefer, async | Stop computer |
| `orgo_restart_computer` | POST /computers/{id}/restart | id*, clear_disk | Restart computer |
| `orgo_suspend_computer` | POST /computers/{id}/suspend | id* | Suspend computer |
| `orgo_resume_computer` | POST /computers/{id}/resume | id*, on_end, ends_in_hours, ends_at | Resume computer |
| `orgo_get_computer_suspension` | GET /computers/{id}/suspension | id*, after | Get suspension |
| `orgo_get_computer_operation` | GET /computers/{id}/operations/{operationId} | id*, operationId* | Get computer operation |

### Computer Actions

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_get_screenshot` | GET /computers/{id}/screenshot | id*, screen, response_format, format, quality, scale | Take screenshot |
| `orgo_mouse_click` | POST /computers/{id}/click | id*, screen, x*, y*, button, double, modifiers, repeat | Click mouse |
| `orgo_mouse_move` | POST /computers/{id}/mouse-move | id*, screen, x*, y* | Move mouse |
| `orgo_mouse_drag` | POST /computers/{id}/drag | id*, screen, start_x*, start_y*, end_x*, end_y* | Drag mouse |
| `orgo_type_text` | POST /computers/{id}/type | id*, screen, text*, delay_ms | Type text |
| `orgo_press_key` | POST /computers/{id}/key | id*, screen, key* | Press key |
| `orgo_scroll` | POST /computers/{id}/scroll | id*, screen, x*, y*, direction, amount | Scroll |
| `orgo_wait` | POST /computers/{id}/wait | id*, seconds*, duration | Wait |
| `orgo_execute_bash` | POST /computers/{id}/bash | id*, screen, command*, timeout | Execute bash |
| `orgo_execute_python` | POST /computers/{id}/exec | id*, code*, timeout | Execute Python |

### Files

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_upload_file` | POST /files/upload | file*, desktopId, destPath, workspaceId* | Upload file |
| `orgo_start_file_upload` | POST /files/uploads | desktopId*, filename*, size_bytes*, destPath | Start file upload |
| `orgo_complete_file_upload` | POST /files/uploads/complete | desktopId*, upload_token* | Complete file upload |
| `orgo_list_files` | GET /files | workspaceId*, desktopId | List files |
| `orgo_export_file` | POST /files/export | desktopId*, path* | Export file |
| `orgo_download_file` | GET /files/download | id, fileId | Download file |
| `orgo_delete_file` | DELETE /files/delete | id, fileId | Delete file |

### Screens

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_list_screens` | GET /computers/{id}/screens | id* | List screens |
| `orgo_create_screen` | POST /computers/{id}/screens | id*, width, height | Create a screen |
| `orgo_get_screen` | GET /computers/{id}/screens/{screenId} | id*, screenId* | Get a screen |
| `orgo_resize_screen` | PATCH /computers/{id}/screens/{screenId} | id*, screenId*, width*, height* | Resize a screen |
| `orgo_destroy_screen` | DELETE /computers/{id}/screens/{screenId} | id*, screenId* | Destroy a screen |

### Account

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_get_account_capacity` | GET /account/capacity | - | Get account capacity |
| `orgo_add_account_capacity` | POST /account/capacity | Idempotency-Key, <application/json> | Add capacity |
| `orgo_reduce_account_capacity` | PATCH /account/capacity | added_computers* | Reduce capacity |
| `orgo_get_residential_data` | GET /billing/residential-data | - | Get residential data |
| `orgo_buy_residential_data` | POST /billing/residential-data/buy | Idempotency-Key*, gb*, expected_price_cents*, desktop_id | Buy residential data |

### Clients

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_list_clients` | GET /v1/accounts | search, status, limit, before | List clients |
| `orgo_create_client` | POST /v1/accounts | name, external_id, max_computers, monthly_ai_cap_usd | Add a client |
| `orgo_get_client` | GET /v1/accounts/{id} | id* | Get client |
| `orgo_update_client` | PATCH /v1/accounts/{id} | id*, name, max_computers, monthly_ai_cap_usd | Update client |
| `orgo_close_client` | DELETE /v1/accounts/{id} | id* | Close client |
| `orgo_replace_client_key` | POST /v1/accounts/{id}/key | id* | Replace a client’s key |
| `orgo_transfer_client` | POST /v1/accounts/{id}/transfer | id*, email* | Transfer a client |
| `orgo_withdraw_client_transfer` | DELETE /v1/accounts/{id}/transfer | id* | Withdraw a transfer |
| `orgo_get_client_billing` | GET /v1/accounts/{id}/billing | id* | Get billing |
| `orgo_send_client_payment_link` | POST /v1/accounts/{id}/billing | id*, email*, price_usd*, ai_usd, setup_fee_usd | Bill a client |
| `orgo_update_client_billing` | PATCH /v1/accounts/{id}/billing | id*, price_usd, ai_usd | Change price |
| `orgo_stop_client_billing` | DELETE /v1/accounts/{id}/billing | id*, now | Stop billing |
| `orgo_resend_client_payment_link` | POST /v1/accounts/{id}/billing/resend | id* | Resend payment link |
| `orgo_list_client_payments` | GET /v1/accounts/{id}/billing/payments | id* | List payments |
| `orgo_refund_client_payment` | POST /v1/accounts/{id}/billing/payments/{payment_id}/refund | id*, payment_id* | Refund a payment |

### Chat

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_create_chat_completion` | POST /v1/chat/completions | computer_id*, messages*, model, stream, max_steps, thread_id | Create chat completion |

### Agent accounts

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_agent_signup` | POST /v1/agents | Idempotency-Key, name, contact_email | Sign up an agent |
| `orgo_get_agent_claim_status` | GET /v1/agents/claim | - | Get claim status |
| `orgo_refresh_agent_claim_link` | POST /v1/agents/claim | - | Refresh the claim link |

### Support

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_ask_support` | POST /v1/support/ask | question, messages | Ask Orgo’s support agent |

### Public URLs

| Tool | Method + path | Params (* = required) | Summary |
| --- | --- | --- | --- |
| `orgo_list_public_urls` | GET /computers/{id}/public-urls | id* | List public URLs |
| `orgo_create_public_url` | POST /computers/{id}/public-urls | id*, port*, name, label | Create public URL |
| `orgo_update_public_url` | PATCH /computers/{id}/public-urls/{urlId} | id*, urlId*, port, password | Update public URL |
| `orgo_delete_public_url` | DELETE /computers/{id}/public-urls/{urlId} | id*, urlId* | Delete public URL |
| `orgo_get_public_url_password` | GET /computers/{id}/public-urls/{urlId}/password | id*, urlId* | Get public URL password |

### Workflows (hosted server only; hand-written tools)

`orgo_list_workflows`, `orgo_create_workflow` (describe or lines), `orgo_get_workflow`, `orgo_save_workflow` (whole `lines`, `if_match` = version read), `orgo_update_workflow` (on, name, settings, computer, time_zone), `orgo_delete_workflow`, `orgo_validate_workflow`, `orgo_run_workflow` (inputs), `orgo_list_workflow_runs`, `orgo_get_workflow_run`, `orgo_stop_workflow_run`, `orgo_answer_workflow_run` (only the person says go), `orgo_list_workflow_computers`, `orgo_workflow_catalog`, `orgo_connect_app`. Line format: https://www.orgo.ai/workflows.md. See site/guides/workflows.md.

Note: the docs MCP page also lists `orgo_get_computer_suspension`, `orgo_get_resize_limits`, etc.; these correspond to the rows above. Public URLs, SSH, auto-stop, residential proxy, webrtc, extend and secrets-sync operations are in the spec; whether the server exposes them depends on the reviewed list (OAuth) or the spec (API key).
