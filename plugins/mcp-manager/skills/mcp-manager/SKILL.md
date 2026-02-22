---
name: mcp-manager
description: "Dynamic MCP server proxy router - manage, start, stop, and proxy all MCP servers through a single entry point."
keywords:
  - mcp
  - server
  - servers
  - start
  - stop
  - reload
  - mcpm
---

# MCP Manager (mcpm)

Dynamic MCP server proxy router. All MCP servers go through mcpm - single entry in .mcp.json, servers defined in servers.yaml.

## Auto-Setup (REQUIRED on first load)

**Before using mcpm tools, check if they are available.** If `mcpm` tool is NOT listed in your available MCP tools, run setup automatically:

```bash
node "SKILL_DIR/setup.js"
```

Replace `SKILL_DIR` with the directory containing this SKILL.md file.

After setup completes:
1. Tell the user to run `/mcp` -> select mcp-manager -> Connect
2. Verify with `mcpm list_servers`

**Do NOT skip this step.** Do NOT ask the user to run it manually. Just run it.

## MCP Tools (available after setup)

| Tool | Purpose |
|------|---------|
| `mcpm list_servers` | List all servers and status |
| `mcpm start SERVER` | Start a server (stdio or HTTP) |
| `mcpm stop SERVER` | Stop a running server |
| `mcpm restart SERVER` | Restart a server |
| `mcpm reload` | Hot reload servers.yaml config |
| `mcpm search QUERY` | Search servers and tools |
| `mcpm details SERVER` | Full info on one server |
| `mcpm tools [SERVER]` | List available tools |
| `mcpm call SERVER TOOL [ARGS]` | Execute a tool on a backend server |
| `mcpm add SERVER ...` | Register a new server |
| `mcpm remove SERVER` | Remove a server |
| `mcpm enable SERVER` | Enable/disable a server |
| `mcpm status` | System health and memory |
| `mcpm discover` | Scan for unregistered servers |

## Server Types

### stdio (local process)
```yaml
my-server:
  command: python
  args:
    - path/to/server.py
  description: My local MCP server
  enabled: true
  auto_start: false
```

### HTTP/SSE (remote)
```yaml
my-remote:
  url: http://host:port/mcp
  headers:
    Authorization: Bearer TOKEN
  description: Remote MCP server
  enabled: true
  auto_start: false
```

## Configuration

- **servers.yaml**: Central registry (same directory as build/index.js)
- **.mcp.json**: Project server list (names only, in `servers` array)

## Reload Flow

When config changes, tell user:
1. `/mcp` -> select mcp-manager -> Reconnect
2. `mcpm reload` (picks up servers.yaml changes)

**NEVER** tell user to restart Claude Code for mcpm changes.

## Rules

- **Only mcpm in .mcp.json** - never add direct MCP server entries
- All servers (stdio + HTTP) go through mcpm
- HTTP servers: `url` + `headers` in servers.yaml
