"""Curaçao Houses scraper (priority 6, lage yield — 5 van de 7 sitemap-URL's)
Site: https://www.curacaohouses.com — WordPress + "Essential Real Estate"
(ERE)-plugin, ZELFDE platformfamilie als GS Real Estate B.V. (`ere__`-CSS-
classes, `property-sitemap.xml`) — zie `gs_realestate.py` voor de volledige
uitleg van het ERE-patroon, dit bestand hergebruikt dezelfde aanpak met een
paar site-specifieke aanpassingen.

**Niet te verwarren met `curacao-houses.com` (MET koppelteken) — dat is het
bestaande alternatieve domein van NH Real Estate & Associates
(`nh_real_estate.py`, al gebouwd/live). Dit is `curacaohouses.com` (ZONDER
koppelteken) — een compleet andere, eigen makelaar ("Curaçao Houses"),
bevestigd via het `RealEstateAgent`/`Organization`-JSON-LD-blok op de
homepage (`"name":"Curaçao Houses"`).**

Site-specifieke afwijkingen t.o.v. `gs_realestate.py`:
  1. Geen wp-json/REST-route beschikbaar voor de property-CPT (`/wp-json/`
     bevat de CPT niet, en `?rest_route=/wp/v2/properties` geeft
     `rest_no_route`) — dus uitsluitend via `property-sitemap.xml` + HTML.
  2. **Slechts 7 URL's in de sitemap (incl. archiefpagina, dus 6 losse
     listings) — en van die 6 is er ook nog 1 in Bonaire i.p.v. Curaçao**
     ("Bonaire: Economische Starterswoning", titel begint met "Bonaire:").
     Filter: sla een listing over als de titel met "Bonaire" begint of het
     woord "Bonaire" bevat (Curaçao Houses adverteert kennelijk af en toe ook
     Bonaire-vastgoed onder dezelfde site).
  3. **Extra valkuil bovenop de bekende ERE-statusklasse-check: één listing
     had wél een actieve statusklasse (`for-rent`) maar de kale `<title>`-tag
     zegt gewoon "... Verhuurd!" — de site update de statusklasse dus niet
     altijd bij verhuur/verkoop.** Zelfde les als bij GS Real Estate
     (`hanenberg`-listing) en DMJ Makelaar: een titel-tekst-check op
     verkocht/verhuurd-woorden blijft nodig BOVENOP de statusklasse-check,
     nooit alleen op de taxonomie vertrouwen.
  4. Resultaat: van de 6 niet-Bonaire listings zijn er 5 daadwerkelijk actief
     (allemaal `for-sale`, geen huur-aanbod in de actieve set).
"""
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

SITEMAP = "https://www.curacaohouses.com/property-sitemap.xml"

RENT_CLASSES = {"verhuur", "for-rent", "te-huur"}
SALE_CLASSES = {"verkoop", "for-sale", "te-koop"}
ACTIVE_CLASSES = RENT_CLASSES | SALE_CLASSES

SOLD_TEXT_RE = re.compile(r"\b(VERKOCHT|VERHUURD|SOLD|RENTED)\b", re.I)
BONAIRE_RE = re.compile(r"\bbonaire\b", re.I)

# LET OP: "house" staat vóór "apartment" in deze prioriteitsvolgorde
# (afwijkend van gs_realestate.py) — bij live-test bleek een listing als
# "Ruime nieuwbouwvilla MET APPARTEMENT en zeezicht" anders fout op
# "apartment" te matchen puur omdat het bijgebouwde inwoonappartement in de
# titel wordt genoemd, terwijl de listing zelf overduidelijk een villa is
# (villa/woning/huis in de titel wint dan terecht van een bijgebouw-vermelding).
TYPE_KEYWORDS = (
    ("commercial", ("commercieel", "bedrijfspand", "warehouse", "kantoorpand", "winkelpand")),
    ("land", ("kavel", "bouwgrond", "perceel", "lot")),
    ("house", ("villa", "woning", "huis", "resort", "bungalow", "starterswoning")),
    ("apartment", ("appartement", "studio", "penthouse", "complex")),
)

# Nederlandse samenstellingen ("nieuwbouwVILLA", "koopWONING") plakken het
# kernwoord vast aan een voorvoegsel zonder spatie — een reguliere \bvilla\b
# mist die dan (geen woordgrens vóór "villa" binnen "nieuwbouwvilla"). Voor
# deze twee kernwoorden daarom alleen een grens AAN HET EIND vereisen. "huis"
# blijft bewust wél aan BEIDE kanten strikt (\bhuis\b) — dat woord zit ook
# als substring in "thuis"/"verhuisd", een losse eind-grens zou daar alsnog
# fout op matchen.
LOOSE_SUFFIX_WORDS = {"villa", "woning"}


