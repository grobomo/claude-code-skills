#!/usr/bin/env bash
# Test: No PII (real names) in any tracked files
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Search for known PII patterns in tracked files only
PII_HITS=$(git -C "$REPO_ROOT" grep -l "Joel Ginsberg" -- ':!.claude/worktrees' ':!scripts/test' 2>/dev/null || true)

if [ -n "$PII_HITS" ]; then
  echo "FAIL: PII found in tracked files:"
  echo "$PII_HITS"
  exit 1
fi

echo "PASS: No PII found in tracked source files"
exit 0
