"""Domicilie Real Estate scraper (priority 8)
Site: https://www.domicilie.net — WordPress + "Houzez"-thema (nieuwe
plugin-familie, niet eerder gezien bij Estatik/RealHomes/JetEngine/
Directorist/Webflow-sites). Standaard Apache-hosting, robots.txt staat
alles toe behalve `/wp-admin/` (met `admin-ajax.php` expliciet weer
toegestaan), `Sitemap: /wp-sitemap.xml`. Geen wp-json-route voor het
`property`-post-type (404 `rest_no_route`) — Houzez registreert de CPT
niet in de REST API, dus gewoon de server-gerenderde HTML parsen.

Methode:
  1. Volledige lijst uit `/wp-sitemap-posts-property-1.xml` (13 listings,
     geen paginering nodig — Houzez' sitemap-generator zou bij >2000 items
     een `-2.xml` etc. toevoegen, hier niet aan de orde).
  2. Per detailpagina staat alle kernbdata in één nette `<ul class="list-
     three-col"><li><strong>Label:</strong> Waarde</li>...` binnen
     `.detail-list` — label/waarde-paren worden gebouwd door de
     `<strong>`-tag uit de `<li>` te knippen en de resttekst te nemen
     (zelfde aanpak als bij Ambiente/Kostabon se `es-property-field`,
     alleen is hier geen aparte class per veld, dus op labeltekst
     gematcht i.p.v. op class-suffix).
  3. **Statusfilter (vierde variant in de scraper-set, weer anders dan de
     vorige drie): het label staat gewoon leesbaar in zowel de header-
     badge (`.label-status`) als de `Eigenschapstatus:`-regel in
     `.detail-list` — "Te koop"/"Te huur" = beschikbaar, "Verkocht"/
     "Verhuurd" = overslaan.** Van de 13 listings in de steekproef waren
     er 7 al verkocht/verhuurd — alleen "Te koop"/"Te huur" meegenomen.
  4. **Domicilie adverteert NIET uitsluitend Curaçao** — één listing in de
     steekproef betrof "Road to White Wall – Sint Eustatius" (Bovenwindse
     eilanden, geen coördinaten dus de gebruikelijke Curaçao-bounding-box-
     check op lat/lng vangt dit niet af). Titel/breadcrumb wordt daarom
     expliciet gescand op eilandnamen buiten Curaçao (Sint Eustatius/
     Statia/Bonaire/Aruba/Sint Maarten/Saba) en zo'n listing wordt
     overgeslagen, ook al is de status verder beschikbaar.
  5. Prijs: de "Prijs:"-waarde bevat een valutaprefix — geziene varianten:
     "XCG 695.000" (native), "US $ 1250000" (native USD), "EURO 199.000,="
     (×1,95 naar XCG — let op de afsluitende ",=" die de gedeelde
     `parse_price()` al correct negeert omdat die alle punten/komma's
     wegstript vóór de digit-extractie). Een enkele huurprijs bevatte
     extra vrije tekst ("XCG 3.750/per maand excl water en elektra,
     inclusief service kosten") — ook hier pakt `parse_price()` gewoon het
     eerste cijferblok correct.
  6. Geen coördinaten gevonden op de detailpagina's — de enige lat/lng in
     de pagina-JS is een vast Houzez-thema-default (`property_lat":
     "25.68654"`, Miami!) dat niets met de listing te maken heeft, dus
     bewust NIET gebruikt. `latitude`/`longitude` blijven leeg, zelfde
     patroon als `nh_real_estate.py`/`top_makelaar.py`.
  7. Bedrooms/bathrooms/oppervlak komen uit dezelfde label/waarde-dict
     ("slaapkamers"/"badkamers"/"landoppervlak"/"eigenschap grootte" —
     Nederlandse labels, kale cijferstring zonder "m²"-suffix dus niet via
     de gedeelde `parse_area()` maar met dezelfde separator-strip-aanpak
     als `parse_price()`).
  8. Foto's: `.detail-slider .item`-divs met een inline
     `background-image: url(...)`-style (geen `<img src>`-tags in de
     slider zelf) — met regex uit de style-attribute gehaald.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.domicilie.net"
SITEMAP = f"{BASE}/wp-sitemap-posts-property-1.xml"
EUR_TO_XCG = 1.95

SOLD_STATUS_HINTS = ("verkocht", "sold", "verhuurd", "rented", "onder optie", "under contract")
RENT_STATUS_HINTS = ("te huur", "for rent", "verhuurd")

NON_CURACAO_HINTS = (
    "sint eustatius", "statia", "bonaire", "aruba", "sint maarten",
    "st. maarten", "st maarten", "saba",
)

TYPE_MAP = {
    "woonhuis": "house", "woning": "house", "luxe woning": "house",
    "vakantiewoning": "house", "twee-onder-een-kap": "house",
    "appartement": "apartment", "appartementencomplex": "apartment",
    "penthouse": "apartment", "studio": "apartment",
    "kavel": "land", "landtong": "land", "grond": "land",
    "conserveringsgebied": "land",
    "bedrijfspand": "commercial", "loods": "commercial", "commercieel": "commercial",
}

PRICE_RE = re.compile(r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\s*([\d][\d.,]{1,14})", re.I)
IMG_STYLE_RE = re.compile(r"background-image:\s*url\(([^)]+)\)")


def _strip_number(text: str) -> float | None:
    """Zelfde separator-strip-aanpak als BaseScraper.parse_price, voor
    kale cijferstrings zonder valuta/eenheid (oppervlak-velden)."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", text.replace(".", "").replace(",", ""))
    return float(cleaned) if cleaned else None


