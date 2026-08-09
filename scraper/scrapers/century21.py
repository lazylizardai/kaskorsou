"""
Century 21 Curaçao scraper (priority 8) — herbouwd
Site verhuisd: century21curacao.com -> https://century21numberone.com

Methode: HTML. Zoekpagina's /en/s/for-sale/ en /en/s/for-rent/ met
article.card-listing cards; paginatie via het data-next attribuut.
Prijzen staan per listing in XCG, US$ of EU€ — alles wordt omgerekend
naar XCG/ANG (USD x1.79, EUR x1.95, XCG as-is).
"""
import re
import time
import random
import json
from ..base_scraper import BaseScraper
from ..models import Listing

USD_TO_XCG = 1.79
EUR_TO_XCG = 1.95


class Century21Scraper(BaseScraper):
    source_name = "century21"
    BASE = "https://century21numberone.com"
    AGENT_COMPANY = "Century 21 Curaçao"

    SEARCH_PATHS = [
        ("sale", "/en/s/for-sale/"),
        ("rent", "/en/s/for-rent/"),
    ]

    MAX_PAGES = 30

    PER_PAGE = 12

    def scrape(self) -> list[Listing]:
        """
        LET OP: century21numberone.com zit achter AWS WAF. Na ~6 snelle
        pagina's (72 listings) volgt een sticky 403 die pas verdwijnt als je
        de WAF JS-challenge oplost (browser). Met requests halen we dus
        betrouwbaar de eerste ~72 listings; daarna stoppen we netjes.
        Volledige dekking (~166) vereist een browser met JS.
        """
        results = []
        seen = set()

        for listing_type, start_path in self.SEARCH_PATHS:
            page = 1
            while page <= self.MAX_PAGES:
                # Paginatie: /en/s/for-sale/ , /en/s/for-sale/hga/2 , /hga/3 , ...
                path = start_path if page == 1 else f"{start_path}hga/{page}"
                soup = self.get(self.BASE + path)
                if soup is None:
                    self.logger.warning(
                        f"C21 {listing_type} p{page}: geblokkeerd (WAF/403), stop sectie"
                    )
                    break

                cards = soup.select("article.card-listing")
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
                        self.logger.warning(f"C21 card error: {e}")

                self.logger.info(f"C21 {listing_type} p{page}: {len(cards)} cards, {new_count} new")

                # minder dan een volle pagina -> laatste pagina
                if len(cards) < self.PER_PAGE or new_count == 0:
                    break
                page += 1

        self.logger.info(f"Century21 total: {len(results)} listings — beschrijving/foto's ophalen")
        for l in results:
            try:
                self._enrich(l)
            except Exception as e:
                self.logger.warning(f"C21 enrich error ({l.external_id}): {e}")
            l.agent_company = self.AGENT_COMPANY

        return results

    def _enrich(self, l: Listing) -> None:
        """
        De kaart op de zoekpagina toont maar 1 thumbnail en geen beschrijving.
        - Beschrijving: staat volledig (ongekort) in de JSON-LD Product-schema
          op de detailpagina, zelfs al is de zichtbare pagina achter de AWS
          WAF geblokkeerd voor snelle requests.
        - Foto's: de detailpagina zelf laadt de galerij client-side (React),
          dus die staat niet in de HTML. De CDN images zelf
          (mls.cdn.../images/listings/{id}/xlg/{n}.jpg) zitten NIET achter de
          WAF en zijn gewoon oplopend genummerd vanaf 0 — dus proberen we die
          rechtstreeks totdat er 2x op rij geen geldige foto meer terugkomt.
        """
        soup = self.get(l.url)
        if soup:
            desc = self._extract_ldjson_description(soup)
            if desc:
                l.description = self.clean_text(desc)

        imgs = self._probe_gallery(l.external_id)
        if imgs:
            l.images = imgs

    @staticmethod
    def _extract_ldjson_description(soup) -> str | None:
        for script in soup.select('script[type="application/ld+json"]'):
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("description"):
                return data["description"]
        return None

    def _probe_gallery(self, ext_id: str, limit: int = 40) -> list[str]:
        if not ext_id:
            return []
        urls: list[str] = []
        misses = 0
        for i in range(limit):
            url = f"{self.BASE}/mls.cdn/images/listings/{ext_id}/xlg/{i}.jpg"
            try:
                time.sleep(random.uniform(0.3, 0.8))
                r = self.session.get(url, timeout=15, allow_redirects=True)
            except Exception:
                misses += 1
                if misses >= 2:
                    break
                continue
            if r.status_code == 200 and len(r.content) > 2000:
                urls.append(r.url)
                misses = 0
            else:
                misses += 1
                if misses >= 2:
                    break
        return self.clean_images(urls, limit=limit)

    def _parse(self, card, listing_type: str) -> Listing | None:
        ext_id = card.get("data-ad-id")
        if not ext_id:
            return None

        title = (card.get("data-ad-title") or "").strip()
        link = card.select_one("a.card-body[href], a[href*='/en/d/']")
        href = link.get("href", "") if link else ""
        if not href:
            return None
        if not href.startswith("http"):
            href = self.BASE + href
        if not title:
            t = card.select_one("h2 span")
            title = t.get_text(strip=True) if t else ""
        if not title:
            return None

        # Prijs: "EU€ 2,400,000" | "US$ 1,495,000" | "XCG 7,500/mth"
        price = None
        price_el = card.select_one("span.card-header")
        if price_el:
            price = self._to_xcg(price_el.get_text(strip=True))

        # District (bv. "Willemstad East") staat in <strong> binnen de h2
        neighborhood = None
        strong = card.select_one("h2 strong")
        if strong:
            neighborhood = strong.get_text(strip=True) or None

        # Categorie: laatste h2-span (Condos/Apartments, Single Family Homes, ...)
        category = ""
        h2_spans = card.select("h2 span")
        if h2_spans:
            category = h2_spans[-1].get_text(strip=True)
        ptype = self._map_ptype(category, title)

        # Beds/baths via de sprite-iconen; area uit "... · 840 m²"
        bedrooms = self._icon_num(card, "fa-bed")
        bathrooms = self._icon_num(card, "fa-bath")
        area = None
        am = re.search(r"([\d.,]+)\s*m²", card.get_text(" ", strip=True))
        if am:
            area = self.parse_price(am.group(1))  # strip separators -> float

        images = []
        img = card.select_one("img.thumb[src]")
        if img:
            images = [img["src"]]

        return Listing(
            source_id=self.source_id,
            external_id=str(ext_id),
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,  # omgerekend naar XCG/ANG
            url=href,
            neighborhood=neighborhood,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area,
            images=images,
        )

    def _to_xcg(self, text: str) -> float | None:
        """'EU€ 2,400,000' / 'US$ 1,495,000' / 'XCG 7,500/mth' -> XCG float."""
        m = re.search(r"(EU€|€|US\$|\$|XCG|NAf|ANG)\s*([\d.,]+)", text)
        if not m:
            return None
        amount = self.parse_price(m.group(2))
        if amount is None:
            return None
        cur = m.group(1)
        if cur in ("EU€", "€"):
            return round(amount * EUR_TO_XCG, 2)
        if cur in ("US$", "$"):
            return round(amount * USD_TO_XCG, 2)
        return amount  # XCG / NAf / ANG

    @staticmethod
    def _icon_num(card, sprite: str):
        """Aantal achter een sprite-icoon (fa-bed / fa-bath)."""
        use = card.select_one(f"use[href*='{sprite}']")
        if not use:
            return None
        svg = use.find_parent("svg")
        if not svg:
            return None
        # het getal staat als tekst direct na de svg
        sib = svg.next_sibling
        while sib is not None:
            txt = sib if isinstance(sib, str) else sib.get_text()
            m = re.search(r"\d+", txt or "")
            if m:
                return int(m.group())
            sib = sib.next_sibling
        return None

    @staticmethod
    def _map_ptype(category: str, title: str) -> str:
        c = (category or "").lower()
        tl = (title or "").lower()
        if "land" in c or any(w in tl for w in [" lot", "land for"]):
            return "land"
        if "condo" in c or "apartment" in c or any(w in tl for w in ["apartment", "condo", "penthouse", "studio"]):
            return "apartment"
        if "commercial" in c or any(w in tl for w in ["commercial", "office", "retail", "warehouse"]):
            return "commercial"
        return "house"
