# mcp-manager

Dynamic MCP server proxy router. All MCP servers go through a single `mcp-manager` entry in `.mcp.json`. Servers are defined in `servers.yaml` and proxied at runtime.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install mcp-manager@grobomo-marketplace --scope user
```

After install, tell Claude to run setup (or it runs automatically on first skill load):
```
setup mcp-manager
```

## Features

- **Single entry point**: Only `mcp-manager` in `.mcp.json` - all other servers proxied through it
- **stdio + HTTP/SSE**: Local process servers and remote HTTP servers with custom headers
- **Hot reload**: Change `servers.yaml`, run `mcpm reload` - no restart needed
- **Auto-start**: Servers in project `.mcp.json` `servers` list start on session connect
- **Idle timeout**: Unused servers auto-stop after configurable timeout
- **Server discovery**: Scan for unregistered MCP servers in common locations
- **Auto-instructions**: Creates Claude instruction files on first startup

## Quick Start

```
mcpm list_servers          # See all servers
mcpm start my-server       # Start a server
mcpm call my-server tool   # Call a tool
mcpm add new-server ...    # Register a server
mcpm reload                # Reload config
```

## Server Types

**Local (stdio):**
```yaml
my-server:
  command: python
  args: [path/to/server.py]
  description: My local server
  enabled: true
```

**Remote (HTTP/SSE):**
```yaml
my-remote:
  url: http://host:port/mcp
  headers:
    Authorization: Bearer TOKEN
  description: Remote server
  enabled: true
```

## Part of super-manager

Can be used standalone or as part of [super-manager](https://github.com/grobomo/claude-code-skills/tree/main/plugins/super-manager).
