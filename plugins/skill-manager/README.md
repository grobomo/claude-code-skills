# skill-manager

Self-installing skill manager with keyword enrichment, hook health checks, and session-start auto-maintenance

> Part of [**super-manager**](https://github.com/grobomo/claude-code-skills/tree/main/plugins/super-manager). Installed automatically with super-manager, or independently.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install skill-manager@grobomo-marketplace --scope user
```

Self-installing skill management system. Scans all skills, enriches keywords for better discovery, installs prompt-matching and logging hooks, auto-maintains on every session start.

## Setup (Zero-Touch Install)

```bash
node ~/.claude/skills/skill-manager/setup.js
```

One command does everything:
1. Scans all skills in ~/.claude/skills/
2. Backs up all SKILL.md files + settings.json
3. Enriches keywords using 6-step NLP extraction
4. Creates skill-registry.json with full keyword index
5. Installs 3 hooks (prompt matching, usage logging, session auto-scan)
6. Patches settings.json with hook entries
7. Runs 5 automated self-tests
8. Generates report at ~/.claude/skill-manager-report.md

No restart needed. Changes take effect on next prompt.

## Uninstall (One-Click Restore)

```bash
node ~/.claude/skills/skill-manager/setup.js --uninstall
```

Restores ALL original files from backup. Removes installed hooks. Never deletes anything.

## What Gets Installed

```
~/.claude/hooks/
  skill-usage-tracker.js     # Logs Skill/Task usage (PostToolUse)
  skill-manager-session.js   # Health check + auto-enrich (SessionStart)
  skill-registry.json        # Keyword index for all skills (observability)
```

## How Skill Discovery Works

Claude Code reads `keywords:` from each SKILL.md frontmatter natively. When a user prompt matches, Claude decides to invoke the Skill tool. No custom injection hooks needed.

## Usage Analytics

```
~/.claude/logs/skill-usage.log
```

Each line:
```json
{"timestamp":"2026-02-18T...","tool":"Skill","skill":"network-scan"}
```

## Commands

```bash
/skill-manager              # Show status and help
node setup.js               # Full setup (scan + enrich + hooks + test)
node setup.js --uninstall   # One-click restore from backup
```

## Rules

1. **Never delete** -- always backup/archive
2. **Additive only** -- never remove existing keywords
3. **Self-testing** -- 5 automated checks on every setup run
4. **Pure Node.js** -- no npm dependencies (fs, path, os only)
