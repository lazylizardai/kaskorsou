"""PriceMatch Real Estate scraper (priority 8)
Site: https://pricematchrealestate.com — WordPress + "Houzez"-thema,
zelfde pluginfamilie als `domicilie.py` maar een ANDERE detailpagina-
template binnen Houzez ("property-detail-v3" i.p.v. Domicilie's "v4") —
compleet andere CSS-classes, dus geen hergebruik van de Domicilie-
selectors mogelijk. Hostinger/LiteSpeed-hosting, robots.txt staat alles
toe behalve `/wp-admin/`, `Sitemap: /wp-sitemap.xml`. Ook hier geen
wp-json-route voor het `property`-post-type (404 `rest_no_route`).

Methode:
  1. Volledige lijst uit `/wp-sitemap-posts-property-1.xml` (9 listings,
     geen paginering nodig).
  2. Per detailpagina staan de kernvelden in `div.detail-wrap ul.list-2-
     cols > li`, met `<strong>Label:</strong><span>Waarde</span>` als
     directe kinderen (waarde in een `<span>`-sibling i.p.v. los in de
     `<li>`-tekst zoals bij Domicilie) — label/waarde-dict gebouwd door
     de `<span>` te pakken i.p.v. de `<strong>` eruit te knippen.
  3. **In de steekproef van 9 listings stond GEEN enkele als verkocht/
     verhuurd gemarkeerd** — alle 9 waren "For Sale"/"For Rent"/"New
     Projects" (nieuwbouwproject, telt hier als beschikbaar/te koop).
     Twee listings ("Rooseveltweg – Commercial Units" en "Christoffel
     Resort – Sta. Catharina") hebben zelfs helemaal geen expliciet
     status-veld — dan is de default "sale" (er is geen aanwijzing dat
     ze niet beschikbaar zijn). SOLD/RENTED-uitsluiting staat wél in de
     code voor toekomstige runs, voor de zekerheid.
  4. Prijs-notatie wijkt af van Domicilie: `XCG.635,000` (valuta-prefix
     gevolgd door een punt, dan het bedrag met komma's als duizendtal-
     scheiding — de gedeelde `parse_price()` negeert punten/komma's toch
     allebei, dus geen probleem). **Eén "New Projects"-listing
     (Rooseveltweg) toont een verdacht lage "Starting from XCG.600"** —
     te laag om een geloofwaardige XCG-vastgoedprijs te zijn (waarschijnlijk
     een fout/onvolledig ingevulde prijs op de bronsite zelf, geen
     scraper-bug). Daarom een sanity-ondergrens: een `sale`-prijs onder
     5.000 wordt als onbetrouwbaar genegeerd (op None gezet, listing zelf
     blijft staan) i.p.v. een misleidend laag bedrag te tonen.
  5. Oppervlak: hier WEL met "m2"-suffix (`180 m2`), dus via de gedeelde
     `parse_area()`. `Property Size:` (bebouwd oppervlak) heeft
     voorrang op `Land Area:` (kaveloppervlak) als beide aanwezig zijn.
  6. Geen coördinaten/adres-blok op de detailpagina's gevonden (geen
     kaartsectie in de steekproef) — `latitude`/`longitude` blijven leeg,
     zelfde patroon als `domicilie.py`.
  7. Foto's: gewone `<img src>`-tags binnen `.lightbox-slider` (geen
     achtergrond-afbeeldingen zoals bij Domicilie's `.detail-slider`).
     Eén "New Projects"-listing had geen `.lightbox-slider` maar wél een
     losse fallback-foto in `.lightbox-gallery-wrap` — als fallback
     toegevoegd zodra de primaire selector niks oplevert.
  8. "Bathroom:" (enkelvoud) komt naast "Bathrooms:" (meervoud) voor
     als labeltekst — matching op het voorvoegsel "bathroom"/"bedroom"
     i.p.v. exacte labeltekst.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://pricematchrealestate.com"
SITEMAP = f"{BASE}/wp-sitemap-posts-property-1.xml"
EUR_TO_XCG = 1.95
MIN_SANE_SALE_PRICE = 5000

SOLD_STATUS_HINTS = ("sold", "verkocht", "rented", "verhuurd", "under contract", "onder optie")
RENT_STATUS_HINTS = ("for rent", "te huur")

TYPE_MAP = {
    "apartment": "apartment", "condo": "apartment", "penthouse": "apartment", "studio": "apartment",
    "land": "land", "lot": "land", "plot": "land",
    "commercial": "commercial", "office": "commercial", "warehouse": "commercial", "retail": "commercial",
    "family home": "house", "villa": "house", "house": "house", "residential": "house",
}

PRICE_RE = re.compile(r"(XCG|ANG|NAF|NAf|ƒ|EUR|€|USD|US\s*\$|\$)\.?\s*([\d][\d.,]{1,14})", re.I)


class PriceMatchScraper(BaseScraper):
    source_name = "pricematch"
    AGENT_COMPANY = "PriceMatch Real Estate"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if "/property/" in u]
        self.logger.info(f"PriceMatch: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"PriceMatch: {len(results)} actieve listings verwerkt")
        return results

    def _detail_dict(self, soup) -> dict[str, str]:
        out: dict[str, str] = {}
        dw = soup.find(class_="detail-wrap")
        if not dw:
            return out
        for li in dw.select("ul.list-2-cols > li"):
            strong = li.find("strong")
            span = li.find("span")
            if not strong or not span:
                continue
            label = self.clean_text(strong.get_text()).rstrip(":").lower()
            value = self.clean_text(span.get_text())
            if label and value:
                out[label] = value
        return out

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title:
            return None

        status_text = ""
        label_status = soup.find(class_="label-status")
        if label_status:
            status_text = self.clean_text(label_status.get_text()).lower()

        fields = self._detail_dict(soup)
        if not status_text:
            status_text = (fields.get("property status") or "").lower()

        if any(h in status_text for h in SOLD_STATUS_HINTS):
            return None
        listing_type = "rent" if any(h in status_text for h in RENT_STATUS_HINTS) else "sale"

        external_id = url.rstrip("/").split("/")[-1]

        property_type = "house"
        type_val = (fields.get("property type") or "").lower()
        for kw, mapped in TYPE_MAP.items():
            if kw in type_val:
                property_type = mapped
                break

        bedrooms = None
        for key, val in fields.items():
            if key.startswith("bedroom"):
                bedrooms = self.parse_int(val)
                break

        bathrooms = None
        for key, val in fields.items():
            if key.startswith("bathroom"):
                bathrooms = self.parse_int(val)
                break

        area_sqm = None
        if "property size" in fields:
            area_sqm = self.parse_area(fields["property size"])
        elif "land area" in fields:
            area_sqm = self.parse_area(fields["land area"])

        price, currency = None, "XCG"
        price_text = fields.get("price")
        if price_text:
            m = PRICE_RE.search(price_text)
            if m:
                cur_raw = re.sub(r"\s+", "", m.group(1)).upper()
                amount = self.parse_price(m.group(2))
                if amount:
                    if cur_raw in ("EUR", "€"):
                        price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                    elif cur_raw in ("US$", "USD", "$"):
                        price, currency = amount, "USD"
                    else:
                        price, currency = amount, "XCG"
            else:
                amount = self.parse_price(price_text)
                if amount:
                    price, currency = amount, "XCG"
        if price is not None and listing_type == "sale" and price < MIN_SANE_SALE_PRICE:
            self.logger.warning(f"PriceMatch: onwaarschijnlijk lage koopprijs ({price}) voor {url} — genegeerd")
            price = None

        description = None
        desc_h2 = soup.find("h2", string=lambda s: s and "description" in s.lower())
        if desc_h2:
            block = desc_h2.find_parent(class_="block-wrap")
            if block:
                content = block.find(class_="block-content-wrap")
                if content:
                    description = self.clean_text(content.get_text(" "))
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        images = []
        slider = soup.find(class_="lightbox-slider")
        if slider:
            for img in slider.find_all("img", src=True):
                images.append(img["src"])
        if not images:
            # Sommige listings (bv. "New Projects"-categorie) hebben geen
            # multi-foto .lightbox-slider maar een enkele fallback-foto in
            # .lightbox-gallery-wrap.
            gallery = soup.find(class_="lightbox-gallery-wrap")
            if gallery:
                for img in gallery.find_all("img", src=True):
                    images.append(img["src"])
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=external_id,
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
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
