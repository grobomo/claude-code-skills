#!/usr/bin/env bash
# T016: Validate all plugin structures — plugin.json fields, SKILL.md frontmatter, no CRLF
set -euo pipefail

FAIL=0
cd "$(git rev-parse --show-toplevel)"

echo "=== Plugin Structure Validation ==="

for p in plugins/*/; do
  name=$(basename "$p")
  pj="$p/.claude-plugin/plugin.json"

  # plugin.json must exist
  if [ ! -f "$pj" ]; then
    echo "FAIL: $name — missing .claude-plugin/plugin.json"
    FAIL=1
    continue
  fi

  # Validate JSON and required fields
  result=$(node -e "
    const j=JSON.parse(require('fs').readFileSync('$pj','utf8'));
    const issues=[];
    if(!j.name) issues.push('no name');
    if(!j.description) issues.push('no description');
    if(!j.version) issues.push('no version');
    if(!j.author?.name) issues.push('no author.name');
    if(issues.length) { console.log(issues.join(', ')); process.exit(1); }
  " 2>&1) || {
    echo "FAIL: $name — plugin.json: $result"
    FAIL=1
  }

  # SKILL.md must exist
  skill=$(find "$p" -name "SKILL.md" 2>/dev/null | head -1)
  if [ -z "$skill" ]; then
    echo "FAIL: $name — no SKILL.md found"
    FAIL=1
    continue
  fi

  # SKILL.md must have YAML frontmatter (first line ---)
  first=$(head -1 "$skill")
  if [ "$first" != "---" ]; then
    echo "FAIL: $name — SKILL.md missing YAML frontmatter"
    FAIL=1
  fi

  # No CRLF in SKILL.md
  if head -1 "$skill" | grep -qP '\r'; then
    echo "FAIL: $name — SKILL.md has CRLF line endings"
    FAIL=1
  fi
done

if [ "$FAIL" -eq 0 ]; then
  echo "ALL PLUGINS PASS"
else
  echo "VALIDATION FAILED"
  exit 1
fi
