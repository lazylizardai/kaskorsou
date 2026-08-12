"""HD Azure Realty scraper (priority 8)
Site: https://hdazurerealty.com — WordPress + Houzez-thema, 'property' custom-post-type
WÉL geregistreerd in de WP REST API (rest_base 'properties', zelfde patroon als
Curaçao Real Estate Solution) — dus vrijwel alles rechtstreeks uit `property_meta`
(fave_property_*) en de `property_type`/`property_status`-taxonomieën te halen.
robots.txt: alleen standaard wp-admin-disallow, geen ClaudeBot/AI-crawler-block.
Gevonden via een nieuw kanaal (OSM Overpass "estate_agent"-zoekopdracht bracht
curacaobusinesspoint.com-bedrijvendirectory aan het licht, waar deze listing zijn
website meldde) nadat WebSearch als kanaal was opgedroogd.

Methode:
  1. GET /wp-json/wp/v2/properties?per_page=100 (34 posts totaal, ruim onder de 100-page
     limiet, dus één call volstaat) met `property_status`/`property_type`/`property_meta`.
  2. **Statusfilter: net als bij Curaçao Real Estate Solution/GS Real Estate kan één
     listing meerdere status-taxonomietermen tegelijk dragen** (bv. "New Listing" ÉN
     "Rented" naast elkaar — duidelijk een vergeten/niet-opgeschoonde tag). Betrouwbaarder
     dan "is er een actieve term aanwezig" is hier "bevat de term-set een van de drie
     ondubbelzinnig-inactieve termen (Sold/Rented/Under Contract)" → dan overslaan,
     ongeacht welke andere termen erbij staan. Van de 34 posts blijven zo 20 actief over.
     **Eén listing had zelfs HELEMAAL GEEN status-term** (`2-story-house-in-brakkeput-
     for-sale`, titel en prijs (575.000) wijzen overduidelijk op een actieve
     koopwoning) — de "alleen uitsluiten bij inactieve term" aanpak laat die er terecht
     in staan, in tegenstelling tot een aanpak die een actieve term zou VEREISEN.
  3. listing_type: direct uit de status-termen (46=For Rent, 47=For Sale) als een van
     beide aanwezig is; anders afgeleid uit `fave_property_price_prefix` ("Monthly" =
     huur) of titel-keywords, met "sale" als laatste fallback.
  4. property_type-taxonomie is hier, in tegenstelling tot Curaçao Real Estate Solution,
     WEL overwegend gevuld, maar bleek bij een steekproef-listing ("House at Harmonie")
     TEGENSTRIJDIGE termen te dragen (zowel Apartment als House tegelijk) — titel-keyword-
     matching gaat daarom hier VOOR de taxonomie-ID's (omgekeerde volgorde t.o.v. Curaçao
     Real Estate Solution, waar de taxonomie meestal leeg was). Titels bevatten vaak
     vetgedrukte Unicode-mathematische letters ("𝐀𝐏𝐀𝐑𝐓𝐌𝐄𝐍𝐓𝐒") — `unicodedata.normalize
     ("NFKD", ...)` vóór het matchen, anders mist een plain-ASCII regex de marketingtekst
     volledig. Pas als de titel geen duidelijk keyword bevat, terugvallen op de
     taxonomie-ID's (gemapt op specificiteit: Apartment/Condo/Studio > Lot >
     Commercial/Office/Shop > House/Villa/Multi Family/Single Family, vage "Residential"
     genegeerd), met "house" als laatste fallback.
  5. **Prijs-veldwissel-bugje (nieuwe valkuil): één listing (`for-rent-home-in-
     vredenberg`) heeft `fave_property_price` LEEG maar `fave_property_price_prefix`
     gevuld met een kale cijferstring ("6500") — duidelijk een verwisseling bij het
     invoeren.** Als price leeg is maar de prefix een kaal getal blijkt (geen "Monthly"/
     "Start from"/tekstlabel), wordt die waarde alsnog als prijs gebruikt.
  6. Valuta: `fave_currency` is meestal "XCG " (met spatie, altijd trimmen), maar 3 van de
     20 actieve listings staan in USD (native, geen omrekening) en 1 in EUR (×1,95 naar
     XCG, zelfde vaste-koers-aanpak als de andere EUR-scrapers in deze set).
  7. Coördinaten (`houzez_geolocation_lat/long`) niet blind vertrouwen — bounding-box-
     check (Wigbold/Curaçao Real Estate Solution-les): één listing had een kennelijke
     Houzez-demo-default-coördinaat ergens in Florida/Miami — buiten de box, dus genegeerd.
  8. Foto's: alleen media-attachment-ID's in `fave_property_images`, geen URL's — één
     bulk-GET naar /wp-json/wp/v2/media?include=<ids> per listing-batch (zelfde patroon
     als Curaçao Real Estate Solution).
"""
import html
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

RENT_STATUS_ID = 46
SALE_STATUS_ID = 47
INACTIVE_STATUS_IDS = {183, 184, 193}  # Sold, Rented, Under Contract

