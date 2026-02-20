#!/usr/bin/env python3
"""
Trend Docs Executor - Playwright extractor for docs.trendmicro.com (JS SPA).
WebFetch returns empty shells on these sites. Playwright is the ONLY way to read them.
Usage: python executor.py --urls "URL1,URL2" or python executor.py "slug-name"
Workflow: WebSearch finds URLs -> this script extracts them -> Claude summarizes.
~25s/page (5s browser launch + 20s SPA hydration). Parallel tabs for multi-page.

Lessons learned:
- "networkidle" adds 10-15s for trackers; use "domcontentloaded" + selector wait
- Blind sleep loops (2s+3s+5s) waste 10s/page; wait for .main-content instead
- OLH uses .main-content, KB uses main.article-page - different extractors
- Pipe chars in table cells replaced with / to avoid breaking markdown tables
- One 2s retry if content <100 chars catches slow hydration edge cases
"""

import sys
import re
import argparse
import logging
import io
import time

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install playwright && playwright install chromium")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("trend-docs")

# ============ Constants ============

OLH_BASE = "https://docs.trendmicro.com/en-us/documentation/article/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BROWSER_ARGS = [
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--no-first-run",
    "--disable-sync",
]


# ============ Helpers ============

def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def is_slug(text):
    return re.match(r"^[a-z0-9-]+$", text) and len(text) > 10


def is_olh(url):
    return "docs.trendmicro.com" in url


# ============ Content Extraction JS ============

OLH_EXTRACT_JS = """() => {
    const res = {content: "", title: document.title, related: []};
    const main = document.querySelector(".main-content");
    if (!main) { res.content = document.body.textContent.trim().substring(0, 5000); return res; }
    const clone = main.cloneNode(true);
    const menu = clone.querySelector(".article-menu");
    if (menu) menu.remove();

    function toMd(node) {
        if (!node) return "";
        if (node.nodeType === 3) return node.textContent;
        if (node.nodeType !== 1) return "";
        const tag = node.tagName;
        const kids = Array.from(node.childNodes).map(c => toMd(c)).join("");
        if (/^H[1-6]$/.test(tag)) return "\\n" + "#".repeat(parseInt(tag[1])) + " " + kids.trim() + "\\n\\n";
        if (tag === "P") return kids.trim() + "\\n\\n";
        if (tag === "LI") return "- " + kids.trim() + "\\n";
        if (tag === "UL" || tag === "OL") return "\\n" + kids + "\\n";
        if (tag === "PRE" || tag === "CODE") return "```\\n" + node.textContent.trim() + "\\n```\\n\\n";
        if (tag === "BR") return "\\n";
        if (tag === "A" && node.href) return "[" + kids.trim() + "](" + node.href + ")";
        if (tag === "STRONG" || tag === "B") return "**" + kids.trim() + "**";
        if (tag === "EM" || tag === "I") return "*" + kids.trim() + "*";
        if (tag === "TABLE") {
            const rows = node.querySelectorAll("tr");
            if (rows.length === 0) return kids;
            let md = "\\n";
            rows.forEach((row, i) => {
                const cells = Array.from(row.querySelectorAll("th, td"));
                md += "| " + cells.map(c => c.textContent.trim().replace(/\\|/g, "/")).join(" | ") + " |\\n";
                if (i === 0) md += "| " + cells.map(() => "---").join(" | ") + " |\\n";
            });
            return md + "\\n";
        }
        if (["THEAD","TBODY","TFOOT","TR","TH","TD"].includes(tag)) return "";
        return kids;
    }

    res.content = toMd(clone).replace(/\\n{3,}/g, "\\n\\n").trim();

    // Related pages from sidebar menu
    const menuEl = document.querySelector(".article-menu");
    if (menuEl) {
        const currentSlug = window.location.pathname.split("/").pop();
        const allLinks = menuEl.querySelectorAll("a.item-link");
        let currentLi = null;
        for (const link of allLinks) {
            const href = link.getAttribute("href") || "";
            if (href === currentSlug || href.endsWith("/" + currentSlug)) { currentLi = link.closest("li"); break; }
        }
        if (currentLi) {
            const childGroup = currentLi.querySelector(":scope > .menu-group > ul");
            if (childGroup) {
                childGroup.querySelectorAll(":scope > li > .menu-item > a.item-link").forEach(a => {
                    res.related.push({title: a.textContent.trim(), slug: a.getAttribute("href"), type: "child"});
                });
            }
            const parentUl = currentLi.parentElement;
            if (parentUl) {
                parentUl.querySelectorAll(":scope > li > .menu-item > a.item-link").forEach(a => {
                    const slug = a.getAttribute("href");
                    if (slug !== currentSlug) res.related.push({title: a.textContent.trim(), slug: slug, type: "sibling"});
                });
            }
            const parentLi = currentLi.parentElement ? currentLi.parentElement.closest("li") : null;
            if (parentLi) {
                const pl = parentLi.querySelector(":scope > .menu-item > a.item-link");
                if (pl) res.related.push({title: pl.textContent.trim(), slug: pl.getAttribute("href"), type: "parent"});
            }
        }
    }
    return res;
}"""


