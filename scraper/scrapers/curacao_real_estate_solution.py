"""Curaçao Real Estate Solution scraper (priority 8)
Site: https://curacaorealestatesolution.com — WordPress + Houzez-thema, met de 'property'
custom-post-type WÉL geregistreerd in de WP REST API (rest_base 'properties') — in
tegenstelling tot Domicilie/PriceMatch (zelfde Houzez-thema, maar daar was de CPT niet in
de REST API geregistreerd, dus HTML-parsing nodig was). Hier kan vrijwel alles rechtstreeks
uit de REST-payload (`property_meta`, fave_*-velden) gehaald worden.
robots.txt: geen ClaudeBot/AI-crawler-disallow, alles toegestaan, geen crawl-delay.

Methode:
  1. GET /wp-json/wp/v2/properties?property_status=24,25 (24=for-rent, 25=for-sale) in
     één call — van de 50 posts zijn er 16 actief; taxonomietermen rented(65)=28, sold(64)=4,
     undercontract(66)=2 sluiten de rest al uit. Geen los "SOLD"/"RENTED"-tekstsignaal
     gezien in titel/beschrijving van de actieve listings (i.t.t. eerdere scrapers in deze
     set) — de site houdt de statustaxonomie zelf schoon bij.
  2. Prijs/bedrooms/bathrooms/size/land/adres/coördinaten/foto-media-ids zitten allemaal in
     `property_meta` (fave_property_*, houzez_geolocation_*). Prijs is altijd al native XCG
     (`fave_currency`), maar kan ook non-numerieke tekst zijn ("Price upon request") → price=None.
  3. property_type-taxonomie staat op deze site altijd leeg (geen enkele listing heeft een
     property_type-term) — het type wordt daarom, net als bij CuraHouseCare, via
     keyword-matching op de titel afgeleid.
  4. Foto's: property_meta bevat alleen media-attachment-IDs (`fave_property_images`), geen
     URL's — één bulk-GET naar /wp-json/wp/v2/media?include=<ids> lost alle IDs in één of
     twee calls op naar source_url, i.p.v. per listing een aparte request.
"""
import html
import re
from ..base_scraper import BaseScraper
from ..models import Listing

RENT_STATUS_ID = 24
SALE_STATUS_ID = 25
ACTIVE_STATUS_IDS = {RENT_STATUS_ID, SALE_STATUS_ID}

# volgorde belangrijk: specifiek → generiek
TYPE_KEYWORDS = (
    ("apartment", ("apartment", "studio", "penthouse", "condo")),
    ("commercial", ("commercial", "office", "warehouse", "retail", "investment opp")),
    ("land", ("lot ", "lots ", "land ", "kavel", "terrein", "acre")),
    ("house", ("villa", "house", "home", "townhouse", "bungalow", "duplex")),
)


