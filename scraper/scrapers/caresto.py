"""Caresto Real Estate scraper (herbouwd)
Site: https://www.caresto.com  (WordPress + custom post type 'caresto_property')

Methode:
  1. De site zit achter een SiteGround PoW-captcha (sgcaptcha). We lossen die
     SHA-1 proof-of-work op in pure Python en bewaren de _I_ cookie.
  2. De lijst komt uit de WP REST API: /wp-json/wp/v2/caresto_property
     (titel, url, taxonomie type/status/buurt, prijstekst in content).
  3. Beds/baths/oppervlak/coords/gallery komen van de detailpagina.
"""
import re
import json
import time
import base64
import hashlib
from ..base_scraper import BaseScraper
from ..models import Listing

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class CarestoScraper(BaseScraper):
    source_name = "caresto"
    BASE = "https://www.caresto.com"
    CANON = "https://caresto.com"
    AGENT_COMPANY = "Caresto Real Estate"

    # ---- SiteGround PoW captcha ----------------------------------------
    @staticmethod
    def _counter_bytes(c: int) -> bytes:
        n = 4 if c > 0xFFFFFF else 3 if c > 0xFFFF else 2 if c > 0xFF else 1
        return c.to_bytes(n, "big")

    def _solve_pow(self, challenge: str) -> tuple[str, int, float]:
        bits = int(challenge.split(":", 1)[0])
        chal = challenge.encode()
        c = 0
        t0 = time.time()
        while True:
            data = chal + self._counter_bytes(c)
            if int.from_bytes(hashlib.sha1(data).digest()[:4], "big") >> (32 - bits) == 0:
                return base64.b64encode(data).decode(), c, time.time() - t0
            c += 1

    def _fetch(self, url: str, tries: int = 4):
        """GET met automatische captcha-oplossing. Retourneert een requests.Response."""
        r = None
        for _ in range(tries):
            r = self.session.get(url, timeout=40)
            if r.status_code == 202 and "sgcaptcha" in r.text:
                m = re.search(r'content="0;([^"]+)"', r.text)
                if not m:
                    continue
                chal_url = self.BASE + m.group(1).replace("&amp;", "&")
                r2 = self.session.get(chal_url, timeout=40)
                mc = re.search(r'sgchallenge="([^"]+)"', r2.text)
                ms = re.search(r'sgsubmit_url="([^"]+)"', r2.text)
                if not (mc and ms):
                    continue
                sol, cnt, dt = self._solve_pow(mc.group(1))
                submit = (
                    self.BASE + ms.group(1)
                    + ("&" if "?" in ms.group(1) else "?")
                    + "sol=" + self._quote(sol)
                    + f"&s={int(dt * 1000)}:{cnt}"
                )
                self.session.get(submit, timeout=40)
                self.logger.info(f"caresto: captcha opgelost (counter={cnt}, {dt:.1f}s)")
                continue
            return r
        return r

    @staticmethod
    def _quote(s: str) -> str:
        from urllib.parse import quote
        return quote(s, safe="")

    # ---- taxonomie -----------------------------------------------------
    def _term_map(self, tax: str) -> dict:
        out = {}
        try:
            r = self._fetch(f"{self.BASE}/wp-json/wp/v2/{tax}?per_page=100")
            for t in r.json():
                out[t["id"]] = t["name"]
        except Exception as e:
            self.logger.warning(f"caresto: kon taxonomie {tax} niet laden: {e}")
        return out

    # ---- main ----------------------------------------------------------
    def scrape(self) -> list[Listing]:
        results: list[Listing] = []

        types = self._term_map("caresto_property_type")
        cats = self._term_map("caresto_property_category")
        hoods = self._term_map("caresto_property_neighborhood")

        page = 1
        props = []
        while page <= 10:
            r = self._fetch(f"{self.BASE}/wp-json/wp/v2/caresto_property?per_page=100&page={page}")
            try:
                batch = r.json()
            except Exception:
                break
            if not isinstance(batch, list) or not batch:
                break
            props.extend(batch)
            total_pages = int(r.headers.get("X-WP-TotalPages", 1) or 1)
            if page >= total_pages:
                break
            page += 1

        self.logger.info(f"caresto: {len(props)} properties uit REST API")

        for p in props:
            try:
                l = self._parse(p, types, cats, hoods)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"caresto parse error ({p.get('slug')}): {e}")
            time.sleep(0.8)  # polite

        self.logger.info(f"Caresto total: {len(results)} listings")
        return results

    def _parse(self, p, types, cats, hoods) -> Listing | None:
        ext_id = str(p.get("id") or p.get("slug") or "")
        if not ext_id:
            return None
        title = (p.get("title") or {}).get("rendered", "").strip()
        url = (p.get("link") or "").replace("://caresto.com", "://www.caresto.com")

        # listing_type uit taxonomie
        type_ids = p.get("caresto_property_type") or []
        type_names = " ".join(types.get(i, "") for i in type_ids).lower()
        listing_type = "rent" if ("huren" in type_names or "huur" in type_names) else "sale"
        # fallback op de prijstekst als de taxonomie leeg is
        if not type_ids:
            ct = (p.get("content") or {}).get("rendered", "").lower()
            if "huurprijs" in ct or "per maand" in ct:
                listing_type = "rent"

        # property_type uit categorie
        cat_ids = p.get("caresto_property_category") or []
        cat_names = " ".join(cats.get(i, "") for i in cat_ids).lower()
        ptype = self._map_ptype(cat_names)

        # buurt
        hood_ids = p.get("caresto_property_neighborhood") or []
        neighborhood = next((hoods.get(i) for i in hood_ids if hoods.get(i)), None)

        # prijs uit content-tekst (XCG / ANG)
        content_html = (p.get("content") or {}).get("rendered", "")
        price = self._price_from_text(content_html)

        # detailpagina voor beschrijving/beds/baths/oppervlak/coords/gallery
        beds = baths = area = lat = lng = None
        images: list[str] = []
        description = None
        try:
            dr = self._fetch(url)
            if dr is not None and dr.status_code == 200:
                beds, baths, area, lat, lng, images, description = self._parse_detail(dr.text, p.get("slug", ""))
        except Exception as e:
            self.logger.warning(f"caresto detail fout ({p.get('slug')}): {e}")

        return Listing(
            source_id=self.source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type=ptype,
            price_ang=price,          # XCG/ANG
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

    def _parse_detail(self, html: str, slug: str):
        text = html
        soup = None
        if BeautifulSoup:
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(" ", strip=True)

        description = None
        if soup is not None:
            entry = soup.select_one(".entry-content") or soup.select_one("article .content")
            if entry:
                dtext = re.sub(r"\s+", " ", entry.get_text(" ", strip=True)).strip()
                if len(dtext) > 40:
                    description = dtext[:6000]
        if not description:
            meta = None
            if soup is not None:
                meta = soup.select_one('meta[name="description"]') or soup.select_one('meta[property="og:description"]')
            if meta and meta.get("content"):
                description = re.sub(r"\s+", " ", meta["content"]).strip() or None

        beds = self._int(re.search(r"(\d+)\s*slaapkamer", text))
        baths = self._int(re.search(r"(\d+)\s*badkamer", text))
        area = None
        am = re.search(r"Oppervlakte\s*([\d.,]+)\s*m", text)
        if am:
            area = self.parse_area(am.group(1) + " m")

        lat = lng = None
        mm = re.search(r'id="map-markers">\s*(\[.*?\])\s*</script>', html, re.S)
        if mm:
            try:
                marker = json.loads(mm.group(1))[0]
                clat = float(marker["latitude"])
                clng = float(marker["longitude"])
                # alleen bewaren als de coords op/rond Curaçao liggen
                if 11.9 <= clat <= 12.45 and -69.25 <= clng <= -68.6:
                    lat, lng = clat, clng
            except Exception:
                pass

        # gallery: jpg/png uploads, size-varianten dedupen, logo weg
        raw = re.findall(
            r'https?://(?:www\.)?caresto\.com/wp-content/uploads/[^\s"\')]+\.(?:jpg|jpeg|png)',
            html, flags=re.I,
        )
        images = []
        seen = set()
        for u in raw:
            if "logo" in u.lower():
                continue
            base = re.sub(r"-\d+x\d+(?=\.\w+$)", "", u)
            if base not in seen:
                seen.add(base)
                images.append(base)
        return beds, baths, area, lat, lng, images, description

    @staticmethod
    def _int(m):
        return int(m.group(1)) if m else None

    def _price_from_text(self, html: str) -> float | None:
        text = html
        if BeautifulSoup:
            text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        # bv. "Vraagprijs: XCG 209.000,-" of "Huurprijs: XCG 6.000,- per maand"
        m = re.search(r"(?:XCG|ANG|Cg\.?|NAf)\s*([\d.]+)", text, flags=re.I)
        if m:
            return self.parse_price(m.group(1))
        return None

    @staticmethod
    def _map_ptype(cat: str) -> str:
        if any(w in cat for w in ["kavel", "bouwkavel"]):
            return "land"
        if "appartement" in cat:
            return "apartment"
        if any(w in cat for w in ["commercieel", "bedrijf", "kantoor", "winkel"]):
            return "commercial"
        return "house"
