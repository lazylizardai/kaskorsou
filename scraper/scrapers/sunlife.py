"""Sunlife Real Estate scraper (priority 8)
Site: https://sunlife.realty — GEEN WordPress. Draait op **Botble CMS**
(Laravel, `botble_session`-cookie, `cms-version` header), achter Cloudflare.
robots.txt: alles toegestaan (Sitemap: /sitemap.xml), geen crawl-delay.

Methode:
  1. Geen wp-json en geen bruikbare JSON-API. De `/properties?...`-zoekpagina
     rendert de resultatengrid client-side via JS (leeg in de ruwe HTML,
     geverifieerd) — dus geen HTML-crawl van de listpagina mogelijk. De
     `/feed/properties`-RSS geeft maar de ~20 nieuwste posts, niet de volledige
     catalogus.
  2. Wél bruikbaar: de sitemap is opgesplitst in maandelijkse
     `properties-YYYY-MM.xml`-bestanden (via de sitemap-index op
     `/sitemap.xml`) — samen alle listing-URLs, actief én verkocht/verhuurd
     door elkaar. Alle maandbestanden ophalen en de `<loc>`-URLs verzamelen.
  3. Per listing de detailpagina fetchen. Twee bronnen op de pagina:
       a. Een iconen-grid met (getal, label)-paren: Bedrooms, Bathrooms,
          Floors, "Square (m²)" (kaveloppervlak), "Living Space m²"
          (woonoppervlak) — niet elk veld is bij elke listing aanwezig.
       b. Een key/value-tabel (`td.property-detail-label` + waarde) met o.a.
          Status, Price, Home Type, Categories, en bij verhuur extra velden
          als "Min. contract length"/"Rent includes" (afwezig bij koop).
  4. **Status-filter**: alleen Status "Available" meenemen — "Sold"/"Rented"
     actief overslaan (net als bij NH Real Estate/rented-sold-exclusie).
  5. **Land-filter — belangrijk**: Sunlife verkoopt niet alleen Curaçao maar
     ook Dominicaanse Republiek (Punta Cana/Bávaro/Santo Domingo) en Sint
     Maarten (het site-zoekfilter heeft een expliciet `country_id`-veld met
     die 3 opties) — maar de detailpagina zelf heeft GEEN gestructureerd
     land/plaats-veld, alleen vrije tekst in titel/meta-omschrijving. Daarom:
     titel + meta-omschrijving scannen op een vaste lijst DR/Sint Maarten-
     plaatsnamen (Punta Cana, Bávaro, Santo Domingo, Piantini, Sint Maarten,
     St. Maarten) en die listings overslaan. Dit is een tekst-heuristiek,
     geen harde garantie — bij twijfel (buurt niet herkend, geen hint van
     een ander land) blijft een listing staan.
  6. listing_type: uit titel/URL-slug ("for sale" vs "for rent"/"for-rent");
     valt terug op de aanwezigheid van huur-specifieke tabelvelden
     ("Rent includes"/"Min. contract length") als de titel geen van beide zegt.
  7. property_type via "Categories"/"Home Type"-tekst (villa/house/apartment/
     land/commercial), zelfde indeling als de andere scrapers.
  8. Prijs: `Price`-tabelveld heeft 3 notaties: "€ 1.825.000,00"/"€
     1,825,000.00" (EUR, ×1,95 naar XCG net als remax/moret/nh_real_estate),
     "Cg 899,000.00" (native XCG — "Cg" = Curaçaose gulden/ANG-afkorting op
     deze site), "$ 295,000.00" (USD, native).
  9. Afbeeldingen: lazy-loaded via `data-src="https://sunlife.realty/storage/
     image-XXXXXX.jpg"` in de gallery-HTML — geen resolutie-varianten nodig
     (geen `-WxH`-suffix zoals bij WordPress-uploads), dus direct dedupen.
  10. Geen coördinaten op de pagina (geen data-lat/data-lng gevonden) —
      latitude/longitude blijven leeg, net als bij NH Real Estate.
"""
import html as html_mod
import re
import time
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://sunlife.realty"
SITEMAP_INDEX = f"{BASE}/sitemap.xml"

EXCLUDE_STATUS = {"sold", "rented", "under contract", "reserved", "off market"}

