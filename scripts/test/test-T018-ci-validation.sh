#!/usr/bin/env bash
# T018: Verify CI workflow includes author.name validation
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if ! grep -q 'author' .github/workflows/plugin-quality-gate.yml; then
  echo "FAIL: plugin-quality-gate.yml does not check author field"
  exit 1
fi

echo "CI workflow includes author validation"
