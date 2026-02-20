# trend-docs-mcp

MCP server for searching and reading Trend Micro documentation pages.

## Why

`docs.trendmicro.com` and `success.trendmicro.com` are JavaScript SPAs -- standard HTTP fetches return empty shells with no content. This MCP server uses Playwright to render pages and extract clean markdown.

## Tools

| Tool | Description |
|------|-------------|
| `trend_docs_search` | DuckDuckGo `site:trendmicro.com` search. Returns titles, URLs, snippets. No API key needed. |
| `trend_docs_extract` | Async Playwright extraction. Renders JS SPA pages. Handles PDFs (Akamai CDN). Saves PDFs to `~/Downloads/`. |

## Pipeline

```
User asks about a product feature
  -> Claude calls trend_docs_search("ZTSA pac file configuration")
  -> Gets 10 URLs with titles and snippets
  -> Claude picks relevant URLs
  -> Claude calls trend_docs_extract("url1,url2")
  -> Gets full page content as markdown
  -> Claude synthesizes answer with sources
```

## Setup

After installing the plugin, add the server to your `.mcp.json`:

```json
{
  "mcpServers": {
    "trend-docs": {
      "command": "python",
      "args": ["<path-to-installed-server.py>"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

Or if using mcp-manager, add to `servers.yaml` and project server list.

## Dependencies (auto-installed on first use)

- `mcp` - FastMCP framework
- `ddgs` - DuckDuckGo search
- `playwright` + chromium - Browser automation
- `PyPDF2` - PDF text extraction

## Compatibility

This MCP server can coexist with the `trend-docs` skill plugin. The skill uses `executor.py` (sync Playwright), while the MCP server uses `server.py` (async Playwright via FastMCP). If both are installed, prefer using the MCP server tools.
