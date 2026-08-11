"""Wigbold Real Estate scraper (priority 8)
Site: https://www.wigboldrealestate.com — DERDE variant van het gedeelde "OG
Online" makelaars-platform (zelfde jQuery/server-rendered stack als
landmark.py, niet de SvelteKit/cpl01-API-variant van international_fine_living
/palmstone). Account-id `63f87fe467f9a1e5cca36cb1` (te zien in elke
media02.ogonline.nl-upload-URL). robots.txt permissief (alleen `/ogtv`,
`/ogweb`, `/ogprint`, `/nl(en)/brochure` disallowed — geen ClaudeBot-vermelding).

Methode:
  1. Net als Landmark: de site laadt zijn listings client-side via een simpele
     JSON-endpoint zonder auth nodig:
     GET https://www.wigboldrealestate.com/en/realtime-listings/consumer
     — geeft in 1 call ALLE listings (incl. verkocht/onder-optie) met adres,
     stad, land, prijs (kant-en-klare display-string), slaapkamers,
     badkamers, oppervlaktes, coördinaten (gewone lat/lng-volgorde), status.
  2. **Status filteren is verplicht** — de feed bevat ook `sold`/`sold_ur`/
     `under_option`. Alleen `available`/`under_bid` meenemen (zelfde
     conventie als Landmark).
  3. Prijs: het `price`-veld is OFWEL een kant-en-klare display-string met
     valuta ("1.500.000 ANG", "€ 425.000") OFWEL de letterlijke tekst
     "On request". **Val NIET terug op het rauwe `salesPrice`-veld bij "On
     request"** — de bijbehorende JSON-LD op de detailpagina claimt altijd
     `priceCurrency: EUR` ongeacht de werkelijke valuta (hardcoded schema.org-
     boilerplate, geverifieerd niet kloppend: een ANG-listing had ook
     `priceCurrency: EUR` in de JSON-LD terwijl de zichtbare prijs ANG was).
     Bij "On request": price=None, net als Landmark bij een niet-vindbare rij.
     ANG/NAf/XCG = native XCG (oude/nieuwe naam), € = ×1,95 naar XCG, $/USD
     native USD (nog niet gezien in de praktijk, wel defensief afgevangen).
  4. Voor description + volledige fotogalerij is een detailpagina-crawl
     nodig (de consumer-feed geeft alleen 1 cover-foto): omschrijving uit
     `.expand-content-content` (zelfde als Landmark), foto's uit
     `img.swiper-lazy` — LET OP: hier is het `data-src`-attribuut, niet
     `src` (lazy-loaded gallery, anders dan Landmark's `img.slide-photo`
     met een gewoon `src`-attribuut).
  5. property_type: `mainType`-veld uit de feed (house/apartment/buildLot/
     other) — vrij schoon, met een fallback op het `type`-tekstveld
     ("Villa", "Build lot", ...) voor de "other"-gevallen.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.wigboldrealestate.com"
CONSUMER_URL = f"{BASE}/en/realtime-listings/consumer"
EUR_TO_XCG = 1.95

ACTIVE_STATUSES = {"available", "under_bid"}

PRICE_RE = re.compile(r"(ANG|NA\S{0,2}|XCG|EUR|USD|€|\$)?\s*([\d.,]{4,})\s*(ANG|EUR|USD)?", re.I)


class WigboldScraper(BaseScraper):
    source_name = "wigbold"
    AGENT_COMPANY = "Wigbold Real Estate"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        try:
            items = self._get_json(CONSUMER_URL)
        except Exception as e:
            self.logger.error(f"Kon consumer-feed niet ophalen: {e}")
            return []

        self.logger.info(f"Wigbold: {len(items)} listings in de feed (incl. verkocht/onder-optie)")

        active = [
            it for it in items
            if (it.get("statusOrig") or "").lower() in ACTIVE_STATUSES
        ]
        self.logger.info(f"Wigbold: {len(active)} actieve listings na statusfilter")

        results = []
        for item in active:
            try:
                l = self._scrape_detail(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({item.get('url')}): {e}")
        return results

    def _resolve_price(self, price_text: str | None):
        if not price_text:
            return None, "XCG"
        text = price_text.strip()
        if text.lower() in ("on request", "op aanvraag", ""):
            return None, "XCG"
        m = PRICE_RE.search(text)
        if not m:
            return None, "XCG"
        prefix = (m.group(1) or "").upper()
        suffix = (m.group(3) or "").upper()
        cur_raw = prefix or suffix
        amount = self.parse_price(m.group(2))
        if not amount:
            return None, "XCG"
        if cur_raw in ("EUR", "€"):
            return round(amount * EUR_TO_XCG, 2), "XCG"
        if cur_raw in ("USD", "$"):
            return amount, "USD"
        # ANG/NAf/XCG/geen-prefix (bv. kale duizendtal) — altijd al native XCG
        return amount, "XCG"

    def _property_type(self, main_type: str | None, type_text: str | None) -> str:
        mt = (main_type or "").lower()
        if mt == "house":
            return "house"
        if mt == "apartment":
            return "apartment"
        if mt == "buildlot":
            return "land"
        # "other" of leeg — terugvallen op het tekstveld
        tl = (type_text or "").lower()
        if "appartement" in tl or "apartment" in tl or "penthouse" in tl or "studio" in tl:
            return "apartment"
        if "bouwgrond" in tl or "build lot" in tl or "kavel" in tl or "land" in tl:
            return "land"
        if "commerc" in tl or "kantoor" in tl or "office" in tl:
            return "commercial"
        return "house"

    def _scrape_detail(self, item: dict) -> Listing | None:
        rel_url = item.get("url")
        listing_id = item.get("_id")
        if not rel_url or not listing_id:
            return None
        url = BASE + rel_url

        is_rentals = bool(item.get("isRentals"))
        listing_type = "rent" if is_rentals else "sale"

        price, currency = self._resolve_price(item.get("price"))

        title = self.clean_text(item.get("address")) or "Woning Curaçao"
        bedrooms = item.get("bedrooms") or None
        bathrooms = item.get("bathrooms") or None
        area_sqm = item.get("livingSurface") or item.get("plotSurface") or None
        neighborhood = self.clean_text(item.get("city")) or self.clean_text(item.get("district"))

        property_type = self._property_type(item.get("mainType"), item.get("type"))

        latitude = item.get("lat")
        longitude = item.get("lng")
        if latitude is not None and longitude is not None:
            if not (11.9 <= latitude <= 12.5 and -69.3 <= longitude <= -68.5):
                self.logger.warning(
                    f"Coördinaten buiten Curaçao voor {rel_url}: {latitude},{longitude} — genegeerd"
                )
                latitude = longitude = None

        description = None
        images = []
        soup = self.get(url)
        if soup is not None:
            content = soup.find(class_="expand-content-content")
            if content:
                description = self.clean_text(content.get_text(" "))
            for img in soup.find_all("img", class_="swiper-lazy"):
                src = img.get("data-src") or img.get("src")
                if src:
                    images.append(src)
        if not images:
            cover = item.get("jpg") or item.get("photo")
            if cover:
                images.append(cover)
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=str(listing_id),
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
