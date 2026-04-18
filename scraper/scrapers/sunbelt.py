"""Sunbelt Realty scraper (priority 9) — sunbelt.an"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing


class SunbeltScraper(BaseScraper):
    source_name = "sunbelt"
    BASE = "https://www.sunbelt.an"

    PATHS = [("sale", "/for-sale"), ("rent", "/for-rent")]

    def scrape(self) -> list[Listing]:
        results = []
        for listing_type, path in self.PATHS:
            page = 1
            while page <= 15:
                soup = self.get(f"{self.BASE}{path}?page={page}")
                if not soup:
                    break
                cards = soup.select(
                    ".property, .listing, .house-item, [class*='property-card']"
                )
                if not cards:
                    break
                for card in cards:
                    try:
                        l = self._parse(card, listing_type)
                        if l:
                            results.append(l)
                    except Exception as e:
                        self.logger.warning(f"Parse error: {e}")
                if not soup.select_one(".pagination a[rel='next'], a.next-page"):
                    break
                page += 1

        self.logger.info(f"Sunbelt: {len(results)} listings")
        return results

    def _parse(self, card, listing_type: str) -> Listing | None:
        title_el = card.select_one("h2, h3, h4, .title, .property-name")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 5:
            return None

        price_el = card.select_one(".price, [class*='price'], .amount")
        price = self.parse_price(price_el.get_text(strip=True) if price_el else "")

        link = card.select_one("a[href]")
        href = self.abs_url(link["href"]) if link else ""
        ext_id = re.search(r"/(\d+)", href)
        ext_id_val = ext_id.group(1) if ext_id else re.sub(r"[^a-z0-9]", "-", href.lower())[-60:]

        imgs = [i["src"] for i in card.select("img[src]")
                if "logo" not in i.get("src", "").lower()]

        loc_el = card.select_one(".location, .address, [class*='neighborhood'], [class*='area']")
        neighborhood = loc_el.get_text(strip=True) if loc_el else None

        bed_el  = card.select_one("[class*='bed']")
        bath_el = card.select_one("[class*='bath']")
        area_el = card.select_one("[class*='sqm'], [class*='area'], [class*='m2']")

        tl = title.lower()
        if "villa" in tl:
            ptype = "house"
        elif any(w in tl for w in ["apartment", "appartement"]):
            ptype = "apartment"
        elif any(w in tl for w in ["land", "grond", "lot"]):
            ptype = "land"
        else:
            ptype = "house"

        return Listing(
            source_id=self.source_id,
            external_id=ext_id_val,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,
            url=href,
            neighborhood=neighborhood,
            bedrooms=self.parse_int(bed_el.get_text() if bed_el else ""),
            bathrooms=self.parse_int(bath_el.get_text() if bath_el else ""),
            area_sqm=self.parse_area(area_el.get_text() if area_el else ""),
            images=imgs[:10],
        )
