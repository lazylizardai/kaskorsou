"""NH Real Estate & Associates scraper (priority 8)
Site: https://curacao-houses.com — WordPress op WordPress.com/WPCloud
(`host-header: wpcloud` in de response headers) — ZELFDE hostingfamilie als
New Winds Realty, dat GitHub Actions-IP's hard blokkeert (429 op elke
request). Draait daarom NIET automatisch mee in de dagelijkse GH Actions-run
totdat een testrun vanaf een andere machine (bv. Mini PC) is bevestigd — zie
new_winds_realty.py voor hetzelfde patroon.
robots.txt: alles toegestaan, geen crawl-delay.

Methode:
  1. WPResidence-thema registreert de property custom post type WEL in de
     REST API (`/wp-json/wp/v2/estate_property`, rest_base `estate_property`)
     — geen HTML-crawl nodig voor de lijst. 96 posts, per_page=100 → 1 pagina.
  2. Taxonomieën property_status / property_action_category / property_category
     / property_area worden één keer opgehaald om ids naar namen te mappen.
     Actief = status NIET rented/sold/sold-recently/under-contract (for-sale,
     for-rent, new-listing, available, pricedrop blijven staan).
  3. listing_type via property_action_category (houses/commercial-for-rent
     vs -for-sale/lots-for-sale); property_type via property_category-slug
     (villa/house/bungalow → house; apartment/condo/duplexe/loft/resort →
     apartment; land/lot → land; industrial/office/retail → commercial).
  4. REST-content bevat GEEN losse prijs/bed/bath-velden (geen `meta`) —
     prijs staat als vrije tekst in de beschrijving ("Asking Price: XCG
     750,000,-" / "asking price for ... is 360.000,- XCG" / "€1.249.000" /
     "for EUR 700,000" / "Monthly Rent: XCG 2,950"). EUR wordt omgerekend
     ×1,95 naar XCG net als bij remax/century21/international_fine_living/
     moret. Sommige (vooral commerciële) listings tonen bewust "Price Upon
     Request" — die blijven gewoon staan met price=None.
  5. Slaapkamers/badkamers staan WEL gestructureerd, maar alleen op de
     detailpagina in de specs-strip (`>4 Bedrooms<` / `>4 Bathrooms<`), niet
     in de REST-payload. Galerij: WP REST media-endpoint per listing
     (`/wp-json/wp/v2/media?parent=<id>`) geeft alle aanhangsels — veel
     completer dan de raw HTML (die maar 1-2 losse afbeeldingen toont, de
     rest laadt via een JS-slider). Coördinaten: alleen de thema-default
     (New York, nooit aangepast) staat in de pagina — geen bruikbare
     per-listing lat/long, dus latitude/longitude blijven leeg.
"""
import html
import re
from ..base_scraper import BaseScraper
from ..models import Listing

EXCLUDE_STATUS_SLUGS = {"rented", "sold", "sold-recently", "under-contract"}
RENT_ACTION_SLUGS = {"houses-for-rent", "commercial-properties-for-rent"}

# volgorde belangrijk: specifiek → generiek
CATEGORY_TYPE_MAP = {
    "land": "land", "lot": "land",
    "industrial": "commercial", "office": "commercial",
    "retail": "commercial", "retail-listings": "commercial",
    "apartment": "apartment", "apartment-2": "apartment",
    "apartment-complex": "apartment", "condo": "apartment", "condos": "apartment",
    "duplexe": "apartment", "loft": "apartment", "resort": "apartment", "resorts": "apartment",
    "bungalow": "house", "bungalows": "house", "house": "house",
    "villa": "house", "villas": "house",
}

