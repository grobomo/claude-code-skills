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
### Super Manager Ecosystem

| Plugin | Description | Install | Links |
|--------|-------------|---------|-------|
| **super-manager** | Unified manager for all Claude Code configuration - hooks, skills, MCP servers, and instructions. Status dashboard, doctor diagnostics, auto-fix, and duplicate detection. | `claude plugin install super-manager@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/super-manager) |
| &nbsp;&nbsp;&nbsp;&nbsp;credential-manager | Store and retrieve API tokens/secrets in OS credential store (Windows Credential Manager / macOS Keychain). GUI popup for zero-friction secure storage. | `claude plugin install credential-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/credential-manager) |
| &nbsp;&nbsp;&nbsp;&nbsp;hook-manager | Create and manage Claude Code hooks - correct schema, all event formats, stdin/stdout contracts, enable/disable/verify. Complete hook knowledge base. | `claude plugin install hook-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/hook-manager) |
| &nbsp;&nbsp;&nbsp;&nbsp;instruction-manager | Manage context-aware instruction files with keyword matching. Conditional context injection for Claude Code sessions. | `claude plugin install instruction-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/instruction-manager) |
| &nbsp;&nbsp;&nbsp;&nbsp;mcp-manager | Manage MCP servers - list, enable, disable, start, stop, reload. Configuration and lifecycle management. | `claude plugin install mcp-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/mcp-manager) |
| &nbsp;&nbsp;&nbsp;&nbsp;skill-manager | Self-installing skill manager with keyword enrichment, hook health checks, and session-start auto-maintenance | `claude plugin install skill-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/skill-manager) |

### Standalone Plugins

| Plugin | Description | Install | Links |
|--------|-------------|---------|-------|
| **diff-view** | Side-by-side diff viewer with editable right side, resizable panels, synced heights, and merge workflow. Opens in browser. | `claude plugin install diff-view@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/diff-view) |
| **memo-edit** | Safely edit CLAUDE.md project memos with proper section management. Prevents accidental overwrites and maintains structure. | `claude plugin install memo-edit@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/memo-edit) |
| **trend-docs** | Read Trend Micro documentation from docs.trendmicro.com and success.trendmicro.com. Uses Playwright to extract content from JS SPA pages. Downloads PDFs via Playwright (handles Akamai CDN redirects). Saves to ~/Downloads. | `claude plugin install trend-docs@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/trend-docs) |
| **v1-api** | Trend Micro Vision One API - skill (280+ ops via executor.py) + MCP server (75 ops via server.py). Alerts, endpoints, threats, cloud security, response actions. | `claude plugin install v1-api@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/v1-api) |
<!-- PLUGINS_TABLE_END -->

## Plugin Details

### diff-view

Launches a local browser-based diff viewer with side-by-side comparison, editable right panel, resizable columns, synced line heights, and a merge workflow for accepting changes.

### memo-edit

Safe section-level editing of CLAUDE.md project memos. Prevents accidental overwrites by targeting specific sections rather than rewriting the entire file.

### super-manager

Unified config dashboard and doctor for Claude Code. Manages hooks, skills, MCP servers, and instructions from a single CLI. Includes `status`, `doctor --fix`, `report`, and `duplicates` commands.

Includes five sub-manager plugins that are installed automatically with super-manager:

- **credential-manager** -- Store and retrieve API tokens/secrets in the OS credential store (Windows Credential Manager / macOS Keychain) instead of plaintext files. GUI popup for secure entry, `.env` migration, and Python/Node.js resolver libraries.
- **hook-manager** -- Create and manage Claude Code hooks with correct schema for all event types. Covers stdin/stdout contracts, matcher rules, Stop hook loop prevention, PreToolUse deny/allow/ask patterns, and management commands.
- **instruction-manager** -- Manage context-aware instruction files that conditionally inject guidance based on prompt keywords. Solves the "Claude forgets rules after long sessions" problem.
- **mcp-manager** -- Manage MCP server configuration and lifecycle. List, enable, disable, start, stop, and reload servers with PID tracking and hot reload.
- **skill-manager** -- Self-installing skill manager that enriches skills with keyword metadata, runs hook health checks, and performs auto-maintenance on session start.

### mcp-manager

Manage MCP server configuration and lifecycle. List, enable, disable, start, stop, and reload servers from a unified CLI. Reads from servers.yaml registry, tracks PIDs, and supports hot reload without restarting Claude.

### instruction-manager

Manage context-aware instruction files that conditionally inject guidance based on prompt keywords. Each instruction is a markdown file with YAML frontmatter containing keywords. When a prompt matches, the instruction content is injected as context -- solving the "Claude forgets rules after long sessions" problem.

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