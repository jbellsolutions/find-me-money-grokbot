#!/usr/bin/env bash
# Put the Find Me Money worker on the Mac's Hermes profile, PAUSED. A live-computer change: Justin's yes first.
#
#   bash hermes-worker/install.sh            dry run: prints what it would do
#   bash hermes-worker/install.sh --go       backup, copy the worker, add one paused job to the find-me-money profile
#   bash hermes-worker/install.sh --remove   take the job and the worker folder off (the backup stays)
#
# Needs ORGO_API_KEY, MUSE_COMPUTER (the Mac) and the never-touch list (NEVER_TOUCH), like every Orgo call in this pack.
# It adds ONE job, fmm-worker-inbox (every 15 minutes, no model of its own: dispatch.py runs the lanes GrokBot asks for).
# It touches no other job, profile, SOUL or config, and turns nothing on.
# Note: the profile's own installer renders jobs.json from its table; a reinstall from there drops this job unless
# that table lists fmm-worker-inbox too. Re-run this installer after any reinstall.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ORGO="$HERE/../skills/worker/orgo-computer-use/scripts/orgo.py"
MODE="${1:-dry}"; C="${MUSE_COMPUTER:?set MUSE_COMPUTER}"
case "$MODE" in dry|--go|--remove) ;; *) echo "dry (no argument), --go or --remove" >&2; exit 2;; esac
REMOTE=$(cat <<'R'
set -euo pipefail; export PATH=$HOME/.local/bin:/opt/homebrew/bin:$PATH
P=$HOME/.hermes/profiles/find-me-money; J=$P/cron/jobs.json; W=$HOME/fmm-worker
[ -f "$J" ] || { echo "no find-me-money profile on this computer"; exit 3; }
B=$HOME/Backups/fmm-worker-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $B; chmod 700 $B; cp $J $B/jobs.json
mkdir -p $HOME/.fmm/grok/inbox $HOME/.fmm/grok/outbox $HOME/.fmm/grok/done $HOME/.fmm/groups
python3 - "$J" "$W" <<'PY'
import json, sys
j, w = sys.argv[1], sys.argv[2]; d = json.load(open(j))
d["jobs"] = [x for x in d["jobs"] if x["id"] != "fmm-worker-inbox"]
d["jobs"].append({"id": "fmm-worker-inbox", "name": "Worker: run GrokBot's work orders", "prompt": None, "skills": [], "skill": None,
  "model": None, "provider": None, "base_url": None, "script": "fmm-worker-inbox.sh", "no_agent": True, "context_from": None,
  "schedule": {"kind": "cron", "expr": "*/15 * * * *", "display": "*/15 * * * *"}, "schedule_display": "*/15 * * * *",
  "repeat": {"times": None, "completed": 0}, "enabled": False, "state": "paused",
  "paused_reason": "ships paused: turned on on Justin's yes", "deliver": "local", "enabled_toolsets": None, "workdir": w})
json.dump(d, open(j + ".tmp", "w"), indent=2); import os; os.replace(j + ".tmp", j)
print("jobs:", len(d["jobs"]), "worker job paused")
PY
mkdir -p $P/scripts
printf '#!/usr/bin/env bash\ncd "%s" && exec python3 dispatch.py run --max 4\n' "$W" > $P/scripts/fmm-worker-inbox.sh; chmod +x $P/scripts/fmm-worker-inbox.sh
python3 $W/dispatch.py selftest
hermes -p find-me-money cron list --all 2>&1 | grep -i "fmm-worker-inbox" || { echo "FAIL: the job does not show in cron list; restoring"; cp $B/jobs.json $J; exit 4; }
R
)
if [ "$MODE" = dry ]; then echo "would push $HERE to $C:~/fmm-worker, then run:"; echo "$REMOTE"; exit 0; fi
if [ "$MODE" = --remove ]; then
  python3 "$ORGO" bash "$C" 'J=$HOME/.hermes/profiles/find-me-money/cron/jobs.json; python3 -c "import json,sys;j=sys.argv[1];d=json.load(open(j));d[\"jobs\"]=[x for x in d[\"jobs\"] if x[\"id\"]!=\"fmm-worker-inbox\"];json.dump(d,open(j,\"w\"),indent=2)" $J; rm -rf $HOME/fmm-worker; echo removed'
  exit 0; fi
cp "$HERE/../skills/radar/lead-map/SKILL.md" "$HERE/lead-map.md"     # the worker's prompts read it next to dispatch.py
RH=$(python3 "$ORGO" bash "$C" 'echo $HOME' | tail -1); [ -n "$RH" ] || { echo "could not read the Mac's home folder" >&2; exit 1; }
python3 "$ORGO" push "$C" "$HERE" "$RH/fmm-worker"
python3 "$ORGO" bash "$C" "$REMOTE" --timeout 200
