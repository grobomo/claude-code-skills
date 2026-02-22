---
name: trend-docs-mcp
description: "MCP server for Trend Micro documentation search and extraction"
keywords:
  - trend-docs-mcp
  - mcp-trend-docs
---

# trend-docs-mcp

MCP server for searching and extracting Trend Micro documentation (JS SPA pages).

## Auto-Setup (REQUIRED on first load)

**Before using MCP tools, check if they are available.** If `trend_docs_search` and `trend_docs_extract` tools are NOT listed in your available MCP tools, run setup automatically:

```bash
node "SKILL_DIR/setup.js"
```

Replace `SKILL_DIR` with the directory containing this SKILL.md file (same directory as setup.js and server.py).

After setup completes, tell the user: "MCP server configured. Please restart your Claude Code session to activate the trend-docs MCP tools."

**Do NOT skip this step.** Do NOT ask the user to run it manually. Just run it.

## MCP Tools (available after setup + session restart)

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
