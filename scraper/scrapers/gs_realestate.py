"""GS Real Estate B.V. scraper (priority 8)
Site: https://www.gs-realestate.com — WordPress + "Essential Real Estate" (ERE)-plugin
(nieuwe plugin-familie in deze scraper-set, herkenbaar aan `ere__`-CSS-classes en een
eigen `property-sitemap.xml`). Standaard hosting, robots.txt staat alles toe (geen
ClaudeBot/AI-crawler-disallow).

Methode:
  1. Lijst uit `/property-sitemap.xml` (31 URL's, waarvan 1 de kale archiefpagina zelf is
     → 30 echte listings).
  2. **Statusfilter (zesde variant in deze scraper-set): een listing kan MEERDERE
     status-tags tegelijk hebben** (`<span class="ere__loop-property-status-item
     KLASSE">`) — bv. "commercieel" (een categorie-tag, geen beschikbaarheidsstatus) ÉN
     "for-sale" naast elkaar op dezelfde listing. Een simpele "pak de eerste
     status-klasse"-aanpak gaf dus een fout beeld (die listing leek "Commercieel" =
     onbekende status, i.p.v. gewoon actief te koop). Oplossing: alle status-klassen op de
     pagina verzamelen en controleren of er een BEKENDE actieve klasse tussen zit
     (verhuur/for-rent/te-huur/verkoop/for-sale/te-koop) — ontbreekt die, dan is de listing
     verkocht/verhuurd/onbekend en wordt hij overgeslagen. Van de 30 listings in de
     steekproef waren er maar 6 actief (4× verhuur, 1× for-rent, 1× for-sale/commercieel) —
     de rest droeg expliciete "sold"/"rented"/"just-sold"/"verkocht"/"verhuurd"-klassen, en
     één listing (`hanenberg`) had zelfs GEEN status-tag meer maar wél "VERKOCHT!" in de
     losse `<title>`-tag — pakt de "vereist een bekende actieve klasse"-aanpak vanzelf ook
     goed (geen actieve klasse aanwezig → overgeslagen, geen aparte titel-check nodig).
  3. Kerndata (Property ID/bedrooms/bathrooms) staat in nette `ere__lpi-value`/
     `ere__lpi-label`-paren; bedrooms/bathrooms zijn er lang niet altijd (leeg bij een deel
     van de actieve listings — data-kwaliteit van de bron, geen scraper-bug).
  4. Prijs staat in `ere__single-property-price` (bv. "XCG700", "XCG2.500.000") — altijd al
     native XCG bij deze site (geen EUR/USD-varianten gezien op de actieve listings, wel op
     enkele verkochte — voor de zekerheid toch dezelfde valuta-detectie als bij
     Domicilie/PriceMatch).
  5. Adres/land-velden (`ere__single-property-address`) stonden bij alle actieve listings in
     de steekproef leeg — geen coördinaten, geen adres, dus `neighborhood`/`latitude`/
     `longitude` blijven meestal `None` (zelfde patroon als Domicilie/NH Real Estate).
  6. Foto's: `<div class="property-gallery-item ere-light-gallery">` bevat telkens één
     `<img src=...>` — regex haalt de src-waardes eruit (geen background-image-stijl zoals
     bij Domicilie).
"""
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

SITEMAP = "https://www.gs-realestate.com/property-sitemap.xml"

RENT_CLASSES = {"verhuur", "for-rent", "te-huur"}
SALE_CLASSES = {"verkoop", "for-sale", "te-koop"}
ACTIVE_CLASSES = RENT_CLASSES | SALE_CLASSES

# Let op: elke listing-beschrijving eindigt met dezelfde contactfooter ("... of bezoek
# ons op kantoor aan de Santa Rosaweg") — "kantoor" (office) is dus GEEN bruikbaar
# commercial-keyword, die matcht op vrijwel elke listing. Losse korte woorden als "lot"/
# "terrein" matchen bovendien als kale substring op Nederlandse woorden (bv. "lot" in
# "afgesloten") — vandaar \b-word-boundary matching i.p.v. "in"-substring-check.
TYPE_KEYWORDS = (
    ("commercial", ("commercieel", "investerings object", "bedrijfspand", "warehouse", "kantoorpand", "winkelpand")),
    ("apartment", ("appartement", "studio", "penthouse", "complex")),
    ("land", ("kavel", "bouwgrond", "perceel", "onbebouwd terrein")),
    ("house", ("villa", "woning", "huis", "resort", "bungalow")),
)

PRICE_RE = re.compile(r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\s*([\d][\d.,]{1,14})", re.I)
STATUS_RE = re.compile(r'ere__loop-property-status-item ([a-z-]+)"')
LPI_RE = re.compile(r'ere__lpi-value">([^<]*)</span>\s*<span class="ere__lpi-label">([^<]*)')
GALLERY_RE = re.compile(
    r'property-gallery-item ere-light-gallery"[^>]*>\s*<img[^>]*src="([^"]+)"'
)
EUR_TO_XCG = 1.95


class GSRealEstateScraper(BaseScraper):
    source_name = "gs_realestate"
    AGENT_COMPANY = "GS Real Estate B.V."

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
            if "/property/" in u and u.rstrip("/") != "https://www.gs-realestate.com/property"
        ]
        self.logger.info(f"GS Real Estate: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"GS Real Estate: {len(results)} actieve listings")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None
        page_html = str(soup)

        status_classes = set(STATUS_RE.findall(page_html))
        if not (status_classes & ACTIVE_CLASSES):
            return None  # verkocht/verhuurd/onbekend — geen bekende actieve status-tag
        listing_type = "rent" if (status_classes & RENT_CLASSES) else "sale"

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title:
            title_tag = soup.find("title")
            title = self.clean_text(title_tag.get_text().split(" - ")[0]) if title_tag else None
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

        # De titel is bij deze site vaak alleen een locatienaam ("Mon Repos", "Banda
        # Abou") zonder woningtype — het type staat meestal alleen in de beschrijving
        # ("dit appartement", "goed onderhouden woning"), dus die moet mee in de haystack.
        # Sommige beschrijvingen gebruiken vetgedrukte Unicode-mathematische letters
        # als marketing-opmaak (bv. "𝐀𝐩𝐩𝐚𝐫𝐭𝐞𝐦𝐞𝐧𝐭" i.p.v. gewone ASCII-tekens) — die matchen
        # niet op een kale regex zonder NFKD-normalisatie eerst.
        haystack = unicodedata.normalize("NFKD", title + " " + (description or "")).lower()
        property_type = "house"
        for ptype, words in TYPE_KEYWORDS:
            if any(re.search(r"\b" + re.escape(w) + r"\b", haystack) for w in words):
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

        # Niet altijd een tweede </span> (postfix, bv. "/ per maand") na de prijs — bij
        # een kale prijs zonder postfix volgt direct de status-<div>. Vangen tot die
        # marker i.p.v. een vast aantal sluit-tags, anders mist de prijs stelselmatig.
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

        # Adresveld bevat bij deze site alleen generieke "Country"/"City"-waardes
        # ("Netherlands Antilles" / "Willemstad" — vrijwel elke listing) i.p.v. een
        # specifieke buurtnaam, dus niet bruikbaar als neighborhood.
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
