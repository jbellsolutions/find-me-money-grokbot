#!/usr/bin/env bash
# Counts only, no model. Reads the bot's own ledger.
set -euo pipefail
. "$(dirname "$0")/_common.sh"
exec python3 $WS/repo/engine/scorecard.py --ledger $WS/pinnacle-reply/state/ledger.sqlite --env $WS/.secrets/fmm.env --vault $WS/vault
