---
name: trend-docs-mcp
description: "MCP server for Trend Micro documentation search and extraction"
keywords:
  - trend-docs-mcp
  - mcp-trend-docs
---

# trend-docs-mcp

This plugin provides an MCP server for searching and extracting Trend Micro documentation.

## Setup

The MCP server file is `server.py` in this directory. Configure it in your `.mcp.json`:

```json
{
  "mcpServers": {
    "trend-docs": {
      "command": "python",
      "args": ["<path-to-this-directory>/server.py"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `trend_docs_search` | DuckDuckGo site:trendmicro.com search (no API key) |
| `trend_docs_extract` | Async Playwright page extraction (HTML + PDF) |

## Workflow

1. `trend_docs_search("query")` to find page URLs
2. Review results, pick relevant URLs
3. `trend_docs_extract("url1,url2")` to read pages
4. Synthesize answer from extracted content

## Compatibility

Coexists with the `trend-docs` skill plugin. If both installed, prefer MCP tools.