def _word_matches(haystack: str, word: str) -> bool:
    if word in LOOSE_SUFFIX_WORDS:
        return re.search(re.escape(word) + r"\b", haystack) is not None
    return re.search(r"\b" + re.escape(word) + r"\b", haystack) is not None

PRICE_RE = re.compile(r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\s*([\d][\d.,]{1,14})", re.I)
STATUS_RE = re.compile(r'ere__loop-property-status-item ([a-z-]+)"')
LPI_RE = re.compile(r'ere__lpi-value">([^<]*)</span>\s*<span class="ere__lpi-label">([^<]*)')
GALLERY_RE = re.compile(
    r'property-gallery-item ere-light-gallery"[^>]*>\s*<img[^>]*src="([^"]+)"'
)
EUR_TO_XCG = 1.95


class CuracaoHousesScraper(BaseScraper):
    source_name = "curacao_houses"
    AGENT_COMPANY = "Curaçao Houses"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [
            u for u in urls
            if "/property/" in u and u.rstrip("/") != "https://www.curacaohouses.com/property"
        ]
        self.logger.info(f"Curaçao Houses: {len(urls)} listing-URL('s) in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Curaçao Houses: {len(results)} actieve Curaçao-listings")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None
        page_html = str(soup)

        title_tag = soup.find("title")
        raw_title = title_tag.get_text() if title_tag else ""
        if BONAIRE_RE.search(raw_title):
            return None  # buiten scope — Bonaire, niet Curaçao

        if SOLD_TEXT_RE.search(raw_title):
            return None  # statusklasse kan achterlopen, titel-tekst wint

        status_classes = set(STATUS_RE.findall(page_html))
        if not (status_classes & ACTIVE_CLASSES):
            return None
        listing_type = "rent" if (status_classes & RENT_CLASSES) else "sale"

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title and title_tag:
            title = self.clean_text(raw_title.split(" - ")[0])
        if not title:
            return None

        description = None
        desc_block = soup.find(class_="ere__single-property-description") or soup.find(
            class_="ere__single-property-content"
        )
        if desc_block:
            description = self.clean_text(desc_block.get_text(" "))
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        # EERST alleen op de titel matchen (schone, korte tekst) — pas als de
        # titel niets oplevert terugvallen op de vrije beschrijvingstekst.
        # Bekende valkuil (ook al eens gezien bij Vastiva): de beschrijving
        # bevat vaak een kenmerken-regel als "Kavel: circa 1.000 m2" die
        # gewoon de perceelgrootte van een doodgewone VILLA aangeeft, geen
        # signaal dat de listing zelf een los stuk grond is — op de volledige
        # tekst matchen gaf zo'n listing dus ten onrechte "land" i.p.v. "house".
        title_haystack = unicodedata.normalize("NFKD", title).lower()
        full_haystack = unicodedata.normalize("NFKD", title + " " + (description or "")).lower()
        property_type = "house"
        matched = False
        for ptype, words in TYPE_KEYWORDS:
            if any(_word_matches(title_haystack, w) for w in words):
                property_type = ptype
                matched = True
                break
        if not matched:
            for ptype, words in TYPE_KEYWORDS:
                if any(_word_matches(full_haystack, w) for w in words):
                    property_type = ptype
                    break

        lpi = {label.strip().lower(): value.strip() for value, label in LPI_RE.findall(page_html)}
        external_id = lpi.get("property id") or url.rstrip("/").split("/")[-1]

        bedrooms = None
        for key in ("bedroom", "bedrooms", "beds"):
            if key in lpi:
                bedrooms = self.parse_int(lpi[key])
                break
        bathrooms = None
        for key in ("bathroom", "bathrooms", "baths"):
            if key in lpi:
                bathrooms = self.parse_int(lpi[key])
                break

        price, currency = None, "XCG"
        m = re.search(
            r'ere__single-property-price">(.*?)<div class="ere__loop-property-status',
            page_html, re.S,
        )
        price_text = self.clean_text(re.sub(r"<[^>]+>", " ", m.group(1))) if m else None
        if price_text:
            pm = PRICE_RE.search(price_text)
            if pm:
                cur_raw = re.sub(r"\s+", "", pm.group(1)).upper()
                amount = self.parse_price(pm.group(2))
                if amount:
                    if cur_raw in ("EURO", "EUR", "€"):
                        price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                    elif cur_raw in ("US$", "USD", "$"):
                        price, currency = amount, "USD"
                    else:
                        price, currency = amount, "XCG"
            else:
                amount = self.parse_price(price_text)
                if amount:
                    price, currency = amount, "XCG"

        neighborhood = None

        images = self.clean_images(GALLERY_RE.findall(page_html))

        return Listing(
            source_id=self.source_id,
            external_id=str(external_id),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=None,
            neighborhood=neighborhood,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
