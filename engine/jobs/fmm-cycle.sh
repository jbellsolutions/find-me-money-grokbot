#!/usr/bin/env bash
# File and draft: pull the Radar, draft and check (local ledger only). The CRM outbox goes to Pinnacle only when the bot owns pinnacle-ghl.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
RA="${REPLY_AGENT:-python3 -m pinnacle_reply.cli}"
out=$($RA cycle) || { echo "cycle failed"; exit 1; }
if owns pinnacle-ghl "File and draft"; then $RA ghl send >/dev/null || { echo "CRM outbox failed"; exit 1; }; crm=sent; else crm="held (live owns pinnacle-ghl)"; fi
found=$(printf '%s' "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("new", d.get("pulled", "?")))' 2>/dev/null || echo "?")
$G beat "cycle ok, CRM $crm" found="$found" --job fmm-cycle
rbeat sales "cycle ok, CRM $crm" found="$found"
echo "cycle ok, found $found, CRM $crm"
