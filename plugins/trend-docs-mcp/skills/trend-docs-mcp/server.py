#!/usr/bin/env python3
"""
mcp-trend-docs - Search and extract Trend Micro documentation.

docs.trendmicro.com and success.trendmicro.com are JS SPAs - WebFetch returns
empty shells. This server uses Playwright to render pages and extract content.

Tools:
  trend_docs_search  - DuckDuckGo site:trendmicro.com search (no API key)
  trend_docs_extract - Playwright-based page extraction (HTML + PDF)

Pipeline: search -> pick URLs -> extract -> Claude synthesizes answer.

NOTE: FastMCP runs in asyncio, so Playwright MUST use async API.
"""

import sys
import os
import io
import re
import time
import asyncio
import subprocess
import logging
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="[trend-docs] %(message)s")
log = logging.getLogger("trend-docs")

from mcp.server.fastmcp import FastMCP


# ============ Auto-install helpers ============

def ensure_ddgs():
    """Auto-install ddgs if missing."""
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        log.info("Installing ddgs...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ddgs", "-q"])
        from ddgs import DDGS
        return DDGS


def ensure_playwright_async():
    """Auto-install playwright + chromium if missing. Returns async_playwright."""
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except ImportError:
        log.info("Installing playwright...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
        log.info("Installing chromium browser...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.async_api import async_playwright
        return async_playwright


def ensure_pypdf2():
    """Auto-install PyPDF2 if missing."""
    try:
        import PyPDF2
        return PyPDF2
    except ImportError:
        log.info("Installing PyPDF2...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2", "-q"])
        import PyPDF2
        return PyPDF2


# ============ Constants ============

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

def is_olh(url):
    return "docs.trendmicro.com" in url


def is_pdf(url):
    return url.lower().rstrip("/").endswith(".pdf")


def get_downloads_dir():
    dl = Path.home() / "Downloads"
    dl.mkdir(exist_ok=True)
    return dl


# ============ JS extractors (from executor.py) ============

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


# ============ Search module ============

def search_trendmicro(query, max_results=10):
    """DuckDuckGo site:trendmicro.com search. Returns [{title, url, snippet}]."""
    DDGS = ensure_ddgs()
    full_query = f"site:trendmicro.com {query}"
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(full_query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", "")),
            })
    return results


def format_search_results(results):
    """Format search results as numbered markdown list."""
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        source_type = "OLH" if "docs.trendmicro.com" in r["url"] else \
                      "KB" if "success.trendmicro.com" in r["url"] else \
                      "PDF" if r["url"].lower().endswith(".pdf") else "Other"
        lines.append(f"{i}. [{source_type}] {r['title']}")
        lines.append(f"   {r['url']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet'][:200]}")
        lines.append("")
    return "\n".join(lines)


# ============ Async extract module ============

async def async_extract_page(page_obj, url):
    """Run JS extractor on a loaded Playwright page (async)."""
    js = OLH_EXTRACT_JS if is_olh(url) else KB_EXTRACT_JS
    try:
        result = await page_obj.evaluate(js)
        result["url"] = url
        return result
    except Exception as e:
        return {"content": f"Error extracting: {e}", "title": url, "url": url, "related": []}


async def async_wait_and_extract(page_obj, url):
    """Wait for SPA content to render, then extract (async)."""
    content_sel = ".main-content" if is_olh(url) else "main.article-page, main"
    try:
        await page_obj.wait_for_selector(content_sel, timeout=10000)
    except Exception:
        pass
    await page_obj.wait_for_timeout(500)
    result = await async_extract_page(page_obj, url)
    # Retry once if SPA shell not rendered
    if not result["content"] or len(result["content"]) < 100 or "window[" in result["content"][:200]:
        await page_obj.wait_for_timeout(2000)
        result = await async_extract_page(page_obj, url)
    return result


