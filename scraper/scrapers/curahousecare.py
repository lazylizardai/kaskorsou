"""CuraHouseCare scraper (priority 8)
Site: https://curahousecare.com — WordPress (RealHomes-theme) op LiteSpeed-hosting
(géén WordPress.com/WPCloud, dus geen bekende reden voor GH Actions-IP-blokkade).
robots.txt: alles toegestaan, geen crawl-delay.

Methode:
  1. Lijst via WP REST: /wp-json/wp/v2/objecten (custom post type 'property',
     rest_base 'objecten'), 122 posts, per_page=100 → 2 pagina's.
  2. Taxonomieën property-statuses / property-types / property-cities worden
     één keer opgehaald om ids naar namen te mappen. Actief = "Te huur" /
     "Te koop"; Verhuurd/Verkocht/Onder bod/Onder contract worden overgeslagen.
  3. De REST-payload bevat GEEN prijs/slaapkamers (acf is leeg) — die staan
     alleen op de detailpagina: slaapkamers in de header-strip, prijs als
     vrije tekst in de beschrijving onder een "Prijzen …:"-kop
     ("De vraagprijs is 515.000 USD kosten koper" / "De huurprijs is 1950 XCG…"
     / "circa 72 m² vanaf XCG 2.250,- per maand"). Coördinaten staan als
     "lat"/"lng" in inline JSON, gallery-foto's als wp-content/uploads-URL's.

Let op: sommige listings tonen bewust géén prijs ("stille verkoop") — die
blijven gewoon staan met price=None, net als bij Keller Williams.
"""
import html
import re
from ..base_scraper import BaseScraper
from ..models import Listing

ACTIVE_STATUS_SLUGS = {"te-huur", "te-koop"}
RENT_STATUS_SLUGS = {"te-huur"}

# volgorde belangrijk: specifiek → generiek
TYPE_KEYWORDS = (
    ("apartment", ("appartement", "studio", "penthouse", "condo")),
    ("commercial", ("kantoor", "commercieel", "bedrijfs", "winkel", "horeca", "commercial")),
    ("land", ("kavel", "grond", "terrein", "bouwkavel", "land")),
    ("house", ("villa", "woning", "huis", "bungalow", "townhouse")),
)

PRICE_CURRENCY = r"(XCG|USD|ANG|NAF)"
# "1950 XCG" / "515.000 USD"
AMOUNT_FIRST = re.compile(r"([\d][\d.,]{2,})\s*" + PRICE_CURRENCY, re.I)
# "XCG 2.250,-" / "USD 515.000"
CURRENCY_FIRST = re.compile(PRICE_CURRENCY + r"\s*([\d][\d.,]{2,})", re.I)