# Vrije-tekst locatiehints die op Dominicaanse Republiek of Sint Maarten
# wijzen i.p.v. Curaçao (zie punt 5 hierboven) — case-insensitive.
NON_CURACAO_HINTS = (
    "punta cana", "dominican republic", "república dominicana",
    "republica dominicana", "bávaro", "bavaro", "santo domingo",
    "piantini", "sint maarten", "st. maarten", "st maarten",
    "philipsburg", "simpson bay", "cupecoy",
)

CATEGORY_TYPE_MAP = [
    ("land", "land"), ("lot", "land"), ("building land", "land"),
    ("office", "commercial"), ("retail", "commercial"), ("business", "commercial"),
    ("hospitality", "commercial"), ("shop", "commercial"),
    ("apartment", "apartment"), ("condo", "apartment"), ("penthouse", "apartment"),
    ("villa", "house"), ("house", "house"), ("family house", "house"),
    ("single house", "house"), ("townhouse", "house"),
]

FEATURE_RE = re.compile(
    r'font-size:\s*24px;\s*font-weight:\s*600;[^>]*>\s*([\d.,]+)\s*</div>\s*'
    r'<div style="font-size:\s*14px;[^>]*>\s*([^<]+?)\s*</div>'
)
TABLE_ROW_RE = re.compile(
    r'<td class="property-detail-label">([^<]+)</td>\s*<td>\s*(.*?)\s*</td>', re.S
)
PROPERTY_ID_RE = re.compile(r'Property ID:</strong>\s*(\d+)')
TITLE_RE = re.compile(r'<title>([^<]+)</title>')
META_DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')
PRICE_RE = re.compile(r'([€$]|Cg)\s*([\d][\d.,]*)', re.I)


