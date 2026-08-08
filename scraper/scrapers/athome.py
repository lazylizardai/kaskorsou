"""At Home Curaçao scraper (herbouwd)
Site: https://www.athomecuracao.com  (WordPress, canonical host: athomecuracao.com)

Methode: HTML scraping van de categorie-archieven. Elke listing-card bevat
alle kernvelden inclusief de prijs in XCG (ANG) via het data-amount attribuut
van de WP Currency Switcher (span.wpcs_price[data-amount]).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing


class AthomeScraper(BaseScraper):
    source_name = "athome"
    BASE = "https://athomecuracao.com"

    # (listing_type, categorie-pad). Parents + leaves; dedup gebeurt op object-id.
    PATHS = [
        ("sale", "/kopen/"),
        ("sale", "/kopen/koopwoning/"),
        ("sale", "/kopen/koopappartement/"),
        ("sale", "/kopen/kavels/"),
        ("sale", "/kopen/nieuwbouw/"),
        ("rent", "/huren/"),
        ("rent", "/huren/huurwoning/"),
        ("rent", "/huren/huurappartement/"),
        ("rent", "/huren/studenten-woning/"),
        ("rent", "/vakantieverhuur/"),
        ("sale", "/commercieel/bedrijfspand-kopen/"),
        ("sale", "/commercieel/bedrijf-kopen/"),
        ("sale", "/commercieel/hotel-kopen/"),
        ("rent", "/commercieel/bedrijfspand-huren/"),
        ("rent", "/commercieel/kantoor-huren/"),
        ("sale", "/vastgoed-investeringen/"),
    ]

    MAX_PAGES = 30

    def scrape(self) -> list[Listing]:
        results: list[Listing] = []
        seen: set[str] = set()

        for listing_type, path in self.PATHS:
            page = 1
            while page <= self.MAX_PAGES:
                url = f"{self.BASE}{path}" if page == 1 else f"{self.BASE}{path}page/{page}/"
                soup = self.get(url)
                if not soup:
                    break

                cards = soup.select("article[class*=property-]")
                if not cards:
                    break

                new_count = 0
                for card in cards:
                    try:
                        l = self._parse(card, listing_type, path)
                        if l and l.external_id and l.external_id not in seen:
                            seen.add(l.external_id)
                            results.append(l)
                            new_count += 1
                    except Exception as e:
                        self.logger.warning(f"Card error: {e}")

                self.logger.info(f"athome {path} p{page}: {len(cards)} cards, {new_count} new")
                # Geen nieuwe items -> einde (of pagina redirect terug naar p1)
                if new_count == 0:
                    break
                page += 1

        self.logger.info(f"At Home total: {len(results)} listings")
        return results

    def _parse(self, card, listing_type: str, path: str) -> Listing | None:
        # Object-id uit de article class (property-<id>) of uit li.objectid
        ext_id = None
        cls = " ".join(card.get("class", []))
        m = re.search(r"property-(\d+)", cls)
        if m:
            ext_id = m.group(1)
        if not ext_id:
            oid = card.select_one("li.objectid")
            if oid:
                mm = re.search(r"\d+", oid.get_text())
                ext_id = mm.group() if mm else None
        if not ext_id:
            return None

        title_el = card.select_one("h2.entry-title a, .property-title a, h2 a")
        title = (title_el.get("title") or title_el.get_text(strip=True)) if title_el else ""
        href = title_el.get("href", "") if title_el else ""
        if not title or not href:
            return None
        if not href.startswith("http"):
            href = self.BASE + href

        # Prijs: XCG (ANG) numeriek via data-amount
        price = None
        price_el = card.select_one("span.wpcs_price[data-amount]")
        if price_el:
            try:
                price = float(price_el["data-amount"])
            except (ValueError, KeyError):
                price = None
        if price is None:
            pe = card.select_one(".property-price, .prop-price")
            price = self.parse_price(pe.get_text(strip=True)) if pe else None

        beds = self._num(card.select_one("li.bedrooms span"))
        baths = self._num(card.select_one("li.bathrooms span"))

        # Afbeelding (thumbnail uit de card)
        images = []
        img = card.select_one(".property_img img[src]")
        if img and img.get("src"):
            images = [img["src"]]

        neighborhood = self._neighborhood_from_title(title)
        ptype = self._property_type(path, title)

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,          # XCG/ANG
            url=href,
            neighborhood=neighborhood,
            bedrooms=beds,
            bathrooms=baths,
            images=images[:10],
        )

    @staticmethod
    def _num(el):
        if not el:
            return None
        m = re.search(r"\d+", el.get_text())
        return int(m.group()) if m else None

    @staticmethod
    def _neighborhood_from_title(title: str) -> str | None:
        # bv. "... te Muizenberg te Koop" / "... in Jan Thiel te huur"
        m = re.search(
            r"\b(?:te|in|op)\s+([A-Z][\wáàéíóúñç'’\- ]{2,30}?)\s+te\s+(?:koop|huur)\b",
            title, flags=re.I,
        )
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _property_type(path: str, title: str) -> str:
        p = path.lower()
        tl = title.lower()
        if "kavel" in p or any(w in tl for w in ["kavel", "bouwgrond", "perceel", " lot"]):
            return "land"
        if "appartement" in p or any(w in tl for w in ["appartement", "penthouse", "studio", "condo"]):
            return "apartment"
        if any(w in p for w in ["commercieel", "bedrijf", "kantoor", "hotel"]) or \
           any(w in tl for w in ["bedrijfspand", "kantoor", "loods", "winkel", "hotel", "commercieel"]):
            return "commercial"
        return "house"
