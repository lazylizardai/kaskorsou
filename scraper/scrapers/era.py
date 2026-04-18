"""
ERA Real Estate Curaçao scraper (priority 7)
Site: https://www.eracuracao.com
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing
from ..config import SOURCES


class ERAScraper(BaseScraper):
    source_name = "era"
    BASE = "https://www.eracuracao.com"

    SEARCH_PATHS = [
        "/buy/",
        "/rent/",
    ]

    def scrape(self) -> list[Listing]:
        results = []
        source_id = SOURCES[self.source_name]["id"]

        for path in self.SEARCH_PATHS:
            listing_type = "sale" if path == "/buy/" else "rent"
            page = 1
            while True:
                url = f"{self.BASE}{path}?p={page}"
                soup = self.get(url)
                if soup is None:
                    break

                cards = soup.select(
                    ".object-item, .property-card, article.object, [class*='listing']"
                )
                if not cards:
                    break

                for card in cards:
                    try:
                        listing = self._parse_card(card, source_id, listing_type)
                        if listing:
                            results.append(listing)
                    except Exception as e:
                        self.logger.warning(f"ERA card parse error: {e}")
                        continue

                next_link = soup.select_one("a.next, a[rel='next'], .pager .next a")
                if not next_link or page >= 15:
                    break
                page += 1

        self.logger.info(f"ERA: {len(results)} listings scraped")
        return results

    def _parse_card(self, card, source_id: str, listing_type: str):
        link = card.select_one("a[href]")
        if not link:
            return None
        href = self.abs_url(self.BASE, link["href"])
        external_id = re.sub(r"[^a-z0-9]", "-", href.lower()).strip("-")[-80:]

        # Title / address
        title_el = card.select_one("h2, h3, .object-title, .address, .street")
        title = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = card.select_one(".price, .object-price, [class*='price']")
        price_raw = price_el.get_text(strip=True) if price_el else ""
        price = self.parse_price(price_raw)

        # Property type
        title_lower = title.lower()
        if any(w in title_lower for w in ["villa", "house", "woning"]):
            prop_type = "house"
        elif any(w in title_lower for w in ["apartment", "appartement"]):
            prop_type = "apartment"
        elif "land" in title_lower:
            prop_type = "land"
        else:
            prop_type = "house"

        # Neighborhood — ERA often includes area/district
        neighborhood_el = card.select_one(".area, .district, .location, [class*='area']")
        neighborhood = neighborhood_el.get_text(strip=True) if neighborhood_el else None

        # Specs (beds, area)
        beds_el = card.select_one("[class*='bed'], [class*='slaap']")
        bedrooms = self.parse_int(beds_el.get_text() if beds_el else "")

        area_el = card.select_one("[class*='area'], [class*='opp'], [class*='size']")
        area = self.parse_area(area_el.get_text() if area_el else "")

        img_el = card.select_one("img[src]")
        images = [self.abs_url(self.BASE, img_el["src"])] if img_el else []

        return Listing(
            source_id=source_id,
            external_id=external_id,
            title=title or "ERA Property",
            listing_type=listing_type,
            property_type=prop_type,
            price_ang=price,
            bedrooms=bedrooms,
            area_sqm=area,
            neighborhood=neighborhood,
            images=images,
            url=href,
            description=None,
            bathrooms=None,
            latitude=None,
            longitude=None,
        )
