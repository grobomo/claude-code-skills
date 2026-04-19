#!/usr/bin/env bash
# T017: Verify CONTRIBUTING.md exists and covers required sections
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

FAIL=0

if [ ! -f "CONTRIBUTING.md" ]; then
  echo "FAIL: CONTRIBUTING.md not found"
  exit 1
fi

# Check required sections exist
for section in "Plugin Structure" "plugin.json" "SKILL.md" "CI Checks" "Line Endings"; do
  if ! grep -q "$section" CONTRIBUTING.md; then
    echo "FAIL: Missing section about '$section'"
    FAIL=1
  fi
done

if [ "$FAIL" -eq 0 ]; then
  echo "CONTRIBUTING.md covers all required sections"
else
  exit 1
fi
