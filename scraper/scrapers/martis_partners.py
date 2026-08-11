"""Martis Partners scraper (priority 8)
Site: https://www.martis-partners.com — Squarespace (géén WordPress/Houzez/
Webflow/eigen-CMS, eerste Squarespace-site in deze scraper-set).

robots.txt-check EERST gedaan (les uit 7th Heaven Properties): de site draait
op de standaard Squarespace-robotslijst. Een lange rij `User-agent:`-regels
(inclusief `ClaudeBot` met naam, naast GPTBot/CCBot/Google-Extended/etc.)
deelt daar gewoon de PERMISSIEVE `User-agent: *`-regelset mee (geen losse
`Disallow: /`-regel voor die bot-groep) — dus géén principiële stop zoals bij
Coldwell Banker/7th Heaven. De regelset disallow't alleen `/config`,
`/search`, `/account`, `/api/`, `/static/` en een aantal querystring-formats
(`?format=json` etc.) — normale contentpagina's zijn toegestaan.

Methode:
  1. Geen losse listing-detailpagina's. `sitemap.xml` bevat alleen 4 vaste
     categoriepagina's (`/koopwoningen`, `/huurwoningen`, `/kavels`,
     `/commercieel`) — elke listing is een los item in een Squarespace
     "gallery"-blok op zo'n pagina, met een WhatsApp-link als CTA i.p.v. een
     eigen detail-URL.
  2. Squarespace rendert de volledige item-data (titel, beschrijving incl.
     kenmerken/prijs, en afbeelding-metadata) al server-side in de HTML als
     HTML-ge-escapte JSON (`&quot;title&quot;: ...`) — dus geen aparte
     `?format=json`-call nodig (die is sowieso disallowed in robots.txt).
     `html.unescape()` op de ruwe pagina-HTML volstaat om de JSON-fragmenten
     leesbaar te maken; per item wordt met regex op de velden
     `title`/`description`/`systemDataId`/`filename` gezocht i.p.v. de hele
     blob als JSON te parsen (de omliggende structuur is geen valide
     top-level JSON-document, wel voorspelbare per-item fragmenten).
  3. Geen los prijs/bedrooms/bathrooms-veld — alles zit in de vrije
     `description`-HTML per item ("3 Slaapkamers<br>2 Badkamers<br>...
     Vraagprijs: XCG. 525.000,-"). Losse regexes per kenmerk op de
     platte tekst van die description.
  4. **Zevende status-signaal-variant in deze scraper-set: een bracket-prefix
     in de item-TITEL zelf** (`[VERHUURD] Appartement Sta. Rosa`,
     `[VERKOCHT] Kavel Brakkeput`) — niet in een taxonomie, niet in de
     beschrijving, maar in de titel-string die verder ook gewoon als
     weergavetitel dient. Regex op een `[WOORD]`-prefix aan het begin van de
     titel; bekende inactieve labels (verhuurd/verkocht/rented/sold/onder
     bod/reserved) filteren de listing eruit, andere labels (kwamen niet
     voor in de steekproef) worden voor de zekerheid ook uitgesloten
     (defensief: onbekend bracket-label = niet meenemen, geen valse actieve
     listing tonen).
  5. Geen eigen detail-URL per listing — de `url` is de categoriepagina met
     een `#<systemDataId>`-fragment erachter geplakt (uniek per listing,
     traceerbaar terug naar de bronpagina, geen dubbele URL's over
     categorieën heen omdat systemDataId per foto/item uniek is).
  6. Afbeeldingen: Squarespace CDN-URL opgebouwd uit het vaste site-ID
     (`64f644a2b2b6e63d0357d935`, gevonden in de favicon-URL/meta-tags op
     elke pagina) + het item's `systemDataId` + url-encoded `filename` —
     zelfde patroon als de image-URL's die al in `sitemap.xml` stonden.
  7. Erg klein aanbod (4 actieve listings op het moment van bouwen: 3 koop,
     1 commercieel; huurwoningen en kavels hadden allebei precies 1 item en
     dat was in beide gevallen al verhuurd/verkocht) — desondanks de moeite
     waard: robots.txt geen blokkade, scrapebaar, en het aanbod kan groeien.
"""
import re
import html as ihtml
import urllib.parse

from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://martis-partners.com"
SITE_ID = "64f644a2b2b6e63d0357d935"

CATEGORY_PAGES = {
    "koopwoningen": ("sale", "house"),
    "huurwoningen": ("rent", "house"),
    "kavels": ("sale", "land"),
    "commercieel": ("sale", "commercial"),
}

# Bracket-prefix aan het begin van de titel duidt op status, bv.
# "[VERHUURD] Appartement Sta. Rosa" of "[VERKOCHT] Kavel Brakkeput".
BRACKET_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(.*)$")

