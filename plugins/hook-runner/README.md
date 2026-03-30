# hook-runner

Modular hook runner for Claude Code. One runner per event, modules in folders. Setup wizard migrates existing hooks safely.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install hook-runner@grobomo-marketplace --scope user
```

Then run `/hook-runner setup` to migrate your existing hooks.

## What It Does

Replaces per-hook entries in `settings.json` with a runner + module system:
- Drop a `.js` file in `~/.claude/hooks/run-modules/<Event>/` to add behavior
- No settings.json editing needed after initial setup
- Project-scoped modules via subfolders
- Safe migration with automatic backup to `~/.claude/hooks/archive/`

## Commands

| Command | Description |
|---------|-------------|
| `/hook-runner setup` | Full wizard: scan, report, backup, install, verify |
| `/hook-runner report` | Generate HTML report of current hooks with hit counts |
| `/hook-runner dry-run` | Preview changes without modifying anything |
| `/hook-runner sync` | Sync modules from GitHub per `~/.claude/hooks/modules.yaml` |
| `/hook-runner sync-dry-run` | Preview module sync without installing |
| `/hook-runner health` | Verify all runners and modules load correctly |

## Source

[grobomo/hook-runner](https://github.com/grobomo/hook-runner)
