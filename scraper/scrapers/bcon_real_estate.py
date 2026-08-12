"""B.CON Real Estate scraper
Site: https://realestatebconcuracao.com — WordPress + "Easy Real Estate"
(ER)-plugin (`es_`-taxonomy/CSS-prefix — LET OP: dit is een ANDERE plugin dan
de "Essential Real Estate" (ERE, `ere__`-prefix) familie van gs_realestate.py/
curacao_houses.py, ondanks de bijna identieke naam. Nieuw platformpatroon.

Bijzonderheden t.o.v. de gebruikelijke ERE/traditional-scrapers:
  1. **REST API werkt gewoon** (`/wp-json/wp/v2/properties`, 42 items in 1
     pagina bij per_page=100) — geen sitemap/HTML-crawl nodig voor de lijst.
  2. **`title.rendered` is bij ELKE listing leeg** — de titel zit als eerste
     `<p>`-paragraaf in `content.rendered` (WYSIWYG-vrije-tekst-invoer, geen
     los titelveld). Titel = eerste niet-lege paragraaftekst.
  3. **Geen los prijsveld** — prijs zit ook los ergens in de vrije
     `content.rendered`-tekst, meestal (niet altijd) op een regel als
     "Asking Price: Cg 1.396.000" / "Huurprijs: XCG 4.500 per maand" /
     "ANG 395,000". "Cg" (zonder punt) is hier ook een XCG-synoniem, net als
     ANG/NAF/ƒ elders in deze scraper-set. Bij geen match: geen prijs (zoals
     Wigbold's "On request"), niet blokkerend.
  4. **Taxonomie-filtering via `es_statuses`/`es_types` i.p.v. CSS-classes**:
     status 21 = AVAILABLE, 22 = NOT AVAILABLE (alleen 21 meenemen). Type 19 =
     RENT, 20 = SALE, 32 = VACATION RENTAL (bewust NIET meenemen — korte-
     termijn-verhuur, geen aggregator-scope, prijzen ($49/nacht) zijn ook
     evident per-nacht-tarieven i.p.v. langetermijnprijzen).
  5. **Foto's via een apart media-endpoint** (`/wp-json/wp/v2/media?parent=<id>`)
     — `featured_media` staat op elke listing op None, dus de featured-media-
     embed levert niks op; de losse media-per-post-query wel (8 foto's bij een
     steekproef).
  6. Van de 42 totaal-items zijn er 20 `AVAILABLE` + `rent`/`sale` (niet
     vacation-rental) — een gezonde actieve set voor een nieuwe scraper.
"""
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

API_BASE = "https://realestatebconcuracao.com/wp-json/wp/v2"
STATUS_AVAILABLE = 21
TYPE_RENT = 19
TYPE_SALE = 20
EUR_TO_XCG = 1.95

PRICE_RE = re.compile(
    r"(CG|XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\.?\s*([\d][\d.,]{1,14})", re.I
)

TYPE_KEYWORDS = (
    ("commercial", ("commercial", "business", "warehouse", "office space", "shop",
                     "bedrijfspand", "kantoorpand", "winkelpand")),
    ("land", ("lot", "kavel", "bouwgrond", "perceel", "land for sale")),
    ("house", ("villa", "woning", "huis", "house", "bungalow", "resort")),
    ("apartment", ("apartment", "appartement", "studio", "penthouse", "duplex", "complex")),
)
# Woorden die vaak vastplakken aan een voorvoegsel ZONDER spatie
# ("nieuwbouwvilla", "koopwoning") — grens alleen aan het EIND vereisen
# (relaxed start-boundary).
LOOSE_START_WORDS = {"villa", "woning"}
# Woorden die in dit corpus ook als meervoud/verbogen vorm zonder spatie
# voorkomen ("appartementEN") — grens alleen aan het BEGIN vereisen
# (relaxed end-boundary), zodat een meervouds-suffix de match niet mist.
LOOSE_END_WORDS = {"appartement", "apartment", "kavel"}


def _word_matches(haystack: str, word: str) -> bool:
    start = "" if word in LOOSE_START_WORDS else r"\b"
    end = "" if word in LOOSE_END_WORDS else r"\b"
    return re.search(start + re.escape(word) + end, haystack) is not None


