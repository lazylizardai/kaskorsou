"""Blue Bay Hills Residences scraper (priority 6)
Site: https://www.bluebayhillsresidences.com — WordPress, zelf-gehost
(nginx/Plesk, GEEN WordPress.com/WPCloud) — dus geen GitHub Actions-IP-
blokkaderisico zoals bij New Winds Realty. ÉÉN nieuwbouw-appartementen-
complex in Blue Bay (Sint Michiel-omgeving) — 24 luxe villa-appartementen
(incl. 6 penthouses) verdeeld over 6 gebouwen, 5 woningtypen (Tiffany,
Celeste, Azure, Sapphire + varianten). Zelfde categorie als Kings View
Residences/Mambo Developers/HD Azure Realty: projectontwikkelaar met een
eigen doorlopende te-koop-inventaris (geen "0 huidige inventory"-geval
zoals Halabi).

Gevonden via WebSearch op "nieuwbouw appartementen Curaçao 2026" (nieuw
zoekresultaat, niet eerder gezien). Het project wordt commercieel bemiddeld
door Curacao Sotheby's International Realty (zie /nl/makelaar/-pagina) —
Sotheby's Realty Curaçao zelf staat al langer geblokkeerd wegens AWS WAF,
maar dit is een APART domein (eigen zelf-gehoste WordPress-site van de
ontwikkelaar/het project, geen AWS WAF) met eigen structurele data — dus
wél scrapebaar, ondanks dat de hoofdmakelaar geblokkeerd blijft.

**Bijzonderheid: de volledige eenheden-inventaris (alle 24 units, incl.
prijs/status/oppervlakte/slaapkamers/badkamers/terras/tuin) staat al
kant-en-klaar als losse `<div class="lot-selector-popup">`-blokken in de
ruwe server-side gerenderde HTML van de /nl/appartementen/-pagina** — geen
JS-executie nodig (getest met zowel gewone Chrome-UA als Googlebot-UA,
identieke content — de data zit gewoon standaard in de HTML, niet achter
een aparte AJAX-call). Simpele BeautifulSoup-parse, geen sitemap-crawl.

Methode:
  1. GET `/nl/appartementen/`, selecteer alle `div.lot-selector-popup`.
  2. Status via de CSS-class op de div zelf (`available`/`reserved`/`sold`,
     bevestigd door het los ernaast staande "Status:"-label-veld in
     `div.lot-detail` — beide bronnen consistent bij alle 24 units getest).
     Alleen `available` telt als actief. `reserved` ("Verkocht onder
     voorbehoud", 1 unit) en `sold` (14 units) worden overgeslagen.
  3. `data-id`-attribuut op de popup-div = uniek per unit (1 t/m 24, geen
     duplicaten) → `external_id`.
  4. Label/waarde-structuur (`div.lot-detail` met `.lot-detail-label` +
     `.lot-detail-value`) voor: Bruto woonoppervlakte (m², → area_sqm),
     Slaapkamers (→ bedrooms), Badkamers (→ bathrooms), Terras/Tuin (alleen
     in beschrijving, geen apart Listing-veld), Koopsom (→ price), Status.
     ALTIJD als dict per label geparsed (niet platte tekst), zelfde
     conventie als Burbach Roycroft/GS Real Estate.
  5. Prijs: "Koopsom"-veld, bv. "$ 829.000" — Nederlandstalige pagina, dus
     punt = duizendtal-scheidingsteken (geen Amerikaans decimaalformaat
     zoals bij Mambo Developers) — de standaard `self.parse_price()` werkt
     hier prima. Altijd USD (geen EUR/XCG-symbool gezien op deze pagina),
     geen omrekening nodig richting `price_ang`/`currency="USD"`. Bij
     ontbrekend Koopsom-veld (kan voorkomen, niet elke listing toont een
     prijs) → geen prijs, listing blijft verder gewoon actief.
  6. Titel: woningtype-naam (Tiffany/Celeste/Azure/Sapphire, uit `<h3>` in
     de popup) + uniek unit-id, want meerdere units delen dezelfde
     typenaam (bv. 7x "Tiffany").
  7. Property-type: altijd "apartment" (villa-appartementen/penthouses,
     zelfde conventie als Kings View Residences voor het hele complex).
  8. Geen individuele foto's per unit gevonden op de pagina (alleen een
     kale "typo"-tekstafbeelding per woningtype, geen echte fotoos) — image
     blijft bewust leeg i.p.v. generieke projectfoto's per unit toe te
     kennen die het echte uiterlijk van de specifieke unit niet
     representeren.
  9. Geen aparte per-unit-URL (JS-modal/lot-selector, geen route-wijziging)
     — `url` = hoofdpagina + `#lot-<id>`-fragment, zelfde conventie als
     Kings View Residences (`#unit-<id>`).
 10. Coördinaten: niet op de pagina gevonden, latitude/longitude blijven
     None. Neighborhood = "Blue Bay" (bevestigde bestaande waarde in
     `kas_listings`, geen nieuwe variant).
 11. robots.txt: alleen `/wp-admin/` disallowed (met expliciete
     `admin-ajax.php`-uitzondering), geen crawl-delay, geen ClaudeBot-
     vermelding — standaard REQUEST_DELAY aanhouden.
"""
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..models import Listing

