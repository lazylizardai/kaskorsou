"""
Facebook Marketplace scraper via Playwright (priority 10)
Vereist: fb_cookies.json in scraper/ root (export via EditThisCookie extensie)
"""
import json, re, time, random, logging
from pathlib import Path
from ..models import Listing, detect_agency
from ..config import SOURCES

PRIVATE_KEYWORDS = ["particulier", "prive", "privé", "eigenaar", "zelf", "no agent", "by owner"]
AGENCY_KEYWORDS  = ["remax", "re/max", "sunbelt", "century21", "century 21", "era ", "makelaar"]

logger = logging.getLogger("facebook")

COOKIES_FILE = Path(__file__).parent.parent / "fb_cookies.json"
URLS = [
    ("rent",  "https://www.facebook.com/marketplace/curacao/propertyrentals"),
    ("sale",  "https://www.facebook.com/marketplace/curacao/propertyforsale"),
]


class FacebookScraper:
    source_name = "facebook"

    def scrape(self, max_listings: int = 100) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Run: pip install playwright && playwright install chromium")
            return []

        if not COOKIES_FILE.exists():
            logger.error(f"Cookies niet gevonden: {COOKIES_FILE}")
            return []

        source_id = SOURCES[self.source_name]["id"]
        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            with open(COOKIES_FILE) as f:
                ctx.add_cookies(json.load(f))

            page = ctx.new_page()

            for listing_type, url in URLS:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(3)

                if "login" in page.url.lower():
                    logger.error("Niet ingelogd — cookies verlopen, herexporteer.")
                    break

                seen = set()
                scrolls = max_listings // 12
                for i in range(scrolls):
                    cards = page.query_selector_all("a[href*='/marketplace/item/']")
                    for card in cards:
                        try:
                            listing = self._parse(card, source_id, listing_type)
                            if listing and listing.external_id not in seen:
                                seen.add(listing.external_id)
                                results.append(listing)
                        except Exception:
                            pass
                    logger.info(f"FB {listing_type} scroll {i+1}/{scrolls}: {len(seen)} listings")
                    page.evaluate("window.scrollBy(0, window.innerHeight * 0.85)")
                    time.sleep(random.uniform(1.5, 3.5))

            browser.close()

        logger.info(f"Facebook: {len(results)} listings total")
        return results

    def _parse(self, card, source_id: str, listing_type: str) -> Listing | None:
        href = card.get_attribute("href") or ""
        m = re.search(r"/item/(\d+)", href)
        if not m:
            return None
        ext_id = m.group(1)
        url = f"https://www.facebook.com{href}" if href.startswith("/") else href

        text = card.inner_text().strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        title = lines[0] if lines else "Facebook listing"
        price_text = next((l for l in lines if any(c in l for c in ["ANG", "$", "NAf", "€"])), "")
        price_num = re.sub(r"[^\d.]", "", price_text)
        price = float(price_num) if price_num else None

        imgs = [img.get_attribute("src") for img in card.query_selector_all("img[src]")]
        neighborhood = lines[2] if len(lines) > 2 else None

        # Deduplicatie: detecteer of dit een makelaar of particulier is
        full_text = " ".join(lines).lower()
        is_private = any(kw in full_text for kw in PRIVATE_KEYWORDS)
        agency_hint = detect_agency(full_text)

        # Als het een bekende makelaar is → markeer als potentieel duplicaat
        # (orchestrator kan later matchen met kas_listings op prijs+buurt)
        if agency_hint and not is_private:
            # Sla op maar markeer — orchestrator doet de match
            pass

        return Listing(
            source_id=source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type="house",
            price_ang=price,
            url=url,
            neighborhood=neighborhood,
            images=[i for i in imgs if i][:10],
            description=None,
            bedrooms=None,
            bathrooms=None,
            area_sqm=None,
            latitude=None,
            longitude=None,
            is_private=is_private,
            agency_hint=agency_hint,
        )
