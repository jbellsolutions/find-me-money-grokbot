#!/usr/bin/env bash
# Print only matching lines (file:line:text), capped, instead of opening whole files.
# usage: grep_lines.sh '<pattern>' [folder] [max_lines]
set -u
pat="$1"; dir="${2:-.}"; max="${3:-60}"
if command -v rg >/dev/null; then
  rg -n --no-heading -i -M 300 -- "$pat" "$dir" 2>/dev/null | head -n "$max"
else
  grep -rniI -- "$pat" "$dir" 2>/dev/null | cut -c1-300 | head -n "$max"
fi
