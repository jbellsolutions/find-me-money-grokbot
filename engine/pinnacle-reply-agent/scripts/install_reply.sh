#!/usr/bin/env bash
# Install (or update) the Reply Agent profile for the Hermes of the user running this script.
#   scripts/install_reply.sh
# Run it as the user Hermes runs as (on a computer where that's `hermes`: su - hermes -c '<repo>/scripts/install_reply.sh').
#
# It makes the Reply Agent its own virtualenv at $REPLY_HOME/venv (anthropic, mcp, psycopg), so the Hermes venv and the
# other profiles on the machine are never changed. Its crons ship paused, and desk writes stay off (REPLY_WRITE).
# Keys go in the profile's .env afterwards, never through this script: ANTHROPIC_API_KEY, RADAR_URL, RADAR_PASSWORD,
# for the other lanes CREATORS_DB_URL, HUB_URL, HUB_PASSWORD, FM_GHL_API_KEY, and for posting the REDDIT_* and
# YOUTUBE_* account keys. Posting itself stays off until REPLY_POST=on and REPLY_POST_PLATFORMS are set there.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
export REPLY_HOME="${REPLY_HOME:-/workspace/find-me-money/pinnacle-reply}"
NAME=pinnacle-reply-agent

PY=""
for candidate in "${REPLY_BASE_PY:-}" python3.13 python3.12 python3.11; do
  [ -n "$candidate" ] || continue
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    PY="$(command -v "$candidate")"; break
  fi
done
[ -n "$PY" ] || { echo "needs Python 3.11 or newer (set REPLY_BASE_PY)" >&2; exit 2; }

mkdir -p "$REPLY_HOME/state"
chmod 700 "$REPLY_HOME" "$REPLY_HOME/state"
if [ ! -x "$REPLY_HOME/venv/bin/python" ]; then
  "$PY" -m venv "$REPLY_HOME/venv"
fi
"$REPLY_HOME/venv/bin/python" -m pip install -q --upgrade pip
"$REPLY_HOME/venv/bin/python" -m pip install -q "anthropic==2.3.0" "mcp==2.3.0" "psycopg[binary]>=3.2"

# The package itself runs from this checkout (PYTHONPATH in the profile's MCP entry); check it imports and passes.
PYTHONPATH="$REPO" "$REPLY_HOME/venv/bin/python" -c "import pinnacle_reply.mcp_server" >/dev/null
PYTHONPATH="$REPO" "$REPLY_HOME/venv/bin/python" -m pinnacle_reply.cli check \
  "Equipment secures its own loan, so a down payment helps. I'm with Find Me Money Group. How long have you been in business?" \
  | grep -q '"passes": true'

python3 "$REPO/scripts/build_profiles.py" --profiles "$NAME" --reply-home "$REPLY_HOME" \
  --reply-python "$REPLY_HOME/venv/bin/python"

HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"
if [ -d "$HERMES_HOME_DIR/profiles/$NAME" ]; then
  hermes profile install "$REPO/build/profiles/$NAME" --name "$NAME" --force -y
else
  hermes profile install "$REPO/build/profiles/$NAME" --name "$NAME" --alias -y
fi
echo "installed $NAME (crons paused, REPLY_WRITE off). Next: its .env keys, then: hermes -p $NAME chat -q 'reply_status'"
