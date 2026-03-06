# trend-docs

Extract Trend Micro product documentation from JS-rendered SPA pages that `curl` and `WebFetch` cannot read.

## Why

docs.trendmicro.com is a JavaScript Single Page App. Standard HTTP tools return empty HTML shells with zero content. This skill uses Playwright (headless Chromium) to render pages fully, then extracts clean markdown.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install trend-docs@grobomo-marketplace --scope user
```

Dependencies auto-install on first run: `playwright` + Chromium, `PyPDF2`, `pyyaml`.

## Files

```
trend-docs/
  SKILL.md          Claude agent instructions (workflow, rules, examples)
  executor.py       Playwright extractor (self-installing deps)
  doc-slugs.yaml    Topic-to-URL index for known pages (skip WebSearch)
  cache/            Auto-created: .md extracts + .hash/.ihash sidecars
```

## Usage

```bash
# Extract by URL
python executor.py "https://docs.trendmicro.com/en-us/.../trend-vision-one-workbench"

# Extract by slug (OLH shorthand)
python executor.py "trend-vision-one-workbench"

# Batch URLs from WebSearch results
python executor.py --urls "URL1,URL2,URL3" --max-pages 5

# Topic lookup -- resolves keyword to known URLs, serves from cache
python executor.py --topic "firewall policy"
python executor.py --topic "sep anti-malware"    # fetches 7-page bundle

# Force fresh fetch (bypass 30-day cache)
python executor.py --no-cache --topic "endpoint security policies"
```

## Cache

Pages cached as `.md` in `cache/`. Cached pages return in <0.1s vs ~15s for Playwright.

| File | Purpose |
|------|---------|
| `slug.md` | Extracted markdown content |
| `slug.md.hash` | MD5 of markdown (set on write) |
| `slug.md.ihash` | MD5 of live page content (set by --check-cache) |

**TTL:** 30 days. Docs rarely change.

### Detect Changes

```bash
# First run seeds hashes, subsequent runs detect changes
python executor.py --check-cache

# Auto-refresh changed pages in one pass
python executor.py --check-cache --refresh

# Check only a topic bundle
python executor.py --check-cache --topic "sep policy"
```

Hashes 4 signals per page (title, meta description, article body, related links sidebar).
Excludes nav chrome and user session elements to prevent false positives.

## Topic Bundles

`doc-slugs.yaml` maps keywords to OLH slugs. Bundles fetch all pages at once:

```yaml
# Single page
firewall policy: trend-vision-one-firewall-policy-settings

# Bundle -- all 7 pages fetched in one call
sep anti-malware:
  - trend-vision-one-policies-anti-malware
  - trend-vision-one-anti-malware-policy-settings
  - trend-vision-one-configuring-real-time-scan-settings
  # ... (see doc-slugs.yaml for full list)
```

Add entries for pages you access frequently.

## Output

Clean markdown per page with title, source URL, content (paragraphs, tables, links, code blocks), and related pages. Multiple pages separated by `---`.