KB_EXTRACT_JS = """() => {
    const res = {content: "", title: document.title, related: []};
    const main = document.querySelector("main.article-page, main");
    if (!main) { res.content = document.body.textContent.trim().substring(0, 5000); return res; }
    function toMd(node) {
        if (!node) return "";
        if (node.nodeType === 3) return node.textContent;
        if (node.nodeType !== 1) return "";
        const tag = node.tagName;
        if (["NAV","HEADER","FOOTER","SCRIPT","STYLE","NOSCRIPT"].includes(tag)) return "";
        const kids = Array.from(node.childNodes).map(c => toMd(c)).join("");
        if (/^H[1-6]$/.test(tag)) return "\\n" + "#".repeat(parseInt(tag[1])) + " " + kids.trim() + "\\n\\n";
        if (tag === "P") return kids.trim() + "\\n\\n";
        if (tag === "LI") return "- " + kids.trim() + "\\n";
        if (tag === "UL" || tag === "OL") return "\\n" + kids + "\\n";
        if (tag === "PRE" || tag === "CODE") return "```\\n" + node.textContent.trim() + "\\n```\\n\\n";
        if (tag === "BR") return "\\n";
        if (tag === "A" && node.href) return "[" + kids.trim() + "](" + node.href + ")";
        if (tag === "STRONG" || tag === "B") return "**" + kids.trim() + "**";
        if (tag === "TABLE") {
            const rows = node.querySelectorAll("tr");
            let md = "\\n";
            rows.forEach((row, i) => {
                const cells = Array.from(row.querySelectorAll("th, td"));
                md += "| " + cells.map(c => c.textContent.trim().replace(/\\|/g, "/")).join(" | ") + " |\\n";
                if (i === 0) md += "| " + cells.map(() => "---").join(" | ") + " |\\n";
            });
            return md + "\\n";
        }
        if (["THEAD","TBODY","TFOOT","TR","TH","TD"].includes(tag)) return "";
        return kids;
    }
    res.content = toMd(main).replace(/\\n{3,}/g, "\\n\\n").trim();
    return res;
}"""


# ============ Extraction ============

def extract_page(page_obj, url):
    """Extract content from a loaded Playwright page."""
    js = OLH_EXTRACT_JS if is_olh(url) else KB_EXTRACT_JS
    try:
        result = page_obj.evaluate(js)
        result["url"] = url
        return result
    except Exception as e:
        return {"content": f"Error extracting: {e}", "title": url, "url": url, "related": []}


def wait_and_extract(page_obj, url):
    """Wait for content to render on an already-navigating page, then extract."""
    content_sel = ".main-content" if is_olh(url) else "main.article-page, main"
    try:
        page_obj.wait_for_selector(content_sel, timeout=10000)
    except Exception:
        pass
    page_obj.wait_for_timeout(500)
    result = extract_page(page_obj, url)
    # Retry once if SPA shell not rendered
    if not result["content"] or len(result["content"]) < 100 or "window[" in result["content"][:200]:
        page_obj.wait_for_timeout(2000)
        result = extract_page(page_obj, url)
    return result


# ============ Main ============

def run_batch(urls, max_pages=10):
    """Extract multiple URLs in parallel tabs within a single browser."""
    urls = [u.strip() for u in urls if u.strip()][:max_pages]
    if not urls:
        print("No URLs provided.")
        return

    output_sections = []
    t0 = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
        context = browser.new_context(user_agent=UA, java_script_enabled=True)

        # Open all pages in parallel tabs
        tabs = []
        for i, url in enumerate(urls):
            log.info(f"[tab {i+1}] loading {url}")
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            tabs.append((page, url))

        # Extract from each tab (they've been loading in parallel)
        for i, (page, url) in enumerate(tabs):
            try:
                result = wait_and_extract(page, url)
                title = result.get("title", url)
                body = result.get("content", "")
                if "Article unavailable" in title or "window[" in body[:200]:
                    log.info(f"  [{i+1}] SKIP: dead/broken ({title[:40]})")
                elif body and len(body) > 50:
                    section = "# " + title + "\nSource: " + url + "\n\n" + body
                    output_sections.append(section)
                else:
                    log.info(f"  [{i+1}] SKIP: too little content")
            except Exception as e:
                log.info(f"  [{i+1}] ERROR: {e}")

        context.close()
        browser.close()

    elapsed = time.time() - t0

    if not output_sections:
        print("No relevant content found.")
    else:
        print("\n\n---\n\n".join(output_sections))

    log.info(f"\n[done] {len(urls)} pages, {len(output_sections)} returned, {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Extract Trend Micro documentation pages")
    parser.add_argument("query", nargs="?", default=None, help="Direct URL or article slug")
    parser.add_argument("--urls", "-u", default=None, help="Comma-separated URLs (batch mode)")
    parser.add_argument("--max-pages", "-m", type=int, default=10, help="Max pages to fetch (default 10)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    args = parser.parse_args()
    if args.quiet:
        log.setLevel(logging.WARNING)

    if args.urls:
        url_list = [u.strip() for u in args.urls.split(",") if u.strip()]
        run_batch(url_list, args.max_pages)
    elif args.query:
        if is_url(args.query):
            run_batch([args.query], args.max_pages)
        elif is_slug(args.query):
            run_batch([OLH_BASE + args.query], args.max_pages)
        else:
            parser.error("Query must be a URL or slug. Use WebSearch for discovery, then pass URLs here.")
    else:
        parser.error("Either a URL/slug or --urls is required")


if __name__ == "__main__":
    main()
