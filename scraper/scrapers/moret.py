"""Moret Real Estate scraper (priority 8)
Site: https://moretrealestate.com — WordPress, thema "wpestate" (WP Estate),
gewone Apache-hosting (géén WordPress.com/WPCloud-signalen, dus geen bekend
GH Actions-IP-blokkaderisico). robots.txt: alles toegestaan, geen crawl-delay.

Methode (geen REST API voor properties — wpestate registreert dat niet):
  1. HTML-crawl van 6 categoriepagina's (elk met "koop"/"huur" +
     woningtype vast), gepagineerd tot een pagina 0 nieuwe listings geeft:
       huizen-te-koop / koop-appartement / terreinen-te-koop  -> sale
       huizen-te-huur / huurappartementen / kantoorruimtes-te-huur -> rent
     Elke kaart (`div.listing_wrapper[data-listid]`) geeft al titel, url,
     prijs (native XCG of USD, geen omrekening nodig), slaapkamers,
     badkamers, oppervlak en wijk/stad — genoeg om zonder detailpagina al
     een compleet record te bouwen.
  2. Overlap-check (9 aug): de som van deze 6 categorieën komt nagenoeg
     exact overeen met de bredere "kies/kopen" + "kies/huren-nl" overzichten
     (35 koop + 38 huur) — dus deze indeling dekt de volledige actieve
     catalogus, met meteen het juiste woningtype per listing.
  3. Per uniek listing (dedup op listid) één keer de detailpagina voor
     verrijking: omschrijving (`#property_description`), coördinaten
     (`data-cur_lat`/`data-cur_long` op de kaart-container), en de volledige
     fotogalerij (alle `wp-content/uploads/...` img-links, logo/favicon
     worden door `clean_images` gefilterd).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://moretrealestate.com"
MAX_PAGES_PER_CATEGORY = 15

# (slug, listing_type, property_type) — meest specifieke categorie EERST:
# de site tagt sommige appartementen dubbel (ook onder "huizen-te-koop"/
# "-te-huur"), dedup op listid houdt de eerste match aan dus de specifieke
# apartment/land/commercial-categorieën moeten vóór de generieke huis-
# categorieën staan, anders krijgt zo'n appartement ten onrechte "house".
CATEGORIES = [
    ("woningen/koop-appartement", "sale", "apartment"),
    ("kies/huurappartementen", "rent", "apartment"),
    ("kies/terreinen-te-koop", "sale", "land"),
    ("kies/kantoorruimtes-te-huur", "rent", "commercial"),
    ("kies/huizen-te-koop", "sale", "house"),
    ("kies/huizen-te-huur", "rent", "house"),
]

# Prijsformaat is inconsistent — soms "XCG 475.000", soms "559.000 USD" —
# dus beide volgordes proberen, valutacode-eerst als voorkeur.
PRICE_CUR_FIRST = re.compile(r"(XCG|USD|ANG|NAF)\s*([\d.,]+)", re.I)
PRICE_AMOUNT_FIRST = re.compile(r"([\d.,]+)\s*(XCG|USD|ANG|NAF)\b", re.I)
# Sommige listings tonen EUR i.p.v. XCG/USD (geen valutacode maar het woord
# "euro") — omgerekend naar XCG met dezelfde koers als remax.py/century21.py.
EUR_RE = re.compile(r"([\d.,]+)\s*eur[o]?\b", re.I)
EUR_TO_XCG = 1.95


class MoretScraper(BaseScraper):
    source_name = "moret"
    AGENT_COMPANY = "Moret Real Estate"

    def scrape(self) -> list[Listing]:
        seen: dict[str, Listing] = {}

        for slug, listing_type, property_type in CATEGORIES:
            page = 1
            while page <= MAX_PAGES_PER_CATEGORY:
                url = f"{BASE}/{slug}/" if page == 1 else f"{BASE}/{slug}/page/{page}/"
                soup = self.get(url)
                if soup is None:
                    break
                cards = soup.find_all("div", class_="listing_wrapper")
                if not cards:
                    break
                new_count = 0
                for card in cards:
                    listid = card.get("data-listid")
                    if not listid or listid in seen:
                        continue
                    l = self._build_from_card(card, listing_type, property_type)
                    if l:
                        seen[listid] = l
                        new_count += 1
                if new_count == 0:
                    break
                page += 1

        results = list(seen.values())
        self.logger.info(f"Moret Real Estate: {len(results)} actieve listings — detailpagina's ophalen")
        for l in results:
            try:
                self._enrich(l)
            except Exception as e:
                self.logger.warning(f"Enrich error ({l.external_id}): {e}")
        return results

    def _build_from_card(self, card, listing_type, property_type) -> Listing | None:
        link_tag = card.find("h4")
        a = link_tag.find("a") if link_tag else None
        if not a or not a.get("href"):
            return None
        url = a["href"].strip()
        title = self.clean_text(a.get_text())
        if not title:
            return None

        listid = card.get("data-listid")

        loc = card.select_one(".property_location_image")
        neighborhood = None
        if loc:
            loc_links = loc.find_all("a")
            if loc_links:
                neighborhood = self.clean_text(loc_links[0].get_text())

        price_wrap = card.select_one(".listing_unit_price_wrapper")
        price, currency = None, "XCG"
        if price_wrap:
            price_text = price_wrap.get_text(" ")
            m = PRICE_CUR_FIRST.search(price_text) or PRICE_AMOUNT_FIRST.search(price_text)
            if m:
                g1, g2 = m.group(1), m.group(2)
                # groep-volgorde hangt af van welk patroon matchte — het
                # cijfergedeelte herkennen aan een startdigit
                amount_str, cur = (g1, g2) if g1[0].isdigit() else (g2, g1)
                cur = cur.upper()
                currency = "USD" if cur == "USD" else "XCG"
                price = self.parse_price(amount_str)
            else:
                m = EUR_RE.search(price_text)
                if m:
                    price_eur = self.parse_price(m.group(1))
                    price = round(price_eur * EUR_TO_XCG, 2) if price_eur else None
                    currency = "XCG"

        bedrooms = bathrooms = None
        area_sqm = None
        room = card.select_one(".inforoom")
        if room:
            bedrooms = self.parse_int(room.get_text())
        bath = card.select_one(".infobath")
        if bath:
            bathrooms = self.parse_int(bath.get_text())
        size = card.select_one(".infosize")
        if size:
            area_sqm = self.parse_area(size.get_text())

        return Listing(
            source_id=self.source_id,
            external_id=str(listid or url),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=url,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood=neighborhood,
            agent_company=self.AGENT_COMPANY,
        )

    def _enrich(self, l: Listing) -> None:
        soup = self.get(l.url)
        if not soup:
            return

        desc_div = soup.find(id="property_description")
        if desc_div:
            paragraphs = desc_div.find_all("p")
            text = " ".join(p.get_text(" ") for p in paragraphs) if paragraphs else desc_div.get_text(" ")
            l.description = self.clean_text(text)

        page_html = str(soup)
        m = re.search(r'data-cur_lat="([\-\d.]+)"\s*data-cur_long="([\-\d.]+)"', page_html)
        if m:
            try:
                l.latitude = float(m.group(1))
                l.longitude = float(m.group(2))
            except ValueError:
                pass

        images = []
        for img_a in soup.find_all("a", href=True):
            href = img_a["href"]
            if "/wp-content/uploads/" in href and re.search(r"\.(jpe?g|png|webp)$", href, re.I):
                images.append(href)
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if "/wp-content/uploads/" in src and re.search(r"\.(jpe?g|png|webp)$", src, re.I):
                images.append(src)
        l.images = self.clean_images(images)
