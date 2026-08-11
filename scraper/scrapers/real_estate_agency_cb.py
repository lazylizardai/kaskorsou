"""Real Estate Agency CB / Curacao-Homes scraper (priority 8)
Site: https://curacao-homes.com — WordPress (Astra-thema) + "Easy Real
Estate" (ES) plugin, gewone hosting (geen WPCloud-signaal, geen captcha).
robots.txt staat alles toe behalve /wp-admin/, expliciet `Allow:
/sitemap_index.xml`. wp-json volledig bereikbaar.

Methode:
  1. De ES-plugin registreert een `properties` custom post type in de REST
     API (rest_base `properties`) — 20 listings, 1 pagina met per_page=100.
     Geen los prijs/bed/bath-veld in de REST-payload (`meta` bevat alleen
     Astra-thema-ruis), dus per listing de gerenderde HTML-detailpagina
     gebruiken (zelfde patroon als moret/sunset_realtors/curacao_exclusive).
  2. Taxonomieën `es_categories` (Huur/Koop/Commercieel, rest_base van
     `es_category`) en `es_types` (Woning/Appartement/Villa/Grond/
     kantoorruimte/etc., rest_base van `es_type`) één keer ophalen om
     REST-taxonomie-ids naar slugs te mappen — veel betrouwbaarder dan een
     keyword-heuristiek op de titel. `es_statuses` bleek een lege taxonomie
     (geen termen) — de publieke REST API geeft sowieso alleen
     publish-status listings terug, dus geen aparte sold/rented-filter nodig.
  3. Op de detailpagina staat de prijs in een kant-en-klaar
     `div.es-cat-price` blok: `es-category-items` (Huur/Koop) +
     `span.es-price` met AL DE VALUTACODE ERIN, bv. "XCG 2.200" — altijd
     native XCG in de steekproef (20/20), dus geen EUR/USD-omrekening nodig
     (wel een defensieve regex voor het geval een listing ooit €/$ toont).
  4. Bedrooms/bathrooms/overige specs staan in een schone label/waarde-lijst
     `div.es-property-fields ul li` ("Aantal slaapkamers: 4",
     "Aantal badkamers: 2.5" — badkamers kan een half getal zijn, net als
     bij Curaçao Exclusive; afgerond naar int voor de Supabase
     integer-kolom).
  5. Geen woonoppervlakte/perceeloppervlakte-veld gevonden op deze site (de
     ES-plugin toont dat hier niet) — area_sqm blijft leeg. Geen
     coördinaten (geen lat/lng in de pagina).
  6. Geen betrouwbare wijk/neighborhood-bron: de titel bevat 'm vaak wel
     (bv. "... AMERIKANENKAMP"), maar niet consistent scheidbaar van de rest
     van de titel zonder een vaste wijkenlijst — bewust leeg gelaten i.p.v.
     giswerk (zie statusdocument).
  7. Afbeeldingen via het WP REST media-endpoint (`/wp-json/wp/v2/media
     ?parent=<id>`) — completer dan de raw HTML-galerij die op JS-sliders
     leunt (zelfde aanpak als nh_real_estate.py).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://curacao-homes.com"
LIST_API = f"{BASE}/wp-json/wp/v2/properties?per_page=100&_fields=id,link,slug,title"

# es_types-slug -> ons property_type (specifiek -> generiek)
TYPE_MAP = {
    "appartement": "apartment", "penthouse": "apartment", "studio": "apartment",
    "grond": "land", "terrein": "land", "terrein-met-appartementen": "land",
    "bedrijfsruimte": "commercial", "commercieel": "commercial",
    "investeringsobject": "commercial", "kantoorpand": "commercial",
    "kantoorruimte": "commercial", "kantoorunits": "commercial",
    "winkelpand": "commercial", "vakantieverhuurobject": "commercial",
    "bungalow": "house", "villa": "house", "woning": "house",
    "woning-en-appartementen": "house", "woning-met-appartement": "house",
    "woonboot": "house",
}

PRICE_RE = re.compile(r"(XCG|USD|ANG|NAF|NAf|EUR|€|\$)\s*([\d][\d.,]{1,12})", re.I)


class RealEstateAgencyCBScraper(BaseScraper):
    source_name = "real_estate_agency_cb"
    AGENT_COMPANY = "Real Estate Agency CB"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def _tax_map(self, rest_base: str) -> dict[int, str]:
        out = {}
        try:
            for t in self._get_json(f"{BASE}/wp-json/wp/v2/{rest_base}?per_page=100&_fields=id,slug"):
                out[t["id"]] = t["slug"]
        except Exception as e:
            self.logger.warning(f"Taxonomie {rest_base} niet opgehaald: {e}")
        return out

    def scrape(self) -> list[Listing]:
        categories = self._tax_map("es_categories")  # huur / koop / commercieel
        types = self._tax_map("es_types")

        try:
            items = self._get_json(LIST_API)
        except Exception as e:
            self.logger.error(f"REST-lijst niet op te halen: {e}")
            return []

        self.logger.info(f"Real Estate Agency CB: {len(items)} listings in REST-lijst")

        results: list[Listing] = []
        for item in items:
            try:
                cat_slugs = {categories.get(i) for i in item.get("es_categories", [])}
                listing_type = "rent" if "huur" in cat_slugs else "sale"

                property_type = "house"
                for i in item.get("es_types", []):
                    slug = types.get(i)
                    if slug in TYPE_MAP:
                        property_type = TYPE_MAP[slug]
                        break

                title = self.clean_text(item.get("title", {}).get("rendered"))
                if not title:
                    continue

                l = self._scrape_detail(item["link"], str(item["id"]), title, listing_type, property_type)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({item.get('link')}): {e}")

        self.logger.info(f"Real Estate Agency CB: {len(results)} listings verwerkt")
        return results

    def _scrape_detail(self, url: str, external_id: str, title: str,
                        listing_type: str, property_type: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        # Prijs: eerste .es-price-span binnen het es-cat-price-blok (er kan
        # een 2e occurrence in een "vergelijkbare woningen"-widget staan
        # verderop op de pagina — die overslaan door alleen binnen
        # es-cat-price te zoeken).
        price, currency = None, "XCG"
        price_block = soup.find(class_="es-cat-price")
        if price_block:
            price_span = price_block.find(class_="es-price")
            if price_span:
                m = PRICE_RE.search(price_span.get_text(" "))
                if m:
                    cur_raw = m.group(1).upper()
                    amount = self.parse_price(m.group(2))
                    if amount:
                        if cur_raw == "€" or cur_raw == "EUR":
                            price, currency = round(amount * 1.95, 2), "XCG"
                        elif cur_raw == "$" or cur_raw == "USD":
                            price, currency = amount, "USD"
                        else:
                            price, currency = amount, "XCG"
            # listing_type bevestigen vanuit de HTML (leidend boven de
            # REST-taxonomie als ze ooit uiteen zouden lopen)
            cat_link = price_block.find(class_="es-category-items")
            if cat_link:
                cat_text = cat_link.get_text(strip=True).lower()
                if "huur" in cat_text:
                    listing_type = "rent"
                elif "koop" in cat_text:
                    listing_type = "sale"

        bedrooms = bathrooms = None
        fields_block = soup.find(class_="es-property-fields")
        if fields_block:
            for li in fields_block.find_all("li"):
                strong = li.find("strong")
                if not strong:
                    continue
                label = self.clean_text(strong.get_text(" ")).lower().rstrip(":")
                value = self.clean_text(li.get_text(" ").replace(strong.get_text(" "), "", 1))
                if not value:
                    continue
                if "slaapkamer" in label:
                    bedrooms = self.parse_int(value)
                elif "badkamer" in label:
                    # kas_listings.bathrooms is integer — halve badkamer
                    # ("2.5") naar beneden afronden/truncaten.
                    n = self.parse_int(value)
                    bathrooms = n

        description = None
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = self.clean_text(og_desc["content"])

        images = []
        try:
            media = self._get_json(
                f"{BASE}/wp-json/wp/v2/media?parent={external_id}&per_page=100&_fields=source_url"
            )
            images = self.clean_images([m.get("source_url") for m in media if m.get("source_url")])
        except Exception as e:
            self.logger.warning(f"Media ophalen mislukt ({external_id}): {e}")

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
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
