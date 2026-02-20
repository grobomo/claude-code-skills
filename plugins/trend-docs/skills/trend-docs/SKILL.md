---
name: trend-docs
description: Read Trend Micro documentation. Searches, extracts, and returns clean content from docs.trendmicro.com and success.trendmicro.com KB articles with relevant related pages.
keywords:
  - docs
  - documentation
  - trend
  - help
  - olh
  - knowledge
  - best practice
  - admin guide
  - install guide
---

# Trend Docs Skill

Reads Trend Micro product documentation using Playwright to handle JS-rendered pages.

## CRITICAL: NEVER use WebFetch on docs.trendmicro.com

docs.trendmicro.com is a JavaScript SPA. WebFetch returns EMPTY SHELLS - no content.
ALWAYS use the Playwright executor below. There are NO exceptions to this rule.

## Source Trust Order

When multiple sources cover the same topic, trust them in this order:
1. **docs.trendmicro.com** (OLH - most up to date)
2. **success.trendmicro.com** (KBs - good for troubleshooting, workarounds)
3. **PDF guides** (admin guides, install guides, best practice guides - may be older)

## CRITICAL: Never Assume Product Equivalence

Trend Micro has dozens of distinct products. NEVER conflate them. When search results
return docs about Product A but the user asked about Product B, do NOT present Product A
info as if it answers the question. Instead:

1. Check: do the results actually match the product the user asked about?
2. If no match: re-search with different terms (product name, abbreviation, feature name)
3. If still no match: say "I couldn't find docs specifically for [product/feature]" and
   ask the user to clarify - do NOT fill in the gap with a guess

Example of what NOT to do: user asks about "Service Gateway pcap" -> results are all
about DDI packet capture -> do NOT say "Service Gateway hosts DDI" and present DDI docs.
Service Gateway and DDI are completely different products.

## Completeness Rule

When the user asks about a topic, get the COMPLETE answer. Do not stop at one page
and ask "want me to get more?". Follow references to related pages that complete the
picture. Examples:

- "what actions are available for Gmail?" -> get the actions-for-different-services page
  that covers ALL policy types (malware, spam, DLP, file blocking, web rep, virtual
  analyzer), not just the first page you find about spam
- "how does ZTSA work?" -> get the overview AND the setup pages
- "what are the API endpoints for X?" -> get the full API reference, not just the intro

Use multiple WebSearches if needed to find the right pages. The user expects a complete
answer, not a partial one with a follow-up question.

## Workflow

1. **WebSearch** to find relevant page URLs (search ALL of trendmicro.com, not just one subdomain):
   ```
   WebSearch: site:trendmicro.com "<query terms>"
   ```

2. **Extract content** based on source type:

   **For docs.trendmicro.com and success.trendmicro.com** (JS SPAs - Playwright required):
   ```bash
   python ~/.claude/skills/trend-docs/executor.py --urls "URL1,URL2,URL3" --max-pages 5
   ```

   **For PDF files** (admin guides, install guides, best practice guides):
   ```bash
   # Download PDF, then read with Read tool (supports PDF natively)
   curl -sL -o /tmp/guide.pdf "https://example.trendmicro.com/guide.pdf"
   # Then use Read tool on /tmp/guide.pdf (supports pages parameter for large PDFs)
   ```

3. **Present findings** to the user. ALWAYS include both parts:

   **Summary** - Concise answer in your own words. Use tables, bullet points, and
   headings to organize. Don't dump raw extracted text - synthesize it.

   **Sources** - List every page you extracted from, at the end:
   ```
   Sources:
   - [Page Title (OLH)](https://docs.trendmicro.com/...)
   - [Article Title (KB)](https://success.trendmicro.com/...)
   ```
   Label each source type: OLH, KB, or PDF. This lets the user click through to verify.

## Best Practice Guides Index

Master list of all Trend Micro product best practice guides (PDFs):
**https://success.trendmicro.com/en-US/solution/KA-0007901**

Use this page when the user asks about best practices for any Trend Micro product.
Extract with executor.py first to get PDF download links, then download and read the PDFs.

## Usage Examples

```bash
# Batch URLs from WebSearch results
python ~/.claude/skills/trend-docs/executor.py --urls "https://docs.trendmicro.com/en-us/documentation/article/trend-vision-one-actions-different-services,https://docs.trendmicro.com/en-us/documentation/article/trend-vision-one-advanced-spam-protection"

# Single URL
python ~/.claude/skills/trend-docs/executor.py "https://docs.trendmicro.com/en-us/documentation/article/trend-vision-one-workbench"

# Slug shorthand (OLH only)
python ~/.claude/skills/trend-docs/executor.py "trend-vision-one-workbench"
```

## Output

Clean markdown with:
- Page title as heading
- Source URL for each page
- Content: paragraphs, tables, lists, code blocks
- Related pages (parent/sibling/child) with type labels
- Section dividers between pages