APARTEMENTEN_URL = "https://www.bluebayhillsresidences.com/nl/appartementen/"
PROJECT_NAME = "Blue Bay Hills Residences"


class BlueBayHillsResidencesScraper(BaseScraper):
    source_name = "blue_bay_hills_residences"
    AGENT_COMPANY = "Blue Bay Hills Residences"

    def scrape(self) -> list[Listing]:
        soup = self.get(APARTEMENTEN_URL)
        if soup is None:
            return []

        popups = soup.select("div.lot-selector-popup")
        if not popups:
            self.logger.error("Blue Bay Hills Residences: geen lot-selector-popup-blokken gevonden")
            return []

        results: list[Listing] = []
        for p in popups:
            try:
                l = self._parse_lot(p)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Lot-parse-fout (data-id={p.get('data-id')}): {e}")

        self.logger.info(
            f"Blue Bay Hills Residences: {len(results)} actieve units van {len(popups)} totaal"
        )
        return results

    def _parse_lot(self, p: BeautifulSoup) -> Listing | None:
        classes = p.get("class", [])
        if "available" not in classes:
            return None

        lot_id = p.get("data-id")
        if not lot_id:
            return None

        title_el = p.select_one("h3")
        type_name = self.clean_text(title_el.get_text()) if title_el else "Appartement"

        details: dict[str, str] = {}
        for d in p.select("div.lot-detail"):
            label_el = d.select_one(".lot-detail-label")
            value_el = d.select_one(".lot-detail-value")
            if label_el and value_el:
                label = self.clean_text(label_el.get_text()) or ""
                value = self.clean_text(value_el.get_text(" ")) or ""
                details[label.rstrip(":")] = value

        # Dubbele check: het losse "Status"-label moet ook "Beschikbaar" zijn.
        status_label = details.get("Status", "").lower()
        if status_label and "beschikbaar" not in status_label:
            return None

        area_sqm = self.parse_area(details.get("Bruto woonoppervlakte"))
        bedrooms = self.parse_int(details.get("Slaapkamers"))
        bathrooms = self.parse_int(details.get("Badkamers"))

        price = None
        koopsom = details.get("Koopsom")
        if koopsom:
            price = self.parse_price(koopsom)

        desc_parts = [f"{type_name}-appartement in Blue Bay Hills Residences."]
        terras = details.get("Terras")
        tuin = details.get("Tuin")
        if terras:
            desc_parts.append(f"Terras: {terras}.")
        if tuin:
            desc_parts.append(f"Tuin: {tuin}.")
        description = self.clean_text(" ".join(desc_parts))

        return Listing(
            source_id=self.source_id,
            external_id=f"lot-{lot_id}",
            title=f"{PROJECT_NAME} – {type_name} (unit {lot_id})",
            listing_type="sale",
            property_type="apartment",
            price_ang=price,
            currency="USD",
            url=f"{APARTEMENTEN_URL}#lot-{lot_id}",
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood="Blue Bay",
            latitude=None,
            longitude=None,
            images=[],
            agent_company=self.AGENT_COMPANY,
        )
