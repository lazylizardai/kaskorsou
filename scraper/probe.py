from playwright.sync_api import sync_playwright
import json

api_calls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=True)

    def on_request(req):
        url = req.url
        if not any(x in url for x in ["google", "font", "analytics", ".png", ".jpg", ".css", ".ico"]):
            api_calls.append(f"{req.method} {url}")

    page.on("request", on_request)
    page.goto("https://www.remax-bonbini.com/", wait_until="networkidle", timeout=20000)

    print(f"Title: {page.title()}")
    print(f"\nAll requests ({len(api_calls)}):")
    for c in api_calls[:30]:
        print(" ", c)

    # Look for any nav links
    links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href).filter(h => h.includes('remax'))")
    print(f"\nInternal links:")
    for l in set(links[:20]):
        print(" ", l)

    browser.close()
