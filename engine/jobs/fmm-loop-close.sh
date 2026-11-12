#!/usr/bin/env bash
# Loop close: list every open loop from the bot's own ledger, write the vault note. Reads only.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
RA="${REPLY_AGENT:-python3 -m pinnacle_reply.cli}"
$RA loops --markdown || exit 1
$RA vault >/dev/null || echo "vault write failed"
$G beat "loop close ok" --job fmm-loop-close; rbeat sales "loop close ok"