PRICE_CUR_FIRST = re.compile(r"(XCG|USD|ANG|NAF|NAf|EUR)\s*[:.,\-]{0,3}\s*([\d][\d.,]{2,})", re.I)
PRICE_AMOUNT_FIRST = re.compile(r"([\d][\d.,]{2,})[,.\-\s]{0,4}(XCG|USD|ANG|NAF|EUR)\b", re.I)
EUR_SYM = re.compile(r"€\s*([\d][\d.,]{2,})")
EUR_WORD = re.compile(r"([\d][\d.,]{2,})[,.\-\s]{0,4}(?:euro?s?)\b", re.I)
DOLLAR_SYM = re.compile(r"\$\s*([\d][\d.,]{2,})")
# Bedragen die vlak vóór de match dit soort woorden hebben zijn geen
# vraagprijs/huurprijs maar een maandelijkse bijdrage/borg — overslaan
# (bv. "Monthly resort fee: XCG 260,-" vóór de echte "€ 995.000,-" prijs).
PRICE_BLOCK_CONTEXT = re.compile(
    r"(?:fee|deposit|borg|association|hoa|maintenance|onderhoud)\W{0,25}$", re.I
)
BED_RE = re.compile(r">(\d+)\s*Bedrooms?<", re.I)
BATH_RE = re.compile(r">(\d+)\s*Bathrooms?<", re.I)
AREA_RE = re.compile(r"([\d][\d.,]{0,8})\s*(?:m²|m2|sq\.?\s*m\b|square meters?)", re.I)


