"""Real Estate Caribe scraper (priority 8)
Site: https://www.realestatecaribe.com — WordPress (Bluehost/LiteSpeed,
"RealHomes"/"Inspiry"-thema, `REAL_HOMES_`/`inspiry_`-metavelden), gewone
hosting, geen WPCloud/SiteGround-blokkade-signalen. robots.txt staat
`/wp-json/` en `/property/` gewoon toe.

Methode:
  1. Volledige lijst rechtstreeks uit de WP REST API: GET
     `/wp-json/wp/v2/property?per_page=100&_embed=1` (50 listings passen in
     1 pagina, dus geen paginering-lus nodig maar wel `while`-lus met
     `per_page=100` voor als de site groeit).
  2. `property_meta` (`REAL_HOMES_*`/`inspiry_*`) bevat alles structured:
     prijs (`REAL_HOMES_property_price`, met los `..._price_prefix`-veld
     voor de valuta: `""`/`"XCG"` → native XCG, `"€"` → EUR ×1.95 naar
     XCG, `"$"` → native USD), slaapkamers/badkamers, oppervlak
     (`REAL_HOMES_property_size`, vaak leeg — dan `inspiry_..._living_area_m2`
     als fallback), en **echte coördinaten**
     (`REAL_HOMES_property_location.latitude/longitude`).
  3. Taxonomieën via `_embed=1` → `_embedded['wp:term']`: `property-status`
     (for-rent/for-sale — geen sold/rented/archived-term aanwezig in deze
     taxonomie, dus geen extra statusfilter nodig) en `property-type`
     (residential/commercial/lots). Voor "residential" bepaalt de
     `inspiry_type`-meta (House/Apartment/Resort/...) huis vs appartement.
  4. Foto's: `/wp-json/wp/v2/media?parent=<property-id>` geeft de volledige
     galerij (featured image zit er niet altijd bij, dus die appart
     toevoegen via `_embedded['wp:featuredmedia']`).
  5. Beschrijving uit `content.rendered` (HTML gestript).
"""
import html
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.realestatecaribe.com"
API = f"{BASE}/wp-json/wp/v2/property"
MEDIA_API = f"{BASE}/wp-json/wp/v2/media"
PAGE_SIZE = 100
EUR_TO_XCG = 1.95

APARTMENT_HINTS = ("apartment", "resort", "penthouse", "condo", "studio")


class RealEstateCaribeScraper(BaseScraper):
    source_name = "real_estate_caribe"
    AGENT_COMPANY = "Real Estate Caribe"

    def _get_json(self, url: str, params: dict):
        r = self.session.get(url, params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        items = []
        page = 1
        while True:
            try:
                batch = self._get_json(API, {"per_page": PAGE_SIZE, "page": page, "_embed": 1})
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon properties niet ophalen: {e}")
                    return []
                break
            if not batch:
                break
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1

        self.logger.info(f"Real Estate Caribe: {len(items)} listings uit de REST API")

        results = []
        for item in items:
            try:
                l = self._build(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({item.get('id')}): {e}")
        return results

    def _terms(self, item: dict) -> dict:
        """taxonomy -> [(slug, name), ...] uit _embedded['wp:term']"""
        out: dict[str, list[tuple[str, str]]] = {}
        for grp in (item.get("_embedded") or {}).get("wp:term", []):
            for t in grp:
                out.setdefault(t.get("taxonomy"), []).append((t.get("slug"), t.get("name")))
        return out

    def _images(self, property_id: int, item: dict) -> list[str]:
        images = []
        fm = (item.get("_embedded") or {}).get("wp:featuredmedia")
        if fm and fm[0].get("source_url"):
            images.append(fm[0]["source_url"])
        try:
            media = self._get_json(MEDIA_API, {"parent": property_id, "per_page": 100})
            for m in media:
                if m.get("source_url"):
                    images.append(m["source_url"])
        except Exception as e:
            self.logger.warning(f"Media error ({property_id}): {e}")
        return self.clean_images(images)

    def _build(self, item: dict) -> Listing | None:
        property_id = item.get("id")
        if not property_id:
            return None

        title = self.clean_text(html.unescape(item.get("title", {}).get("rendered", ""))) or "Woning Curaçao"
        url = item.get("link") or f"{BASE}/property/{item.get('slug', '')}/"

        terms = self._terms(item)
        status_slugs = {s for s, _ in terms.get("property-status", [])}
        if "for-rent" in status_slugs:
            listing_type = "rent"
        elif "for-sale" in status_slugs:
            listing_type = "sale"
        else:
            listing_type = "sale"

        type_slugs = {s for s, _ in terms.get("property-type", [])}
        pm = item.get("property_meta") or {}
        if "lots" in type_slugs:
            property_type = "land"
        elif "commercial" in type_slugs:
            property_type = "commercial"
        else:
            inspiry_type = (pm.get("inspiry_type") or "").lower()
            property_type = "apartment" if any(h in inspiry_type for h in APARTMENT_HINTS) else "house"

        prefix = (pm.get("REAL_HOMES_property_price_prefix") or "").strip().upper()
        price_raw = pm.get("REAL_HOMES_property_price")
        price, currency = None, "XCG"
        if price_raw:
            amount = self.parse_price(str(price_raw))
            if amount:
                if prefix == "€":
                    price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                elif prefix == "$":
                    price, currency = amount, "USD"
                else:
                    price, currency = amount, "XCG"

        bedrooms = self.parse_int(pm.get("REAL_HOMES_property_bedrooms") or "")
        bathrooms = self.parse_int(pm.get("REAL_HOMES_property_bathrooms") or "")

        area_sqm = None
        for key in ("REAL_HOMES_property_size", "inspiry_caribe-resi-living_area_m2", "inspiry_caribe-resi-total_space"):
            v = pm.get(key)
            if v:
                area_sqm = self.parse_area(str(v)) or self.parse_int(str(v))
                if area_sqm:
                    break

        city_terms = terms.get("property-city", [])
        neighborhood = self.clean_text(city_terms[0][1]) if city_terms else None
        if not neighborhood:
            neighborhood = self.clean_text(pm.get("REAL_HOMES_property_address"))

        latitude = longitude = None
        loc = pm.get("REAL_HOMES_property_location") or {}
        try:
            lat_c = float(loc.get("latitude"))
            lng_c = float(loc.get("longitude"))
            if 11.9 <= lat_c <= 12.5 and -69.3 <= lng_c <= -68.5:
                latitude, longitude = lat_c, lng_c
        except (TypeError, ValueError):
            pass

        description = None
        content_html = (item.get("content") or {}).get("rendered")
        if content_html:
            from bs4 import BeautifulSoup
            description = self.clean_text(BeautifulSoup(content_html, "lxml").get_text(" "))

        images = self._images(property_id, item)

        return Listing(
            source_id=self.source_id,
            external_id=str(property_id),
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
