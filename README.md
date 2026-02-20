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
| **super-manager** | Unified manager for all Claude Code configuration - hooks, skills, MCP servers, and instructions. | 1.0.0 | `claude plugin install super-manager@grobomo-marketplace` |
| **v1-api** | Trend Micro Vision One API wrapper with 280+ operations. Query alerts, endpoints, threats, cloud security, and more. | 1.0.0 | `claude plugin install v1-api@grobomo-marketplace` |
| **diff-view** | Side-by-side diff viewer with editable right side, resizable panels, synced heights, and merge workflow. | 1.0.0 | `claude plugin install diff-view@grobomo-marketplace` |
| **hook-maker** | Create Claude Code hooks from templates. Generates correct hook schema for all event types. | 1.0.0 | `claude plugin install hook-maker@grobomo-marketplace` |
| **memo-edit** | Safely edit CLAUDE.md project memos with proper section management. | 1.0.0 | `claude plugin install memo-edit@grobomo-marketplace` |
| **skill-manager** | Self-installing skill manager with keyword enrichment, hook health checks, and session-start auto-maintenance. | 1.0.0 | `claude plugin install skill-manager@grobomo-marketplace` |
<!-- PLUGINS_TABLE_END -->

## Plugin Details

### super-manager

Unified config dashboard and doctor for Claude Code. Manages hooks, skills, MCP servers, and instructions from a single CLI. Includes `status`, `doctor --fix`, `report`, and `duplicates` commands.

### v1-api

Full-featured Trend Micro Vision One API wrapper. Covers 280+ operations across alerts, endpoints, cloud security, XDR search, response actions, and more. Includes auto-pagination and example scripts for every endpoint.

### diff-view

Launches a local browser-based diff viewer with side-by-side comparison, editable right panel, resizable columns, synced line heights, and a merge workflow for accepting changes.

### hook-maker

Generates Claude Code hooks from templates. Supports all hook event types (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, etc.) with correct JSON schema and helper utilities.

### memo-edit

Safe section-level editing of CLAUDE.md project memos. Prevents accidental overwrites by targeting specific sections rather than rewriting the entire file.

### skill-manager

Self-installing skill manager that enriches skills with keyword metadata, runs hook health checks, and performs auto-maintenance on session start. Includes a setup script for first-time configuration.

## Contributing

### Plugin Structure

Each plugin lives under `plugins/` and follows this layout:

```
plugins/your-plugin/
  .claude-plugin/plugin.json     # Plugin metadata (name, version, description)
  skills/your-skill/SKILL.md     # Skill instructions loaded by Claude Code
  skills/your-skill/...          # Supporting files (scripts, configs, etc.)
```

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
