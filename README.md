# Claude Code Skills Marketplace

A public marketplace of plugins for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Anthropic's official CLI. Each plugin adds specialized skills -- from API wrappers and config management to diff viewers and hook generators.

## Quick Start

```bash
# 1. Add this marketplace
claude plugin marketplace add grobomo/claude-code-skills

# 2. Install any plugin
claude plugin install super-manager@grobomo-marketplace --scope user
```

## Available Plugins

<!-- PLUGINS_TABLE_START -->
| Plugin | Description | Version | Install |
|--------|-------------|---------|---------|
|| **diff-view** | Side-by-side diff viewer with editable right side, resizable panels, synced heights, and merge workflow. Opens in browser. | 1.0.0 | `claude plugin install diff-view@grobomo-marketplace` |
|| **memo-edit** | Safely edit CLAUDE.md project memos with proper section management. Prevents accidental overwrites and maintains structure. | 1.0.0 | `claude plugin install memo-edit@grobomo-marketplace` |
|| **super-manager** | Unified manager for all Claude Code configuration - hooks, skills, MCP servers, and instructions. Status dashboard, doctor diagnostics, auto-fix, and duplicate detection. | 1.0.0 | `claude plugin install super-manager@grobomo-marketplace` |
|credential-manager| &nbsp;&nbsp;&nbsp;&nbsp;credential-manager | Store and retrieve API tokens/secrets in OS credential store (Windows Credential Manager / macOS Keychain). GUI popup for zero-friction secure storage. | 1.0.0 | included with super-manager |
|hook-manager| &nbsp;&nbsp;&nbsp;&nbsp;hook-manager | Create and manage Claude Code hooks - correct schema, all event formats, stdin/stdout contracts, enable/disable/verify. Complete hook knowledge base. | 1.0.0 | included with super-manager |
|skill-manager| &nbsp;&nbsp;&nbsp;&nbsp;skill-manager | Self-installing skill manager with keyword enrichment, hook health checks, and session-start auto-maintenance | 1.0.0 | included with super-manager |
|| **trend-docs** | Read Trend Micro documentation from docs.trendmicro.com and success.trendmicro.com. Uses Playwright to extract content from JS SPA pages that WebFetch cannot read. | 1.0.0 | `claude plugin install trend-docs@grobomo-marketplace` |
|| **v1-api** | Trend Micro Vision One API wrapper with 280+ operations. Query alerts, endpoints, threats, cloud security, and more. | 1.0.0 | `claude plugin install v1-api@grobomo-marketplace` |
<!-- PLUGINS_TABLE_END -->

## Plugin Details

### diff-view

Launches a local browser-based diff viewer with side-by-side comparison, editable right panel, resizable columns, synced line heights, and a merge workflow for accepting changes.

### memo-edit

Safe section-level editing of CLAUDE.md project memos. Prevents accidental overwrites by targeting specific sections rather than rewriting the entire file.

### super-manager

Unified config dashboard and doctor for Claude Code. Manages hooks, skills, MCP servers, and instructions from a single CLI. Includes `status`, `doctor --fix`, `report`, and `duplicates` commands.

Includes three sub-manager plugins that are installed automatically with super-manager:

- **credential-manager** -- Store and retrieve API tokens/secrets in the OS credential store (Windows Credential Manager / macOS Keychain) instead of plaintext files. GUI popup for secure entry, `.env` migration, and Python/Node.js resolver libraries.
- **hook-manager** -- Create and manage Claude Code hooks with correct schema for all event types. Covers stdin/stdout contracts, matcher rules, Stop hook loop prevention, PreToolUse deny/allow/ask patterns, and management commands.
- **skill-manager** -- Self-installing skill manager that enriches skills with keyword metadata, runs hook health checks, and performs auto-maintenance on session start.

### trend-docs

Read Trend Micro documentation from docs.trendmicro.com and success.trendmicro.com. Uses Playwright to extract content from JavaScript SPA pages that standard web fetch tools cannot read.

### v1-api

Full-featured Trend Micro Vision One API wrapper. Covers 280+ operations across alerts, endpoints, cloud security, XDR search, response actions, and more. Includes auto-pagination and example scripts for every endpoint.

## Contributing

### Plugin Structure

Each plugin lives under `plugins/` and follows this layout:

```
plugins/your-plugin/
  .claude-plugin/plugin.json     # Plugin metadata (name, version, description)
  skills/your-skill/SKILL.md     # Skill instructions loaded by Claude Code
  skills/your-skill/...          # Supporting files (scripts, configs, etc.)
```

Sub-manager plugins add `"parent": "parent-plugin-name"` to their `plugin.json` to indicate they are bundled with the parent plugin.

### Steps

1. Fork this repository
2. Create your plugin directory under `plugins/`
3. Add a `.claude-plugin/plugin.json` with name, version, and description
4. Add your skill files under `skills/`
5. Update `.claude-plugin/marketplace.json` at the repo root to include your plugin
6. Submit a pull request

The README plugins table is automatically updated by a GitHub Action when `plugins/` or `marketplace.json` changes on main.

## License

MIT