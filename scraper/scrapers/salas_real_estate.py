"""Salas Real Estate scraper (priority 6 — kleine site, 6 dynamic-property-pagina's)
Site: https://www.salasrealestate.net — Wix (Dynamic Pages / CMS-collectie
`properties`). **Eerder (twee vorige runs) foutief als "headless browser nodig"
weggezet, samen met CPM Real Estate en MP Real Estate Services** — bleek bij
nader onderzoek NIET te kloppen voor deze specifieke site: elke individuele
`/properties/<slug>`-pagina is gewoon server-side gerenderd met de volledige
tekst (titel, status, prijs, property-details) al in de kale HTML aanwezig,
GEEN client-side JS-rendering nodig voor de data die we nodig hebben. **Les:
niet elke Wix-site heeft per definitie een headless browser nodig — per site
verifiëren of de individuele contentpagina's server-gerenderd zijn (curl +
kijken of prijs/kenmerken al in de ruwe HTML staan) vóórdat je 'm afschrijft.**
Ter vergelijking: CPM Real Estate is WEL hetzelfde Wix-Dynamic-Pages-patroon
en ook server-gerenderd, maar heeft slechts 1 echte listing (rest is lege
project-marketingpagina's) — te weinig yield om te bouwen. MP Real Estate
Services gebruikt wél een client-side geladen Repeater/galerij zonder SSR-
data in de ruwe HTML — daar blijft een headless browser wél nodig.

Methode:
  1. robots.txt EERST gecheckt: permissief (`Allow: /`, geen ClaudeBot-
     vermelding, geen captcha-signalen — alleen een PetalBot-block en een
     crawl-delay van 10s voor dotbot/AhrefsBot, dus ruim voldoende marge
     met de standaard REQUEST_DELAY van deze scraper-set).
  2. Lijst uit de losse Wix-CMS-sitemap
     `dynamic-properties_..._0_5000-sitemap.xml` (via `sitemap.xml`-index) —
     6 URL's onder `/properties/<slug>`.
  3. **Status staat als kale platte tekst direct ná de locatieregel, VÓÓR de
     prijs** ("For Sale" / "For Rent" / "Sold" / "Under Contract" / evt.
     "Under Option") — geen class/data-attribuut nodig, content-patroon-
     match op de tekst tussen de locatieregel en het "XCG."-prijs-label.
     Alleen "For Sale" en "For Rent" tellen als actief; "Sold"/"Under
     Contract"/"Under Option" worden overgeslagen. Van de 6 listings waren
     er bij het testen 3 actief (2x for sale, 1x for rent) en 3 niet
     (2x sold, 1x under contract).
  4. Prijs: altijd al native "XCG. 1.234.567,- k.k." of "XCG. 2.350,-"
     (huur) — geen valuta-omrekening nodig, XCG is de enige gebruikte
     valuta op deze site. `parse_price()` verwerkt het duizendtal-punt/
     komma-decimaal-formaat prima (alles behalve cijfers wordt weggehaald).
  5. Property Details-blok bevat nette labels: "Property Type", "Bedrooms",
     "Bathrooms", "Size". Bedrooms/Bathrooms zijn soms leeg of een losse
     zero-width-space (`\\u200b`) i.p.v. een cijfer (bij land/kavel-listings
     zonder woonruimte) — dan blijft het veld `None` i.p.v. een foutieve 0.
     Bathrooms kan een half getal zijn ("1.5") — expliciet afronden i.p.v.
     de generieke `parse_int` (integer-kolom-valkuil, zoals eerder gezien).
  6. Beschrijving: de vrije tekst tussen "Property Description" en "Contact
     Agent" — beide koppen zijn altijd aanwezig en vormen een betrouwbare
     grens.
  7. Foto's: swiper/PhotoGallery-items met `data-hook="gallery-item-image-
     img"` en een gewone `src` (geen lazy-load-`data-src` zoals bij
     Wigbold) — het Wix-logo/header-image wordt vanzelf weggefilterd door
     `clean_images()`'s standaard logo/watermerk-uitsluiting.
  8. Property-type: het "Property Type"-veld zelf is al schoon ("Lot",
     "Residential", "Residential, Commercial", "Commercial") — direct
     mappen i.p.v. keyword-gokken op titel/beschrijving zoals bij minder
     nette bronnen nodig is.
  9. Geen coördinaten op de pagina gevonden (alleen een adrestekst) —
     latitude/longitude blijven None, net als bij vergelijkbare kleine
     sites in deze set.
 10. Alle 6 URL's zijn Curaçao (geen regio-filter nodig, kleine lokale
     makelaar zonder buiten-eiland-kantoren).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.salasrealestate.net"
SITEMAP_INDEX = f"{BASE}/sitemap.xml"

STATUS_RE = re.compile(
    r"(For Sale|For Rent|Sold|Under Contract|Under Option)\s*XCG",
    re.I,
)
ACTIVE_STATUSES = {"for sale", "for rent"}

PRICE_RE = re.compile(r"XCG\.?\s*([\d.,]+)", re.I)
BEDROOMS_RE = re.compile(r"Bedrooms?\s*(\d+)", re.I)
BATHROOMS_RE = re.compile(r"Bathrooms?\s*([\d.]+)", re.I)
SIZE_RE = re.compile(r"Size\s*([\d.,]+)\s*m", re.I)

TYPE_MAP = {
    "lot": "land",
    "residential": "house",
    "commercial": "commercial",
}


class SalasRealEstateScraper(BaseScraper):
    source_name = "salas_real_estate"
    AGENT_COMPANY = "Salas Real Estate"

    def scrape(self) -> list[Listing]:
        index_soup = self.get(SITEMAP_INDEX)
        if index_soup is None:
            self.logger.error("Sitemap-index niet opgehaald")
            return []

        properties_sitemap_url = None
        for loc in index_soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if "dynamic-properties" in url:
                properties_sitemap_url = url
                break

        if not properties_sitemap_url:
            self.logger.error("Geen dynamic-properties-sitemap gevonden in index")
            return []

        props_soup = self.get(properties_sitemap_url)
        if props_soup is None:
            self.logger.error("Properties-sitemap niet opgehaald")
            return []

        urls = [loc.get_text(strip=True) for loc in props_soup.find_all("loc")]
        urls = [u for u in urls if "/properties/" in u]
        self.logger.info(f"Salas Real Estate: {len(urls)} listing(s) gevonden in sitemap")

        results = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({url}): {e}")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        slug = url.rstrip("/").rsplit("/", 1)[-1]

        title_tag = soup.select_one("title")
        title = None
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            # "<Naam> | Salas Real Estate - Curacao" -> alleen de naam
            if title and "|" in title:
                title = title.split("|", 1)[0].strip()
        if not title:
            title = slug.replace("-", " ").title()

        page_text = self.clean_text(soup.get_text(" "), max_len=20000) or ""

        m = STATUS_RE.search(page_text)
        status = m.group(1).lower() if m else None
        if status and status not in ACTIVE_STATUSES:
            return None  # sold / under contract / under option

        listing_type = "rent" if status == "for rent" else "sale"

        price = None
        m = PRICE_RE.search(page_text)
        if m:
            price = self.parse_price(m.group(1))
            if price is not None and price < 500:
                price = None  # sanity-ondergrens (huurprijzen kunnen laag zijn, dus laag)

        bedrooms = None
        m = BEDROOMS_RE.search(page_text)
        if m:
            bedrooms = int(m.group(1))

        bathrooms = None
        m = BATHROOMS_RE.search(page_text)
        if m:
            try:
                bathrooms = round(float(m.group(1)))
            except ValueError:
                bathrooms = None

        area_sqm = None
        m = SIZE_RE.search(page_text)
        if m:
            area_sqm = self.parse_area(m.group(0))

        description = None
        dm = re.search(
            r"Property Description(.*?)Contact Agent", page_text, re.S | re.I
        )
        if dm:
            description = self.clean_text(dm.group(1))

        type_text = None
        tm = re.search(r"Property Type\s*([A-Za-z, ]+?)\s*Bedrooms", page_text, re.I)
        if tm:
            type_text = tm.group(1).strip().lower()
        property_type = "house"
        if type_text:
            for key, val in TYPE_MAP.items():
                if key in type_text:
                    property_type = val
                    break

        images = self.clean_images(
            [img.get("src") for img in soup.select('img[data-hook="gallery-item-image-img"]')]
        )

        return Listing(
            source_id=self.source_id,
            external_id=slug,
            title=title or "Woning Curaçao",
            listing_type=listing_type,
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
