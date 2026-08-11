"""DMJ Makelaar scraper (priority 9 — laagste van de set, bewust)
Site: https://dmjmakelaar.com — WordPress + Elementor, GEEN eigen
property-CPT (bevestigd via `/wp-json/wp/v2/types`: alleen `post`/`page`).
Listings staan als losse hand-gebouwde WordPress-PAGINA's onder `/aanbod/`.

**Zeer lage yield, bewust toch gebouwd:** van de ~10 URL's in
`page-sitemap.xml` onder `/aanbod/` zijn er maar 3 daadwerkelijk Curaçao
(de rest is Bonaire of Spanje — DMJ is een Nederlands/Caribisch kantoor
met een breder werkgebied dan alleen Curaçao). Filter: alleen aanbod-URL's
die eindigen op `-curacao`.

Methode:
  1. robots.txt EERST gecheckt: permissief (alleen `/wp-admin/` disallow),
     geen ClaudeBot-vermelding, geen captcha-signalen. Sitemap:
     `/sitemap_index.xml` → `page-sitemap.xml` (geen aparte listings-sitemap,
     alle content zit in gewone WP-pagina's).
  2. Prijs/kenmerken zitten NIET in een JSON-LD-schema (dat veld is
     inconsistent gevuld — soms een marketingtekst, soms de structured
     samenvatting) en ook niet betrouwbaar te vinden via een generieke
     `.price`-class (bestaat niet). WEL betrouwbaar: elke listing-pagina
     heeft een Elementor "icon list"-widget met `<span
     class="elementor-icon-list-text">`-items voor prijs/slaapkamers/
     badkamers/woonoppervlak/perceeloppervlak — MAAR dezelfde class-naam
     wordt ook gebruikt in de footer-contactblokken (adres/telefoon/KvK).
     Bekende valkuil (generieke class zonder scope): dus NIET op index of
     scope vertrouwen, maar op CONTENT-patroon filteren (regex per
     kenmerk: prijs bevat een valutacode + cijfers, "N Slaapkamers",
     "N Badkamers", "N m2 Wonen", "N m2 Perceel") — werkt ongeacht waar op
     de pagina het span staat.
  3. Prijs-tekst-vorm: "XCG 350.000 / € 170.000 kk" of "ANG 1.378.000 /
     € 689.000 kk" — het EERSTE bedrag (vóór de "/") is de native valuta,
     ANG en XCG zijn hier hetzelfde (oude/nieuwe naam Antilliaanse gulden).
     Soms een prefix "Prijs is verlaagd naar:" of "Prijs verlaagd naar:"
     vóór het bedrag — genegeerd, alleen het bedrag zelf wordt geparsed.
  4. Geen status-taxonomie of ribbon-element gevonden — status blijkt uit
     de titel ("Te koop: ..."). Geen van de 3 Curaçao-listings toont een
     verkocht/verhuurd-signaal in titel of icon-list; wel bevat de
     Bredestraat-pandbeschrijving de tekst "verhuurd" — maar dat gaat over
     de HUIDIGE HURENDE HUURDERS van units in het te-koop-zijnde pand, niet
     over de listing-status zelf. Geen aparte SOLD/RENTED-regex nodig voor
     deze kleine set, wel voor de zekerheid een basis-check op "VERKOCHT"/
     "VERHUURD" als LOS woord in de titel (voorkomt false negatives als een
     toekomstige 4e listing die tekst wél in de titel heeft).
  5. Property-type: keyword-matching EERST op de titel (bekende valkuil —
     spec-labels/amenities in de beschrijving geven valse hits). "villa"/
     "woning"/"huis" → house, "appartement" → apartment, "commercieel
     pand"/"kantoor"/"bedrijfspand" → commercial, "kavel"/"grond"/"perceel
     te koop" (als LOSSE listing, niet als spec-veld) → land. Standaard
     house als niets matcht.
  6. Geen coördinaten op de paginas gevonden (alleen een contactformulier-
     kaart-widget zonder listing-specifieke lat/lng) — latitude/longitude
     blijven None.
  7. Alle 3 listings zijn 'sale' (geen huur-aanbod gezien op deze site).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://dmjmakelaar.com"
SITEMAP = f"{BASE}/page-sitemap.xml"

PRICE_RE = re.compile(
    r"(XCG|ANG)\s*([\d.,]+)", re.I
)
BEDROOMS_RE = re.compile(r"(\d+)\s*Slaapkamers?", re.I)
BATHROOMS_RE = re.compile(r"(\d+)\s*Badkamers?", re.I)
LIVING_AREA_RE = re.compile(r"([\d.,]+)\s*m2\s*Wonen", re.I)
LOT_AREA_RE = re.compile(r"([\d.,]+)\s*m2\s*Perceel", re.I)

SOLD_TITLE_RE = re.compile(r"\b(VERKOCHT|VERHUURD|SOLD)\b", re.I)

HOUSE_HINTS = ("villa", "woning", "huis")
APARTMENT_HINTS = ("appartement", "penthouse", "studio")
COMMERCIAL_HINTS = ("commercieel pand", "kantoor", "bedrijfspand", "pand ")
LAND_HINTS = ("kavel", "bouwgrond", "perceel te koop", "grond te koop")


class DmjMakelaarScraper(BaseScraper):
    source_name = "dmj_makelaar"
    AGENT_COMPANY = "DMJ Makelaar"

    def scrape(self) -> list[Listing]:
        soup = self.get(SITEMAP)
        if soup is None:
            self.logger.error("Sitemap niet opgehaald")
            return []

        slugs = []
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if "/aanbod/" not in url:
                continue
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            if not slug or slug == "aanbod":
                continue
            if not slug.endswith("-curacao"):
                continue  # Bonaire/Spanje-listings van hetzelfde kantoor overslaan
            slugs.append(slug)

        self.logger.info(f"DMJ Makelaar: {len(slugs)} Curaçao-listing(s) gevonden in sitemap")

        results = []
        for slug in slugs:
            try:
                l = self._scrape_detail(slug)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({slug}): {e}")
        return results

    def _scrape_detail(self, slug: str) -> Listing | None:
        url = f"{BASE}/aanbod/{slug}/"
        soup = self.get(url)
        if soup is None:
            return None

        # Niet elke listing-pagina heeft een <h1> (Elementor-pagina's gebruiken
        # soms alleen <h2>'s) — dan valt de <title>-tag terug als betere bron
        # dan de kale slug.
        h1_tag = soup.select_one("h1")
        title_tag = soup.select_one("title")
        title = None
        if h1_tag:
            title = self.clean_text(h1_tag.get_text())
        if not title and title_tag:
            title = self.clean_text(title_tag.get_text())
        if not title:
            title = slug.replace("-", " ").title()

        if title and SOLD_TITLE_RE.search(title):
            return None

        # Content-patroon-filtering i.p.v. class-scope (bekende valkuil):
        # verzamel alle icon-list-tekst-spans en match op inhoud, niet op positie.
        spans = [self.clean_text(s.get_text()) for s in soup.select("span.elementor-icon-list-text")]
        spans = [s for s in spans if s]
        combined = " | ".join(spans)

        price = None
        m = PRICE_RE.search(combined)
        if m:
            price = self.parse_price(m.group(2))
            if price is not None and price < 5000:
                price = None  # sanity-ondergrens, zelfde les als eerdere scrapers

        bedrooms = None
        m = BEDROOMS_RE.search(combined)
        if m:
            bedrooms = int(m.group(1))

        bathrooms = None
        m = BATHROOMS_RE.search(combined)
        if m:
            try:
                bathrooms = round(float(m.group(1).replace(",", ".")))
            except ValueError:
                bathrooms = None

        area_sqm = None
        m = LIVING_AREA_RE.search(combined)
        if m:
            area_sqm = self.parse_area(m.group(0))
        else:
            m = LOT_AREA_RE.search(combined)
            if m:
                area_sqm = self.parse_area(m.group(0))

        # Geen betrouwbare description-container-class gevonden (`<article>`
        # matcht alleen de "gerelateerd aanbod"-widget-cards elders op de
        # pagina — bekende valkuil). In plaats daarvan: de "Omschrijving"-
        # kop zoeken en alle <p>-tags die daarna volgen (tot de volgende
        # <h2>) samenvoegen — werkt op alle geziene listing-paginas.
        description = None
        heading_flow = soup.find_all(["h2", "p"])
        omschrijving_idx = None
        for i, el in enumerate(heading_flow):
            if el.name == "h2" and "omschrijving" in el.get_text(strip=True).lower():
                omschrijving_idx = i
                break
        if omschrijving_idx is not None:
            paras = []
            for el in heading_flow[omschrijving_idx + 1:]:
                if el.name == "h2":
                    break
                t = el.get_text(" ", strip=True)
                if t:
                    paras.append(t)
            if paras:
                description = self.clean_text(" ".join(paras))

        images = self.clean_images(
            [img.get("src") for img in soup.select("img[src*='wp-content/uploads']")]
        )

        hint_text = title.lower() if title else ""
        if any(h in hint_text for h in COMMERCIAL_HINTS):
            property_type = "commercial"
        elif any(h in hint_text for h in APARTMENT_HINTS):
            property_type = "apartment"
        elif any(h in hint_text for h in LAND_HINTS):
            property_type = "land"
        elif any(h in hint_text for h in HOUSE_HINTS):
            property_type = "house"
        else:
            property_type = "house"

        return Listing(
            source_id=self.source_id,
            external_id=slug,
            title=title or "Woning Curaçao",
            listing_type="sale",
            property_type=property_type,
            price_ang=price,
            currency="XCG",
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
