"""Sunset Realtors scraper (priority 8)
Site: https://sunset-realtors.com — WordPress (Kadence-thema), LiteSpeed-
hosting (geen WordPress.com/WPCloud-signaal, dus geen bekend GH Actions-
IP-blokkaderisico). robots.txt disallow't expliciet /wp-json/ (naast de
standaard wp-admin-regels), dus i.p.v. de REST API wordt de sitemap +
detailpagina-HTML gebruikt — zelfde aanpak als moret.py.

Methode:
  1. `property-sitemap.xml` (los sitemap-bestand, apart van post/page/office)
     linkt naar alle ~65 listing-detailpagina's. URL-structuur zelf geeft al
     listing_type + property_type: /vastgoed/{koop|huur}/{wijk}/{type}/{slug}
     (type: appartement/woning/commercieel/bouwkavel).
  2. Per detailpagina een schone `dl`-tabel (`div.property-data-table` >
     `dl` > dt/dd-paren) met Status/Straatnaam/Stad/Aantal slaapkamers/
     Aantal badkamers/Woonoppervlakte/Oppervlakte/Perceeloppervlakte.
     Status filter: alleen "Te koop"/"Te huur" meenemen, "Verkocht"/
     "Verhuurd" overslaan.
  3. Prijs NIET uit de tekst parsen — de site zet het al voorgerekende
     bedrag in 3 valuta's als data-attributen op het EERSTE
     `.sunset-property-price`-element op de pagina (dat is altijd de prijs
     van de hoofdlisting; latere occurrences op dezelfde pagina horen bij
     de "gerelateerd vastgoed"-carousel onderaan en worden genegeerd):
     `data-price-eur`/`data-price-usd`/`data-price-ang`. We gebruiken
     `data-price-ang` direct als XCG-prijs (geen eigen omrekening nodig).
     "Prijs op aanvraag"-listings hebben geen data-attributen -> price=None.
  4. Foto's uit de ingebedde `ysd-mapi-property-single-js-extra`-JSON
     (`image_list[].full`), coördinaten uit de `mapData`-JSON
     (`property.lattitude`/`property.longitude`, let op de typo in de
     brondata). Omschrijving uit de og:description meta-tag. external_id =
     WordPress post-ID uit de `postid-<nr>`-class op de <body>.
"""
import json
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://sunset-realtors.com"
SITEMAP_URL = f"{BASE}/property-sitemap.xml"

PROPERTY_TYPE_MAP = {
    "appartement": "apartment",
    "woning": "house",
    "commercieel": "commercial",
    "bouwkavel": "land",
}

ACTIVE_STATUSES = {"te koop", "te huur"}

POSTID_RE = re.compile(r"postid-(\d+)")
MAPDATA_RE = re.compile(r"var mapData = (\{.*?\});", re.DOTALL)
IMAGEDATA_RE = re.compile(
    r'<script id="ysd-mapi-property-single-js-extra"[^>]*>(.*?)</script>', re.DOTALL
)
IMAGEDATA_VAR_RE = re.compile(r"var data = (\{.*?\});", re.DOTALL)


class SunsetRealtorsScraper(BaseScraper):
    source_name = "sunset_realtors"
    AGENT_COMPANY = "Sunset Realtors"

    def scrape(self) -> list[Listing]:
        soup = self.get(SITEMAP_URL)
        if soup is None:
            self.logger.error("Sitemap niet op te halen")
            return []

        urls = []
        for loc in soup.find_all("loc"):
            u = loc.get_text(strip=True)
            if "/vastgoed/" in u:
                urls.append(u)

        self.logger.info(f"Sunset Realtors: {len(urls)} listing-URLs in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Sunset Realtors: {len(results)} actieve listings na status/land-filter")
        return results

    def _url_type_hints(self, url: str):
        parts = url.replace(f"{BASE}/vastgoed/", "").strip("/").split("/")
        listing_type = None
        property_type = None
        if len(parts) >= 1:
            listing_type = "sale" if parts[0] == "koop" else "rent" if parts[0] == "huur" else None
        if len(parts) >= 3:
            property_type = PROPERTY_TYPE_MAP.get(parts[2])
        return listing_type, property_type

    def _scrape_detail(self, url: str) -> Listing | None:
        page_soup = self.get(url)
        if page_soup is None:
            return None
        html = str(page_soup)

        # Status + kerncijfers uit de dt/dd-tabellen
        fields: dict[str, str] = {}
        for wrap in page_soup.find_all("div", class_="property-data-table"):
            dl = wrap.find("dl")
            if not dl:
                continue
            for dt in dl.find_all("dt"):
                dd = dt.find_next_sibling("dd")
                if dd:
                    fields[self.clean_text(dt.get_text())] = self.clean_text(dd.get_text(" "))

        status = (fields.get("Status") or "").strip().lower()
        if status and status not in ACTIVE_STATUSES:
            return None
        if not status:
            # geen Status-veld gevonden -> voorzichtigheidshalve overslaan,
            # kan een niet-standaard detailpagina zijn (bv. project-overzicht)
            return None

        listing_type, property_type = self._url_type_hints(url)
        if listing_type is None:
            listing_type = "rent" if "huur" in status else "sale"
        if property_type is None:
            property_type = "house"

        title_tag = page_soup.find("h1")
        title = self.clean_text(title_tag.get_text()) if title_tag else None
        if not title:
            return None

        m = POSTID_RE.search(html)
        external_id = m.group(1) if m else url

        # Prijs: eerste .sunset-property-price met data-price-ang op de pagina
        price = None
        currency = "XCG"
        price_el = page_soup.find(class_="sunset-property-price")
        if price_el and price_el.get("data-price-ang"):
            try:
                price = float(price_el["data-price-ang"])
            except (TypeError, ValueError):
                price = None

        # De site vult "Aantal slaapkamers"/"Aantal badkamers" ook in voor
        # commercieel/grond met een zinloze default ("1 slaapkamer" voor een
        # kantoorruimte) — alleen echt vertrouwen bij woning/appartement.
        bedrooms = bathrooms = None
        if property_type in ("house", "apartment"):
            bedrooms = self.parse_int(fields.get("Aantal slaapkamers", "")) if fields.get("Aantal slaapkamers") else None
            bathrooms = self.parse_int(fields.get("Aantal badkamers", "")) if fields.get("Aantal badkamers") else None
        area_text = fields.get("Woonoppervlakte") or fields.get("Oppervlakte") or fields.get("Perceeloppervlakte")
        area_sqm = self.parse_area(area_text) if area_text else None

        neighborhood = fields.get("Straatnaam") or fields.get("Stad")

        # Coördinaten uit mapData-JSON
        latitude = longitude = None
        mm = MAPDATA_RE.search(html)
        if mm:
            try:
                map_data = json.loads(mm.group(1))
                prop = map_data.get("property", {})
                if prop.get("lattitude"):
                    latitude = float(prop["lattitude"])
                if prop.get("longitude"):
                    longitude = float(prop["longitude"])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Omschrijving uit og:description
        description = None
        og_desc = page_soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = self.clean_text(og_desc["content"])

        # Foto's uit ingebedde image_list-JSON
        images = []
        im = IMAGEDATA_RE.search(html)
        if im:
            vm = IMAGEDATA_VAR_RE.search(im.group(1))
            if vm:
                try:
                    image_data = json.loads(vm.group(1))
                    images = [img.get("full") for img in image_data.get("image_list", []) if img.get("full")]
                except (json.JSONDecodeError, TypeError):
                    pass
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=str(external_id),
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
