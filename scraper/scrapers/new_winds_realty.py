"""New Winds Realty scraper
Site: https://www.newwindsrealty.com (WordPress + REM ("Real Estate Manager") plugin,
custom post type 'rem_property' exposed as /wp-json/wp/v2/properties)

Methode:
  1. Lijst + beschrijving komen uit de standaard WP REST API (geen captcha, geen auth).
  2. Prijs/beds/baths/oppervlak/wijk/foto's/sold-status komen van de detailpagina —
     die staan niet in de REST-response (acf staat leeg voor dit CPT).
"""
import re
import time
from ..base_scraper import BaseScraper
from ..models import Listing

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class NewWindsRealtyScraper(BaseScraper):
    source_name = "new_winds_realty"
    BASE = "https://www.newwindsrealty.com"
    AGENT_COMPANY = "New Winds Realty"

    def _fetch(self, url: str, tries: int = 4):
        """GET met retry/backoff — de site draait op WordPress.com/WPCloud (Automattic),
        die bekend staat om agressieve 429-blokkades op cloud/datacenter-IP-ranges
        (o.a. GitHub Actions). Respecteert Retry-After als die er is."""
        r = None
        for attempt in range(tries):
            try:
                r = self.session.get(url, timeout=40)
            except Exception as e:
                self.logger.warning(f"new_winds_realty: request naar {url} faalde: {e}")
                r = None
            if r is not None and r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 0) or 0)
                wait = max(wait, 15 * (attempt + 1))
                self.logger.warning(
                    f"new_winds_realty: 429 op {url} (poging {attempt+1}/{tries}), "
                    f"wacht {wait}s"
                )
                time.sleep(wait)
                continue
            if r is not None and r.status_code == 200:
                return r
            if attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
        return r

    def scrape(self) -> list[Listing]:
        results: list[Listing] = []

        page = 1
        props = []
        while page <= 5:
            r = self._fetch(f"{self.BASE}/wp-json/wp/v2/properties?per_page=100&page={page}")
            if r is None:
                self.logger.warning(f"new_winds_realty: geen response voor pagina {page}")
                break
            try:
                batch = r.json()
            except Exception as e:
                self.logger.warning(
                    f"new_winds_realty: kon pagina {page} niet parsen "
                    f"(status={r.status_code}, len={len(r.text)}, ct={r.headers.get('content-type')}): {e}"
                )
                self.logger.warning(f"new_winds_realty: body snippet: {r.text[:300]!r}")
                break
            if not isinstance(batch, list) or not batch:
                if isinstance(batch, dict):
                    self.logger.warning(f"new_winds_realty: API-fout pagina {page}: {batch}")
                break
            props.extend(batch)
            total_pages = int(r.headers.get("X-WP-TotalPages", 1) or 1)
            if page >= total_pages:
                break
            page += 1
            time.sleep(1)

        self.logger.info(f"new_winds_realty: {len(props)} properties uit REST API")

        skipped_sold = 0
        for p in props:
            try:
                l = self._parse(p)
                if l == "SOLD":
                    skipped_sold += 1
                    continue
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"new_winds_realty parse error ({p.get('slug')}): {e}")
            time.sleep(0.8)  # polite

        self.logger.info(
            f"New Winds Realty total: {len(results)} listings (sold overgeslagen: {skipped_sold})"
        )
        return results

    def _parse(self, p):
        ext_id = str(p.get("id") or p.get("slug") or "")
        if not ext_id:
            return None
        title = (p.get("title") or {}).get("rendered", "").strip()
        url = p.get("link") or ""

        # Beschrijving komt uit de API-content (rendered HTML), schoongemaakt.
        content_html = (p.get("content") or {}).get("rendered", "")
        description = None
        if BeautifulSoup:
            dtext = BeautifulSoup(content_html, "lxml").get_text(" ", strip=True)
            dtext = re.sub(r"\s+", " ", dtext).strip()
            if len(dtext) > 40:
                description = dtext[:6000]

        # Detailpagina voor prijs/beds/baths/oppervlak/wijk/foto's/sold-status
        listing_type = "sale"
        ptype = "house"
        price = None
        currency = "XCG"
        beds = baths = area = None
        neighborhood = None
        images: list[str] = []

        try:
            dr = self._fetch(url)
            if dr is not None and dr.status_code == 200 and BeautifulSoup:
                soup = BeautifulSoup(dr.text, "lxml")

                # Sold/silent-sale listings overslaan — niet meer beschikbaar
                badge = soup.select_one(".hero-slide .purpose-badge, .featured-text.purpose-badge")
                if badge and "sold" in badge.get_text(" ", strip=True).lower():
                    return "SOLD"

                # Type (koop/huur + property type) uit de ptype-badge
                ptype_el = soup.select_one(".ptype")
                ptype_text = ptype_el.get_text(" ", strip=True).lower() if ptype_el else ""
                if "rent" in ptype_text:
                    listing_type = "rent"
                if "commercial" in ptype_text:
                    ptype = "commercial"
                elif "lot" in ptype_text:
                    ptype = "land"
                elif "apartment" in ptype_text or "condo" in ptype_text or "apartment" in title.lower():
                    ptype = "apartment"

                # Beds/baths/oppervlak
                icons = soup.select_one(".inline-property-icons")
                if icons:
                    itext = icons.get_text(" ", strip=True)
                    bm = re.search(r"(\d+(?:\.\d+)?)\s*Bedrooms?", itext, re.I)
                    if bm:
                        beds = int(float(bm.group(1)))
                    bam = re.search(r"(\d+(?:\.\d+)?)\s*Bathrooms?", itext, re.I)
                    if bam:
                        # DB-kolom is integer; half badkamers (2.5) naar boven afronden
                        baths = int(-(-float(bam.group(1)) // 1))
                    am = re.search(r"([\d,.]+)\s*M(?:<sup>2</sup>|2|²)?\s*Lot", itext, re.I)
                    if am:
                        area = self.parse_area(am.group(1).replace(",", "") + " m")

                # Prijs — de "active" prijs is de native valuta zoals de site 'm toont
                # (meestal ANG/XCG, soms USD voor bepaalde verhuur-listings). De
                # class-naam (priceANG/priceUSD/priceEUR) verraadt de valuta.
                price_el = soup.select_one(".price.active")
                if price_el:
                    price = self.parse_price(price_el.get_text(" ", strip=True))
                    cls = " ".join(price_el.get("class") or [])
                    if "priceUSD" in cls:
                        currency = "USD"
                    elif "priceEUR" in cls:
                        currency = "EUR"

                # Wijk/locatie
                loc_el = soup.select_one(".meta-loc")
                if loc_el:
                    loc_text = loc_el.get_text(" ", strip=True)
                    neighborhood = loc_text or None

                # Foto's — hoofdgalerij in #heroslider (voorkomt agent-foto's /
                # 'meer woningen'-sidebar die elders op de pagina staan)
                gallery = soup.select_one("#heroslider")
                if gallery:
                    for img in gallery.select("img"):
                        src = img.get("data-src") or img.get("src") or ""
                        if src and not src.startswith("data:"):
                            images.append(src)
                if not images:
                    # Sommige "project"-listings (meerdere units) tonen alleen
                    # YouTube-video's in de heroslider, geen foto's — dan de
                    # og:image (cover) als enige foto pakken.
                    og = soup.select_one('meta[property="og:image"]')
                    if og and og.get("content"):
                        images.append(og["content"])
        except Exception as e:
            self.logger.warning(f"new_winds_realty detail fout ({p.get('slug')}): {e}")

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,
            currency=currency,
            url=url,
            description=description,
            neighborhood=neighborhood,
            bedrooms=beds,
            bathrooms=baths,
            area_sqm=area,
            images=self.clean_images(images, limit=40),
            agent_company=self.AGENT_COMPANY,
        )
