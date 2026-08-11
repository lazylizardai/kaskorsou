"""Simmer Real Estate scraper (priority 8)
Site: https://simmerrealestate.com — WordPress, "RealHomes"-thema (child-
thema `realhomes-child`), zelfde theme-familie als Real Estate Caribe.
Gewone hosting, geen WPCloud/SiteGround-blokkade-signalen. robots.txt heeft
alleen `Crawl-delay: 3`, geen disallow op `/wp-json/`.

Methode (zelfde patroon als real_estate_caribe.py):
  1. Volledige lijst rechtstreeks uit de WP REST API: GET
     `/wp-json/wp/v2/property?per_page=100&_embed=1` (19 listings passen
     ruim in 1 pagina, `while`-lus met `per_page=100` voor als de site
     groeit).
  2. `property_meta` (`REAL_HOMES_*`) bevat alles structured: prijs
     (`REAL_HOMES_property_price`, los `..._price_prefix`-veld voor de
     valuta: `""`/`"Nafl"` → native XCG, `"€"` → EUR ×1.95 naar XCG, `"$"`
     → native USD), slaapkamers, badkamers (soms een breuk-notatie zoals
     `"3 1/2"` — apart afgehandeld, `parse_int()` zou de `.5` laten
     vallen), en echte coördinaten (`REAL_HOMES_property_location`).
  3. Taxonomie `property-status` gebruikt hier Nederlandse slugs
     (`te-koop`/`te-huur` i.p.v. Real Estate Caribe's `for-sale`/
     `for-rent`) maar is GEEN betrouwbare beschikbaarheidsindicator: van de
     19 listings in de steekproef staan er 10 nog gewoon op `te-huur`/
     `te-koop` terwijl de titel zelf een `<span class="callout">VERHUURD
     </span>` of `<span class="callout">VERKOCHT</span>` bevat — de site
     laat verhuurde/verkochte listings gewoon online staan, alleen de
     titel-HTML verraadt het. Titel moet dus HTML-gestript worden (niet
     alleen `html.unescape()`) en een VERHUURD/VERKOCHT-callout in de rauwe
     titel-HTML betekent: listing overslaan (niet meer beschikbaar).
     `property-type`-taxonomie is hier vrije-tekst-achtig
     (`vrijstaande-woning-met-appartement-en-zwembad` etc.) i.p.v. de
     schone residential/commercial/lots-set van Real Estate Caribe — dus
     woningtype afgeleid uit trefwoorden in de gecombineerde
     type-slugs + titel i.p.v. één schone taxonomie-waarde.
  4. Foto's: featured media + `/wp-json/wp/v2/media?parent=<id>`.
  5. Beschrijving uit `content.rendered` (HTML gestript).
"""
import html
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://simmerrealestate.com"
API = f"{BASE}/wp-json/wp/v2/property"
MEDIA_API = f"{BASE}/wp-json/wp/v2/media"
PAGE_SIZE = 100
EUR_TO_XCG = 1.95

LAND_HINTS = ("bouwkavel", "kavel", "grond", "land")
COMMERCIAL_HINTS = ("commercieel", "commercial", "bedrijfspand", "kantoor")
APARTMENT_HINTS = ("appartement", "penthouse", "studio", "condo")


