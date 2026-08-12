"""Mambo Developers scraper (priority 6 — kleine "resales"-sectie, 5 unieke listings)
Site: https://www.mambodevelopers.com — Wix (Dynamic Pages / CMS-collectie
`resales`), zelfde patroon als salas_real_estate.py: elke individuele
`/resales/<slug>`-pagina is server-side gerenderd, prijs/status/kenmerken
staan al kant-en-klaar in de ruwe HTML (geen headless browser nodig).
robots.txt: `Allow: /` voor alle user-agents, geen ClaudeBot-vermelding,
geen captcha-signalen (alleen een PetalBot-block en een crawl-delay van 10s
voor dotbot/AhrefsBot specifiek) — ruim voldoende marge met de standaard
REQUEST_DELAY.

Mambo Developers is een projectontwikkelaar (Bocazul, Mambo Hills, ONE Mambo
Beach, Epic Residences) die naast nieuwbouw ook een kleine "Resales"-sectie
heeft: doorverkoop van reeds opgeleverde/eerder verkochte units door de
huidige eigenaar, via dezelfde developer als bemiddelaar. Dit is dus geen
klassieke onafhankelijke makelaar, maar wel een echte, actieve verkoop-
inventory op Curaçao met eigen structurele data — vergelijkbaar met hoe
New Winds Realty (ook developer-met-projectpagina) al is meegenomen.

Methode:
  1. Lijst uit de losse Wix-CMS-sitemap `dynamic-resales_..._0_5000-sitemap.xml`
     (via `sitemap.xml`-index) — 6 URL's onder `/resales/<slug>`, maar één
     daarvan (`unit-1-one-mambo-beach`) is een VERLOPEN/hernoemde slug die
     301-redirect naar `unit-8-one-mambo-beach` (zelfde listing, "ONE Mambo
     Beach Unit 8") — dedup via de `<link rel="canonical">`-tag op de
     uiteindelijke pagina i.p.v. de sitemap-URL zelf, dus 5 unieke listings.
  2. Status staat als kale platte tekst direct ná het "Status"-label
     ("For Sale" bij alle 5 geziene listings, dus (nog) geen "Sold"/"Under
     Contract"-voorbeeld gezien — de check op ACTIVE_STATUSES staat er wel,
     voor de toekomst).
  3. Prijs: eerste "$"-bedrag met duizendtal-komma's in de ruwe HTML
     (`\\$\\s?\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?`) — dit is betrouwbaar de
     échte prijs, want de labels variëren tussen pagina's ("Price" met
     onzichtbare zero-width-space-tekens erna, "Asking Price", "Asking
     Price:") maar de eerste grote "$"-match op de pagina is bij alle 5
     geteste listings steeds de juiste prijs (tweede match is een losse
     "$1" uit een ongerelateerd Wix-JS-blok, geen bruikbare tweede prijs).
     Amerikaans decimaalformaat (bv. "$609,333.33") — GEEN generieke
     `self.parse_price()` gebruiken (die behandelt "." als duizendtal-
     scheidingsteken en zou de prijs 100x te hoog maken), losse eigen regex
     i.p.v.
  4. Bedrooms/Bathrooms/oppervlakte staan in een vaste label→waarde-
     structuur (`>Bedrooms<...waarde`, `>Bathrooms<...waarde`,
     `>SQFT<...waarde`) — simpele regex-match op de eerstvolgende
     `wixui-rich-text__text`-paragraaf ná het label. "N/A" bij land/kavel-
     listings (geen woonruimte) → blijft `None` i.p.v. een foutieve 0.
     Bathrooms kan een komma-decimaal zijn ("3.5" bij Bocazul Villa, komma-
     variant elders) → `round(float(...))`.
  5. **Onzekerheid (ANG. 12 aug 2026): het "SQFT"-label is zeer waarschijnlijk
     fout/verouderd content op de site zelf** — de onderliggende Wix-CMS-
     velddefinitie heet intern `sqft` maar heeft als displayName letterlijk
     "m2", en de vrije beschrijvingstekst bij Bocazul Villa noemt expliciet
     "This 380-square-meter villa..." (exact dezelfde waarde als het SQFT-
     veld, 380) — dus het label toont "SQFT" maar de waarde is in
     werkelijkheid m². `area_sqm` wordt daarom direct van de waarde
     overgenomen zonder eenheidsconversie. **Losstaande onzekerheid: bij
     Bocazul Villa noemt de structurele data 3 slaapkamers/3,5 badkamers,
     maar de vrije beschrijvingstekst noemt expliciet "four bedrooms, four
     full bathrooms"** — een reële tegenstrijdigheid op de bron zelf tussen
     het spec-blok en de marketingtekst. Het spec-blok (structurele data,
     consistent format over alle 5 listings) is aangehouden, niet de
     mogelijk generieke/onnauwkeurige beschrijvingstekst — Peter kan dit
     zelf verifiëren op https://www.mambodevelopers.com/resales/bocazul-villa.
  6. Property-type uit de titel: "Plot"/"Lot" → land (vóór "Villa" gecheckt,
     want "Villa Plot" bevat beide), "Villa" → house, "Unit"/"Apartment" →
     apartment, default house.
  7. Beschrijving: de eerste paar vrije-tekst-alinea's (>80 tekens) uit de
     rich-text-paragrafen, samengevoegd — geen vaste "Description"-label
     gevonden op de pagina, dus een lengte-heuristiek i.p.v. een vaste
     kop-tot-kop-grens.
  8. Foto's: zelfde patroon als Salas Real Estate — swiper/gallery-items
     met `data-hook="gallery-item-image-img"` en een gewone `src`.
  9. Geen coördinaten op de pagina gevonden — latitude/longitude blijven
     None, net als bij vergelijkbare kleine sites in deze set.
 10. Alle listings zijn in Curaçao (Blue Bay/Mambo Beach-omgeving, geen
     regio-filter nodig). Valuta altijd native USD (geen "XCG"/"ANG"-
     vermelding gezien op de resale-pagina's), geen omrekening.
"""
import re
import time
import random
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..models import Listing
from ..config import REQUEST_DELAY, TIMEOUT

