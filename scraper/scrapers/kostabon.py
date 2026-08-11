"""Kostabon scraper (priority 8)
Site: https://kostabon.com — WordPress + Estatik real-estate plugin,
zelfde pluginfamilie/markup als ambiente.py en real_estate_agency_cb.py.
nginx-hosting, geen blokkade-signalen. robots.txt: alles toegestaan
behalve `/wp-admin/`, `Sitemap: /sitemap_index.xml`.

Vóór deze scraper stond er handmatig 1 test-listing in Supabase (zie
`claude/session-2026-08-11-kostabon-fix-en-scraper-scheduled-task.md`)
met een prijs/locatie-fix — die sessie ontdekte dat de **JSON-LD op de
detailpagina lat/lng verwisseld heeft** (`geo.latitude`/`geo.longitude`
staan omgekeerd). Deze scraper gebruikt daarom NIET de JSON-LD, maar de
`data-latitude`/`data-longitude`-attributen van `#es-single-map`, die wél
in de juiste volgorde staan (geverifieerd met een Curaçao-bounding-box-
check op dezelfde listing als de handmatige fix).

Methode:
  1. De `properties`-achtige custom post type zit niet in de WP REST API
     (404 rest_no_route) — complete lijst komt uit `properties-sitemap.xml`
     (de kale `/aanbod/`-indexpagina overslaan).
  2. Per detailpagina staan alle velden in `<li class="es-property-field
     es-property-field--<veld>">`-elementen (zelfde patroon als Ambiente):
     `--es_status` (alleen "beschikbaar" meegenomen, "verkocht"/"verhuurd"/
     "onder-optie"-varianten overslaan zodra ze voorkomen), `--es_type`
     (Woning/Kavel/Appartement, Nederlandse taxonomie-slugs), `--bedrooms`,
     `--bathrooms`, `--area` (of `--lot_size` voor kavels zonder
     woonoppervlak), `--es_neighborhood`, en **`--post_content`** voor de
     volledige beschrijving (de og:description-meta en de JSON-LD-
     description zijn allebei kort afgekapt met "[…]" — post_content is de
     enige plek met de volledige tekst).
  3. Prijs: `div.es-price-container span.es-price`, bv. "ƒ3,580,000" — het
     ƒ-symbool is hier NAf/XCG (site-config bevestigt `currency: "ANG"`,
     `currency_sign: "ƒ"`), dus native XCG, geen omrekening. $ / € defensief
     ook afgevangen (USD native resp. ×1.95 naar XCG), nog niet gezien in
     de steekproef.
  4. Foto's: alleen `a.js-es-image`-links binnen `div.es-gallery` (volledige
     `-scaled.jpg`-resolutie) — een kale `img[src*=wp-content/uploads]`-
     selectie over de hele pagina zou ook het Kostabon-brandmark-logo in
     de header meenemen (niet gevangen door de generieke logo/watermark-
     uitsluitlijst in `clean_images`).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://kostabon.com"
SITEMAP = f"{BASE}/properties-sitemap.xml"
EUR_TO_XCG = 1.95

EXCLUDE_STATUS_SLUGS = {
    "verkocht", "sold", "verhuurd", "rented",
    "onder-optie", "in-optie", "under-contract",
}

TYPE_MAP = {
    "woning": "house",
    "kavel": "land",
    "appartement": "apartment",
    "penthouse": "apartment",
    "studio": "apartment",
    "commercieel": "commercial",
    "bedrijfspand": "commercial",
}

PRICE_RE = re.compile(r"(ƒ|XCG|ANG|NAF|NAf|EUR|€|USD|\$)\s*([\d][\d.,]{1,12})", re.I)


class KostabonScraper(BaseScraper):
    source_name = "kostabon"
    AGENT_COMPANY = "Kostabon"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if re.search(r"/aanbod/[^/]+/?$", u)]
        self.logger.info(f"Kostabon: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Kostabon: {len(results)} actieve listings verwerkt")
        return results

    def _field_value(self, soup, field: str):
        li = soup.find("li", class_=f"es-property-field--{field}")
        if not li:
            return None
        val = li.find(class_="es-property-field__value")
        return val if val else None

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title:
            return None

        external_id = url.rstrip("/").split("/")[-1]

        status_val = self._field_value(soup, "es_status")
        status_slug = None
        listing_type = "sale"
        if status_val:
            link = status_val.find("a")
            if link and link.get("href"):
                m = re.search(r"/es_status/([^/]+)/", link["href"])
                if m:
                    status_slug = m.group(1)
            status_text = self.clean_text(status_val.get_text()).lower()
            if "huur" in status_text:
                listing_type = "rent"
        if status_slug in EXCLUDE_STATUS_SLUGS:
            return None

        property_type = "house"
        type_val = self._field_value(soup, "es_type")
        type_slug = None
        if type_val:
            link = type_val.find("a")
            if link and link.get("href"):
                m = re.search(r"/aanbod-type/([^/]+)/", link["href"])
                if m:
                    type_slug = m.group(1)
                    property_type = TYPE_MAP.get(type_slug, "house")

        bedrooms = None
        v = self._field_value(soup, "bedrooms")
        if v:
            bedrooms = self.parse_int(v.get_text())
        bathrooms = None
        v = self._field_value(soup, "bathrooms")
        if v:
            bathrooms = self.parse_int(v.get_text())

        area_sqm = None
        v = self._field_value(soup, "area")
        if v:
            area_sqm = self.parse_area(v.get_text())
        if not area_sqm:
            v = self._field_value(soup, "lot_size")
            if v:
                area_sqm = self.parse_area(v.get_text())

        neighborhood = None
        v = self._field_value(soup, "es_neighborhood")
        if v:
            neighborhood = self.clean_text(v.get_text())

        latitude = longitude = None
        map_div = soup.find(id="es-single-map")
        if map_div:
            try:
                latitude = float(map_div.get("data-latitude"))
                longitude = float(map_div.get("data-longitude"))
            except (TypeError, ValueError):
                pass
        if latitude is not None and longitude is not None:
            if not (11.9 <= latitude <= 12.5 and -69.3 <= longitude <= -68.5):
                self.logger.warning(
                    f"Coördinaten buiten Curaçao voor {url}: {latitude},{longitude} — genegeerd"
                )
                latitude = longitude = None

        price, currency = None, "XCG"
        price_container = soup.find(class_="es-price-container")
        if price_container:
            price_span = price_container.find(class_="es-price")
            if price_span:
                m = PRICE_RE.search(price_span.get_text(" "))
                if m:
                    cur_raw = m.group(1).upper()
                    amount = self.parse_price(m.group(2))
                    if amount:
                        if cur_raw in ("€", "EUR"):
                            price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                        elif cur_raw in ("$", "USD"):
                            price, currency = amount, "USD"
                        else:
                            price, currency = amount, "XCG"

        description = None
        v = self._field_value(soup, "post_content")
        if v:
            description = self.clean_text(v.get_text(" "))
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        images = []
        gallery = soup.find(class_="es-gallery")
        if gallery:
            for a in gallery.find_all("a", class_="js-es-image", href=True):
                images.append(a["href"])
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=external_id,
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
            latitude=latitude,
            longitude=longitude,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
