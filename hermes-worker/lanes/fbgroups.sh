#!/usr/bin/env bash
# One theme's Facebook groups through One API, graded, report only (no Radar import: the live lane owns imports).
#   fbgroups.sh <theme> <max_groups> <out.jsonl>
# The group lists are private: ~/.fmm/groups/<theme>.txt, given at intake, never in the public pack.
set -uo pipefail
THEME="$1"; MAX="$2"; OUT="$3"; HERE="$(cd "$(dirname "$0")" && pwd)"
LIST="$HOME/.fmm/groups/$THEME.txt"
[ -f "$LIST" ] || { echo "{\"blocked\": \"no group list for theme $THEME (intake)\"}" > "$OUT"; exit 0; }
MINER="$HOME/.fmm/miner/fbgroups_miner.py"; [ -f "$MINER" ] || MINER="$HERE/../../engine/fbgroups_miner.py"
STATE="$HOME/.fmm/grok/state-fbgroups-$THEME.json"
python3 "$MINER" --groups "$LIST" --pages 1 --max-groups "$MAX" --days 3 --state "$STATE" > "$OUT.log" 2>&1
rc=$?
python3 - "$STATE" "$OUT" <<'PY'
import json, sys
try: s = json.load(open(sys.argv[1]))
except Exception: s = {}
open(sys.argv[2], "w").write(json.dumps({"theme_state": {k: (v if not isinstance(v, (list, dict)) else len(v)) for k, v in s.items()}}) + "\n")
PY
exit $rc
