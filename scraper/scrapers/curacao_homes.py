"""Curaçao Homes scraper (priority 8)
Site: https://www.curacaohomes.com — géén WordPress/Houzez/Webflow, maar een
custom "Spin" real-estate-CMS (assets via `assets.spin-cdn.com`,
foto's via `curacaohomes.spin-cdn.com`), met Laravel-sessiebeheer
(`XSRF-TOKEN`/`laravel_session`-cookies). Ondanks de Laravel-cookies is de
site GEWOON server-side gerenderd — geen SPA, geen aparte JSON-API nodig,
gewone HTML-parsing volstaat. (Eerdere sessie dacht dat dit "eigen
onderzoek" nodig had wegens de Laravel-signalen — bleek in de praktijk
net zo scrapebaar als de WordPress-sites.)

Methode:
  1. Geen losse listing-sitemap (het `sitemap.xml` bevat alleen categorie-
     pagina's). Listing-URL's dus verzameld via de 4 categoriepagina's:
     `/realestate/houses-for-sale`, `/realestate/houses-for-rent`,
     `/realestate/commercial-for-sale`, `/realestate/commercial-for-rent`.
     Deze pagina's tonen ALLE listings al server-side in de HTML (een
     `jpages`-jQuery-plugin verzorgt client-side paginering/filtering,
     maar verstopt niets uit de eerste `curl`-response — bevestigd door
     te tellen dat alle zichtbare listing-links al in de kale HTML zitten).
  2. Detailpagina is nette server-rendered HTML: titel in `<h1>`, prijs in
     `<span class="prop-price" data-price="123456">`, kenmerken in een
     `<div class="details-title">Details:</div>` gevolgd door een `<ul>`
     met vrije-tekst `<li>`-items ("Bedrooms: 3", "Bathrooms: 2,5",
     "Lot size: 809 m2", soms ook "Living space: … m2" — overige `<li>`'s
     zijn ongelabelde features/amenities en worden genegeerd). Coördinaten
     staan in een `LatLng(lat, lng)`-aanroep in de Google Maps-embed-JS.
  3. **Kritieke status-valkuil (vijfde variant in deze scraper-set): hier
     staat "SOLD"/"SOLD!"/"RENTED" als LOSSE eerste alinea vóór de eigenlijke
     beschrijvingstekst** (`<p>SOLD</p>` direct na de "Description"-kop),
     niet in de titel en niet in een aparte statustaxonomie. Steekproef op
     alle 26 listings: slechts 9 nog echt beschikbaar (1/9 te-koop, 6/15
     te-huur, 2/2 commercieel) — de rest staat nog live maar is al
     verkocht/verhuurd. Check op een exacte paragraaf-match
     (`SOLD`/`SOLD!`/`RENTED`/`RENTED!`/`UNDER OFFER`), niet op een losse
     substring in de vrije beschrijvingstekst (voorkomt false positives
     als het woord toevallig elders in de tekst voorkomt).
  4. Bathrooms kan een halve badkamer zijn ("2,5") — afgerond naar
     integer (kolom is `integer` in Supabase, zie bekende valkuil).
  5. Eén listing (kantoor-ruimten-emmastad) stond zowel op de
     for-sale- als de for-rent-commercial-pagina — sale krijgt voorrang
     (enige zo'n geval in de steekproef, geen aparte dedup-logica nodig).
  6. Geen coördinaten-bounding-box-uitschieters gezien in de steekproef
     (Curaçao-only site, geen multi-eiland-aanbod zoals bij Domicilie),
     wel voor de zekerheid dezelfde bounding-box-check toegepast.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.curacaohomes.com"

CATEGORY_PAGES = {
    "houses-for-sale": ("sale", "house"),
    "commercial-for-sale": ("sale", "commercial"),
    "houses-for-rent": ("rent", "house"),
    "commercial-for-rent": ("rent", "commercial"),
}

UNAVAILABLE_RE = re.compile(
    r"<p[^>]*>\s*(SOLD!?|RENTED!?|UNDER OFFER|NOT AVAILABLE)\s*</p>", re.I
)
LATLNG_RE = re.compile(r"LatLng\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\)")
PRICE_RE = re.compile(r'class="prop-price"\s+data-price="(\d+)"')
BEDROOMS_RE = re.compile(r"Bedrooms:\s*(\d+)", re.I)
BATHROOMS_RE = re.compile(r"Bathrooms:\s*([\d.,]+)", re.I)
LIVING_AREA_RE = re.compile(r"Living space:\s*([\d.,]+)\s*m", re.I)
LOT_AREA_RE = re.compile(r"Lot size:\s*([\d.,]+)\s*m", re.I)

APARTMENT_HINTS = ("appartement", "apartment", "penthouse", "studio")
LAND_HINTS = ("kavel", "land for", "bouwgrond", "plot", "lot for")


class CuracaoHomesScraper(BaseScraper):
    source_name = "curacao_homes"
    AGENT_COMPANY = "Curaçao Homes"

    def scrape(self) -> list[Listing]:
        # slug -> (listing_type, category_property_type), sale wint bij dubbels
        found: dict[str, tuple[str, str]] = {}
        for cat, (ltype, ptype) in CATEGORY_PAGES.items():
            soup = self.get(f"{BASE}/realestate/{cat}")
            if soup is None:
                self.logger.warning(f"Categoriepagina niet opgehaald: {cat}")
                continue
            slugs = set()
            for a in soup.select('a[href^="/realestate/"]'):
                href = a.get("href", "")
                slug = href.rsplit("/", 1)[-1]
                if slug in CATEGORY_PAGES or slug in ("map", ""):
                    continue
                slugs.add(slug)
            self.logger.info(f"{cat}: {len(slugs)} listing-links")
            for slug in slugs:
                if slug not in found or ltype == "sale":
                    found[slug] = (ltype, ptype)

        self.logger.info(f"Curaçao Homes: {len(found)} unieke listing-URL's gevonden")

        results = []
        for slug, (ltype, ptype) in found.items():
            try:
                l = self._scrape_detail(slug, ltype, ptype)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({slug}): {e}")
        return results

    def _scrape_detail(self, slug: str, listing_type: str, category_ptype: str) -> Listing | None:
        url = f"{BASE}/realestate/{slug}"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        html_text = r.text

        if UNAVAILABLE_RE.search(html_text):
            return None

        soup = __import__("bs4").BeautifulSoup(html_text, "lxml")

        title_tag = soup.select_one("h1")
        title = self.clean_text(title_tag.get_text()) if title_tag else slug.replace("-", " ").title()

        price = None
        m = PRICE_RE.search(html_text)
        if m:
            price = float(m.group(1))
            # Sanity-ondergrens (zelfde les als PriceMatch): een listing kan
            # zowel op een for-sale- als for-rent-categoriepagina staan maar
            # de detailpagina toont dan één prijs die eigenlijk de huurprijs
            # is (bv. "XCG 1.100" als koopprijs is onwaarschijnlijk) —
            # zo'n implausibele koopprijs op None zetten, listing blijft staan.
            if listing_type == "sale" and price is not None and price < 5000:
                price = None

        details_block = soup.select_one(".details-title")
        details_text = ""
        if details_block:
            ul = details_block.find_next_sibling("ul")
            if ul:
                details_text = ul.get_text(" ", strip=True)

        bedrooms = None
        m = BEDROOMS_RE.search(details_text)
        if m:
            bedrooms = int(m.group(1))

        bathrooms = None
        m = BATHROOMS_RE.search(details_text)
        if m:
            try:
                bathrooms = round(float(m.group(1).replace(",", ".")))
            except ValueError:
                bathrooms = None

        area_sqm = None
        m = LIVING_AREA_RE.search(details_text) or LOT_AREA_RE.search(details_text)
        if m:
            area_sqm = self.parse_area(m.group(0))

        description_tag = soup.select_one("#el-col-1 .text") or soup.select_one(".text")
        description = self.clean_text(description_tag.get_text(" ", strip=True)) if description_tag else None

        latitude = longitude = None
        m = LATLNG_RE.search(html_text)
        if m:
            try:
                lat_c, lng_c = float(m.group(1)), float(m.group(2))
                if 11.9 <= lat_c <= 12.5 and -69.3 <= lng_c <= -68.5:
                    latitude, longitude = lat_c, lng_c
            except ValueError:
                pass

        images = self.clean_images(
            [im.get("href") for im in soup.select('a[data-rel="eid_slide"]')]
        )

        hint_text = f"{slug} {title.lower()}"
        if category_ptype == "commercial":
            property_type = "commercial"
        elif any(h in hint_text for h in APARTMENT_HINTS):
            property_type = "apartment"
        elif any(h in hint_text for h in LAND_HINTS):
            property_type = "land"
        else:
            property_type = "house"

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
            latitude=latitude,
            longitude=longitude,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
