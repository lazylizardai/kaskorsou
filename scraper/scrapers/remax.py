"""RE/MAX Bonbini scraper (priority 9)
Real domain: realestate-curacao.com (remax-bonbini.com redirects here)
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing


class RemaxScraper(BaseScraper):
    source_name = "remax"
    BASE = "https://www.realestate-curacao.com"

    PATHS = [
        ("sale", "/nl/woningen/koopwoningen/"),
        ("rent", "/nl/woningen/huurwoningen/"),
        ("sale", "/nl/commercieel/commercieel-koop/"),
        ("rent", "/nl/commercieel/commercieel-huur/"),
    ]

    def scrape(self) -> list[Listing]:
        results = []
        seen = set()

        for listing_type, base_path in self.PATHS:
            page = 0
            while True:
                url = f"{self.BASE}{base_path}" if page == 0 else \
                      f"{self.BASE}{base_path}paginate-{page}/"
                soup = self.get(url)
                if not soup:
                    break

                cards = soup.select(".listing")
                if not cards:
                    break

                new_count = 0
                for card in cards:
                    try:
                        l = self._parse(card, listing_type)
                        if l and l.external_id and l.external_id not in seen:
                            seen.add(l.external_id)
                            results.append(l)
                            new_count += 1
                    except Exception as e:
                        self.logger.warning(f"Card error: {e}")

                self.logger.info(f"RE/MAX {listing_type} p{page}: {new_count} new")

                # Check if there's a next page
                next_page = soup.select_one(
                    f"a[href*='paginate-{page+1}']"
                )
                if not next_page or page >= 20:
                    break
                page += 1

        self.logger.info(f"RE/MAX total: {len(results)} listings")
        return results

    def _parse(self, card, listing_type: str) -> Listing | None:
        link = card.select_one("a[href]")
        if not link:
            return None
        href = link.get("href", "")
        if not href.startswith("http"):
            href = self.BASE + href

        # Extract ID from URL like /nl/woningen/.../hs3021/title.html
        ext_id_m = re.search(r"/(hs\d+|[a-z]{2}\d+)/", href)
        ext_id = ext_id_m.group(1) if ext_id_m else re.sub(r"[^a-z0-9]", "-", href.lower())[-60:]

        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price_el = card.select_one("[class*='price'], .price, strong")
        price = self.parse_price(price_el.get_text(strip=True) if price_el else "")

        # Neighborhood — first text line that looks like a location
        loc_el = card.select_one("[class*='location'], [class*='area'], [class*='place'], address")
        neighborhood = loc_el.get_text(strip=True) if loc_el else None
        if neighborhood:
            # Strip "Curaçao" / "Curacao" suffix
            neighborhood = re.sub(r"\s*(Curaçao|Curacao)$", "", neighborhood, flags=re.I).strip()

        # Bedrooms — icon has class 'fa-bed', count is in sibling/parent text
        beds_icon = card.select_one("[class*='fa-bed']")
        bedrooms = None
        if beds_icon:
            parent = beds_icon.parent
            bedrooms = self.parse_int(parent.get_text() if parent else "")

        # Area — look for m² text
        area_el = card.select_one("[class*='fa-ruler'], [class*='area'], [class*='opp']")
        area = None
        if area_el:
            area = self.parse_area(area_el.parent.get_text() if area_el.parent else area_el.get_text())

        # Images from CDN
        imgs = [img["src"] for img in card.select("img[src]") if "cdn" in img.get("src", "")]

        # Property type from title
        tl = title.lower()
        if any(w in tl for w in ["villa", "woning", "house", "huis"]):
            ptype = "house"
        elif any(w in tl for w in ["apartment", "appartement", "penthouse"]):
            ptype = "apartment"
        elif any(w in tl for w in ["land", "grond", "lot"]):
            ptype = "land"
        elif any(w in tl for w in ["commercial", "commercieel", "office", "kantoor"]):
            ptype = "commercial"
        else:
            ptype = "house"

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,  # Note: RE/MAX uses EUR, stored as-is
            url=href,
            neighborhood=neighborhood,
            bedrooms=bedrooms,
            area_sqm=area,
            images=imgs[:10],
        )