async def async_download_pdf(url, context):
    """Download PDF via Playwright async (handles Akamai cookie redirects).
    Saves to ~/Downloads. Returns (local_path, filename) or (None, error_msg)."""
    downloads_dir = get_downloads_dir()
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    save_path = downloads_dir / filename

    try:
        page = await context.new_page()
        async with page.expect_download(timeout=30000) as dl_info:
            await page.goto(url, timeout=30000)
        download = dl_info.value
        await download.save_as(str(save_path))
        await page.close()
        return str(save_path), filename
    except Exception:
        try:
            await page.close()
        except Exception:
            pass
        # Fallback: direct request via Playwright API context
        try:
            resp = await context.request.get(url)
            if resp.status == 200 and len(await resp.body()) > 1000:
                save_path.write_bytes(await resp.body())
                return str(save_path), filename
        except Exception as e2:
            return None, f"Download failed: {e2}"
    return None, "Download failed: unknown error"


def extract_pdf_text(pdf_path, url=""):
    """Extract text from PDF using PyPDF2. Returns markdown string."""
    PyPDF2 = ensure_pypdf2()
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        total = len(reader.pages)
        page_limit = min(total, 20)

        texts = []
        for i in range(page_limit):
            text = reader.pages[i].extract_text()
            if text and text.strip():
                texts.append(f"--- Page {i+1} ---\n{text.strip()}")

        filename = Path(pdf_path).name
        header = f"# {filename}\nSource: {url or pdf_path}\nPages: 1-{page_limit} of {total}\n\n"
        return header + "\n\n".join(texts) if texts else header + "(No extractable text)"
    except Exception as e:
        return f"# PDF Extract Error\n{e}"


async def async_extract_pages(urls):
    """Extract content from a list of URLs (async). Returns markdown string."""
    urls = [u.strip() for u in urls if u.strip()]
    if not urls:
        return "No URLs provided."

    pdf_urls = [u for u in urls if is_pdf(u)]
    html_urls = [u for u in urls if not is_pdf(u)]

    sections = []
    saved_files = []
    t0 = time.time()

    async_playwright = ensure_playwright_async()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
        context = await browser.new_context(
            user_agent=UA, java_script_enabled=True, accept_downloads=True
        )

        # PDF downloads
        for url in pdf_urls:
            log.info(f"Downloading PDF: {url}")
            path, info = await async_download_pdf(url, context)
            if path:
                log.info(f"  Saved: {path}")
                text = extract_pdf_text(path, url)
                if text:
                    sections.append(text)
                saved_files.append(path)
            else:
                sections.append(f"# PDF Download Failed\nURL: {url}\nError: {info}")

        # HTML pages - open in parallel tabs
        tabs = []
        for url in html_urls:
            log.info(f"Loading: {url}")
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                tabs.append((page, url))
            except Exception as e:
                sections.append(f"# Navigation Error\nURL: {url}\nError: {e}")
                try:
                    await page.close()
                except Exception:
                    pass

        # Extract from each tab
        for page, url in tabs:
            try:
                result = await async_wait_and_extract(page, url)
                title = result.get("title", url)
                body = result.get("content", "")
                related = result.get("related", [])

                if "Article unavailable" in title or "window[" in body[:200]:
                    sections.append(f"# Page Unavailable\nURL: {url}")
                elif body and len(body) > 50:
                    section = f"# {title}\nSource: {url}\n\n{body}"
                    if related:
                        section += "\n\n## Related Pages\n"
                        for rel in related[:10]:
                            rtype = rel.get("type", "")
                            rtitle = rel.get("title", "")
                            rslug = rel.get("slug", "")
                            section += f"- [{rtype}] {rtitle} ({rslug})\n"
                    sections.append(section)
                else:
                    sections.append(f"# Insufficient Content\nURL: {url}\nExtracted < 50 chars.")
            except Exception as e:
                sections.append(f"# Extraction Error\nURL: {url}\nError: {e}")

        await context.close()
        await browser.close()

    elapsed = time.time() - t0
    output = "\n\n---\n\n".join(sections) if sections else "No content extracted."

    if saved_files:
        output += "\n\n## Files Saved\n"
        for f in saved_files:
            output += f"- {f}\n"

    output += f"\n\n[{len(urls)} pages ({len(pdf_urls)} PDF, {len(html_urls)} HTML), {elapsed:.1f}s]"
    return output


