# Sourced by every job. One workspace, one guard set, and the owner rule: a job writes to a live system
# only when context/owners.md moves that system to the bot AND its routine is `on`. Otherwise it runs dry.
WS=/workspace/find-me-money
G="python3 $WS/repo/skills/lead/fmm-guards/guards.py"
OG="python3 $WS/repo/guards/scripts/owner_guard.py"
export FMM_HOME=$WS/state BOT_HOME=$WS
# Intake values (FMM_HOSTS, NEVER_TOUCH, ids) load before preflight, which refuses without them.
[ -f $WS/.secrets/fmm.env ] && { set -a; . $WS/.secrets/fmm.env; set +a; }
$G preflight || exit $?
export PYTHONPATH=$WS/repo/engine/fcm/src:$WS/repo/engine/pinnacle-reply-agent FCM_CONFIG_DIR=$WS/repo/engine/fcm/config FCM_STATE_DIR=$WS/state/fcm FCM_VAULT_DIR=$WS/vault/fcm
# owns <system> <routine name>: exit 0 only when the bot owns the system's writes and the routine is on
owns() { $OG check "$1" --routine "$2" >/dev/null; }
# rbeat <role> '<line>' [k=v ...]: the role heartbeat the lead's watchdog reads (guards/scripts/beat.py)
rbeat() { local r="$1" l="$2"; shift 2; python3 $WS/repo/guards/scripts/beat.py write "$r" "$l" "$@" >/dev/null; }
