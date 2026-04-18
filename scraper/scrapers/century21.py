"""
Century21 Curaçao scraper (priority 8)
Site: https://www.century21curacao.com
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing
from ..config import SOURCES


class Century21Scraper(BaseScraper):
    source_name = "century21"
    BASE = "https://www.century21curacao.com"

    SEARCH_PATHS = [
        "/properties-for-sale/",
        "/properties-for-rent/",
    ]

    def scrape(self) -> list[Listing]:
        results = []
        source_id = SOURCES[self.source_name]["id"]

        for path in self.SEARCH_PATHS:
            listing_type = "sale" if "sale" in path else "rent"
            page = 1
            while True:
                url = f"{self.BASE}{path}?page={page}"
                soup = self.get(url)
                if soup is None:
                    break

                cards = soup.select(".property-item, .listing-item, article.property")
                if not cards:
                    # Try alternative selectors
                    cards = soup.select("[class*='property'], [class*='listing']")
                if not cards:
                    break

                for card in cards:
                    try:
                        listing = self._parse_card(card, source_id, listing_type)
                        if listing:
                            results.append(listing)
                    except Exception as e:
                        self.logger.warning(f"Card parse error: {e}")
                        continue

                # Check for next page
                next_btn = soup.select_one("a.next, a[rel='next'], .pagination .next")
                if not next_btn or page >= 20:
                    break
                page += 1

        self.logger.info(f"Century21: {len(results)} listings scraped")
        return results

    def _parse_card(self, card, source_id: str, listing_type: str):
        # URL + external ID
        link = card.select_one("a[href]")
        if not link:
            return None
        href = self.abs_url(self.BASE, link["href"])
        external_id = re.sub(r"[^a-z0-9]", "-", href.lower()).strip("-")[-80:]

        # Title
        title_el = card.select_one("h2, h3, .title, .property-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = card.select_one(".price, [class*='price']")
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price = self.parse_price(price_raw)

        # Property type from title
        title_lower = title.lower()
        if any(w in title_lower for w in ["villa", "house", "woning", "home"]):
            prop_type = "house"
        elif any(w in title_lower for w in ["apartment", "appartement", "condo"]):
            prop_type = "apartment"
        elif "land" in title_lower or "lot" in title_lower:
            prop_type = "land"
        elif "commercial" in title_lower or "office" in title_lower:
            prop_type = "commercial"
        else:
            prop_type = "house"

        # Bedrooms
        beds_el = card.select_one("[class*='bed'], [class*='room']")
        bedrooms = self.parse_int(beds_el.get_text() if beds_el else "")

        # Area
        area_el = card.select_one("[class*='area'], [class*='size'], [class*='sqm']")
        area = self.parse_area(area_el.get_text() if area_el else "")

        # Image
        img_el = card.select_one("img[src]")
        images = [self.abs_url(self.BASE, img_el["src"])] if img_el else []

        return Listing(
            source_id=source_id,
            external_id=external_id,
            title=title or "Century21 Property",
            listing_type=listing_type,
            property_type=prop_type,
            price_ang=price,
            bedrooms=bedrooms,
            area_sqm=area,
            images=images,
            url=href,
            neighborhood=None,
            description=None,
            bathrooms=None,
            latitude=None,
            longitude=None,
        )
