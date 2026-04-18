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
| &nbsp;&nbsp;&nbsp;&nbsp;skill-manager | Self-installing skill manager with keyword enrichment, hook health checks, and session-start auto-maintenance | `claude plugin install skill-manager@grobomo-marketplace` (included with super-manager) | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/skill-manager) |

### Standalone Plugins

| Plugin | Description | Install | Links |
|--------|-------------|---------|-------|
| **claude-code-chat-export** | Export Claude Code conversations to styled HTML with search and optional Markdown output. Strips system noise, smart tool formatting. | `claude plugin install claude-code-chat-export@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/claude-code-chat-export) |
| **claude-report** | Generate interactive HTML inventory of Claude Code MCPs, skills, and hooks with security awareness. | `claude plugin install claude-report@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/claude-report) |
| **cloud-claude** | Launch Claude Code on AWS EC2 spot instances. Auto-provisions SSH keys, security groups, Docker container with Chrome and MCP support. Multi-instance with inter-instance messaging. ~$0.03-0.06/hr. | `claude plugin install cloud-claude@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/cloud-claude) |
| **diff-view** | Side-by-side diff viewer with editable right side, resizable panels, synced heights, and merge workflow. Opens in browser. | `claude plugin install diff-view@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/diff-view) |
| **hook-runner** | Modular hook system for Claude Code. Drop `.js` files in folders to enforce workflows, block mistakes, and inject context. Includes 40+ built-in modules and YAML workflow engine. | `claude plugin install hook-runner@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/hook-runner) |
| **jumpbox** | Windows EC2 jumpbox manager. Provisions Win Server 2022 with Chrome, Git Bash, SSM, and configurable timezone. RDP with auto credential injection. | `claude plugin install jumpbox@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/jumpbox) |
| **mcp-manager** | Dynamic MCP server proxy router - manage, start, stop, and proxy all MCP servers through a single entry point. Supports stdio and HTTP/SSE transports. | `claude plugin install mcp-manager@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/mcp-manager) |
| **pm-report** | Generate evidence-based technical analysis reports for Product Management audiences. PDF output with coverage tables, bar charts, score cards, tiered recommendations, and embedded screenshots. | `claude plugin install pm-report@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/pm-report) |
| **trend-docs** | Read Trend Micro documentation from docs.trendmicro.com and success.trendmicro.com. Playwright extractor for JS SPA pages. 30-day cache with change detection. Topic bundles for batch fetches. PDF download with Akamai CDN handling. | `claude plugin install trend-docs@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/trend-docs) |
| **trend-docs-mcp** | MCP server for searching and reading Trend Micro documentation. DuckDuckGo search + async Playwright extraction for JS SPA pages. Companion to the trend-docs skill. | `claude plugin install trend-docs-mcp@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/trend-docs-mcp) |
| **v1-api** | Trend Micro Vision One API - skill (280+ ops via executor.py) + MCP server (75 ops via server.py). Alerts, endpoints, threats, cloud security, response actions. | `claude plugin install v1-api@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/v1-api) |
| **v1-oat-report** | Generate styled HTML reports of Vision One OAT detections with MITRE mapping | `claude plugin install v1-oat-report@grobomo-marketplace` | [GitHub](https://github.com/grobomo/claude-code-skills/tree/main/plugins/v1-oat-report) |
<!-- PLUGINS_TABLE_END -->

## License

MIT