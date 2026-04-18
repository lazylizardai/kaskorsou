"""
KasKorsou — NotebookLM Site Analyzer
=====================================
Scrape a real estate site with Playwright (rendered HTML),
save HTML + clean markdown to scraper/analysis/ for upload to NotebookLM.

Usage:
  cd KasKorsou-web
  python -m scraper.notebooklm_helper remax
  python -m scraper.notebooklm_helper --url https://www.sunbelt.an/for-sale sunbelt

NotebookLM workflow:
  1. Run this script → analysis/<site>_structure.html + .md saved
  2. Upload .html to NotebookLM notebook
  3. Ask: "What CSS selectors identify property listing cards?"
  4. Ask: "Where is the price, bedrooms, neighborhood, and image in each card?"
  5. Paste exact selectors back into scrapers/<site>.py
"""
import argparse
import asyncio
import os
import re
from datetime import datetime
from pathlib import Path

SITES = {
    "remax":     "https://www.realestate-curacao.com/nl/woningen/koopwoningen/",
    "sunbelt":   "https://www.sunbelt.an/for-sale",
    "century21": "https://www.century21curacao.com/properties",
    "era":       "https://www.eracuracao.com/listings",
}

OUTPUT_DIR = Path(__file__).parent / "analysis"


def html_to_markdown(html: str, url: str) -> str:
    """Very light HTML → markdown conversion for LLM readability."""
    from bs4 import BeautifulSoup, Comment
    soup = BeautifulSoup(html, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()

    lines = []
    lines.append(f"# Site Structure: {url}")
    lines.append(f"_Captured: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    # Walk headings, links, and text blocks
    for el in soup.find_all(["h1","h2","h3","h4","p","li","a","div","span"]):
        text = el.get_text(strip=True)
        if not text or len(text) < 3:
            continue
        classes = " ".join(el.get("class", []))
        eid = el.get("id", "")
        tag = el.name

        if tag in ("h1","h2","h3","h4"):
            level = int(tag[1])
            lines.append(f"\n{'#' * level} {text}")
        elif tag == "a" and el.get("href"):
            href = el["href"]
            lines.append(f"- [{text}]({href})")
        elif classes or eid:
            label = f"[{tag}"
            if classes: label += f".{'.'.join(classes.split()[:3])}"
            if eid: label += f"#{eid}"
            label += "]"
            lines.append(f"{label} {text[:120]}")

    return "\n".join(lines)


async def capture_site(url: str, site_name: str, wait_seconds: int = 4):
    from playwright.async_api import async_playwright

    print(f"\n🔍 Capturing: {url}")
    print("   (Playwright browser opens headfully so JS renders...)")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Let JS render
        print(f"   Waiting {wait_seconds}s for JS to render...")
        await asyncio.sleep(wait_seconds)

        # Scroll to trigger lazy-loading
        for _ in range(4):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)

        html = await page.content()
        await browser.close()

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Save full HTML
    html_path = OUTPUT_DIR / f"{site_name}_{timestamp}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"✅ HTML saved: {html_path} ({len(html):,} chars)")

    # Save markdown for LLM
    md = html_to_markdown(html, url)
    md_path = OUTPUT_DIR / f"{site_name}_{timestamp}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"✅ Markdown saved: {md_path} ({len(md):,} chars)")

    # Print first 2000 chars of markdown as preview
    print("\n--- Markdown preview (first 2000 chars) ---")
    print(md[:2000])
    print("---\n")

    print("📋 Next steps:")
    print(f"  1. Upload {html_path.name} to NotebookLM")
    print("  2. Ask: 'What CSS class or selector identifies a property listing card?'")
    print("  3. Ask: 'Where is price, bedrooms, neighborhood, and image URL in each card?'")
    print(f"  4. Update scrapers/{site_name}.py with exact selectors (zero hallucination!)")

    return html_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Capture site HTML for NotebookLM analysis")
    parser.add_argument("site", nargs="?", choices=list(SITES.keys()), help="Predefined site name")
    parser.add_argument("--url", "-u", help="Custom URL to capture")
    parser.add_argument("--name", "-n", help="Name for output files (required with --url)")
    parser.add_argument("--wait", "-w", type=int, default=4, help="Seconds to wait for JS render (default: 4)")
    args = parser.parse_args()

    if args.url:
        name = args.name or re.sub(r"[^a-z0-9]", "_", args.url.lower())[:30]
        url = args.url
    elif args.site:
        name = args.site
        url = SITES[args.site]
    else:
        parser.print_help()
        print(f"\nAvailable sites: {', '.join(SITES.keys())}")
        return

    asyncio.run(capture_site(url, name, wait_seconds=args.wait))


if __name__ == "__main__":
    main()
