"""TOP Makelaar Curacao scraper (priority 8)
Site: https://www.topmakelaarcuracao.com — Webflow (CMS Collections,
"Realtor X"-template), gewone hosting/CDN (cdn.prod.website-files.com),
geen WPCloud/SiteGround-blokkade-signalen, geen wp-json (geen WordPress).
robots.txt: geen bestand (404) — geen expliciete regels, dus generieke
beleefde delay aanhouden.

Methode:
  1. Geen sitemap/REST — Webflow CMS Collection Lists worden gewoon
     server-side gerenderd op `/aanbod` (`div.w-dyn-list` met
     `a.card-property`-links naar `/property/<slug>`). 12 listings passen
     op 1 pagina, geen paginering nodig.
  2. Elke detailpagina heeft alle data server-rendered in de HTML: adres
     (`.text-200.margin-bottom-6px` net boven de `<h1>`), prijs
     (`.card-property-request-info .h2-size`, prefix `€`/`XCG`/`$` en
     suffix `k.k.`/`p.m.`), en badges met alt-tekst-gestuurde iconen
     (Scale=m², Bed=slaapkamers, Bathroom=badkamers, Parking=genegeerd).
  3. **Kritieke status-valkuil (zelfde patroon als Simmer's VERHUURD-
     callout, maar via Webflow's conditional-visibility-mechanisme i.p.v.
     inline tekst):** een verkochte/onder-contract-listing blijft gewoon op
     de site staan. De pagina bevat altijd meerdere `.sold-text`-divs (voor
     verschillende badge-varianten), maar Webflow toont er normaal maar één
     — de rest krijgt de class `w-condition-invisible`. Van de 12 listings
     in de steekproef bleken 6 al "Verkocht", "Verkocht onder voorbehoud"
     of "Onder contract" te zijn (zichtbaar via een `.sold-text`-div ZONDER
     `w-condition-invisible` in de class-list) terwijl ze qua HTML-structuur
     verder identiek zijn aan de 6 nog beschikbare listings. Alleen tekst
     zoeken op "Verkocht" is dus onvoldoende (die tekst staat ALTIJD in de
     HTML, ook verborgen) — de class-check op `w-condition-invisible` is
     verplicht.
  4. Geen coördinaten in de HTML (alleen een Google Maps zoeklink op
     adrestekst) — latitude/longitude blijven leeg, net als bij
     `nh_real_estate.py`.
  5. Foto's: `#gallery a.gallery-item-image img.image.cover` (de
     eye-icon-overlay-afbeelding in dezelfde anchor wordt door de
     class-selector vanzelf uitgesloten).
  6. Beschrijving uit `.rich-text.w-richtext` (HTML gestript).
  7. Geen numerieke listing-ID zichtbaar — de URL-slug is de external_id.

Let op: de server stuurt geen `charset` mee in de Content-Type-header
(alleen `text/html`), terwijl de pagina zelf `<meta charset="utf-8"/>`
declareert. `requests` valt dan terug op de HTTP-default ISO-8859-1 en
`self.get()` (de gedeelde BaseScraper-helper) geeft dus gemojibakete tekst
("CuraÃ§ao" i.p.v. "Curaçao") — deze scraper gebruikt daarom een eigen
`_get_soup()` die de encoding expliciet op utf-8 zet vóór het parsen, i.p.v.
de gedeelde `self.get()`.
"""
import re
import time
import random
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..config import REQUEST_DELAY, TIMEOUT
from ..models import Listing

BASE = "https://www.topmakelaarcuracao.com"
LIST_URL = f"{BASE}/aanbod"
EUR_TO_XCG = 1.95

NEGATIVE_STATUS_HINTS = ("verkocht", "onder contract", "sold", "under contract", "verhuurd")


