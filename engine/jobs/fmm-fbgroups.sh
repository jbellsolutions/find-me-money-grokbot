#!/usr/bin/env bash
# Facebook groups lane through One API. The live Hermes lane mines these 785 groups nightly, so this runs only when the bot owns fbgroups-lane.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
if ! owns fbgroups-lane "Mine Facebook groups"; then rbeat radar "fbgroups skipped: live owns it"; $G beat "fbgroups skipped: live owns fbgroups-lane" --job fmm-fbgroups; echo "skipped: live owns fbgroups-lane"; exit 0; fi
mkdir -p $WS/state/miner && cd $WS/state/miner || exit 1
[ -f fb-groups-all.txt ] || { echo "no fb-groups-all.txt in state/miner: ask Justin for the group list"; exit 1; }
python3 $WS/repo/engine/fbgroups_miner.py --groups fb-groups-all.txt --pages 2 --max-groups 785 --state fbgroups-state.json --go 2>&1 | tail -4
