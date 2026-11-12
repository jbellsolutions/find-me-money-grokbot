#!/usr/bin/env bash
# Install the usage-saver extras with pinned versions. Safe to run twice.
# Every script works without these (plainer fallbacks); these make them better.
# Free, open-source, no keys, nothing sent anywhere.
set -u
PY=${PYTHON:-python3}
PKGS="trafilatura==2.3.1 duckdb==2.0.0 pypdf==7.0.1 tenacity==9.2.1 pydantic==2.14.3"
echo "usage-saver: installing $PKGS"
if ! $PY -m pip install --user --quiet $PKGS 2>/dev/null; then
  $PY -m pip install --user --quiet --break-system-packages $PKGS || echo "usage-saver: pip install failed; scripts will use their fallbacks"
fi
for t in jq rg; do
  if command -v $t >/dev/null; then echo "usage-saver: $t present"; else
    echo "usage-saver: $t missing (optional). Install with your package manager if allowed: apt-get install -y ${t/rg/ripgrep} or brew install ${t/rg/ripgrep}"
  fi
done
$PY - <<'EOF'
import importlib
for m in ["trafilatura","duckdb","pypdf","tenacity","pydantic"]:
    try:
        importlib.import_module(m); print(f"usage-saver: {m} ok")
    except Exception:
        print(f"usage-saver: {m} not available (fallback in use)")
EOF
echo "usage-saver: CHECK done"