class SunlifeScraper(BaseScraper):
    source_name = "sunlife"
    AGENT_COMPANY = "Sunlife Real Estate"

    def _fetch(self, url: str, tries: int = 4) -> str | None:
        for attempt in range(tries):
            try:
                time.sleep(1.5 if attempt == 0 else 3 * attempt)
                r = self.session.get(url, timeout=40)
                if r.status_code == 200 and len(r.text) > 500:
                    return r.text
            except Exception as e:
                self.logger.debug(f"sunlife fetch poging {attempt+1} faalde ({url}): {e}")
        return None

    def _sitemap_urls(self) -> list[str]:
        idx = self._fetch(SITEMAP_INDEX)
        if not idx:
            self.logger.error("sunlife: sitemap-index niet beschikbaar")
            return []
        month_sitemaps = sorted(set(re.findall(r"<loc>(https://sunlife\.realty/properties-[\d-]+\.xml)</loc>", idx)))
        urls: list[str] = []
        for sm in month_sitemaps:
            xml = self._fetch(sm)
            if not xml:
                continue
            urls.extend(re.findall(r"<loc>(https://sunlife\.realty/properties/[^<]+)</loc>", xml))
            time.sleep(0.5)
        return list(dict.fromkeys(urls))

    def scrape(self) -> list[Listing]:
        urls = self._sitemap_urls()
        self.logger.info(f"Sunlife: {len(urls)} listing-URLs in sitemaps")
        results: list[Listing] = []
        skipped_status, skipped_country = 0, 0
        for url in urls:
            try:
                page_html = self._fetch(url)
                if not page_html:
                    self.logger.warning(f"sunlife: geen HTML voor {url}")
                    continue
                l, reason = self._parse(url, page_html)
                if l:
                    results.append(l)
                elif reason == "status":
                    skipped_status += 1
                elif reason == "country":
                    skipped_country += 1
            except Exception as e:
                self.logger.warning(f"sunlife parse error ({url}): {e}")
            time.sleep(1.5)
        self.logger.info(
            f"Sunlife total: {len(results)} actieve Curaçao-listings "
            f"({skipped_status} sold/rented overgeslagen, {skipped_country} niet-Curaçao overgeslagen)"
        )
        return results

    def _parse(self, url: str, page_html: str) -> tuple[Listing | None, str | None]:
        m = TITLE_RE.search(page_html)
        title = html_mod.unescape(m.group(1)).strip() if m else None
        if not title:
            return None, "no_title"

        md = META_DESC_RE.search(page_html)
        meta_desc = html_mod.unescape(md.group(1)) if md else ""

        haystack = f"{title} {meta_desc}".lower()
        if any(hint in haystack for hint in NON_CURACAO_HINTS):
            return None, "country"

        pairs = TABLE_ROW_RE.findall(page_html)
        table = {k.strip(): re.sub(r"\s+", " ", html_mod.unescape(v)).strip() for k, v in pairs}

        status = table.get("Status", "").strip().lower()
        if status in EXCLUDE_STATUS:
            return None, "status"

        pid_m = PROPERTY_ID_RE.search(page_html)
        # fallback: slug als geen Property ID gevonden (komt voor bij oudere posts)
        ext_id = pid_m.group(1) if pid_m else url.rstrip("/").rsplit("/", 1)[-1]

        features = {lbl.strip(): val for val, lbl in FEATURE_RE.findall(page_html)}
        bedrooms = self._int(features.get("Bedrooms"))
        bathrooms = self._int(features.get("Bathrooms"))
        area_sqm = self._flt(features.get("Square (m²)")) or self._flt(
            re.sub(r"[^\d.,]", "", features.get("Living Space m²", "")) or None
        )

        # listing_type: titel/URL-slug, met huur-specifieke tabelvelden als terugval
        slug_and_title = f"{url} {title}".lower()
        rent_field_present = bool(table.get("Min. contract length") or table.get("Rent includes"))
        if re.search(r"for[\s-]rent|to[\s-]rent|/rent\b", slug_and_title):
            listing_type = "rent"
        elif re.search(r"for[\s-]sale", slug_and_title):
            listing_type = "sale"
        else:
            listing_type = "rent" if rent_field_present else "sale"

        categories_text = f"{table.get('Categories', '')} {table.get('Home Type', '')}".lower()
        property_type = "house"
        for needle, ptype in CATEGORY_TYPE_MAP:
            if needle in categories_text:
                property_type = ptype
                break

        price_ang, currency = self._parse_price(table.get("Price", ""))

        description = None
        if meta_desc:
            description = self.clean_text(meta_desc)

        images = self._images(page_html)

        listing = Listing(
            source_id=self.source_id,
            external_id=str(ext_id),
            title=self.clean_text(title, max_len=300) or title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price_ang,
            currency=currency,
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
        return listing, None

    def _parse_price(self, raw: str) -> tuple[float | None, str]:
        if not raw:
            return None, "XCG"
        m = PRICE_RE.search(raw)
        if not m:
            return None, "XCG"
        symbol, amount = m.group(1), m.group(2)
        # Altijd Amerikaanse notatie op deze site: komma = duizendtal, punt =
        # decimaal, met exact 2 decimalen (bv. "1,825,000.00"). NIET de
        # generieke self.parse_price gebruiken — die strip "." én "," en zou
        # de ".00" hier per ongeluk in het geheel-getal mengen (100x te hoog).
        try:
            price = float(amount.replace(",", ""))
        except ValueError:
            price = None
        # Sanity-vloer: enkele listings hebben een kapotte/placeholder-prijs
        # op de bron zelf (bv. "Cg 3.00" i.p.v. een echt bedrag) — die als
        # None behandelen i.p.v. als een absurd lage huur/koopprijs op te
        # slaan (zelfde patroon als nh_real_estate.py: price >= 100).
        if not price or price < 100:
            return None, "XCG"
        if symbol == "€":
            return round(price * 1.95, 2), "XCG"
        if symbol == "$":
            return price, "USD"
        return price, "XCG"  # "Cg" = native ANG/XCG

    def _images(self, page_html: str) -> list[str]:
        urls = re.findall(r'data-src="(https://sunlife\.realty/storage/[^"]+\.(?:jpe?g|png|webp))"', page_html, re.I)
        return self.clean_images(urls, limit=40)

    @staticmethod
    def _int(v):
        if not v:
            return None
        try:
            return int(float(str(v).replace(",", "")))
        except ValueError:
            return None

    @staticmethod
    def _flt(v):
        if not v:
            return None
        try:
            return float(str(v).replace(",", ""))
        except ValueError:
            return None