# ============ FastMCP server ============

INSTRUCTIONS = """\
## Workflow
1. Use trend_docs_search(query) to find relevant page URLs
2. Review results - verify they match the product/feature asked about
3. Use trend_docs_extract(urls) to read the pages

## Search Preference
- ALWAYS prefer trend_docs_search over Claude's built-in WebSearch for Trend Micro docs
- Only fall back to WebSearch if DDG returns errors or no results
- Always retry with different terms before falling back

## Rules
- Source trust: docs.trendmicro.com (OLH) > success.trendmicro.com (KB) > PDF guides
- NEVER assume product equivalence (DDI != Service Gateway, etc.)
- Get COMPLETE answers - extract multiple related pages if needed
- Always present: Summary (synthesized) + Sources (labeled OLH/KB/PDF links)
"""

mcp = FastMCP("trend-docs", instructions=INSTRUCTIONS)


@mcp.tool()
def trend_docs_search(query: str, max_results: int = 10) -> str:
    """Search Trend Micro documentation via DuckDuckGo.

    Returns numbered list of results with title, URL, snippet, and source type
    (OLH/KB/PDF). Use the URLs with trend_docs_extract to read page content.

    Args:
        query: Search terms. Use product names and feature keywords.
        max_results: Max results to return (default 10).

    Product abbreviations for better search results:
        DDAN = Deep Discovery Analyzer    DDI  = Deep Discovery Inspector
        ZTSA = Zero Trust Secure Access   SAM  = Secure Access Module
        VNS  = Virtual Network Sensor     CECP = Cloud Email/Collaboration Protection
        IMSVA = InterScan Messaging       IWSVA = InterScan Web Security
        CAS  = Cloud App Security         TMCM = Trend Micro Control Manager

    Examples:
        trend_docs_search("ZTSA pac file configuration")
        trend_docs_search("DDI packet capture setup")
        trend_docs_search("Vision One workbench alert API")
    """
    try:
        results = search_trendmicro(query, max_results)
        return format_search_results(results)
    except Exception as e:
        return (
            f"[DDG search failed: {e}]\n"
            f"Fallback: Use your built-in web search with: site:trendmicro.com {query}\n"
            f"Then pass found URLs to trend_docs_extract."
        )


@mcp.tool()
async def trend_docs_extract(urls: str, max_pages: int = 5) -> str:
    """Extract content from Trend Micro documentation pages.

    Reads HTML pages via Playwright (handles JS SPA rendering) and downloads
    PDFs (handles Akamai cookie redirects). Returns clean markdown with page
    titles, source URLs, content, and related pages.

    Args:
        urls: Comma-separated URLs to extract. Supports docs.trendmicro.com,
              success.trendmicro.com, and PDF URLs.
        max_pages: Max pages to process (default 5).

    PDF handling:
        - PDF URLs are auto-detected by .pdf extension
        - Downloaded via Playwright (handles Akamai CDN redirects)
        - Saved to ~/Downloads/
        - Text extracted with PyPDF2

    Examples:
        trend_docs_extract("https://docs.trendmicro.com/en-us/documentation/article/trend-vision-one-workbench")
        trend_docs_extract("https://docs.trendmicro.com/.../page1,https://success.trendmicro.com/.../page2")
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()][:max_pages]
    if not url_list:
        return "No URLs provided. Use trend_docs_search first to find page URLs."
    return await async_extract_pages(url_list)


if __name__ == "__main__":
    mcp.run()
