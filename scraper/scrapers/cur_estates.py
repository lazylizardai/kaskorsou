"""Cur-Estates scraper (priority 8)
Site: https://www.cur-estates.com — géén WordPress/Squarespace/Houzez, maar een
custom Next.js (Vercel) app die de listing-data rechtstreeks client-side uit
een EIGEN Supabase-project trekt (niet het KasKorsou-Supabase-project — een
los, eigen backend van deze makelaar).

robots.txt: bestaat niet op dit domein (`/robots.txt` geeft een kale 404 —
geen bestand, geen blokkade). De `/properties`-pagina zelf levert vrijwel
lege server-HTML (Next.js App Router, alle content client-gerenderd na een
losse data-fetch) — dus geen HTML om te parsen.

Methode:
  1. De publieke JS-bundle (`/_next/static/chunks/*.js`) bevat een hardcoded
     Supabase-project-URL + ANON-key (bedoeld om vanuit de browser te worden
     gebruikt — standaard Supabase-praktijk met Row Level Security, geen
     credential-lek). Rechtstreeks een GET op
     `{SUPABASE_URL}/rest/v1/properties` met die anon-key levert de volledige
     tabel als JSON — geen HTML-parsing nodig, rijkere data dan de meeste
     andere scrapers in deze set (aparte `beds`/`baths`/`area_size`/`lat`/
     `lng`/`slug`/`availability_status`-kolommen).
  2. **Achtste status-signaal-variant in deze scraper-set: hier bestaat een
     schoon `availability_status`-veld** (`available`/`under_contract`/
     `rented`) — geen tekstsignaal nodig, gewoon filteren op
     `availability_status == "available"` (14 van de 17 rijen op het moment
     van bouwen; 2× `under_contract`, 1× `rented`).
  3. `price` is een STRING met een inconsistent scheidingsteken: soms
     Amerikaans (komma als duizendtal-scheiding, "892,500"), soms Europees
     (punt als duizendtal-scheiding, "950.000"), soms zonder scheiding
     ("375000") — nooit decimalen. `self.parse_price()` (die alle "."/","
     hoe dan ook wegstript) werkt hier toevallig al correct voor alle drie
     de varianten, geen aparte parser nodig.
  4. `beds` is al een integer, `baths` een cijferstring (kan in theorie een
     halve badkamer zijn, nergens gezien in de steekproef maar voor de
     zekerheid afgerond net als bij andere scrapers). `area_size` is een kale
     cijferstring in m² (geen eenheid in de tekst, zelfde patroon als
     Curaçao Real Estate Solution se `fave_property_size`).
  5. `property_type` staat op 4 van de 17 rijen op `null` — title-keyword-
     fallback (villa/apartment/land-hints), default "house".
  6. Coördinaten (`lat`/`lng`) staan al als losse float-kolommen — gewoon de
     Curaçao-bounding-box-check erop, geen regex-extractie nodig.
  7. Geen aparte detailpagina-fetch nodig — `slug` uit de API-rij bouwt de
     canonieke `/properties/<slug>`-URL zelf op.
"""
from ..base_scraper import BaseScraper
from ..models import Listing

SUPABASE_URL = "https://jvteswzwfnzqzlhykqxh.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2dGVzd3p3Zm56cXpsaHlrcXhoIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODEwNjA1OTMsImV4cCI6MjA5NjYzNjU5M30."
    "i24QRs9nsWVoGZpr4AaKZECdckGBS6zW4WGhzR6mXqc"
)

APARTMENT_HINTS = ("apartment", "appartement", "penthouse", "studio", "condo")
LAND_HINTS = ("kavel", "land", "lot", "terrein", "plot")


class CurEstatesScraper(BaseScraper):
    source_name = "cur_estates"
    BASE = "https://www.cur-estates.com"
    AGENT_COMPANY = "Cur-Estates"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(
                f"{SUPABASE_URL}/rest/v1/properties?select=*",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                },
                timeout=30,
            )
            r.raise_for_status()
            rows = r.json()
        except Exception as e:
            self.logger.error(f"Kon properties-tabel niet ophalen: {e}")
            return []

        results = []
        for row in rows:
            if row.get("availability_status") != "available":
                continue
            try:
                l = self._build(row)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Rij-error ({row.get('id')}): {e}")

        self.logger.info(f"Cur-Estates: {len(results)} actieve listings")
        return results

    def _build(self, row: dict) -> Listing | None:
        title = self.clean_text(row.get("title")) or "Woning Curaçao"

        status_raw = (row.get("status") or "").lower()
        listing_type = "rent" if "rent" in status_raw else "sale"

        price = self.parse_price(str(row.get("price") or ""))
        currency_raw = (row.get("currency") or "XCG").upper()
        currency = "USD" if currency_raw == "USD" else "XCG"

        bedrooms = row.get("beds")
        if isinstance(bedrooms, str):
            bedrooms = self.parse_int(bedrooms)

        bathrooms = None
        baths_raw = row.get("baths")
        if baths_raw not in (None, ""):
            try:
                bathrooms = round(float(str(baths_raw).replace(",", ".")))
            except ValueError:
                bathrooms = None

        area_sqm = None
        size_raw = row.get("area_size")
        if size_raw not in (None, ""):
            try:
                area_sqm = float(str(size_raw).replace(",", "."))
            except ValueError:
                area_sqm = None

        latitude = longitude = None
        lat_raw, lng_raw = row.get("lat"), row.get("lng")
        if lat_raw is not None and lng_raw is not None:
            try:
                lat, lng = float(lat_raw), float(lng_raw)
                if 11.9 <= lat <= 12.5 and -69.3 <= lng <= -68.5:
                    latitude, longitude = lat, lng
            except (TypeError, ValueError):
                pass

        area_id = row.get("area_id")
        neighborhood = area_id.replace("-", " ").title() if area_id else None

        description = self.clean_text(row.get("description"))

        images = self.clean_images(row.get("image_urls") or [])
        if not images and row.get("image_url"):
            images = self.clean_images([row["image_url"]])

        haystack = f"{title.lower()} {(row.get('property_type') or '').lower()}"
        raw_ptype = (row.get("property_type") or "").lower()
        if raw_ptype == "land" or any(h in haystack for h in LAND_HINTS):
            property_type = "land"
        elif raw_ptype == "apartment" or any(h in haystack for h in APARTMENT_HINTS):
            property_type = "apartment"
        elif raw_ptype in ("villa", "house"):
            property_type = "house"
        else:
            property_type = "house"

        slug = row.get("slug") or row.get("id")

        return Listing(
            source_id=self.source_id,
            external_id=str(row.get("id")),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=f"{self.BASE}/properties/{slug}",
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