PRICE_RE = re.compile(r"XCG\.?\s*([\d.,]+)", re.I)
BEDROOMS_RE = re.compile(r"(\d+)\s*Slaapkamer", re.I)
BATHROOMS_RE = re.compile(r"(\d+)\s*Badkamer", re.I)
LIVING_AREA_RE = re.compile(r"Woonoppervlakte\D{0,10}([\d.,]+)\s*m", re.I)
LOT_AREA_RE = re.compile(r"(?:Eigendomsgrond|Erfpachtsgrond)\D{0,10}([\d.,]+)\s*m", re.I)
GENERIC_AREA_RE = re.compile(r"([\d.,]+)\s*m2", re.I)

ITEM_TITLE_RE = re.compile(r'"title":\s*"([^"]{2,150})"')
SKIP_TITLES = ("Koopwoningen", "Huurwoningen", "Kavels", "Commercieel", "Blok {@}", "")


class MartisPartnersScraper(BaseScraper):
    source_name = "martis_partners"
    AGENT_COMPANY = "Martis Partners"

    def scrape(self) -> list[Listing]:
        results: list[Listing] = []
        for slug, (listing_type, category_ptype) in CATEGORY_PAGES.items():
            url = f"{BASE}/{slug}"
            try:
                r = self.session.get(url, timeout=30)
                r.raise_for_status()
            except Exception as e:
                self.logger.warning(f"Categoriepagina niet opgehaald: {slug} ({e})")
                continue
            decoded = ihtml.unescape(r.text)

            for m in ITEM_TITLE_RE.finditer(decoded):
                raw_title = m.group(1)
                if raw_title in SKIP_TITLES:
                    continue

                bm = BRACKET_RE.match(raw_title)
                if bm:
                    # Elk bracket-label sluit uit (les 4 in de docstring):
                    # bekende inactieve labels expliciet, onbekende labels
                    # defensief ook (geen valse actieve listing tonen).
                    label = bm.group(1).strip().lower()
                    self.logger.info(f"Overgeslagen (bracket-status '{label}'): {raw_title}")
                    continue

                chunk = decoded[m.start():m.start() + 6000]
                l = self._parse_item(chunk, raw_title, url, listing_type, category_ptype)
                if l:
                    results.append(l)

        self.logger.info(f"Martis Partners: {len(results)} actieve listings")
        return results

    def _parse_item(self, chunk: str, title: str, page_url: str,
                     listing_type: str, category_ptype: str) -> Listing | None:
        desc_m = re.search(r'"description":\s*"(.*?)",\s*\n?\s*"button"', chunk, re.S)
        sysid_m = re.search(r'"systemDataId":\s*"([a-f0-9\-]+)"', chunk)
        fname_m = re.search(r'"filename":\s*"([^"]*)"', chunk)

        if not sysid_m:
            # Geen item-record (bv. een tekstblok dat toevallig een
            # "title"-veld had) — overslaan.
            return None

        desc_html = desc_m.group(1) if desc_m else ""
        # De ruwe chunk komt uit een JS-string-literal (backslash-escaped
        # quotes/slashes) — unescapen voor leesbare platte tekst.
        desc_html = desc_html.replace('\\/', '/').replace('\\"', '"')
        desc_text = re.sub(r"<[^>]+>", " ", desc_html)
        desc_text = re.sub(r"\s+", " ", desc_text).strip()

        price = None
        pm = PRICE_RE.search(desc_text)
        if pm:
            price = self.parse_price(pm.group(1))

        bedrooms = None
        bm = BEDROOMS_RE.search(desc_text)
        if bm:
            bedrooms = int(bm.group(1))

        bathrooms = None
        bam = BATHROOMS_RE.search(desc_text)
        if bam:
            bathrooms = int(bam.group(1))

        area_sqm = None
        am = LIVING_AREA_RE.search(desc_text) or LOT_AREA_RE.search(desc_text) or GENERIC_AREA_RE.search(desc_text)
        if am:
            try:
                area_sqm = float(am.group(1).replace(".", "").replace(",", "."))
            except ValueError:
                area_sqm = None

        sysid = sysid_m.group(1)
        fname = fname_m.group(1) if fname_m else ""
        images = []
        if fname:
            encoded_fname = urllib.parse.quote(fname)
            images = [f"https://images.squarespace-cdn.com/content/v1/{SITE_ID}/{sysid}/{encoded_fname}"]

        hint = title.lower()
        if category_ptype == "commercial":
            property_type = "commercial"
        elif category_ptype == "land":
            property_type = "land"
        elif "appartement" in hint or "apartment" in hint or "penthouse" in hint:
            property_type = "apartment"
        else:
            property_type = "house"

        return Listing(
            source_id=self.source_id,
            external_id=sysid,
            title=title or "Woning Curaçao",
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency="XCG",
            url=f"{page_url}#{sysid}",
            description=desc_text or None,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
