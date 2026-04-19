# Contributing to Claude Code Skills Marketplace

## Plugin Structure

Each plugin lives in `plugins/<name>/` with this layout:

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required: metadata for marketplace
├── skills/
│   └── my-plugin/
│       └── SKILL.md         # Required: skill definition with YAML frontmatter
├── README.md                # Optional: detailed docs
└── ...                      # Plugin-specific files (JS, Python, configs)
```

## plugin.json

Every plugin must have `.claude-plugin/plugin.json` with these fields:

```json
{
  "name": "my-plugin",
  "description": "What the plugin does in one sentence.",
  "version": "1.0.0",
  "author": {
    "name": "grobomo"
  },
  "keywords": ["relevant", "search", "terms"],
  "skills": ["./skills/my-plugin"]
}
```

**Required fields**: `name`, `description`, `version`, `author.name`

Sub-plugins (bundled with a parent) also include `"parent": "super-manager"`.

## SKILL.md

Every plugin needs at least one `SKILL.md` with YAML frontmatter:

```yaml
---
name: my-plugin
description: "What the plugin does."
keywords:
  - keyword1
  - keyword2
---

# My Plugin

Instructions for Claude Code on how to use this plugin...
```

**The first line must be `---`** (YAML frontmatter delimiter). CI will reject SKILL.md files without it.

## CI Checks

Four automated checks run on every PR that touches `plugins/`:

| Check | What it validates |
|-------|-------------------|
| **Plugin Structure Validation** | plugin.json exists, valid JSON, required fields, SKILL.md exists with frontmatter |
| **Personal Path & Secret Scan** | No hardcoded user paths (`C:/Users/...`), no `.env` files, no plaintext tokens/keys |
| **Line Ending Check** | All files must use LF line endings (not CRLF) |
| **Secret Scan** | Broader secret pattern detection across all file types |

A separate `secret-scan.yml` runs on all pushes (not just plugin changes).

## Line Endings

All files must use **LF** line endings. Configure git:

```bash
git config core.autocrlf input
```

If CI fails on CRLF, fix with:

```bash
# Fix a single file
sed -i 's/\r$//' path/to/file

# Fix all files in a plugin
find plugins/my-plugin -type f \( -name "*.js" -o -name "*.json" -o -name "*.md" \) -exec sed -i 's/\r$//' {} +
```

## Adding a New Plugin

1. Create `plugins/<name>/` with the structure above
2. Run the local validation test: `bash scripts/test/test-T016-plugin-validation.sh`
3. Submit a PR -- CI runs automatically
4. The README table auto-updates from plugin.json after merge (via `update-readme.yml`)

## Syncing from Source Repos

Some plugins (e.g., `hook-runner`) have separate source repos. The sync workflow:

1. Copy files per the source repo's `CLAUDE.md` push workflow instructions
2. Update `plugin.json` version to match source
3. Run `bash scripts/test/test-T016-plugin-validation.sh`
4. Submit PR, verify CI, merge

## No Personal Data

This is a **public** marketplace. Never include:
- Hardcoded user paths
- Customer names or data
- API keys, tokens, or secrets
- Internal infrastructure details

Use `credential-manager` (OS keyring) for secrets. Use `os.homedir()` or `$HOME` for paths.
