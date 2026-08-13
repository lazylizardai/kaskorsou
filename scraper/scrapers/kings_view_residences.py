"""Kings View Residences scraper (priority 6)
Site: https://kingsviewresidences.com — Laravel/nginx (XSRF-TOKEN + eigen
sessioncookie, geen WordPress). ÉÉN nieuwbouw-appartementencomplex bij Mambo
Beach (Dr. Martin Luther King Boulevard 117, Willemstad, "Mambo, tegenover
Marie Pampoen") — projectontwikkelaar met een eigen doorlopend te-koop-aanbod
(geen "0 huidige inventory"-geval zoals Halabi, zelfde categorie als Mambo
Developers/HD Azure Realty: developer met echte actieve eenheden).

Gevonden via een nieuw kanaal: het exposanten-overzicht van de Nederlandse
"Second Home Beurs" (secondhome.nl/exposanten-land/curacao/), gefilterd op
Curaçao — een vakantiewoning-beurs-portal met een doorzoekbare exposantenlijst
(niet eerder als kanaal gebruikt; caribbeanhousehunt.com/24 andere kanalen
waren al uitgeput). Leverde naast dit ook een aantal AFGEWEZEN kandidaten op:
Azariah Real Estate and Services (azariahrealestate.com — 503 upstream
connect/timeout, dood domein), en een aantal niet-makelaars (ENNIA-verzekering,
Hanzepay-betaaldienst, Mogelijk-hypotheekadvies, Dormio Investments-resort-
investeerder) — die horen niet in de makelaarslijst thuis.

**Belangrijke bijzonderheid: de volledige eenheden-inventaris (alle 64 units,
incl. prijs/status/oppervlakte/slaapkamers/foto's) staat als één grote JSON-
array in een Vue-component-attribuut (`:units='[...]'`) op de
/aankopen-pagina zelf** — geen aparte detail-requests per unit nodig, geen
WP-REST, geen sitemap-crawl. Dit is dus een scraper met precies ÉÉN HTTP-
request.

Methode:
  1. GET `/aankopen`, regex/string-search naar `:units='[...]'` (het attribuut
     bevat pure JSON, dubbele aanhalingstekens, dus veilig met `json.loads`
     te parsen zodra het attribuut zelf — dat met single quotes is
     omsloten — eruit geknipt is).
  2. `status`-veld per unit: "available" | "in_option" | "sold". Zelfde
     conventie als Burbach Roycroft (SOLD_STATUS_WORDS): alleen "available"
     telt als actief-te-koop; "in_option" (onder optie/gereserveerd) en
     "sold" worden overgeslagen.
  3. Prijs: `price`-object bevat het bedrag al native in EUR/USD/XCG (door de
     bron zelf omgerekend, niet noodzakelijk tegen de project-vaste koersen
     1 EUR=1,95 XCG / 1 USD=1,79 XCG). We nemen de XCG-waarde RECHTSTREEKS
     over (zelfde conventie als Cur-Estates: "currency-kolom rechtstreeks"),
     geen eigen herberekening.
  4. Titel: `display_name` ("Appartement A0 - 01"), met projectnaam ervoor.
  5. Oppervlakte: `sum_area` (bevat balkon/bvo, al numeriek — geen tekst-
     parsing nodig).
  6. Slaap-/badkamers: `bedrooms`/`bathrooms`, al numeriek in de JSON.
  7. Beschrijving: `type_indication_description` + `location_description` +
     `unique_selling_points` (bullet-tekst met `\n`-scheiding) samengevoegd.
  8. Foto's: `images`-array, al volledige Backblaze-B2-URL's — rechtstreeks
     door `clean_images()`.
  9. Geen aparte per-unit-URL gevonden (Vue-modal, geen route-wijziging) —
     alle listings verwijzen naar de hoofdpagina met een `#unit-<id>`-fragment
     voor uniciteit, `external_id` = de numerieke unit-`id`.
 10. robots.txt: `Disallow:` leeg, geen crawl-delay — standaard REQUEST_DELAY
     aanhouden (al is het hier maar 1 request per scrape-run).
"""
import json
import re
from ..base_scraper import BaseScraper
from ..models import Listing

AANKOPEN_URL = "https://kingsviewresidences.com/aankopen"
PROJECT_NAME = "Kings View Residences"
ACTIVE_STATUS = "available"


class KingsViewResidencesScraper(BaseScraper):
    source_name = "kings_view_residences"
    AGENT_COMPANY = "Kings View Residences"

    def scrape(self) -> list[Listing]:
        soup = self.get(AANKOPEN_URL)
        if soup is None:
            return []
        html = str(soup)

        marker = ":units='["
        start = html.find(marker)
        if start == -1:
            self.logger.error("Kings View Residences: :units-attribuut niet gevonden")
            return []
        start += len(":units='")
        end = html.find("'>", start)
        if end == -1:
            self.logger.error("Kings View Residences: einde van :units-attribuut niet gevonden")
            return []
        raw = html[start:end]

        try:
            units = json.loads(raw)
        except json.JSONDecodeError as e:
            self.logger.error(f"Kings View Residences: JSON-parse-fout: {e}")
            return []

        results: list[Listing] = []
        for u in units:
            try:
                l = self._parse_unit(u)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Unit-parse-fout (id={u.get('id')}): {e}")

        self.logger.info(
            f"Kings View Residences: {len(results)} actieve units van {len(units)} totaal"
        )
        return results

    def _parse_unit(self, u: dict) -> Listing | None:
        if u.get("status") != ACTIVE_STATUS:
            return None

        unit_id = u.get("id")
        if unit_id is None:
            return None

        display_name = self.clean_text(u.get("display_name")) or f"Unit {u.get('unit', unit_id)}"
        title = f"{PROJECT_NAME} – {display_name}"

        price_obj = u.get("price") or {}
        price = None
        currency = "XCG"
        xcg_raw = price_obj.get("XCG")
        if xcg_raw:
            try:
                price = round(float(xcg_raw), 2)
            except (TypeError, ValueError):
                price = None

        area_sqm = None
        sum_area = u.get("sum_area")
        if sum_area is not None:
            try:
                area_sqm = float(sum_area)
            except (TypeError, ValueError):
                area_sqm = None

        bedrooms = u.get("bedrooms")
        bathrooms = u.get("bathrooms")
        try:
            bedrooms = int(bedrooms) if bedrooms is not None else None
        except (TypeError, ValueError):
            bedrooms = None
        try:
            bathrooms = round(float(bathrooms)) if bathrooms is not None else None
        except (TypeError, ValueError):
            bathrooms = None

        desc_parts = []
        if u.get("type_indication_description"):
            desc_parts.append(u["type_indication_description"])
        if u.get("location_description"):
            desc_parts.append(u["location_description"])
        usp = u.get("unique_selling_points")
        if usp:
            desc_parts.append(re.sub(r"\n+", ". ", usp))
        description = self.clean_text(" — ".join(desc_parts)) if desc_parts else None

        images = self.clean_images(u.get("images") or [])

        return Listing(
            source_id=self.source_id,
            external_id=f"unit-{unit_id}",
            title=title,
            listing_type="sale",
            property_type="apartment",
            price_ang=price,
            currency=currency,
            url=f"{AANKOPEN_URL}#unit-{unit_id}",
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood="Mambo (Willemstad)",
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