class BconRealEstateScraper(BaseScraper):
    source_name = "bcon_real_estate"
    AGENT_COMPANY = "B.CON Real Estate"

    def scrape(self) -> list[Listing]:
        items = self._fetch_all_properties()
        self.logger.info(f"B.CON Real Estate: {len(items)} items totaal via REST")

        results: list[Listing] = []
        for item in items:
            try:
                statuses = item.get("es_statuses") or []
                types = item.get("es_types") or []
                if STATUS_AVAILABLE not in statuses:
                    continue
                if TYPE_RENT in types:
                    taxonomy_type = "rent"
                elif TYPE_SALE in types:
                    taxonomy_type = "sale"
                else:
                    continue  # vacation-rental (32) of ongeclassificeerd

                l = self._parse_item(item, taxonomy_type)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Item error (id={item.get('id')}): {e}")

        self.logger.info(f"B.CON Real Estate: {len(results)} actieve rent/sale-listings")
        return results

    def _fetch_all_properties(self) -> list[dict]:
        try:
            r = self.session.get(f"{API_BASE}/properties?per_page=100", timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.logger.error(f"REST-lijst niet op te halen: {e}")
            return []

    def _parse_item(self, item: dict, taxonomy_type: str) -> Listing | None:
        post_id = item.get("id")
        url = item.get("link") or f"https://realestatebconcuracao.com/?p={post_id}"
        content_html = item.get("content", {}).get("rendered", "") or ""

        # Titel = eerste niet-lege <p>-paragraaf (los titelveld is altijd leeg).
        # Niet elke listing gebruikt nette <p>-tags (sommige zijn geplakt vanuit
        # Facebook/WhatsApp met kale <div>'s, of content is helemaal leeg) — in
        # die gevallen valt title terug op de <title>-tag van de detailpagina
        # zelf (zelfde fallback-keten als DMJ Makelaar: paragraaf -> title-tag).
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", content_html, re.S)
        clean_paragraphs = []
        for p in paragraphs:
            t = self.clean_text(re.sub(r"<[^>]+>", " ", p).replace("&nbsp;", " "))
            if t:
                clean_paragraphs.append(t)

        # full_text = platte tekst van de HELE content, ongeacht p/div-structuur
        # — gebruikt voor prijs/slaapkamer/badkamer-regex, robuuster dan alleen
        # de <p>-paragrafen (die kunnen ontbreken terwijl de tekst er wel is).
        full_text = self.clean_text(
            re.sub(r"<[^>]+>", " ", content_html).replace("&nbsp;", " ")
        ) or ""

        if clean_paragraphs:
            title = clean_paragraphs[0]
            description = self.clean_text(" ".join(clean_paragraphs[1:])) or None
        else:
            title = self._fetch_title_fallback(url)
            description = full_text or None
            if not title:
                return None

        price, currency = None, "XCG"
        pm = PRICE_RE.search(full_text)
        if pm:
            cur_raw = re.sub(r"\s+", "", pm.group(1)).upper()
            amount = self.parse_price(pm.group(2))
            if amount:
                if cur_raw in ("EURO", "EUR", "€"):
                    price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                elif cur_raw in ("US$", "USD", "$"):
                    price, currency = amount, "USD"
                else:
                    price, currency = amount, "XCG"  # CG/XCG/ANG/NAF/NAf/ƒ

        # De es_types-taxonomie op deze site is niet altijd betrouwbaar (1x
        # gezien: een listing getagd als SALE terwijl titel+tekst overduidelijk
        # "For rent"/"Rent price: ... p/m" zegt) — zelfde les als elders in
        # deze scraper-set: een titel/tekst-signaal wint van een taxonomie/
        # statusveld. Alleen overschrijven bij een ondubbelzinnig signaal (het
        # ene type wel genoemd, het andere niet); bij twijfel de taxonomie
        # gewoon vertrouwen.
        text_haystack = (title + " " + full_text).lower()
        has_rent_signal = any(s in text_haystack for s in ("for rent", "te huur", "rent price", "huurprijs"))
        has_sale_signal = any(s in text_haystack for s in ("for sale", "te koop", "asking price", "vraagprijs", "koopprijs"))
        if has_rent_signal and not has_sale_signal:
            listing_type = "rent"
        elif has_sale_signal and not has_rent_signal:
            listing_type = "sale"
        else:
            listing_type = taxonomy_type

        # Sanity-ondergrens voor huur: een enkele listing bleek getagd als
        # RENT (19) terwijl het overduidelijk een per-NACHT vakantietarief was
        # ("$83 a night") — dat hoort bij de al uitgesloten vacation-rental-
        # taxonomie (32), niet bij langetermijnhuur. Een huurprijs onder 200
        # (XCG of USD) is voor Curaçao geen realistische maandhuur.
        if listing_type == "rent" and price is not None and price < 200:
            return None

        bedrooms = None
        bm = re.search(r"(\d+)\s*bedroom", full_text, re.I) or re.search(r"(\d+)\s*slaapkamer", full_text, re.I)
        if bm:
            bedrooms = int(bm.group(1))
        bathrooms = None
        bam = re.search(r"(\d+(?:[.,]5)?)\s*bathroom", full_text, re.I) or re.search(r"(\d+(?:[.,]5)?)\s*badkamer", full_text, re.I)
        if bam:
            bathrooms = round(float(bam.group(1).replace(",", ".")))

        title_haystack = unicodedata.normalize("NFKD", title).lower()
        full_haystack = unicodedata.normalize("NFKD", full_text).lower()
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

        images = self._fetch_images(post_id)

        return Listing(
            source_id=self.source_id,
            external_id=str(post_id),
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
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )

    def _fetch_title_fallback(self, url: str) -> str | None:
        soup = self.get(url)
        if soup is None:
            return None
        title_tag = soup.find("title")
        if not title_tag:
            return None
        raw = title_tag.get_text()
        # Site-suffix " | Real Estate Curacao Bcon" eraf knippen.
        return self.clean_text(raw.split(" | Real Estate Curacao Bcon")[0])

    def _fetch_images(self, post_id) -> list[str]:
        try:
            r = self.session.get(f"{API_BASE}/media?parent={post_id}&per_page=40", timeout=30)
            r.raise_for_status()
            urls = [m.get("source_url") for m in r.json() if m.get("source_url")]
            return self.clean_images(urls)
        except Exception as e:
            self.logger.warning(f"Media-fetch mislukt voor id={post_id}: {e}")
            return []
