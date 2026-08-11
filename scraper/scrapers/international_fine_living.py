"""International Fine Living scraper (priority 8)
Site: https://www.internationalfineliving.com — SvelteKit-frontend (Vercel),
data komt van een gedeeld makelaars-CMS/API op https://cpl01.ogonline.nl
(vermoedelijk gebruikt door meerdere Curaçao-makelaars — waard om te checken
bij toekomstige scrapers uit de lijst). Geen WordPress, geen GH Actions-
IP-blokkade-risico (Vercel + los API-domein, robots.txt: alles toegestaan).

Methode:
  1. JSON API rechtstreeks: GET https://cpl01.ogonline.nl/api/listings
     met where[account][equals]=<account-id>&where[isPublished][equals]=true
     &where[status][equals]=available, gepagineerd (limit=50).
     Account-id voor International Fine Living: 677e470ccbe508bb8de38ce7
     (gevonden via een losse listing-detailpagina, __NEXT_DATA__/fetch-calls
     in de HTML wezen naar deze API).
  2. depth=1 geeft prijs, adres, consumer/commercial-details, description,
     photos — alles in 1 call, geen aparte detailpagina nodig.
  3. Detail-URL: de site routeert alleen op het laatste pad-segment (id) —
     categorie/wijk/straat-slugs in de URL zijn puur cosmetisch (getest:
     een fake slug met de juiste id geeft gewoon HTTP 200). Dus altijd
     `/nl/aanbod/listing/curacao/listing/listing/<id>` als canonieke URL.
  4. Foto's: elk photos[].upload.original is een relatief pad op
     media02.ogonline.nl dat de originele foto direct teruggeeft.
  5. Valuta: site toont EUR (settings.currency == "EUR" bij alle listings
     tot nu toe) — omgerekend naar XCG met dezelfde koers als remax.py/
     century21.py (EUR × 1.95).
"""
from ..base_scraper import BaseScraper
from ..models import Listing

API_BASE = "https://cpl01.ogonline.nl/api/listings"
ACCOUNT_ID = "677e470ccbe508bb8de38ce7"
MEDIA_BASE = "https://media02.ogonline.nl"
EUR_TO_XCG = 1.95
PAGE_SIZE = 50


class InternationalFineLivingScraper(BaseScraper):
    source_name = "international_fine_living"
    AGENT_COMPANY = "International Fine Living"

    def _get_json(self, params: dict):
        r = self.session.get(API_BASE, params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        docs = []
        page = 1
        while True:
            params = {
                "page": page,
                "limit": PAGE_SIZE,
                "depth": 1,
                "locale": "nl",
                "sort": "-createdAt",
                "where[isPublished][equals]": "true",
                "where[account][equals]": ACCOUNT_ID,
                "where[status][equals]": "available",
            }
            try:
                data = self._get_json(params)
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon listings niet ophalen: {e}")
                    return []
                break
            batch = data.get("docs") or []
            docs.extend(batch)
            if page >= (data.get("totalPages") or 1):
                break
            page += 1

        self.logger.info(f"International Fine Living: {len(docs)} actieve listings")

        results = []
        for d in docs:
            try:
                l = self._build(d)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({d.get('id')}): {e}")
        return results

    def _build(self, d: dict) -> Listing | None:
        listing_id = d.get("id")
        if not listing_id:
            return None

        address = d.get("address") or {}
        street = self.clean_text(address.get("street"))
        house_number = address.get("houseNumber")
        title = self.clean_text(
            f"{street} {house_number}".strip() if street else None
        ) or self.clean_text(d.get("title")) or "Woning Curaçao"

        is_rentals = bool(d.get("isRentals"))
        listing_type = "rent" if is_rentals else "sale"

        property_type = "house"
        consumer = d.get("consumer") or {}
        commercial = d.get("commercial") or {}
        if d.get("market") == "commercial":
            property_type = "commercial"
        elif consumer.get("isApartment"):
            property_type = "apartment"
        elif consumer.get("isBuildLot"):
            property_type = "land"
        elif consumer.get("isHouse"):
            house = consumer.get("house") or {}
            main_type = ((house.get("mainType") or {}).get("title") or "").lower()
            if "appartement" in main_type or "penthouse" in main_type or "studio" in main_type:
                property_type = "apartment"
            else:
                property_type = "house"

        price_eur = None
        if is_rentals:
            price_eur = (d.get("rentalsPrice") or {}).get("amount")
        else:
            price_eur = (d.get("salesPrice") or {}).get("amount")
        price = round(price_eur * EUR_TO_XCG, 2) if price_eur else None

        details = consumer.get("details") or {}
        bedrooms = details.get("bedrooms")
        bathrooms = details.get("bathrooms")
        area_sqm = details.get("livingSurface") or details.get("plotSurface")

        desc = (d.get("description") or {}).get("full")
        description = self.clean_text(desc)

        neighborhood = self.clean_text(address.get("settlementLevel1"))

        loc = d.get("location") or [None, None]
        longitude, latitude = (loc + [None, None])[:2]
        # Bron heeft af en toe een verkeerde geocode (bv. "San Sebastiaan" ->
        # San Sebastián, Spanje i.p.v. de wijk op Curaçao) — buiten het eiland
        # laten we de coördinaten leeg i.p.v. een pin in Europa te tonen.
        if latitude is not None and longitude is not None:
            if not (11.9 <= latitude <= 12.5 and -69.3 <= longitude <= -68.5):
                self.logger.warning(
                    f"Coördinaten buiten Curaçao voor {listing_id}: {latitude},{longitude} — genegeerd"
                )
                latitude = longitude = None

        images = []
        for p in (d.get("photos") or []):
            original = ((p.get("upload") or {}).get("original"))
            if original:
                images.append(f"{MEDIA_BASE}{original}")
        images = self.clean_images(images)

        url = f"https://www.internationalfineliving.com/nl/aanbod/listing/curacao/listing/listing/{listing_id}"

        return Listing(
            source_id=self.source_id,
            external_id=str(listing_id),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency="XCG",
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
