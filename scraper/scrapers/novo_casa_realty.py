"""Novo Casa Realty scraper (priority 8)
Site: https://novocasarealty.com — WordPress + "WP Residence"-thema (`wpresidence`-
referenties, `estate_property`-CPT). NIEUWE thema-familie in deze scraper-set. Standaard
hosting, robots.txt staat alles toe (geen ClaudeBot/AI-crawler-disallow, geen crawl-delay).

Methode:
  1. Lijst uit `/estate_property-sitemap.xml` (~34 URL's). Geen CPT in de WP REST API
     (`wp-json/wp/v2/estate_property` → 404) — dus HTML-detailpagina's parsen.
  2. **Status: een schoon status-"ribbon" element boven elke galerij**
     (`<div class="slider-property-status horizontalstatus ribbon-wrapper-XXX XXX">LABEL
     </div>`) — negende variant in deze scraper-set, en net als Cur-Estates een POSITIEF
     geval (geen tekst-speurwerk nodig). Waarden gezien: "For Sale", "For Rent",
     "Under Contract", "SOLD". Alleen "For Sale"/"For Rent" tellen als actief — "Under
     Contract" en "SOLD" worden overgeslagen (een aparte `property_status`-taxonomie-
     archiefpagina bevestigt dit patroon, maar de taxonomie-archieven zijn niet compleet
     voor alle 34 listings — de ribbon op de detailpagina zelf is de betrouwbare bron).
     "Under Construction" komt NIET als eigen ribbon-waarde voor (een listing die zowel
     in de for-sale- als de under-construction-taxonomie-archiefpagina stond, had gewoon
     "For Sale" als ribbon) — dus geen aparte behandeling nodig.
  3. **Regio-filter: het "Country"-veld is hier ONBETROUWBAAR** — een Sint Maarten-listing
     had toch `Country: Curacao` staan (bron-typefout/kopieerfout, geen scraper-bug). Het
     `State/County`-veld in dezelfde `listing_detail`-rij is wél betrouwbaar (Panama,
     Colombia, Netherlands, Sint Maarten gezien naast Curaçao/Curacao) — dat veld gebruiken
     om buiten-eiland-listings uit te sluiten. Een enkele listing had geen State/County-
     veld ingevuld maar wél een herkenbare Curaçao-buurtnaam (Santa Maria) — bij ontbrekend
     veld dus NIET uitsluiten, alleen bij een expliciet ander land/eiland in dat veld.
  4. **Prijs — 3 fallback-lagen zoals eerder vermoed, maar goedkoper dan verwacht:** de
     `price_area`-div (`<span class="price_label price_label_before">PREFIX</span> BEDRAG
     <span class="price_label">SUFFIX</span>`) bevat bij de meeste listings een nette
     "XCG 2.250.000"/"EUR  775.000"/"USD  395.000". Bij een deel van de listings staat er
     ECHTER een vrije marketing-zin IN diezelfde `price_label_before`-span in plaats van
     een schone valuta+bedrag ("Starting at USD$ 273,000") — de generieke valuta-regex
     matcht dat toevallig ook goed (pakt "USD" + "273,000"), dus geen aparte laag nodig
     voor dat geval. Bij een aantal listings (bv. hotel-apartments zonder vermelde prijs)
     is de hele `price_area`-div leeg — dan een fallback-zoektocht op de vrije platte
     paginatekst naar "Starting (at|from) ... (USD|EUR|US\\$|\\$) ... BEDRAG" of een los
     "Price: VALUTA BEDRAG"-label. Blijft dat ook leeg: `price=None` opslaan (listing zelf
     blijft bruikbaar), niet overslaan.
  5. Bedrooms/bathrooms uit de `listing_detail`-rijen (`Bedrooms:`/`Bathrooms:`). Bathrooms
     kan een halve badkamer zijn ("3.5") — **bekende valkuil: `kas_listings.bathrooms` is
     een integer-kolom** — hier expliciet afronden (`round(float(...))`) i.p.v. de generieke
     `parse_int` (die zou "3.5" toch al afkappen tot 3, maar afronden is correcter dan
     afkappen bij "3.5" → 4 i.p.v. 3... eigenlijk wiskundig identiek dicht bij elkaar, maar
     rond expliciet i.p.v. impliciet af zodat een "3.9"-waarde niet per ongeluk naar 3
     afgekapt wordt).
  6. area_sqm: voorkeur voor "Build area size (m2)"/"Property Size" (woonoppervlak), anders
     terugvallen op "Property Lot Size"/"Lot size (m2)" (kaveloppervlak).
  7. Geen bruikbare per-listing coördinaten — het enige lat/lng-paar op de pagina
     (`hq_latitude`/`hq_longitude`) is het HOOFDKANTOOR-adres van de makelaar, niet van de
     listing (zelfde valkuil als eerder gedocumenteerd voor andere sites). `latitude`/
     `longitude` blijven `None`.
  8. Property-type: geen bruikbare categorie-veld op de pagina (de `property_categs`-div
     bevat adresinfo, geen categorie) — keyword-detectie op titel + URL-slug, met
     `\\b`-word-boundary-regex.
  9. Afbeeldingen: `background-image:url(...)`-stijlen in de galerij-thumbnails — dezelfde
     resolutie-variant-namen (`-835x467`/`-1110x623`) als andere WordPress-thema's, dus
     `clean_images()` dedupt ze vanzelf naar de grootste variant.
  10. external_id: WordPress-post-ID uit `<body class="... postid-NNNNN ...">` — betrouwbaar
      aanwezig op elke detailpagina.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

SITEMAP = "https://novocasarealty.com/estate_property-sitemap.xml"

RIBBON_RE = re.compile(r'ribbon-wrapper-([A-Za-z-]+) [A-Za-z-]+">([^<]*)</div>')
POSTID_RE = re.compile(r'\bpostid-(\d+)\b')
PRICE_AREA_RE = re.compile(r'<div class="price_area">(.*?)</div>', re.S)
IMG_RE = re.compile(r'background-image:url\(([^)]+)\)')

# Niet-Curaçao regio's die in het State/County-veld zijn gezien (case-insensitive substring).
OUT_OF_SCOPE_REGIONS = (
    "panama", "colombia", "netherlands", "nederland", "sint maarten", "st maarten",
    "st. maarten", "st-maarten", "aruba", "bonaire",
)

CURRENCY_RE = re.compile(
    r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\s*([\d][\d.,]{1,14})", re.I
)
EUR_TO_XCG = 1.95

TYPE_KEYWORDS = (
    ("commercial", ("office", "warehouse", "retail", "commercial", "business center", "industrial", "party center")),
    ("land", ("lot", "land", "hectare", "acre", "kavel")),
    ("apartment", ("apartment", "apartments", "condo", "condos", "penthouse", "residencies", "residence", "studio")),
    ("house", ("villa", "house", "home", "eco lodge", "estate", "finca")),
)
# Generieke spec-labels die in bijna elke beschrijving voorkomen ("Lot Size: 900 m2" op
# een gewoon woonhuis, "Office space to work from home" als amenity op een appartement)
# en dus een valse trigger geven als de volledige beschrijving in één keer gescand wordt.
# Daarom eerst ALLEEN de titel proberen (waar "Lot for Sale ..."/"Office Space in ..."
# een betrouwbaar signaal is) en pas bij géén titelmatch terugvallen op titel+beschrijving.


class NovoCasaRealtyScraper(BaseScraper):
    source_name = "novo_casa_realty"
    AGENT_COMPANY = "Novo Casa Realty"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc><!\[CDATA\[([^\]]+)\]\]></loc>", r.text)
        urls = [u for u in urls if "/properties/" in u]
        self.logger.info(f"Novo Casa Realty: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Novo Casa Realty: {len(results)} actieve listings")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None
        page_html = str(soup)

        m = RIBBON_RE.search(page_html)
        if not m:
            return None  # geen statusbadge gevonden — geen betrouwbare status, overslaan
        status_slug = m.group(1).lower()
        if status_slug == "for-sale":
            listing_type = "sale"
        elif status_slug == "for-rent":
            listing_type = "rent"
        else:
            return None  # Under-Contract / SOLD / andere onbekende status

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title:
            title_tag = soup.find("title")
            title = self.clean_text(title_tag.get_text().split(" - ")[0]) if title_tag else None
        if not title:
            return None

        # listing_detail key/value-rijen (Neighborhood, State/County, Country, Price,
        # Bedrooms, Bathrooms, Property Size, Property Lot Size, Build area size, ...)
        details: dict[str, str] = {}
        for dm in re.finditer(r'<div class="listing_detail[^"]*">(.*?)</div>', page_html, re.S):
            txt = re.sub(r"<[^>]+>", "|", dm.group(1))
            txt = re.sub(r"\|+", "|", txt).strip("|")
            if ":" in txt:
                key, _, val = txt.partition(":")
                key = key.strip().lower()
                val = val.strip(" |")
                if key and val and key not in details:
                    details[key] = val

        # Sommige State/County-waardes noemen zowel "Curaçao" als "Netherlands" (het
        # Koninkrijk-verband, bv. "Curaçao, Netherlands") — dat is GEEN buitenlandse
        # listing. Alleen uitsluiten als een out-of-scope regio genoemd wordt ZONDER
        # dat Curaçao/Curacao er ook bij staat.
        state_county = details.get("state/county", "").lower()
        mentions_curacao = "curaçao" in state_county or "curacao" in state_county
        if state_county and not mentions_curacao and any(r in state_county for r in OUT_OF_SCOPE_REGIONS):
            return None  # buiten Curaçao (State/County betrouwbaarder dan Country hier)

        description = None
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = self.clean_text(og_desc["content"])
        if not description:
            desc_block = soup.find(class_="property_description") or soup.find(class_="entry_content")
            if desc_block:
                description = self.clean_text(desc_block.get_text(" "))

        title_haystack = (title + " " + url).lower()
        full_haystack = (title_haystack + " " + (description or "")).lower()
        property_type = "house"
        matched = False
        for ptype, words in TYPE_KEYWORDS:
            if any(re.search(r"\b" + re.escape(w) + r"\b", title_haystack) for w in words):
                property_type = ptype
                matched = True
                break
        if not matched:
            for ptype, words in TYPE_KEYWORDS:
                if any(re.search(r"\b" + re.escape(w) + r"\b", full_haystack) for w in words):
                    property_type = ptype
                    break

        bedrooms = self.parse_int(details["bedrooms"]) if "bedrooms" in details else None
        bathrooms = None
        if "bathrooms" in details:
            bm = re.search(r"[\d.]+", details["bathrooms"])
            if bm:
                try:
                    bathrooms = round(float(bm.group()))
                except ValueError:
                    bathrooms = None

        area_sqm = None
        for key in ("build area size (m2)", "property size", "living area (m2)"):
            if key in details:
                area_sqm = self.parse_area(details[key] + " m2")
                break
        if area_sqm is None:
            for key in ("property lot size", "lot size (m2)"):
                if key in details:
                    area_sqm = self.parse_area(details[key] + " m2")
                    break

        neighborhood = details.get("neighborhood")

        price, currency = self._extract_price(details, page_html)

        pid = POSTID_RE.search(page_html)
        external_id = pid.group(1) if pid else url.rstrip("/").split("/")[-1]

        images = self.clean_images(IMG_RE.findall(page_html))

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
            area_sqm=area_sqm,
            neighborhood=neighborhood,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )

    def _extract_price(self, details: dict, page_html: str) -> tuple[float | None, str]:
        # Laag 1: price_area-div (prefix-span + bedrag + suffix-span) — dekt zowel nette
        # "XCG 2.250.000" als de vrije "Starting at USD$ 273,000"-variant, want de
        # valuta-regex zoekt gewoon overal in die tekst.
        pm = PRICE_AREA_RE.search(page_html)
        price_area_text = None
        if pm:
            price_area_text = self.clean_text(re.sub(r"<[^>]+>", " ", pm.group(1)))
        price, currency = self._match_currency(price_area_text)
        if price:
            return price, currency

        # Laag 2: het "Price:"-veld uit listing_detail (zelfde bron als price_area
        # meestal, maar soms staat het alleen hier en niet in de div).
        if "price" in details:
            price, currency = self._match_currency(details["price"])
            if price:
                return price, currency

        # Laag 3: vrije platte tekst — "Starting at/from ... BEDRAG" ergens in de pagina
        # (bv. in een losse alinea buiten price_area/listing_detail).
        text = self.clean_text(re.sub(r"<[^>]+>", " ", page_html), max_len=20000) or ""
        sm = re.search(
            r"Starting (?:at|from)\s*(XCG|ANG|EUR|EURO|€|USD|US\s*\$|\$)?\s*([\d][\d.,]{2,14})",
            text, re.I,
        )
        if sm:
            cur_raw = (sm.group(1) or "USD").strip()
            amount = self.parse_price(sm.group(2))
            if amount:
                return self._normalize_currency(cur_raw, amount)

        return None, "XCG"

    def _match_currency(self, text: str | None) -> tuple[float | None, str]:
        if not text:
            return None, "XCG"
        cm = CURRENCY_RE.search(text)
        if not cm:
            return None, "XCG"
        amount = self.parse_price(cm.group(2))
        if not amount:
            return None, "XCG"
        return self._normalize_currency(cm.group(1), amount)

    def _normalize_currency(self, cur_raw: str, amount: float) -> tuple[float, str]:
        cur = re.sub(r"\s+", "", cur_raw).upper()
        if cur in ("EURO", "EUR", "€"):
            return round(amount * EUR_TO_XCG, 2), "XCG"
        if cur in ("US$", "USD", "$"):
            return amount, "USD"
        return amount, "XCG"
