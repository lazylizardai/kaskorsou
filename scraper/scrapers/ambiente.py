"""Ambiente Real Estate scraper (priority 8)
Site: https://ambienterealestate.com — WordPress + Estatik real-estate
plugin (`es_` prefix, `estatik/public/js/...` scripts — zelfde
pluginfamilie als real_estate_agency_cb.py maar een nieuwere versie met
veel rijkere HTML-markup). LiteSpeed-hosting, geen WPCloud-signaal.
robots.txt: alles toegestaan, `Sitemap: /sitemap_index.xml`.

Methode:
  1. De `properties` custom post type zit NIET in de WP REST API
     (`/wp-json/wp/v2/properties` → 404 rest_no_route) — dus de complete
     lijst komt uit `properties-sitemap.xml` (19 URL's, de kale
     `/property/` index-URL overslaan).
  2. Per detailpagina staat alles in nette `<li class="es-property-field
     es-property-field--<veld>">`-elementen — geen label-tekst parsen
     nodig, gewoon op exacte CSS-classnaam selecteren:
     `--es_type` (Apartments/Commercial/Houses/Lots/Penthouse),
     `--es_status` (For sale/Under contract — under-contract/sold/rented
     worden overgeslagen), `--bedrooms`, `--bathrooms`, `--area`
     (waarde in een `<b>`-tag, bv. "114 m²"), `--es_neighborhood` (niet op
     elke listing aanwezig).
  3. Prijs staat los in `div.es-price-container span.es-price`, bv.
     "$450,000" (Amerikaans duizendtal-format, USD — geen listing met een
     ander valutasymbool gezien in de steekproef, dus defensief ook
     XCG/€-varianten afgevangen). Soms alleen een "Call for price"-badge
     zonder bedrag → price=None (geen "Price Upon Request"-tekst om te
     parsen, gewoon leeg).
  4. **Bijzonder: ECHTE coördinaten beschikbaar** — `div.es-property-map`
     heeft `data-latitude`/`data-longitude`-attributen met de exacte
     locatie. Dit is de eerste van de nieuwe makelaars in deze reeks met
     bruikbare lat/long (de meeste WordPress-sites tot nu toe hadden een
     lege of thema-default kaart).
  5. Alle 19 sitemap-listings bleken "For sale" (geen for-rent-status
     geregistreerd op deze site).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://ambienterealestate.com"
SITEMAP = f"{BASE}/properties-sitemap.xml"

EXCLUDE_STATUS_SLUGS = {"under-contract", "sold", "rented"}

TYPE_MAP = {
    "apartments": "apartment", "penthouse": "apartment",
    "houses": "house",
    "lots": "land",
    "commercial": "commercial",
}

PRICE_RE = re.compile(r"(XCG|USD|ANG|NAF|NAf|EUR|€|\$)\s*([\d][\d.,]{1,12})", re.I)


class AmbienteScraper(BaseScraper):
    source_name = "ambiente"
    AGENT_COMPANY = "Ambiente Real Estate"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if re.search(r"/property/[^/]+/?$", u)]
        self.logger.info(f"Ambiente: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Ambiente: {len(results)} actieve listings verwerkt")
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
            if "rent" in status_text:
                listing_type = "rent"
        if status_slug in EXCLUDE_STATUS_SLUGS:
            return None

        property_type = "house"
        type_val = self._field_value(soup, "es_type")
        if type_val:
            link = type_val.find("a")
            if link and link.get("href"):
                m = re.search(r"/property-type/([^/]+)/", link["href"])
                if m:
                    property_type = TYPE_MAP.get(m.group(1), "house")

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

        neighborhood = None
        v = self._field_value(soup, "es_neighborhood")
        if v:
            neighborhood = self.clean_text(v.get_text())

        latitude = longitude = None
        map_div = soup.find(class_="es-property-map")
        if map_div:
            try:
                latitude = float(map_div.get("data-latitude"))
                longitude = float(map_div.get("data-longitude"))
            except (TypeError, ValueError):
                pass

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
                            price, currency = round(amount * 1.95, 2), "XCG"
                        elif cur_raw in ("$", "USD"):
                            price, currency = amount, "USD"
                        else:
                            price, currency = amount, "XCG"

        description = None
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = self.clean_text(og_desc["content"])

        images = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "/wp-content/uploads/" in src:
                images.append(src)
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
