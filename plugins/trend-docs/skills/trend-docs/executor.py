#!/usr/bin/env python3
"""
Trend Docs Executor - Playwright extractor for docs.trendmicro.com (JS SPA).
WebFetch returns empty shells on these sites. Playwright is the ONLY way to read them.
Usage: python executor.py --urls "URL1,URL2" or python executor.py "slug-name"
Workflow: WebSearch finds URLs -> this script extracts them -> Claude summarizes.
~25s/page (5s browser launch + 20s SPA hydration). Parallel tabs for multi-page.

PDF support: Detects .pdf URLs, downloads via Playwright (handles Akamai cookie
redirects that break curl with exit code 47), saves to ~/Downloads, extracts text
with PyPDF2.

Lessons learned:
- "networkidle" adds 10-15s for trackers; use "domcontentloaded" + selector wait
- Blind sleep loops (2s+3s+5s) waste 10s/page; wait for .main-content instead
- OLH uses .main-content, KB uses main.article-page - different extractors
- Pipe chars in table cells replaced with / to avoid breaking markdown tables
- One 2s retry if content <100 chars catches slow hydration edge cases
- docs.trendmicro.com PDFs use Akamai CDN that sets ew-request cookie + redirect
  loop; curl fails with exit 47 (max redirects). Playwright handles cookies natively.
- ohc.blob.core.windows.net PDFs work with curl (direct Azure blob, no Akamai)
"""

import sys
import os
import re
import argparse
import logging
import io
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def ensure_playwright():
    """Auto-install playwright + chromium if missing."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        import subprocess
        print("[trend-docs] Installing playwright...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        print("[trend-docs] Installing chromium browser...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright
        return sync_playwright

sync_playwright = ensure_playwright()

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


def is_pdf(url):
    return url.lower().rstrip("/").endswith(".pdf")


def get_downloads_dir():
    """Get ~/Downloads, create if missing."""
    dl = Path.home() / "Downloads"
    dl.mkdir(exist_ok=True)
    return dl


def ensure_pypdf2():
    """Auto-install PyPDF2 if missing."""
    try:
        import PyPDF2
        return PyPDF2
    except ImportError:
        import subprocess
        log.info("[trend-docs] Installing PyPDF2...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2", "-q"])
        import PyPDF2
        return PyPDF2


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


# ============ PDF Download + Extract ============

def download_pdf_playwright(url, context):
    """Download PDF via Playwright (handles Akamai cookie redirects that break curl).
    Saves to ~/Downloads, returns (local_path, filename) or (None, error_msg)."""
    downloads_dir = get_downloads_dir()
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    save_path = downloads_dir / filename

    try:
        page = context.new_page()
        # Intercept the download triggered by navigating to a PDF URL
        with page.expect_download(timeout=30000) as dl_info:
            page.goto(url, timeout=30000)
        download = dl_info.value
        download.save_as(str(save_path))
        page.close()
        return str(save_path), filename
    except Exception:
        # Fallback: some PDFs render in-browser instead of downloading.
        # Try a direct request via Playwright's API context.
        try:
            page.close()
        except Exception:
            pass
        try:
            api_ctx = context.request
            resp = api_ctx.get(url)
            if resp.status == 200 and len(resp.body()) > 1000:
                save_path.write_bytes(resp.body())
                return str(save_path), filename
        except Exception as e2:
            return None, f"Download failed: {e2}"
    return None, "Download failed: unknown error"


def extract_pdf_text(pdf_path, pages=None):
    """Extract text from PDF using PyPDF2. Returns markdown string."""
    PyPDF2 = ensure_pypdf2()
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        total = len(reader.pages)
        # Parse page range like "1-5" or "3" or None (all)
        if pages:
            parts = pages.split("-")
            start = int(parts[0]) - 1
            end = int(parts[1]) if len(parts) > 1 else start + 1
        else:
            start, end = 0, min(total, 20)  # Cap at 20 pages by default

        texts = []
        for i in range(start, min(end, total)):
            text = reader.pages[i].extract_text()
            if text and text.strip():
                texts.append(f"--- Page {i+1} ---\n{text.strip()}")

        filename = Path(pdf_path).name
        header = f"# {filename}\nSource: {pdf_path}\nPages: {start+1}-{min(end, total)} of {total}\n\n"
        return header + "\n\n".join(texts) if texts else header + "(No extractable text)"
    except Exception as e:
        return f"# PDF Extract Error\n{e}"


# ============ Main ============

def run_batch(urls, max_pages=10):
    """Extract multiple URLs in parallel tabs within a single browser."""
    urls = [u.strip() for u in urls if u.strip()][:max_pages]
    if not urls:
        print("No URLs provided.")
        return

    # Separate PDF URLs from HTML URLs
    pdf_urls = [u for u in urls if is_pdf(u)]
    html_urls = [u for u in urls if not is_pdf(u)]

    output_sections = []
    t0 = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
        context = browser.new_context(user_agent=UA, java_script_enabled=True,
                                       accept_downloads=True)

        # Handle PDF downloads first
        for i, url in enumerate(pdf_urls):
            log.info(f"[pdf {i+1}] downloading {url}")
            path, info = download_pdf_playwright(url, context)
            if path:
                log.info(f"  [pdf {i+1}] saved: {path}")
                text = extract_pdf_text(path)
                if text:
                    output_sections.append(text)
                # Always notify where PDF was saved
                print(f"[SAVED] {info} -> {path}")
            else:
                log.info(f"  [pdf {i+1}] FAILED: {info}")

        # Open all HTML pages in parallel tabs
        tabs = []
        for i, url in enumerate(html_urls):
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

    log.info(f"\n[done] {len(urls)} pages ({len(pdf_urls)} PDF, {len(html_urls)} HTML), {len(output_sections)} returned, {elapsed:.1f}s")


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