class CuraHouseCareScraper(BaseScraper):
    source_name = "curahousecare"
    BASE = "https://curahousecare.com"
    AGENT_COMPANY = "CuraHouseCare"

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
        statuses = self._tax_map("property-statuses")
        types = self._tax_map("property-types")
        cities = self._tax_map("property-cities")

        posts, page = [], 1
        while True:
            try:
                batch = self._get_json(
                    f"{self.BASE}/wp-json/wp/v2/objecten?per_page=100&page={page}"
                    "&_fields=id,slug,link,title,content,modified,"
                    "property-statuses,property-types,property-cities"
                )
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon objecten-lijst niet ophalen: {e}")
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
                    statuses.get(i, {}).get("slug") for i in p.get("property-statuses", [])
                }
                if not (status_slugs & ACTIVE_STATUS_SLUGS):
                    continue  # verhuurd/verkocht/onder bod/onder contract/geen status

                l = self._build(p, status_slugs, types, cities)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Post error ({p.get('id')}): {e}")

        self.logger.info(
            f"CuraHouseCare: {len(results)} actieve listings — detailpagina's ophalen"
        )
        for l in results:
            try:
                self._enrich(l)
            except Exception as e:
                self.logger.warning(f"Enrich error ({l.external_id}): {e}")
        return results

    def _build(self, p, status_slugs, types, cities) -> Listing | None:
        title = self.clean_text(html.unescape(p["title"]["rendered"]))
        if not title:
            return None

        listing_type = "rent" if (status_slugs & RENT_STATUS_SLUGS) else "sale"

        type_names = " ".join(
            (types.get(i, {}).get("slug") or "") + " " + (types.get(i, {}).get("name") or "")
            for i in p.get("property-types", [])
        ).lower()
        haystack = type_names + " " + title.lower()
        property_type = "house"
        for ptype, words in TYPE_KEYWORDS:
            if any(w in haystack for w in words):
                property_type = ptype
                break

        neighborhood = None
        for i in p.get("property-cities", []):
            name = cities.get(i, {}).get("name")
            if name:
                neighborhood = self.clean_text(html.unescape(name))
                break

        content_html = (p.get("content") or {}).get("rendered", "") or ""
        description = self.clean_text(
            html.unescape(re.sub(r"<[^>]+>", " ", content_html))
        )
        price, currency = self._parse_price_from_text(description or "")

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
        )

    def _parse_price_from_text(self, text: str) -> tuple[float | None, str]:
        """Prijs uit vrije tekst. Voorkeur: de zin met huurprijs/vraagprijs,
        anders (in de 'Prijzen'-sectie) de eerste valuta+bedrag-combinatie."""
        scopes = []
        m = re.search(r"(?:huurprijs|vraagprijs|koopprijs)[^.]{0,120}", text, re.I)
        if m:
            scopes.append(m.group(0))
        m = re.search(r"Prijzen[^:]{0,80}:(.{0,400})", text, re.I | re.S)
        if m:
            scopes.append(m.group(1))
        scopes.append(text[:2000])

        for scope in scopes:
            for pat, amt_i, cur_i in ((AMOUNT_FIRST, 1, 2), (CURRENCY_FIRST, 2, 1)):
                mm = pat.search(scope)
                if mm:
                    price = self.parse_price(mm.group(amt_i))
                    if price and price >= 100:
                        cur = mm.group(cur_i).upper()
                        # ANG/NAf = zelfde waarde als XCG
                        return price, ("USD" if cur == "USD" else "XCG")
        return None, "XCG"

    def _enrich(self, l: Listing) -> None:
        soup = self.get(l.url)
        if not soup:
            return
        page_html = str(soup)

        # Slaapkamers uit de header-strip ("2&nbsp;Slaapkamers")
        m = re.search(r"(\d+)\s*(?:&nbsp;| |\s)*Slaapkamers", page_html)
        if m:
            l.bedrooms = int(m.group(1))
        m = re.search(r"(\d+)\s*(?:&nbsp;| |\s)*Badkamers", page_html)
        if m:
            l.bathrooms = int(m.group(1))

        # Oppervlakte alleen als expliciet vermeld in de tekst ("circa 72 m²")
        if l.area_sqm is None:
            m = re.search(r"(?:circa\s+)?(\d{2,4})\s*m(?:²|2)\b", page_html)
            if m:
                try:
                    area = float(m.group(1))
                    if 20 <= area <= 100000:
                        l.area_sqm = area
                except ValueError:
                    pass

        # Coördinaten uit inline JSON: "lat":"12.10..." (soms met backslashes)
        m = re.search(
            r'lat\\?["\']?\s*:\s*\\?["\']?(-?\d{1,2}\.\d+).{0,80}?'
            r'l(?:ng|on)\\?["\']?\s*:\s*\\?["\']?(-?\d{1,3}\.\d+)',
            page_html,
            re.S,
        )
        if m:
            lat, lng = float(m.group(1)), float(m.group(2))
            # sanity check: Curaçao
            if 11.9 <= lat <= 12.5 and -69.3 <= lng <= -68.6:
                l.latitude, l.longitude = lat, lng

        # Fotogalerij: alle uploads-afbeeldingen; clean_images() dedupt de
        # resolutie-varianten en filtert het logo eruit.
        imgs = re.findall(
            r'https://curahousecare\.com/wp-content/uploads/[^"\'\s\\]+\.(?:jpe?g|png|webp)',
            page_html,
        )
        if imgs:
            l.images = self.clean_images(imgs)

        # Prijs: als de REST-content niets opleverde, nogmaals op de
        # detailpagina-tekst proberen (zelfde tekst, maar voor de zekerheid).
        if l.price_ang is None:
            text = self.clean_text(soup.get_text(" ", strip=True), max_len=20000) or ""
            price, currency = self._parse_price_from_text(text)
            if price:
                l.price_ang, l.currency = price, currency

        l.agent_company = self.AGENT_COMPANY
