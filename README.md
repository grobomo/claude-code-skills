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
| **trend-docs** | Read Trend Micro documentation from docs.trendmicro.com and success.trendmicro.com. Uses Playwright to extract content from JS SPA pages. Downloads PDFs via Playwright (handles Akamai CDN redirects). Saves to ~/Downloads. | `claude plugin install trend-docs@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/trend-docs) |
| **trend-docs-mcp** | MCP server for searching and reading Trend Micro documentation. DuckDuckGo search + async Playwright extraction for JS SPA pages. Companion to the trend-docs skill. | `claude plugin install trend-docs-mcp@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/trend-docs-mcp) |
| **v1-api** | Trend Micro Vision One API - skill (280+ ops via executor.py) + MCP server (75 ops via server.py). Alerts, endpoints, threats, cloud security, response actions. | `claude plugin install v1-api@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/v1-api) |
<!-- PLUGINS_TABLE_END -->

## License

MIT