class NHRealEstateScraper(BaseScraper):
    source_name = "nh_real_estate"
    BASE = "https://curacao-houses.com"
    AGENT_COMPANY = "NH Real Estate & Associates"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def _tax_map(self, tax: str) -> dict[int, dict]:
        out = {}
        try:
            for t in self._get_json(
                f"{self.BASE}/wp-json/wp/v2/{tax}?per_page=100&_fields=id,name,slug"
            ):
                out[t["id"]] = {"name": t["name"], "slug": t["slug"]}
        except Exception as e:
            self.logger.warning(f"Taxonomie {tax} niet opgehaald: {e}")
        return out

    def scrape(self) -> list[Listing]:
        actions = self._tax_map("property_action_category")
        statuses = self._tax_map("property_status")
        categories = self._tax_map("property_category")
        areas = self._tax_map("property_area")

        posts, page = [], 1
        while True:
            try:
                batch = self._get_json(
                    f"{self.BASE}/wp-json/wp/v2/estate_property?per_page=100&page={page}"
                    "&_fields=id,slug,link,title,content,modified,"
                    "property_status,property_action_category,property_category,property_area"
                )
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon estate_property-lijst niet ophalen: {e}")
                    return []
                break
            if not batch:
                break
            posts.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        results = []
        for p in posts:
            try:
                status_slugs = {
                    statuses.get(i, {}).get("slug") for i in p.get("property_status", [])
                }
                if status_slugs & EXCLUDE_STATUS_SLUGS:
                    continue  # verhuurd/verkocht/onder contract

                l = self._build(p, actions, categories, areas, status_slugs)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Post error ({p.get('id')}): {e}")

        self.logger.info(
            f"NH Real Estate: {len(results)} actieve listings — detailpagina's + media ophalen"
        )
        for l in results:
            try:
                self._enrich(l)
            except Exception as e:
                self.logger.warning(f"Enrich error ({l.external_id}): {e}")
        return results

    def _build(self, p, actions, categories, areas, status_slugs) -> Listing | None:
        title = self.clean_text(html.unescape(p["title"]["rendered"]))
        if not title:
            return None

        action_slugs = {
            actions.get(i, {}).get("slug") for i in p.get("property_action_category", [])
        }
        # property_action_category staat niet altijd ingevuld (bv. "Rooi
        # Catootje" heeft alleen property_status=for-rent) — dan die als
        # terugvaloptie gebruiken.
        if action_slugs:
            listing_type = "rent" if (action_slugs & RENT_ACTION_SLUGS) else "sale"
        else:
            listing_type = "rent" if "for-rent" in status_slugs else "sale"

        cat_slugs = [categories.get(i, {}).get("slug") for i in p.get("property_category", [])]
        property_type = "house"
        for slug in cat_slugs:
            if slug in CATEGORY_TYPE_MAP:
                property_type = CATEGORY_TYPE_MAP[slug]
                break

        neighborhood = None
        for i in p.get("property_area", []):
            name = areas.get(i, {}).get("name")
            if name:
                neighborhood = self.clean_text(html.unescape(name))
                break

        content_html = (p.get("content") or {}).get("rendered", "") or ""
        description = self.clean_text(
            html.unescape(re.sub(r"<[^>]+>", " ", content_html))
        )
        price, currency = self._parse_price_from_text(description or "")
        area_sqm = self._parse_area_from_text(description or "")

        return Listing(
            source_id=self.source_id,
            external_id=str(p["id"]),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=p["link"],
            description=description,
            neighborhood=neighborhood,
            area_sqm=area_sqm,
        )

    def _parse_price_from_text(self, text: str) -> tuple[float | None, str]:
        """Eerste valuta+bedrag-match die niet direct voorafgegaan wordt door
        een fee/borg/HOA-woord (bv. "Monthly resort fee: XCG 260,-" moet niet
        als vraagprijs gepakt worden als er verderop een echte "€ 995.000,-"
        staat)."""
        for pat, amt_i, cur_i in (
            (PRICE_CUR_FIRST, 2, 1),
            (PRICE_AMOUNT_FIRST, 1, 2),
        ):
            for m in pat.finditer(text):
                if PRICE_BLOCK_CONTEXT.search(text[max(0, m.start() - 30):m.start()]):
                    continue
                price = self.parse_price(m.group(amt_i))
                if price and price >= 100:
                    cur = m.group(cur_i).upper()
                    if cur == "EUR":
                        return round(price * 1.95, 2), "XCG"
                    return price, ("USD" if cur == "USD" else "XCG")
        for pat in (EUR_SYM, EUR_WORD):
            for m in pat.finditer(text):
                if PRICE_BLOCK_CONTEXT.search(text[max(0, m.start() - 30):m.start()]):
                    continue
                price = self.parse_price(m.group(1))
                if price and price >= 100:
                    return round(price * 1.95, 2), "XCG"
        for m in DOLLAR_SYM.finditer(text):
            if PRICE_BLOCK_CONTEXT.search(text[max(0, m.start() - 30):m.start()]):
                continue
            price = self.parse_price(m.group(1))
            if price and price >= 100:
                return price, "USD"
        return None, "XCG"

    def _parse_area_from_text(self, text: str) -> float | None:
        m = AREA_RE.search(text)
        if not m:
            return None
        raw = m.group(1)
        # laatste scheidingsteken gevolgd door 1-2 cijfers = decimaal
        # (zeldzaam, bv. "72,5 m²"), anders is elk scheidingsteken een
        # duizendtal-separator (bv. "1,100 m²" / "3.020 m²").
        dm = re.match(r"^(.*)[.,](\d{1,2})$", raw)
        if dm and len(re.sub(r"[^\d]", "", dm.group(1))) <= 3:
            whole = re.sub(r"[^\d]", "", dm.group(1))
            try:
                area = float(f"{whole}.{dm.group(2)}") if whole else None
            except ValueError:
                area = None
        else:
            digits = re.sub(r"[^\d]", "", raw)
            area = float(digits) if digits else None
        if area is not None and 5 <= area <= 200000:
            return area
        return None

    def _enrich(self, l: Listing) -> None:
        # Galerij via WP REST media-endpoint (completer dan de raw HTML,
        # die maar 1-2 losse afbeeldingen toont — de rest laadt via JS-slider).
        try:
            media = self._get_json(
                f"{self.BASE}/wp-json/wp/v2/media?parent={l.external_id}&per_page=100"
                "&_fields=source_url"
            )
            imgs = [m.get("source_url") for m in media if m.get("source_url")]
            if imgs:
                l.images = self.clean_images(imgs)
        except Exception as e:
            self.logger.warning(f"Media ophalen mislukt ({l.external_id}): {e}")

        soup = self.get(l.url)
        if not soup:
            return
        page_html = str(soup)

        m = BED_RE.search(page_html)
        if m:
            l.bedrooms = int(m.group(1))
        m = BATH_RE.search(page_html)
        if m:
            l.bathrooms = int(m.group(1))

        if l.price_ang is None:
            text = self.clean_text(soup.get_text(" ", strip=True), max_len=20000) or ""
            price, currency = self._parse_price_from_text(text)
            if price:
                l.price_ang, l.currency = price, currency

        l.agent_company = self.AGENT_COMPANY
