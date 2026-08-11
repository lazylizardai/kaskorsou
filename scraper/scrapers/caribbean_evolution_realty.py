"""Caribbean Evolution Realty scraper (priority 8)
Site: https://www.caribbeanevolutionrealty.com — WordPress (Bluehost,
"RealHomes"-thema, `REAL_HOMES_*`-metavelden zoals bij Real Estate Caribe/
Simmer/Bru de Roque/CuraHouseCare/Domicilie). Content-signal-robots.txt
zonder daadwerkelijke Disallow-regels — permissief.

Methode:
  1. **Geen pretty permalinks voor de REST API** — `/wp-json/...` geeft 404.
     Gebruik overal `?rest_route=/wp/v2/...` (WP-core fallback-syntax), zowel
     voor `/properties` als voor `/media`.
  2. Volledige lijst: `?rest_route=/wp/v2/properties&per_page=100&_embed=1`
     (59 items totaal, past in 1 pagina — `while`-lus met `per_page=100`
     voor als de site groeit).
  3. `property_meta` (`REAL_HOMES_*`) bevat prijs (altijd al native XCG in
     deze set, `..._price_prefix` leeg bij alle actieve listings — geen
     EUR/USD-omrekening nodig gezien, maar prefix-check blijft staan als
     vangnet), slaapkamers/badkamers (badkamers kunnen een halve kamer zijn,
     bv. "2.5" — **bekende valkuil: `kas_listings.bathrooms` is integer**,
     dus afronden vóór upsert).
  4. Taxonomieën via `_embed=1` → `_embedded['wp:term']`: `property-status`
     kent 7 waarden (`for-sale`, `for-rent`, `sold`, `rented`,
     `under-buying-negotiations`, `under-buying-contract`,
     `sold-under-reservation`) — alleen `for-sale`/`for-rent` zonder een van
     de overige (inactieve) statussen op dezelfde listing meenemen.
     `property-type` is vrije tekst zonder vaste taxonomie (bv.
     "luxurious-apartments-model-a", "2-houses-1-extra-land-space") —
     keyword-matching op de slug (business/commercial → commercial, land
     zonder house/apartment → land, apartment zonder house → apartment,
     anders house). `property-city` geeft een schone buurtnaam.
  5. **Titels bevatten vetgedrukte Unicode-mathematische letters** (bv.
     "𝗙𝗢𝗥 𝗦𝗔𝗟𝗘") als marketing-opmaak — titel zelf ongewijzigd laten (rendert
     prima), maar voor keyword-matching (property-type-fallback) een
     `unicodedata.normalize("NFKD", ...)`-kopie gebruiken, zelfde patroon
     als bij GS Real Estate.
  6. Coördinaten in `REAL_HOMES_property_location` staan bij alle listings op
     `0/0` (niet ingevuld) — bounding-box-check laat deze dus vanzelf weg.
  7. Foto's: `?rest_route=/wp/v2/media&parent=<id>` geeft de volledige
     galerij; featured image via `_embedded['wp:featuredmedia']`.
"""
import html
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.caribbeanevolutionrealty.com"
API = f"{BASE}/index.php"
PAGE_SIZE = 100

INACTIVE_STATUSES = {
    "sold",
    "rented",
    "under-buying-negotiations",
    "under-buying-contract",
    "sold-under-reservation",
}


class CaribbeanEvolutionRealtyScraper(BaseScraper):
    source_name = "caribbean_evolution_realty"
    AGENT_COMPANY = "Caribbean Evolution Realty"

    def _get_json(self, rest_route: str, params: dict | None = None):
        p = {"rest_route": rest_route}
        if params:
            p.update(params)
        r = self.session.get(API, params=p, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        items = []
        page = 1
        while True:
            try:
                batch = self._get_json(
                    "/wp/v2/properties",
                    {"per_page": PAGE_SIZE, "page": page, "_embed": 1},
                )
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

        self.logger.info(f"Caribbean Evolution Realty: {len(items)} listings uit de REST API")

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
            media = self._get_json("/wp/v2/media", {"parent": property_id, "per_page": 100})
            for m in media:
                if m.get("source_url"):
                    images.append(m["source_url"])
        except Exception as e:
            self.logger.warning(f"Media error ({property_id}): {e}")
        return self.clean_images(images)

    def _property_type(self, type_slugs: list[str], title_norm: str) -> str:
        haystack = (" ".join(type_slugs) + " " + title_norm).lower()
        if any(k in haystack for k in ("business", "commercial", "shop", "office")):
            return "commercial"
        if "land" in haystack and "house" not in haystack and "apartment" not in haystack:
            return "land"
        if "apartment" in haystack and "house" not in haystack:
            return "apartment"
        return "house"

    def _build(self, item: dict) -> Listing | None:
        property_id = item.get("id")
        if not property_id:
            return None

        terms = self._terms(item)
        status_slugs = {s for s, _ in terms.get("property-status", [])}
        if status_slugs & INACTIVE_STATUSES:
            return None
        if "for-rent" in status_slugs:
            listing_type = "rent"
        elif "for-sale" in status_slugs:
            listing_type = "sale"
        else:
            return None

        title_raw = html.unescape(item.get("title", {}).get("rendered", ""))
        title = self.clean_text(title_raw) or "Woning Curaçao"
        title_norm = unicodedata.normalize("NFKD", title)
        url = item.get("link") or f"{BASE}/?property={item.get('slug', '')}"

        pm = item.get("property_meta") or {}
        prefix = (pm.get("REAL_HOMES_property_price_prefix") or "").strip().upper()
        price_raw = pm.get("REAL_HOMES_property_price")
        price, currency = None, "XCG"
        if price_raw:
            amount = self.parse_price(str(price_raw))
            if amount:
                if prefix == "€":
                    price, currency = round(amount * 1.95, 2), "XCG"
                elif prefix == "$":
                    price, currency = amount, "USD"
                else:
                    price, currency = amount, "XCG"
        if not price:
            return None

        bedrooms = self.parse_int(pm.get("REAL_HOMES_property_bedrooms") or "")
        bathrooms_raw = pm.get("REAL_HOMES_property_bathrooms") or ""
        bathrooms = None
        try:
            if bathrooms_raw:
                bathrooms = round(float(str(bathrooms_raw).replace(",", ".")))
        except (TypeError, ValueError):
            bathrooms = None

        area_sqm = None
        for key in ("REAL_HOMES_property_size", "REAL_HOMES_property_lot_size"):
            v = pm.get(key)
            if v:
                area_sqm = self.parse_area(str(v)) or self.parse_int(str(v))
                if area_sqm:
                    break

        type_slugs = [s for s, _ in terms.get("property-type", [])]
        property_type = self._property_type(type_slugs, title_norm)

        city_terms = terms.get("property-city", [])
        neighborhood = self.clean_text(city_terms[0][1]) if city_terms else None

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
