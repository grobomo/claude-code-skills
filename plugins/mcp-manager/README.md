# mcp-manager

Manage MCP servers - list, enable, disable, start, stop, reload. Configuration and lifecycle management.

> Part of [**super-manager**](https://github.com/grobomo/claude-code-skills/tree/main/plugins/super-manager). Installed automatically with super-manager, or independently.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install mcp-manager@grobomo-marketplace --scope user
```

Manage MCP server configuration and lifecycle. Part of super-manager.

## Commands

```bash
# List all servers from servers.yaml
python ~/.claude/super-manager/super_manager.py mcp list

# Enable/disable a server
python ~/.claude/super-manager/super_manager.py mcp enable SERVER_NAME
python ~/.claude/super-manager/super_manager.py mcp disable SERVER_NAME

# Verify all servers healthy
python ~/.claude/super-manager/super_manager.py mcp verify

# Start/stop/reload (lifecycle via mcpm)
python ~/.claude/super-manager/super_manager.py mcp start SERVER_NAME
python ~/.claude/super-manager/super_manager.py mcp stop SERVER_NAME
python ~/.claude/super-manager/super_manager.py mcp reload
```

## Also Available via MCP Manager Tool

The `mcp-manager` MCP server (mcpm) provides the same operations as MCP tool calls:

```
mcpm list_servers       # List all servers and status
mcpm start SERVER       # Start a server
mcpm stop SERVER        # Stop a server
mcpm reload             # Hot reload configs
```

## Configuration

**Central registry:** `servers.yaml` (searched in multiple locations)
**Project servers:** `.mcp.json` in project root

## Architecture

```
~/.claude/super-manager/managers/
└── mcp_server_manager.py    # Config-only (servers.yaml read/write)

Lifecycle (start/stop/reload) delegated to mcpm subprocess.
PID tracking: ~/.claude/super-manager/logs/server-pids.json
```

## Dependency

Part of **super-manager** (`~/.claude/super-manager/`).
