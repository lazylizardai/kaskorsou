"""Keller Williams Curaçao scraper (priority 8)
Domein: kw-curacao.com — October CMS (Laravel), geen WordPress/WPCloud dus
geen bekende reden om aan te nemen dat GitHub Actions-IP's hier net als bij
New Winds Realty geblokkeerd worden (11 aug 2026: nog niet op GH Actions
zelf getest, wel handmatig vanuit de Cowork-sandbox — 200 OK, geen 429).

robots.txt vraagt expliciet Crawl-Delay: 20 — deze scraper respecteert dat
met een eigen (langere) delay tussen requests i.p.v. de globale
REQUEST_DELAY uit config.py (die is te snel voor deze site).

Alle listings staan op één enkele /listings-pagina (geen paginering nodig,
server-rendered, ~160 kaarten in de HTML). Prijzen worden getoond in zowel
USD als XCG — we slaan de XCG-waarde native op (currency="XCG"), geen eigen
omrekening nodig.
"""
import re
import time
import random
from ..base_scraper import BaseScraper
from ..models import Listing

# Crawl-Delay: 20 uit robots.txt — iets ruimer genomen om vriendelijk te blijven.
DETAIL_DELAY = (20, 26)


class KellerWilliamsScraper(BaseScraper):
    source_name = "keller_williams"
    BASE = "https://kw-curacao.com"
    AGENT_COMPANY = "Keller Williams Curacao"

    def scrape(self) -> list[Listing]:
        soup = self.get(f"{self.BASE}/listings")
        if not soup:
            self.logger.error("Kon /listings niet ophalen")
            return []

        cards = soup.select("div.card")
        results = []
        seen = set()

        for card in cards:
            link = card.select_one("a.card__overlay[href], a[href^='/listings/']")
            if not link:
                continue
            href = link.get("href", "")
            if not href.startswith("/listings/"):
                continue
            if href in seen:
                continue
            seen.add(href)

            # Alleen echt-niet-meer-beschikbare listings overslaan. 'Price upon
            # Request' en 'Reduced in Price' zijn secundaire badges op nog
            # actieve listings — NIET overslaan (site toont dan geen prijs-
            # cijfer, dat vangt de price-regex vanzelf af als None).
            label_el = card.select_one(".card__label")
            status_text = self.clean_text(label_el.get_text()) if label_el else "Active"
            if status_text and status_text.lower() in (
                "sold", "rented/leased", "under contract", "under offer",
            ):
                self.logger.info(f"Skip niet-actieve listing ({status_text}): {href}")
                continue

            try:
                l = self._parse_card(card, href)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Card error ({href}): {e}")

        self.logger.info(f"Keller Williams: {len(results)} actieve listings gevonden — detailpagina's ophalen")

        enriched = []
        for l in results:
            try:
                time.sleep(random.uniform(*DETAIL_DELAY))
                self._enrich(l)
                enriched.append(l)
            except Exception as e:
                self.logger.warning(f"Enrich error ({l.external_id}): {e}")
                enriched.append(l)  # kaart-data is beter dan niets

        return enriched

    def _parse_card(self, card, href: str) -> Listing | None:
        url = self.BASE + href
        # slug is uniek per listing, dus prima bruikbaar als external_id
        ext_id = href.rstrip("/").split("/")[-1]

        title_el = card.select_one(".card__heading, h2, h3, .card__title, [class*='title']")
        title = self.clean_text(title_el.get_text()) if title_el else None
        if not title:
            return None

        price_el = card.select_one(".card__price")
        price = None
        if price_el:
            price_text = price_el.get_text(" ", strip=True)
            m = re.search(r"XCG\s*([\d.,]+)", price_text)
            if m:
                price = self.parse_price(m.group(1))

        area = bedrooms = None
        for opt in card.select(".card__options .option"):
            txt = opt.get_text(" ", strip=True)
            if "m²" in txt or "m2" in txt:
                area = self.parse_area(txt)
            elif "bedroom" in txt.lower():
                bedrooms = self.parse_int(txt)

        img_el = card.select_one(".card__image img")
        images = [img_el["src"]] if img_el and img_el.get("src") else []

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type="sale",  # correctie gebeurt in _enrich() a.d.h.v. detailpagina
            property_type="house",
            price_ang=price,
            currency="XCG",
            url=url,
            bedrooms=bedrooms,
            area_sqm=area,
            images=images,
        )

    def _enrich(self, l: Listing) -> None:
        soup = self.get(l.url)
        if not soup:
            return

        type_el = soup.select_one(".page-property-details__type")
        if type_el:
            type_text = type_el.get_text(strip=True)
            l.listing_type = "rent" if "rent" in type_text.lower() else "sale"
            tl = type_text.lower()
            if "commercial" in tl:
                l.property_type = "commercial"
            elif "land" in tl or "lot" in tl:
                l.property_type = "land"
            elif "apartment" in tl or "condo" in tl or "penthouse" in tl:
                l.property_type = "apartment"

        tl_title = l.title.lower()
        if any(w in tl_title for w in ("apartment", "condo", "penthouse", "flat")):
            l.property_type = "apartment"
        elif any(w in tl_title for w in ("land", "lot", "kavel", "grond")):
            l.property_type = "land"
        elif any(w in tl_title for w in ("commercial", "office", "kantoor", "warehouse")):
            l.property_type = "commercial"

        loc_el = soup.select_one(".page-property-details__location")
        if loc_el:
            l.neighborhood = self.clean_text(loc_el.get_text())

        # Prijs op detailpagina is de canonieke waarde (kaart kan afronden verschillen).
        price_el = soup.select_one(".page-property-details__price")
        if price_el:
            price_text = price_el.get_text(" ", strip=True)
            m = re.search(r"XCG\s*([\d.,]+)", price_text)
            if m:
                price = self.parse_price(m.group(1))
                if price:
                    l.price_ang = price

        for opt in soup.select(".page-property-details__options .option"):
            txt = opt.get_text(" ", strip=True)
            if "m²" in txt or "m2" in txt:
                l.area_sqm = self.parse_area(txt) or l.area_sqm
            elif "bedroom" in txt.lower():
                l.bedrooms = self.parse_int(txt) or l.bedrooms
            elif "bathroom" in txt.lower():
                l.bathrooms = self.parse_int(txt)

        desc_el = soup.select_one("#description .wysiwyg, #description")
        if desc_el:
            l.description = self.clean_text(desc_el.get_text(" ", strip=True))

        # Volledige fotogalerij — de originele bestanden (niet de thumb_*-crops).
        gallery_links = soup.select("a.gallery__slide-image[href]")
        imgs = [a["href"] for a in gallery_links if a.get("href", "").startswith("http")]
        if imgs:
            l.images = self.clean_images(imgs)

        # Coördinaten staan in een inline <script> als JS-object (mapS.latLng).
        m = re.search(
            r"lat:\s*(-?[\d.]+)\s*,\s*lng:\s*(-?[\d.]+)", str(soup)
        )
        if m:
            try:
                l.latitude = float(m.group(1))
                l.longitude = float(m.group(2))
            except ValueError:
                pass

        agent_name_el = soup.select_one(".card-agent__name")
        if agent_name_el:
            # Bevat ook een icoon-<div>, dus alleen de tekstnode gebruiken.
            name_text = "".join(
                t for t in agent_name_el.find_all(string=True, recursive=True)
            )
            l.agent_name = self.clean_text(name_text)

        l.agent_company = self.AGENT_COMPANY
