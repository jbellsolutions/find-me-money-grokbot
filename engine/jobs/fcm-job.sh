#!/usr/bin/env bash
# One fcm step. Usage: fcm-job.sh <step> "<routine name>"
#   sweep   leads sync + handoffs propose     (Applications)
#   triage  sales triage + suppress-sync      (Read answers)
#   day     the day's open loops              (Day check)
#   watch   handoffs watch + outbox resume    (Handoff watch)
# --apply (writes to Pinnacle and the Hub) only when the bot owns pinnacle-ghl and lending-hub and the routine is on. Otherwise dry.
set -uo pipefail
. "$(dirname "$0")/_common.sh"
STEP="$1"; ROUTINE="$2"; A=""; mode="dry (live owns the writes)"
if owns pinnacle-ghl "$ROUTINE" && owns lending-hub "$ROUTINE"; then A="--apply"; mode=apply; fi
F="python3 -m fcm.cli"
case "$STEP" in
  sweep)  $F leads sync $A && $F handoffs propose $A ;;
  triage) $F sales triage $A; owns cold-email-sender "$ROUTINE" && $F sales suppress-sync ;;
  day)    $F day $A ;;
  watch)  $F handoffs watch $A; [ -n "$A" ] && $F outbox resume ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
rc=$?
$G beat "fcm $STEP $mode rc=$rc" --job "fcm-$STEP"
ROLE=sales; [ "$STEP" = watch ] && ROLE=partners; rbeat $ROLE "fcm $STEP $mode rc=$rc"
echo "fcm $STEP: $mode, exit $rc"; exit $rc
