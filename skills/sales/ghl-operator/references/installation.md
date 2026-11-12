# Package location

For one-command installs, use `ghl` or `~/.local/bin/ghl`. The installer prints the
absolute CLI path too. For native plugin installs, the plugin root is two directories
above the skill directory. Run `bash <plugin-root>/scripts/run-hub.sh ...` there;
the first call prepares its persistent Python runtime automatically.

For a normal source checkout, use `./ghl` at the repository root. Use `ghl hub connect`
to save credentials through a hidden terminal prompt. Existing `GHL_API_KEY`,
`GHL_LOCATION_ID` and explicit `--env-file` profiles are supported. Installing a
plugin does not authorize launching campaigns or changing live GHL data.

For installation or missing setup, use the repository's `INSTALL-AGENT.md` protocol:
run `--preflight`, ask for missing prerequisites/choices before installing, and use
secure secret entry or a hidden terminal prompt. Never request tokens in chat.
Choose `--docs-only` only with the user's explicit preference. For dashboard work,
check browser/Orgo connectivity and GHL login before starting the task.

Hermes one-command setup installs skills and merges MCP configuration directly;
portable plugin-manager support is optional. Preserve `HERMES_HOME`. An existing
protected tenant file can be selected with `--credentials-file /secure/tenant.env`;
0600 is correct and does not require execute permission. The Orgo Hermes CLI at
`/opt/hermes/.venv/bin/hermes` is automatically detected outside PATH.
