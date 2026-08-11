"""Bru de Roque scraper (priority 8)
Site: https://bruderoque.com — WordPress, nginx-hosting, "Directorist"-
plugin (algemene business-directory-plugin, hier ingezet als
vastgoedaanbod — nieuwe plugin-familie, niet eerder gezien bij
Estatik/RealHomes/JetEngine-sites). robots.txt staat alles toe, geen
blokkade-signalen.

Methode:
  1. Volledige lijst in 1 call: `GET /wp-json/directorist/v2/listings
     ?per_page=100` — 12 listings totaal, geen paginering nodig. Rijk
     JSON per listing (`fields`-object): titel, beschrijving (HTML),
     `categories` (for-rent/for-sale), `price` (kale numerieke string,
     al native XCG — bevestigd via een steekproef waar de beschrijving
     zelf "XCG 1.250.000 / USD 694.000" vermeldt en het `price`-veld
     exact 1250000 was), `latitude`/`longitude` (altijd aanwezig en
     correct, geen bounding-box-uitschieters in de steekproef),
     `listing_img` (lijst met volledige foto-URLs).
  2. **Geen bedrooms/bathrooms/area-veld in de API** — de
     `custom-text-*`-velden bleken bij inspectie GEEN oppervlakte te zijn
     maar een alternatieve USD-prijsnotatie (bv. `custom-text-7` = "694.000"
     bij een listing waar de beschrijving "USD 694,000" vermeldt) — dus
     bewust niet gebruikt. Slaapkamers/badkamers/m² worden in plaats
     daarvan uit de platte tekst van de (HTML-gestripte) beschrijving
     geregexed (NL "slaapkamer(s)"/"badkamer(s)" en EN
     "bedroom(s)"/"bathroom(s)", en "m2"/"m²"/"sq ft" voor oppervlak —
     sq ft wordt niet omgerekend, alleen de m²-variant gebruikt als die
     aanwezig is).
  3. **Kritieke status-valkuil (derde variant in deze sessie): hier staat
     de niet-beschikbaarheid, anders dan bij Simmer/TOP Makelaar, gewoon
     LEESBAAR in de titel-tekst zelf** — "– UNDER CONTRACT –" of "SOLD:"
     als prefix. Van de 12 listings zijn er 7 al verkocht/onder contract
     maar nog steeds live op de site. Simpele substring-check op de titel
     (vóór HTML-entity-decode, dus op de rauwe titel) volstaat hier, geen
     hidden-DOM-trucje zoals bij de vorige twee sites.
  4. Property-type: geen aparte taxonomie (alleen for-rent/for-sale-
     categorieën) — afgeleid uit trefwoorden in titel+beschrijving
     (villa/kavel-grond/appartement/penthouse/studio).
"""
import html
import re
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://bruderoque.com"
API = f"{BASE}/wp-json/directorist/v2/listings"
PAGE_SIZE = 100

NEGATIVE_STATUS_HINTS = ("under contract", "sold", "verkocht", "onder contract")
# "eigen grond"/"own land" bewust NIET hier — dat matchte ook een "bouw uw
# droomwoning op uw eigen grond"-bouwpakket-listing (een huizenmodel om te
# laten bouwen, geen kale kavel). Alleen ondubbelzinnige kavel-signalen.
LAND_HINTS = ("kavel", "bouwgrond", "grond te koop", "bouwperceel")
APARTMENT_HINTS = ("appartement", "penthouse", "studio", "apartment")

# Sta een paar tussenwoorden toe tussen het getal en het zelfstandig
# naamwoord (bv. "2 ruime slaapkamers", "2 moderne badkamers, waaronder").
BEDROOM_RE = re.compile(r"(\d+)(?:[^\d.]{0,20})(?:slaapkamer|bedroom)", re.I)
BATHROOM_RE = re.compile(r"(\d+)(?:[^\d.]{0,20})(?:badkamer|bathroom)", re.I)
AREA_RE = re.compile(r"(\d[\d.,]*)\s*m[\s]?[²2]", re.I)


class BruDeRoqueScraper(BaseScraper):
    source_name = "bru_de_roque"
    AGENT_COMPANY = "Bru de Roque"

    def _get_json(self, url: str, params: dict):
        r = self.session.get(url, params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        try:
            items = self._get_json(API, {"per_page": PAGE_SIZE})
        except Exception as e:
            self.logger.error(f"Kon listings niet ophalen: {e}")
            return []

        self.logger.info(f"Bru de Roque: {len(items)} listings uit de Directorist-API")

        results = []
        for item in items:
            try:
                l = self._build(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({item.get('id')}): {e}")
        return results

    def _build(self, item: dict) -> Listing | None:
        listing_id = item.get("id")
        if not listing_id:
            return None

        f = item.get("fields") or {}
        title_raw = f.get("title") or ""
        if any(h in title_raw.lower() for h in NEGATIVE_STATUS_HINTS):
            return None

        title = self.clean_text(html.unescape(title_raw)) or "Woning Curaçao"
        url = item.get("permalink") or f"{BASE}/?p={listing_id}"

        cat_slugs = {c.get("slug") for c in f.get("categories") or []}
        listing_type = "rent" if "for-rent" in cat_slugs else "sale"

        description_html = f.get("description") or ""
        description_text = self.clean_text(BeautifulSoup(description_html, "lxml").get_text(" ")) or ""

        hint_text = f"{title.lower()} {description_text.lower()}"
        if any(h in hint_text for h in LAND_HINTS):
            property_type = "land"
        elif any(h in hint_text for h in APARTMENT_HINTS):
            property_type = "apartment"
        else:
            property_type = "house"

        price = self.parse_price(str(f.get("price") or ""))
        currency = "XCG"

        bedrooms = None
        m = BEDROOM_RE.search(description_text)
        if m:
            bedrooms = int(m.group(1))

        bathrooms = None
        m = BATHROOM_RE.search(description_text)
        if m:
            bathrooms = int(m.group(1))

        area_sqm = None
        m = AREA_RE.search(description_text)
        if m:
            area_sqm = self.parse_area(m.group(0))

        locations = f.get("locations") or []
        neighborhood = self.clean_text(locations[0].get("name")) if locations else None
        if not neighborhood:
            neighborhood = self.clean_text(f.get("address"))

        latitude = longitude = None
        try:
            lat_c = float(f.get("latitude"))
            lng_c = float(f.get("longitude"))
            if 11.9 <= lat_c <= 12.5 and -69.3 <= lng_c <= -68.5:
                latitude, longitude = lat_c, lng_c
        except (TypeError, ValueError):
            pass

        images = self.clean_images([im.get("src") for im in (f.get("listing_img") or [])])

        return Listing(
            source_id=self.source_id,
            external_id=str(listing_id),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=url,
            description=description_text or None,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood=neighborhood,
            latitude=latitude,
            longitude=longitude,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