class SimmerScraper(BaseScraper):
    source_name = "simmer"
    AGENT_COMPANY = "Simmer Real Estate"

    def _get_json(self, url: str, params: dict):
        r = self.session.get(url, params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        items = []
        page = 1
        while True:
            try:
                batch = self._get_json(API, {"per_page": PAGE_SIZE, "page": page, "_embed": 1})
            except Exception as e:
                if page == 1:
                    self.logger.error(f"Kon properties niet ophalen: {e}")
                    return []
                break
            if not batch:
                break
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1

        self.logger.info(f"Simmer Real Estate: {len(items)} listings uit de REST API")

        results = []
        for item in items:
            try:
                l = self._build(item)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({item.get('id')}): {e}")
        return results

    def _terms(self, item: dict) -> dict:
        out: dict[str, list[tuple[str, str]]] = {}
        for grp in (item.get("_embedded") or {}).get("wp:term", []):
            for t in grp:
                out.setdefault(t.get("taxonomy"), []).append((t.get("slug"), t.get("name")))
        return out

    def _images(self, property_id: int, item: dict) -> list[str]:
        images = []
        fm = (item.get("_embedded") or {}).get("wp:featuredmedia")
        if fm and fm[0].get("source_url"):
            images.append(fm[0]["source_url"])
        try:
            media = self._get_json(MEDIA_API, {"parent": property_id, "per_page": 100})
            for m in media:
                if m.get("source_url"):
                    images.append(m["source_url"])
        except Exception as e:
            self.logger.warning(f"Media error ({property_id}): {e}")
        return self.clean_images(images)

    def _bathrooms(self, raw: str | None) -> int | None:
        """'3 1/2' -> 4 (afgerond), '2' -> 2. parse_int() alleen zou de
        '.5' bij een breuk-notatie laten vallen."""
        if not raw:
            return None
        raw = raw.strip()
        whole = self.parse_int(raw)
        if whole is None:
            return None
        if "1/2" in raw:
            return round(whole + 0.5)
        return whole

    def _build(self, item: dict) -> Listing | None:
        property_id = item.get("id")
        if not property_id:
            return None

        title_raw = item.get("title", {}).get("rendered", "")
        title_upper = title_raw.upper()
        if "VERHUURD" in title_upper or "VERKOCHT" in title_upper:
            # Niet meer beschikbaar, maar de site laat 'm gewoon online staan
            # met alleen een callout-span in de titel-HTML als signaal.
            return None

        title = self.clean_text(html.unescape(BeautifulSoup(title_raw, "lxml").get_text(" "))) or "Woning Curaçao"
        url = item.get("link") or f"{BASE}/property/{item.get('slug', '')}/"

        terms = self._terms(item)
        status_slugs = {s for s, _ in terms.get("property-status", [])}
        listing_type = "rent" if "te-huur" in status_slugs else "sale"

        type_slugs = " ".join(s for s, _ in terms.get("property-type", [])).lower()
        hint_text = f"{type_slugs} {title.lower()}"
        if any(h in hint_text for h in LAND_HINTS):
            property_type = "land"
        elif any(h in hint_text for h in COMMERCIAL_HINTS):
            property_type = "commercial"
        elif any(h in hint_text for h in APARTMENT_HINTS):
            property_type = "apartment"
        else:
            property_type = "house"

        pm = item.get("property_meta") or {}
        prefix = (pm.get("REAL_HOMES_property_price_prefix") or "").strip().upper()
        price_raw = pm.get("REAL_HOMES_property_price")
        price, currency = None, "XCG"
        if price_raw:
            amount = self.parse_price(str(price_raw))
            if amount:
                if prefix == "€":
                    price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                elif prefix == "$":
                    price, currency = amount, "USD"
                else:
                    price, currency = amount, "XCG"

        bedrooms = self.parse_int(pm.get("REAL_HOMES_property_bedrooms") or "")
        bathrooms = self._bathrooms(pm.get("REAL_HOMES_property_bathrooms"))

        area_sqm = None
        for key in ("REAL_HOMES_property_size", "REAL_HOMES_property_lot_size"):
            v = pm.get(key)
            if v:
                area_sqm = self.parse_area(str(v)) or self.parse_int(str(v))
                if area_sqm:
                    break

        neighborhood = self.clean_text(pm.get("REAL_HOMES_property_address"))

        latitude = longitude = None
        loc = pm.get("REAL_HOMES_property_location") or {}
        try:
            lat_c = float(loc.get("latitude"))
            lng_c = float(loc.get("longitude"))
            if 11.9 <= lat_c <= 12.5 and -69.3 <= lng_c <= -68.5:
                latitude, longitude = lat_c, lng_c
        except (TypeError, ValueError):
            pass

        description = None
        content_html = (item.get("content") or {}).get("rendered")
        if content_html:
            description = self.clean_text(BeautifulSoup(content_html, "lxml").get_text(" "))

        images = self._images(property_id, item)

        return Listing(
            source_id=self.source_id,
            external_id=str(property_id),
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
            latitude=latitude,
            longitude=longitude,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
