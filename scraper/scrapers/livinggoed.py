"""Livinggoed Real Estate scraper (herbouwd)
Site: https://livinggoed.com  (WordPress + Houzez thema, custom post type 'property')

Methode:
  1. Lijst met alle objecten uit de XML-sitemap (/property-sitemap.xml).
  2. Per object de detailpagina ophalen. Houzez zet een JSON-blob
     `houzez_single_property_map={...}` in de pagina met titel, prijs, type,
     adres en lat/lng. Beds/baths/oppervlak komen uit de detail-tekst.

Prijzen staan in Cg. (ANG) — numeriek opgeslagen zoals getoond.
"""
import re
import json
import time
from ..base_scraper import BaseScraper
from ..models import Listing

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class LivinggoedScraper(BaseScraper):
    source_name = "livinggoed"
    BASE = "https://livinggoed.com"
    SITEMAP = "https://livinggoed.com/property-sitemap.xml"
    AGENT_COMPANY = "Livinggoed Real Estate"

    def _fetch(self, url: str, tries: int = 5):
        """Robuuste GET (livinggoed geeft af en toe transiente 000/proxy-fouten)."""
        for attempt in range(tries):
            try:
                r = self.session.get(url, timeout=45)
                if r.status_code == 200 and len(r.text) > 500:
                    return r.text
            except Exception as e:
                self.logger.debug(f"livinggoed fetch poging {attempt+1} faalde: {e}")
            time.sleep(2 * (attempt + 1))
        return None

    def scrape(self) -> list[Listing]:
        xml = self._fetch(self.SITEMAP)
        if not xml:
            self.logger.error("livinggoed: sitemap niet beschikbaar")
            return []

        urls = re.findall(
            r"<loc>\s*<!\[CDATA\[(https://livinggoed\.com/object/[^\]]+)\]\]>", xml
        )
        # fallback zonder CDATA
        if not urls:
            urls = re.findall(r"<loc>(https://livinggoed\.com/object/[^<]+)</loc>", xml)
        urls = list(dict.fromkeys(urls))
        self.logger.info(f"livinggoed: {len(urls)} objecten in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                html = self._fetch(url)
                if not html:
                    self.logger.warning(f"livinggoed: geen HTML voor {url}")
                    continue
                l = self._parse(url, html)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"livinggoed parse error ({url}): {e}")
            time.sleep(1.0)

        self.logger.info(f"Livinggoed total: {len(results)} listings")
        return results

    def _parse(self, url: str, html: str) -> Listing | None:
        jm = {}
        m = re.search(r"houzez_single_property_map\s*=\s*(\{.*?\});", html, re.S)
        if m:
            try:
                jm = json.loads(m.group(1))
            except Exception:
                jm = {}

        slug = url.rstrip("/").rsplit("/", 1)[-1]
        ext_id = str(jm.get("property_id") or slug)
        title = (jm.get("title") or "").strip() or slug.replace("-", " ").title()

        price_pin = jm.get("pricePin") or ""
        price = self.parse_price(price_pin) if price_pin else None

        # listing_type
        if re.search(r"per\s*maand", price_pin, re.I) or re.search(r"/status/huur|Huurprijs", html, re.I):
            listing_type = "rent"
        else:
            listing_type = "sale"

        # property_type uit het Houzez type-veld
        ptype = self._map_ptype((jm.get("property_type") or "").lower())

        # buurt uit het adres (achter de laatste komma)
        neighborhood = None
        addr = jm.get("address") or ""
        if "," in addr:
            neighborhood = addr.rsplit(",", 1)[-1].strip()
        elif addr:
            neighborhood = addr.strip() or None

        lat = self._flt(jm.get("lat"))
        lng = self._flt(jm.get("lng"))
        # coords buiten Curaçao verwerpen (soms staat er een default-marker)
        if lat is not None and lng is not None:
            if not (11.9 <= lat <= 12.45 and -69.25 <= lng <= -68.6):
                lat = lng = None

        # beschrijving: Houzez zet 'm meestal in het JSON-blok zelf, anders in
        # een genest content-blok op de pagina, anders de SEO meta-omschrijving
        soup = BeautifulSoup(html, "lxml") if BeautifulSoup else None
        description = jm.get("content") or jm.get("description") or None
        if description:
            description = re.sub(r"<[^>]+>", " ", description)
        if not description and soup is not None:
            entry = (
                soup.select_one("#tab-description")
                or soup.select_one(".property_description")
                or soup.select_one(".item_description")
                or soup.select_one(".single_property_element .content")
                or soup.select_one(".entry-content")
            )
            if entry:
                dtext = re.sub(r"\s+", " ", entry.get_text(" ", strip=True)).strip()
                if len(dtext) > 40:
                    description = dtext
        if not description and soup is not None:
            meta = soup.select_one('meta[name="description"]') or soup.select_one('meta[property="og:description"]')
            if meta and meta.get("content"):
                description = meta["content"]
        if description:
            description = re.sub(r"\s+", " ", description).strip()[:6000] or None

        # beds/baths/oppervlak uit detail-tekst
        text = html
        if BeautifulSoup:
            text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        beds = self._int(re.search(r"(\d+)\s*[Ss]laapkamer", text))
        baths = self._int(re.search(r"(\d+)\s*[Bb]adkamer", text))
        area = None
        am = re.search(r"Woonoppervlak\w*:?\s*([\d.,]+)\s*m", text)
        if not am:
            am = re.search(r"Perceeloppervlak\w*:?\s*([\d.,]+)\s*m", text)
        if am:
            area = self.parse_area(am.group(1) + " m")

        # afbeeldingen: uploads, size-varianten dedupen
        raw = re.findall(
            r"https://livinggoed\.com/wp-content/uploads/[^\s\"')]+\.(?:jpg|jpeg|png)",
            html, flags=re.I,
        )
        images, seen = [], set()
        for u in raw:
            base = re.sub(r"-\d+x\d+(?=\.\w+$)", "", u)
            if base not in seen:
                seen.add(base)
                images.append(base)

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,          # Cg. / ANG
            url=url,
            description=description,
            neighborhood=neighborhood,
            bedrooms=beds,
            bathrooms=baths,
            area_sqm=area,
            latitude=lat,
            longitude=lng,
            images=self.clean_images(images, limit=40),
            agent_company=self.AGENT_COMPANY,
        )

    @staticmethod
    def _int(m):
        return int(m.group(1)) if m else None

    @staticmethod
    def _flt(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _map_ptype(t: str) -> str:
        if "kavel" in t or "grond" in t:
            return "land"
        if "appartement" in t or "penthouse" in t or "studio" in t:
            return "apartment"
        if any(w in t for w in ["commerc", "bedrijf", "kantoor", "winkel"]):
            return "commercial"
        return "house"
