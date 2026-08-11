"""Landmark Real Estate scraper (priority 8)
Site: https://www.landmark.cw — draait op hetzelfde gedeelde "OG Online"
makelaars-platform als International Fine Living/Palmstone, maar op een
DERDE, oudere jQuery/server-rendered variant (geen React/SvelteKit, geen
cpl01/cdn.ogonline.nl-API). Gewone Apache-hosting achter Cloudflare, geen
blokkade-signalen, robots.txt staat alles toe (alleen `/cms/` disallowed).

Methode:
  1. De site laadt zijn listings client-side via een simpele JSON-endpoint:
     GET https://www.landmark.cw/nl/realtime-listings/consumer
     (gevonden via het `data-url`-attribuut van de `realtime-listings`-
     widget) — geeft in 1 call ALLE listings (incl. verkocht/gearchiveerd)
     met adres, stad, land, prijs (NAf/USD/EUR als kant-en-klare HTML-
     string), slaapkamers, badkamers, oppervlaktes, coördinaten (gewone
     lat/lng-volgorde) en status.
  2. **Status filteren is verplicht**: van de ~90 listings in de consumer-
     feed is het gros (`statusOrig == "sold"`) allang verkocht — de feed
     bevat de volledige portfolio-historie. Alleen `available`/`under_bid`
     meenemen.
  3. Prijs: de `price`-HTML-string bevat per rij een valuta-prefix
     (NAf/NAƒ/USD/EUR) + bedrag + suffix (`k.k.` voor koop, `p.m.` voor
     huur) — zelf geparsed i.p.v. het kant-en-klare `salesPrice`-veld
     vertrouwd, want dat veld bevat soms het EUR-bedrag ongeconverteerd
     (bv. "The Ritz building C 2": NAf 313.369 / EUR 152.500, salesPrice
     staat op 152500 — dat zou als XCG worden gelezen als je het veld
     blind gebruikt). Voorkeursvolgorde: USD (native) > EUR (×1.95 naar
     XCG) > NAf (al XCG, 1:1).
  4. Voor description + volledige fotogalerij is een detailpagina-crawl
     nodig (de consumer-feed geeft alleen 1 cover-foto): omschrijving uit
     `.expand-content-content` (na de "Omschrijving"-kop), foto's uit
     `img.slide-photo` (volledige resolutie, geen taal-vlaggetjes).
  5. property_type: meestal een bruikbare Nederlandse `type`-string
     ("Vrijstaande woning", "Bouwgrond", "Split-level woning", ...). Voor
     de zeldzame gevallen waar `type` ontbreekt (`false`) een minimale
     heuristiek: wel slaapkamers → appartement, geen slaapkamers/alleen
     kaveloppervlak → land (geen giswerk verder dan dat).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.landmark.cw"
CONSUMER_URL = f"{BASE}/nl/realtime-listings/consumer"
EUR_TO_XCG = 1.95

ACTIVE_STATUSES = {"available", "under_bid"}

PRICE_ROW_RE = re.compile(r"(NA\S{0,2}|USD|EUR|XCG)\s+([\d.,]+)", re.I)


class LandmarkScraper(BaseScraper):
    source_name = "landmark"
    AGENT_COMPANY = "Landmark Real Estate"

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

        self.logger.info(f"Landmark: {len(items)} listings in de feed (incl. verkocht/gearchiveerd)")

        active = [
            it for it in items
            if (it.get("statusOrig") or "").lower() in ACTIVE_STATUSES
        ]
        self.logger.info(f"Landmark: {len(active)} actieve listings na statusfilter")

        results = []
        for item in active:
            try:
                l = self._scrape_detail(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({item.get('url')}): {e}")
        return results

    def _parse_price_rows(self, price_html: str | None, want_rent: bool):
        candidates: dict[str, float] = {}
        if not price_html:
            return candidates
        rows = price_html.replace("&nbsp;", " ").split("<br>")
        for row in rows:
            is_rent_row = "p.m." in row
            if is_rent_row != want_rent:
                continue
            m = PRICE_ROW_RE.search(row)
            if not m:
                continue
            cur_raw = m.group(1).upper()
            amount = self.parse_price(m.group(2))
            if not amount:
                continue
            if cur_raw.startswith("NA") or cur_raw == "XCG":
                candidates["XCG"] = amount
            elif cur_raw == "USD":
                candidates["USD"] = amount
            elif cur_raw == "EUR":
                candidates["EUR"] = amount
        return candidates

    def _resolve_price(self, price_html: str | None, want_rent: bool):
        candidates = self._parse_price_rows(price_html, want_rent)
        if "USD" in candidates:
            return candidates["USD"], "USD"
        if "EUR" in candidates:
            return round(candidates["EUR"] * EUR_TO_XCG, 2), "XCG"
        if "XCG" in candidates:
            return candidates["XCG"], "XCG"
        return None, "XCG"

    def _property_type(self, type_text, bedrooms) -> str:
        if type_text:
            tl = type_text.lower()
            if "bouwgrond" in tl or "kavel" in tl or "perceel" in tl:
                return "land"
            if "appartement" in tl or "penthouse" in tl or "studio" in tl or "condo" in tl:
                return "apartment"
            if "commerc" in tl or "bedrijf" in tl or "kantoor" in tl:
                return "commercial"
            return "house"
        # Geen type-tekst beschikbaar — minimale heuristiek.
        if bedrooms:
            return "apartment"
        return "land"

    def _scrape_detail(self, item: dict) -> Listing | None:
        rel_url = item.get("url")
        if not rel_url:
            return None
        url = BASE + rel_url

        is_sales = bool(item.get("isSales"))
        is_rentals = bool(item.get("isRentals"))
        if is_sales:
            listing_type = "sale"
            price, currency = self._resolve_price(item.get("price"), want_rent=False)
        elif is_rentals:
            listing_type = "rent"
            price, currency = self._resolve_price(item.get("price"), want_rent=True)
        else:
            return None

        title = self.clean_text(item.get("address")) or "Woning Curaçao"
        bedrooms = item.get("bedrooms") or None
        bathrooms = item.get("bathrooms") or None
        area_sqm = item.get("livingSurface") or item.get("plotSurface") or None
        neighborhood = self.clean_text(item.get("city"))

        property_type = self._property_type(item.get("type"), bedrooms)

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
            for img in soup.find_all("img", class_="slide-photo"):
                src = img.get("src")
                if src:
                    images.append(src)
        images = self.clean_images(images)

        # Ontbrekende hex-ObjectId uit de URL als stabiele external_id.
        external_id = rel_url.rstrip("/").split("/")[-1]

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
