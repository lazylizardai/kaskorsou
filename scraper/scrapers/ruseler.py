"""Ruseler Makelaars scraper (priority 8)
Site: https://ruselermakelaars.com — WordPress (LiteSpeed) + Elementor +
JetEngine (custom post type `aanbod`, rest_base `aanbod`). Gewone hosting,
geen blokkade-signalen, robots.txt staat alles toe.

Methode:
  1. De WP REST API (`/wp-json/wp/v2/aanbod?per_page=100`, 59 listings in
     1 pagina) geeft ALLEEN id/titel/slug/link/Yoast-SEO-data terug — geen
     custom-field-data (JetEngine-velden zijn hier niet los in REST
     geregistreerd). Wel bruikbaar als complete lijst-enumeratie.
  2. Alle veldwaarden (bouwjaar, m², slaapkamers, prijs, status) staan op
     de HTML-detailpagina in herhalende Elementor/JetEngine-containers met
     class `jedv-enabled--yes` — elke container bevat een
     `elementor-heading-title` (het label, bv. "Slaapkamers") + een of
     meerdere `jet-listing-dynamic-field__content`-elementen (de waarde).
     Geen vaste CSS-class per veldnaam, dus label-tekst is de sleutel
     (zelfde aanpak als curacao_exclusive.py, met dezelfde
     dict-key-voorzichtigheid).
  3. De **status staat als een label-only container** (heading tekst zelf
     is de status, bv. "In verkoop"/"Verkocht"/"In verhuur"/"Verhuurd" —
     geen aparte waarde eronder). Alleen listings met status "in verkoop"
     of "in verhuur" nemen we mee; "verkocht"/"verhuurd" wordt
     overgeslagen. **De `/aanbod/`-sitemap én de eigen archiefpagina's van
     de site bevatten OOK al lang verkochte panden (portfolio-historie) —
     dus zonder deze status-check op de detailpagina zou een groot deel
     van de meegenomen listings allang niet meer beschikbaar zijn.**
     Tot nu toe alleen verkoop-listings gezien (geen actieve verhuur), dus
     `listing_type` defaultet naar "sale" tenzij de status expliciet
     "verhuur" bevat.
  4. Prijs staat in het "Vraagprijs"-veld als los symbool + bedrag + suffix
     (bv. `["€", "1.295.000", "k.k."]`) — currency-symbool en numeriek
     bedrag apart uit de waarde-lijst gehaald.
  5. Geen coördinaten en geen apart wijk-veld beschikbaar op deze site —
     bewust leeg gelaten (zelfde afweging als real_estate_agency_cb.py:
     titel/Yoast-tekst bevat de wijk vaak wel, maar niet betrouwbaar
     scheidbaar zonder vaste wijkenlijst — geen giswerk).
  6. Foto's: alleen `<img class="wp-post-gallery">`-elementen meenemen
     (overige `<img>`-tags op de pagina zijn taal-vlaggetjes/logo's met
     een SVG-placeholder als `src`) — volledige resolutie via het
     `data-src`-attribuut.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://ruselermakelaars.com"
API = f"{BASE}/wp-json/wp/v2/aanbod"
PAGE_SIZE = 100

SOLD_STATUS_WORDS = ("verkocht", "verhuurd")
RENT_STATUS_WORDS = ("verhuur",)
STATUS_LABELS = {
    "in verkoop", "verkocht", "in verhuur", "verhuurd",
    "onder optie", "onder bod", "nieuw", "new",
}

CURRENCY_RE = re.compile(r"^(€|\$|XCG|ANG|USD|EUR)$", re.I)


class RuselerScraper(BaseScraper):
    source_name = "ruseler"
    AGENT_COMPANY = "Ruseler Makelaars"

    def _get_json(self, url: str, params: dict):
        r = self.session.get(url, params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        items = []
        page = 1
        while True:
            try:
                batch = self._get_json(API, {"per_page": PAGE_SIZE, "page": page})
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon aanbod niet ophalen: {e}")
                    return []
                break
            if not batch:
                break
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1

        self.logger.info(f"Ruseler: {len(items)} listings uit de REST API (incl. gearchiveerd/verkocht)")

        results = []
        for item in items:
            try:
                l = self._scrape_detail(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({item.get('id')}): {e}")

        self.logger.info(f"Ruseler: {len(results)} actieve listings verwerkt")
        return results

    def _field_map(self, soup) -> dict[str, list[str]]:
        field_map: dict[str, list[str]] = {}
        for c in soup.find_all(class_="jedv-enabled--yes"):
            heading = c.find(class_="elementor-heading-title")
            if not heading:
                continue
            label = self.clean_text(heading.get_text())
            if not label:
                continue
            values = [
                self.clean_text(v.get_text())
                for v in c.find_all(class_="jet-listing-dynamic-field__content")
            ]
            values = [v for v in values if v]
            # Bij dubbele labels (verborgen/ongebruikte alternatieve widget)
            # de langste (meest informatieve) waarde-lijst bewaren.
            if label not in field_map or len(values) > len(field_map[label]):
                field_map[label] = values
        return field_map

    def _scrape_detail(self, item: dict) -> Listing | None:
        url = item.get("link")
        if not url:
            return None
        soup = self.get(url)
        if soup is None:
            return None

        field_map = self._field_map(soup)

        status_label = None
        for label in field_map:
            if not field_map[label] and label.lower() in STATUS_LABELS:
                status_label = label.lower()
                break
        if status_label and any(w in status_label for w in SOLD_STATUS_WORDS):
            return None

        listing_type = "rent" if status_label and any(w in status_label for w in RENT_STATUS_WORDS) else "sale"

        title = self.clean_text(item.get("title", {}).get("rendered")) or "Woning Curaçao"

        title_l = (title + " " + ((item.get("yoast_head_json") or {}).get("title") or "")).lower()
        if "kavel" in title_l or "bouwperceel" in title_l:
            property_type = "land"
        elif "appartement" in title_l or "penthouse" in title_l:
            property_type = "apartment"
        else:
            property_type = "house"

        bedrooms = None
        for key in ("Slaapkamers",):
            if field_map.get(key):
                bedrooms = self.parse_int(field_map[key][0])
        bathrooms = None
        for key in ("Badkamers",):
            if field_map.get(key):
                bathrooms = self.parse_int(field_map[key][0])

        area_sqm = None
        for key in ("Aantal m2 BVO*", "Woonoppervlak"):
            if field_map.get(key):
                area_sqm = self.parse_area(field_map[key][0])
                if area_sqm:
                    break
        if not area_sqm and field_map.get("Kaveloppervlak"):
            area_sqm = self.parse_area(field_map["Kaveloppervlak"][0])

        price, currency = None, "XCG"
        price_values = field_map.get("Vraagprijs") or []
        if price_values:
            cur_symbol = next((v for v in price_values if CURRENCY_RE.match(v)), "").upper()
            amount = None
            for v in price_values:
                if CURRENCY_RE.match(v):
                    continue
                parsed = self.parse_price(v)
                if parsed:
                    amount = parsed
                    break
            if amount:
                if cur_symbol in ("€", "EUR"):
                    price, currency = round(amount * 1.95, 2), "XCG"
                elif cur_symbol in ("$", "USD"):
                    price, currency = amount, "USD"
                else:
                    price, currency = amount, "XCG"

        description = None
        yoast = item.get("yoast_head_json") or {}
        if yoast.get("description"):
            description = self.clean_text(yoast["description"])

        images = []
        for img in soup.find_all("img", class_="wp-post-gallery"):
            src = img.get("data-src") or img.get("src")
            if src and "/wp-content/uploads/" in src:
                images.append(src)
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=str(item.get("id")),
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
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
