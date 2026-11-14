#!/bin/sh
# Install this skill. Usage:
#   ./install.sh claude            -> /workspace/find-me-money/repo/skills/worker/orgo-computer-use
#   ./install.sh hermes [profile]  -> ~/.hermes/skills/orgo-computer-use (or a profile's skills)
#   ./install.sh <dir>             -> <dir>/orgo-computer-use (GrokBot /workspace, any agent)
set -e
SRC=$(cd "$(dirname "$0")" && pwd)
case "${1:-claude}" in
  claude) DEST="$HOME/.claude/skills" ;;
  hermes) H="${HERMES_HOME:-$HOME/.hermes}"; if [ -n "$2" ]; then DEST="$H/profiles/$2/skills"; else DEST="$H/skills"; fi ;;
  *) DEST="$1" ;;
esac
mkdir -p "$DEST/orgo-computer-use"
cp -R "$SRC/SKILL.md" "$SRC/scripts" "$SRC/references" "$SRC/docs" "$DEST/orgo-computer-use/"
chmod +x "$DEST/orgo-computer-use/scripts/orgo.py"
echo "installed: $DEST/orgo-computer-use"
echo "next: export ORGO_API_KEY=... (workspace-scoped), then: python3 $DEST/orgo-computer-use/scripts/orgo.py list"
