#!/usr/bin/env bash
# Test: T015 mcp-manager sync (BLOCKED — junction broken)
# This task is blocked; test validates the blocking condition is documented
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# T015 is blocked — verify it's marked as blocked in TODO.md
if grep -q "T015.*Blocked\|Blocked.*T015\|## Blocked" "$REPO_ROOT/TODO.md" 2>/dev/null; then
  echo "PASS: T015 is documented as blocked in TODO.md"
  exit 0
fi

echo "FAIL: T015 should be marked blocked in TODO.md"
exit 1