class TopMakelaarScraper(BaseScraper):
    source_name = "top_makelaar"
    AGENT_COMPANY = "TOP Makelaar Curacao"

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        for attempt in range(3):
            try:
                time.sleep(random.uniform(*REQUEST_DELAY))
                r = self.session.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                r.encoding = "utf-8"
                return BeautifulSoup(r.text, "lxml")
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
        self.logger.error(f"All retries failed for {url}")
        return None

    def scrape(self) -> list[Listing]:
        soup = self._get_soup(LIST_URL)
        if not soup:
            self.logger.error("Kon aanbod-pagina niet ophalen")
            return []

        links = set()
        for a in soup.select('a[href^="/property/"]'):
            href = a.get("href")
            if href:
                links.add(BASE + href if href.startswith("/") else href)

        self.logger.info(f"TOP Makelaar: {len(links)} listing-links gevonden op /aanbod")

        results = []
        for url in sorted(links):
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({url}): {e}")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self._get_soup(url)
        if not soup:
            return None

        # Status-check: een zichtbare .sold-text (zonder w-condition-invisible)
        # met een negatieve statustekst betekent niet meer beschikbaar.
        for div in soup.select(".sold-text"):
            classes = div.get("class") or []
            if "w-condition-invisible" in classes:
                continue
            text = (div.get_text(strip=True) or "").lower()
            if any(h in text for h in NEGATIVE_STATUS_HINTS):
                return None

        slug = url.rstrip("/").rsplit("/", 1)[-1]

        h1 = soup.select_one("h1")
        title = self.clean_text(h1.get_text(" ")) if h1 else None
        if not title:
            return None

        address_el = h1.find_previous(class_="text-200") if h1 else None
        neighborhood = self.clean_text(address_el.get_text(" ")) if address_el else None

        price_el = soup.select_one(".card-property-request-info .h2-size")
        price_text = price_el.get_text(" ") if price_el else ""
        listing_type = "rent" if re.search(r"p\.?m\.?|per maand|/maand", price_text, re.I) else "sale"

        price, currency = None, "XCG"
        amount = self.parse_price(price_text)
        if amount:
            if "€" in price_text:
                price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
            elif "$" in price_text:
                price, currency = amount, "USD"
            else:
                price, currency = amount, "XCG"

        # Let op: `.badge` komt ook voor in een "gerelateerde listings"-blok
        # onderaan de pagina — zonder scope tot `.property-content-top`
        # overschrijven die badges (van heel andere woningen) de echte
        # waarden stilletjes (geverifieerd bij Metro Residences Type A/B/C).
        bedrooms = bathrooms = area_sqm = None
        info_block = soup.select_one(".property-content-top") or soup
        for badge in info_block.select(".badge"):
            icon = badge.select_one("img")
            alt = (icon.get("alt") or "").lower() if icon else ""
            val_el = badge.select_one("div")
            raw = val_el.get_text(" ") if val_el else ""
            if "bathroom" in alt:
                # kan een halve badkamer bevatten (bv. "2.5") — score
                # afronden i.p.v. parse_int() die de '.5' zou laten vallen.
                try:
                    bathrooms = round(float(raw.strip())) if raw.strip() else None
                except ValueError:
                    bathrooms = self.parse_int(raw)
            elif "scale" in alt:
                area_sqm = self.parse_int(raw)
            elif "bed" in alt:
                bedrooms = self.parse_int(raw)

        hint_text = f"{title.lower()} {neighborhood or ''}".lower()
        if "kavel" in hint_text or "bouwgrond" in hint_text:
            property_type = "land"
        elif "commercieel" in hint_text or "kantoor" in hint_text:
            property_type = "commercial"
        elif "appartement" in hint_text and "villa" not in hint_text:
            property_type = "apartment"
        else:
            property_type = "house"

        description = None
        rich = soup.select_one(".rich-text.w-richtext")
        if rich:
            description = self.clean_text(rich.get_text(" "))

        images = []
        gallery = soup.select_one("#gallery")
        if gallery:
            for img in gallery.select("a.gallery-item-image img.image.cover"):
                src = img.get("src")
                if src:
                    images.append(src)
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=slug,
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood=neighborhood,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