class DomicilieScraper(BaseScraper):
    source_name = "domicilie"
    AGENT_COMPANY = "Domicilie Real Estate"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if "/property/" in u]
        self.logger.info(f"Domicilie: {len(urls)} listing-URL's in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Domicilie: {len(results)} actieve Curaçao-listings verwerkt")
        return results

    def _detail_dict(self, soup) -> dict[str, str]:
        out: dict[str, str] = {}
        dl = soup.find(class_="detail-list")
        if not dl:
            return out
        for li in dl.select("ul.list-three-col > li"):
            strong = li.find("strong")
            if not strong:
                continue
            label = self.clean_text(strong.get_text()).rstrip(":").lower()
            strong.extract()
            value = self.clean_text(li.get_text())
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

        breadcrumb = soup.find(class_="breadcrumb")
        breadcrumb_text = self.clean_text(breadcrumb.get_text(" ")) if breadcrumb else ""
        combined = f"{title} {breadcrumb_text}".lower()
        if any(h in combined for h in NON_CURACAO_HINTS):
            self.logger.info(f"Domicilie: {url} buiten Curaçao — overgeslagen")
            return None

        status_text = ""
        label_status = soup.find(class_="label-status")
        if label_status:
            status_text = self.clean_text(label_status.get_text()).lower()

        fields = self._detail_dict(soup)
        if not status_text:
            status_text = (fields.get("eigenschapstatus") or fields.get("property status") or "").lower()

        if any(h in status_text for h in SOLD_STATUS_HINTS):
            return None
        listing_type = "rent" if any(h in status_text for h in RENT_STATUS_HINTS) else "sale"

        external_id = url.rstrip("/").split("/")[-1]

        property_type = "house"
        type_val = (fields.get("eigendom type") or fields.get("property type") or "").lower()
        for kw, mapped in TYPE_MAP.items():
            if kw in type_val:
                property_type = mapped
                break

        bedrooms = None
        for key in ("slaapkamers", "bedrooms"):
            if key in fields:
                bedrooms = self.parse_int(fields[key])
                break

        bathrooms = None
        for key in ("badkamers", "bathrooms"):
            if key in fields:
                bathrooms = self.parse_int(fields[key])
                break

        area_sqm = None
        for key in ("landoppervlak", "eigenschap grootte", "property size", "land area"):
            if key in fields:
                area_sqm = _strip_number(fields[key])
                break

        price, currency = None, "XCG"
        price_text = fields.get("prijs") or fields.get("price")
        if price_text:
            m = PRICE_RE.search(price_text)
            if m:
                cur_raw = re.sub(r"\s+", "", m.group(1)).upper()
                amount = self.parse_price(m.group(2))
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

        description = None
        desc_block = soup.find(class_="property-description")
        if desc_block:
            paragraphs = desc_block.find_all("p")
            description = self.clean_text(" ".join(p.get_text(" ") for p in paragraphs))
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        images = []
        slider = soup.find(class_="detail-slider")
        if slider:
            for item in slider.find_all(class_="item"):
                style = item.get("style", "")
                m = IMG_STYLE_RE.search(style)
                if m:
                    images.append(m.group(1).strip("'\""))
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