class CuracaoRealEstateSolutionScraper(BaseScraper):
    source_name = "curacao_real_estate_solution"
    BASE = "https://curacaorealestatesolution.com"
    AGENT_COMPANY = "Curaçao Real Estate Solution"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        try:
            posts = self._get_json(
                f"{self.BASE}/wp-json/wp/v2/properties"
                f"?property_status={RENT_STATUS_ID},{SALE_STATUS_ID}&per_page=100"
                "&_fields=id,slug,link,title,content,property_status,property_meta"
            )
        except Exception as e:
            self.logger.error(f"Kon properties-lijst niet ophalen: {e}")
            return []

        # Alle media-IDs verzamelen voor één (of enkele) bulk-lookup i.p.v. per listing.
        media_ids: set[str] = set()
        for p in posts:
            for mid in (p.get("property_meta") or {}).get("fave_property_images", []):
                if mid:
                    media_ids.add(str(mid))
        media_url = self._resolve_media(media_ids)

        results = []
        for p in posts:
            status_ids = set(p.get("property_status") or [])
            if not (status_ids & ACTIVE_STATUS_IDS):
                continue  # rented/sold/undercontract/geen status
            try:
                l = self._build(p, status_ids, media_url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Post error ({p.get('id')}): {e}")

        self.logger.info(f"Curaçao Real Estate Solution: {len(results)} actieve listings")
        return results

    def _resolve_media(self, ids: set[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        ids_list = sorted(ids, key=lambda x: int(x))
        for i in range(0, len(ids_list), 80):
            chunk = ids_list[i:i + 80]
            try:
                items = self._get_json(
                    f"{self.BASE}/wp-json/wp/v2/media?include={','.join(chunk)}"
                    f"&per_page=100&_fields=id,source_url"
                )
                for m in items:
                    if m.get("source_url"):
                        out[str(m["id"])] = m["source_url"]
            except Exception as e:
                self.logger.warning(f"Media-lookup mislukt voor chunk: {e}")
        return out

    def _meta(self, p, key):
        vals = (p.get("property_meta") or {}).get(key)
        if not vals:
            return None
        v = vals[0]
        return v if v not in ("", None) else None

    def _build(self, p, status_ids, media_url) -> Listing | None:
        title = self.clean_text(html.unescape(p["title"]["rendered"]))
        if not title:
            return None

        listing_type = "rent" if RENT_STATUS_ID in status_ids else "sale"

        haystack = title.lower()
        property_type = "house"
        for ptype, words in TYPE_KEYWORDS:
            if any(w in haystack for w in words):
                property_type = ptype
                break

        price, currency = self._parse_price(p)

        bedrooms = self.parse_int(self._meta(p, "fave_property_bedrooms") or "")
        bathrooms = self.parse_int(self._meta(p, "fave_property_bathrooms") or "")
        # fave_property_size is een kale cijferstring zonder eenheid ("100", "~100"),
        # niet "100 m²" — self.parse_area() (die een "m" in de tekst verwacht) mist dit
        # dus stelselmatig. Bij land/kavels staat de oppervlakte soms alleen in
        # fave_property_land i.p.v. fave_property_size.
        area_sqm = (
            self._parse_size(self._meta(p, "fave_property_size"))
            or self._parse_size(self._meta(p, "fave_property_land"))
        )

        lat_raw = self._meta(p, "houzez_geolocation_lat")
        lng_raw = self._meta(p, "houzez_geolocation_long")
        latitude = longitude = None
        if lat_raw and lng_raw:
            try:
                lat, lng = float(lat_raw), float(lng_raw)
                if 11.9 <= lat <= 12.5 and -69.3 <= lng <= -68.6:
                    latitude, longitude = lat, lng
            except ValueError:
                pass

        address = self._meta(p, "fave_property_address") or self._meta(p, "fave_property_map_address")
        neighborhood = self.clean_text(html.unescape(address)) if address else None

        content_html = (p.get("content") or {}).get("rendered", "") or ""
        description = self.clean_text(html.unescape(re.sub(r"<[^>]+>", " ", content_html)))

        images = []
        for mid in (p.get("property_meta") or {}).get("fave_property_images", []):
            u = media_url.get(str(mid))
            if u:
                images.append(u)
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=str(p["id"]),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=p["link"],
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

    def _parse_size(self, raw) -> float | None:
        if not raw:
            return None
        m = re.search(r"([\d]+[.,]?[\d]*)", str(raw).replace(",", "."))
        if not m:
            return None
        try:
            v = float(m.group(1))
            return v if 5 <= v <= 1_000_000 else None
        except ValueError:
            return None

    def _parse_price(self, p) -> tuple[float | None, str]:
        raw = self._meta(p, "fave_property_price")
        currency_raw = (self._meta(p, "fave_currency") or "XCG").upper()
        currency = "USD" if currency_raw == "USD" else "XCG"
        if not raw:
            return None, currency
        price = self.parse_price(str(raw))
        # sanity-ondergrens (zelfde les als PriceMatch/Curaçao Homes): een
        # ongeloofwaardig lage waarde is vermoedelijk geen echte prijs.
        if price is not None and price < 100:
            return None, currency
        return price, currency