BASE = "https://www.mambodevelopers.com"
SITEMAP_INDEX = f"{BASE}/sitemap.xml"

ACTIVE_STATUSES = {"for sale", "for rent"}

PRICE_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def _label_value(html: str, label: str) -> str | None:
    m = re.search(
        re.escape(">" + label) + r"[​\s:]*<.*?wixui-rich-text__text\">([^<]*)</p>",
        html,
        re.S,
    )
    if not m:
        return None
    val = m.group(1).replace("​", "").strip()
    return val or None


class MamboDevelopersScraper(BaseScraper):
    source_name = "mambo_developers"
    AGENT_COMPANY = "Mambo Developers"

    def scrape(self) -> list[Listing]:
        index_soup = self.get(SITEMAP_INDEX)
        if index_soup is None:
            self.logger.error("Sitemap-index niet opgehaald")
            return []

        resales_sitemap_url = None
        for loc in index_soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if "dynamic-resales" in url:
                resales_sitemap_url = url
                break

        if not resales_sitemap_url:
            self.logger.error("Geen dynamic-resales-sitemap gevonden in index")
            return []

        resales_soup = self.get(resales_sitemap_url)
        if resales_soup is None:
            self.logger.error("Resales-sitemap niet opgehaald")
            return []

        urls = [loc.get_text(strip=True) for loc in resales_soup.find_all("loc")]
        urls = [u for u in urls if "/resales/" in u]
        self.logger.info(f"Mambo Developers: {len(urls)} listing(s) gevonden in sitemap")

        results = []
        seen_ids = set()
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l and l.external_id not in seen_ids:
                    seen_ids.add(l.external_id)
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({url}): {e}")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        # self.get() volgt redirects al (requests default) en parsed de
        # uiteindelijke pagina — we hebben alleen de RUWE HTML nodig voor de
        # label→waarde-regex, dus fetchen we los i.p.v. via self.get()'s
        # BeautifulSoup-only return.
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))
            r = self.session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            self.logger.warning(f"Fetch mislukt ({url}): {e}")
            return None

        soup = BeautifulSoup(html, "lxml")

        canonical = soup.select_one('link[rel="canonical"]')
        final_url = canonical.get("href") if canonical and canonical.get("href") else url
        slug = final_url.rstrip("/").rsplit("/", 1)[-1]

        title_tag = soup.select_one("title")
        title = None
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            if title and "|" in title:
                title = title.split("|", 1)[0].strip()
        if not title:
            title = slug.replace("-", " ").title()

        status_val = _label_value(html, "Status")
        status = status_val.strip().lower() if status_val else None
        if status and status not in ACTIVE_STATUSES:
            return None  # sold / under contract / reserved e.d.

        listing_type = "rent" if status == "for rent" else "sale"

        price = None
        pm = PRICE_RE.search(html)
        if pm:
            price = float(pm.group(0).replace("$", "").replace(",", "").split(".")[0])

        bedrooms = None
        bd_val = _label_value(html, "Bedrooms")
        if bd_val and bd_val.upper() != "N/A":
            m = re.search(r"\d+", bd_val)
            if m:
                bedrooms = int(m.group())

        bathrooms = None
        ba_val = _label_value(html, "Bathrooms")
        if ba_val and ba_val.upper() != "N/A":
            try:
                bathrooms = round(float(ba_val.replace(",", ".")))
            except ValueError:
                bathrooms = None

        area_sqm = None
        sqft_val = _label_value(html, "SQFT")
        if sqft_val and sqft_val.upper() != "N/A":
            try:
                area_sqm = float(sqft_val.replace(",", "."))
            except ValueError:
                area_sqm = None

        title_l = (title or "").lower()
        if "plot" in title_l or "lot" in title_l:
            property_type = "land"
        elif "villa" in title_l:
            property_type = "house"
        elif "unit" in title_l or "apartment" in title_l or "residence" in title_l:
            property_type = "apartment"
        else:
            property_type = "house"

        paragraphs = [
            self.clean_text(p.get_text(" ", strip=True))
            for p in soup.select("p.wixui-rich-text__text")
        ]
        paragraphs = [p for p in paragraphs if p and len(p) > 80]
        description = self.clean_text(" ".join(paragraphs[:4]), max_len=2000)

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
            currency="USD",
            url=final_url,
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
