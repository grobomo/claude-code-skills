# Skill Manager Technical Reference

## Architecture Decision (2026-02-18)

**Native frontmatter matching only.** Claude Code reads `keywords:` from SKILL.md frontmatter natively. No custom skill injection via hooks. skill-reminder.js removed from pipeline.

- skill-registry.json still exists for dashboards/observability but NOT for matching
- All skills must have single-word keywords in frontmatter
- Flow: user prompt -> Claude sees skill list -> calls Skill tool -> SKILL.md loads -> executes

## What setup.js Does

`setup.js` is a self-installing, self-testing skill manager for Claude Code. Run it once and it configures everything. Pure Node.js, no npm dependencies.

### Pipeline (7 steps)

1. **Scan** - Reads `~/.claude/skills/*/SKILL.md`, parses frontmatter (name, description, keywords)
2. **Backup** - Copies settings.json, skill-registry.json, and all SKILL.md files to timestamped backup
3. **Enrich** - Runs 6-step keyword extraction on each SKILL.md, merges additively
4. **Registry** - Builds/updates `~/.claude/hooks/skill-registry.json` with all skills and keywords
5. **Hooks** - Writes 2 hook files (skips if already exist)
6. **Settings** - Patches `~/.claude/settings.json` with hook entries (preserves existing)
7. **Self-Test** - 5 automated checks: registry validity, hook files, settings, keyword matching, logging

### Exported Functions

```javascript
module.exports = {
  main,              // Run full setup pipeline
  scanAllSkills,     // Scan skills dir, return inventory array
  enrichAllSkills,   // Enrich keywords in all SKILL.md files
  extractKeywords,   // 6-step NLP keyword extraction
  filterKeywords,    // Remove generic/stopword keywords
  buildSkillRegistry,// Create/update skill-registry.json
  installHooks,      // Write 2 hook files
  patchSettings,     // Add hooks to settings.json
  uninstall,         // Restore from most recent backup
  selfTest,          // Run 5 automated tests
  generateReport     // Write report to ~/.claude/skill-manager-report.md
};
```

## Hooks (2)

### skill-usage-tracker.js (PostToolUse, matcher: Skill|Task)

Logs every Skill/Task invocation to `~/.claude/logs/skill-usage.log`. Each line:
```json
{"timestamp":"2026-02-18T...","tool":"Skill","skill":"network-scan"}
```

### skill-manager-session.js (SessionStart, matcher: *)

Runs on every session start:
1. **Hook health check** - Verifies both hook files exist and are registered in settings.json
2. **Auto-remediation** - If any hooks are missing, calls setup.installHooks() and setup.patchSettings()
3. **Frontmatter compliance** - Scans all SKILL.md files for missing `keywords:` blocks
4. **Auto-enrichment** - Enriches skills missing keywords via setup.js exports
5. **Logging** - All actions logged to skill-usage.log with action/detail fields

### Removed: skill-reminder.js (UserPromptSubmit)

Removed 2026-02-18. Was injecting skill suggestions into context via keyword matching against skill-registry.json. Replaced by Claude Code's native frontmatter keyword matching.

## Keyword Extraction Pipeline

Six-step NLP extraction:

1. **Parse frontmatter** - Extract name, description, existing keywords
2. **Trigger patterns** - Find "Use when...", "Triggers: ...", quoted phrases in description
3. **Body sections** - Parse ## Usage, ## When to use, ## Triggers for verb+noun phrases
4. **Verb phrases** - Extract 2-3 word phrases starting with action verbs from description
5. **Variations** - Generate reversed 2-word phrases ("scan network" -> "network scan")
6. **Filter** - Remove stopwords, single-word generic terms, duplicate-word phrases

### Generic word filter

Single-word keywords like "scan", "open", "file" are blocked (too many false positives). Multi-word phrases containing them are fine ("scan network" passes).

## Backup/Restore Workflow

### Backup (automatic on every setup run)

```
~/.claude/backups/skill-manager/
  2026-02-18T21-20-13/
    settings.json
    skill-registry.json
    manifest.json
    skills/
      network-scan/SKILL.md
      weekly-update/SKILL.md
      ...
```

### Uninstall

```bash
node ~/.claude/skills/skill-manager/setup.js --uninstall
```

Restores from most recent backup. Hook files moved to archive (never deleted).

## Key Files

```
~/.claude/
  skills/skill-manager/
    setup.js              # Main setup script
    SKILL.md              # Skill frontmatter + docs
    CLAUDE.md             # This file
    archive/              # Backed-up originals
  hooks/
    skill-usage-tracker.js # Usage logging hook
    skill-manager-session.js # Health check + auto-enrich on session start
    skill-registry.json   # All skills with keywords (observability only)
  logs/
    skill-usage.log       # Usage + health check log
  backups/skill-manager/  # Timestamped backups
  skill-manager-report.md # Last setup report
```

## Rules

- Never delete files -- always backup/archive
- Pure Node.js only (fs, path, os) -- no npm dependencies
- All paths via path.join() and os.homedir() -- no hardcoded separators
- Forward-slash paths in settings.json command strings
- Additive-only keyword merging -- never remove existing keywords
- Single-word keywords preferred for frontmatter (native matching)