# property_type-taxonomie-ID's → interne categorie, meest-specifiek eerst
TYPE_ID_MAP = (
    ("apartment", (89, 90, 79)),   # Apartment, Condo, Studio
    ("land", (166,)),              # Lot
    ("commercial", (43, 65, 76)),  # Commercial, Office, Shop
    ("house", (168, 83, 91, 77)),  # House, Villa, Multi Family Home, Single Family Home
)

TYPE_KEYWORDS = (
    ("apartment", ("apartment", "studio", "penthouse", "condo")),
    ("commercial", ("commercial", "office", "warehouse", "retail", "boutique", "shop")),
    ("land", ("lot ", "lots ", "land ", "kavel", "terrein")),
    ("house", ("villa", "house", "home", "townhouse", "bungalow", "duplex", "woning")),
)

RENT_KEYWORDS = ("for rent", "te huur", "huur")
SALE_KEYWORDS = ("for sale", "te koop", "koop")


class HdAzureRealtyScraper(BaseScraper):
    source_name = "hd_azure_realty"
    BASE = "https://hdazurerealty.com"
    AGENT_COMPANY = "HD Azure Realty"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        try:
            posts = self._get_json(
                f"{self.BASE}/wp-json/wp/v2/properties?per_page=100"
                "&_fields=id,slug,link,title,content,property_status,property_type,property_meta"
            )
        except Exception as e:
            self.logger.error(f"Kon properties-lijst niet ophalen: {e}")
            return []

        media_ids: set[str] = set()
        for p in posts:
            for mid in (p.get("property_meta") or {}).get("fave_property_images", []):
                if mid:
                    media_ids.add(str(mid))
        media_url = self._resolve_media(media_ids)

        results = []
        for p in posts:
            status_ids = set(p.get("property_status") or [])
            if status_ids & INACTIVE_STATUS_IDS:
                continue
            try:
                l = self._build(p, status_ids, media_url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Post error ({p.get('id')}): {e}")

        self.logger.info(f"HD Azure Realty: {len(results)} actieve listings")
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
        # Vetgedrukte Unicode-mathematische letters komen vaak voor in titels
        # ("𝐀𝐏𝐀𝐑𝐓𝐌𝐄𝐍𝐓𝐒") — NFKD-normaliseren vóór keyword-matching, anders mist een
        # plain-ASCII regex de marketing-opmaak volledig.
        title_l = unicodedata.normalize("NFKD", title).lower()

        listing_type = self._listing_type(status_ids, p, title_l)
        property_type = self._property_type(p.get("property_type") or [], title_l)
        price, currency = self._parse_price(p)

        bedrooms = self.parse_int(self._meta(p, "fave_property_bedrooms") or "")
        bathrooms = self.parse_int(self._meta(p, "fave_property_bathrooms") or "")
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

    def _listing_type(self, status_ids: set, p, title_l: str) -> str:
        if RENT_STATUS_ID in status_ids:
            return "rent"
        if SALE_STATUS_ID in status_ids:
            return "sale"
        prefix = (self._meta(p, "fave_property_price_prefix") or "").lower()
        if "month" in prefix or "week" in prefix or "huur" in prefix:
            return "rent"
        if any(k in title_l for k in RENT_KEYWORDS):
            return "rent"
        if any(k in title_l for k in SALE_KEYWORDS):
            return "sale"
        return "sale"

    def _property_type(self, type_ids: list, title_l: str) -> str:
        # Titel eerst: de property_type-taxonomie draagt op deze site soms
        # TEGENSTRIJDIGE termen tegelijk (bv. zowel Apartment als House op
        # dezelfde listing terwijl de titel duidelijk "House at Harmonie"
        # zegt) — de titel is dan de betrouwbaardere bron. Pas als de titel
        # geen duidelijk keyword bevat, terugvallen op de taxonomie-ID's.
        for ptype, words in TYPE_KEYWORDS:
            if any(w in title_l for w in words):
                return ptype
        type_ids_set = set(type_ids)
        for ptype, ids in TYPE_ID_MAP:
            if type_ids_set & set(ids):
                return ptype
        return "house"

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
        currency_raw = (self._meta(p, "fave_currency") or "XCG").strip().upper()
        raw = self._meta(p, "fave_property_price")
        prefix_raw = self._meta(p, "fave_property_price_prefix")

        if not raw and prefix_raw:
            # Veldwissel-bugje (fave_property_price leeg, prefix bevat een kaal getal
            # i.p.v. een tekstlabel als "Monthly"/"Start from") — dan alsnog gebruiken.
            if re.fullmatch(r"[\d.,]+", prefix_raw.strip()):
                raw = prefix_raw

        if not raw:
            return None, self._normalize_currency(currency_raw)

        price = self.parse_price(str(raw))
        if price is not None and price < 100:
            return None, self._normalize_currency(currency_raw)

        if currency_raw == "EUR" and price is not None:
            price = round(price * 1.95, 2)
            return price, "XCG"

        return price, self._normalize_currency(currency_raw)

    def _normalize_currency(self, currency_raw: str) -> str:
        return "USD" if currency_raw == "USD" else "XCG"
