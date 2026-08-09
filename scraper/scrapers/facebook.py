"""
Facebook Marketplace scraper via Playwright (priority 10)
Vereist: fb_cookies.json in scraper/ root (export via EditThisCookie extensie)

BELANGRIJK — locatie (9 aug 2026):
De marketplace-URL met een tekst-slug ("curacao") wordt door Facebook genegeerd
en valt terug op de opgeslagen Marketplace-locatie van het account. Als die
locatie niet handmatig op Willemstad, Curacao staat, scraped dit script de
locatie van het account (bv. San Francisco) in plaats van Curacao — geen
foutmelding, gewoon compleet verkeerde listings. Zie scraper/README of
kaskorsou-status.md voor de eenmalige handmatige stap om dit recht te zetten.
"""
import json, re, time, random, logging
from pathlib import Path
from ..models import Listing, detect_agency
from ..config import SOURCES

PRIVATE_KEYWORDS = ["particulier", "prive", "privé", "eigenaar", "zelf", "no agent", "by owner"]
AGENCY_KEYWORDS  = ["remax", "re/max", "sunbelt", "century21", "century 21", "era ", "makelaar"]
# UI-tekst die Facebook zelf voor de fotocarrousel van DEZE advertentie gebruikt.
# Alles zonder deze prefix is een aanbevolen/gerelateerde advertentie van iemand
# anders (gitaren, ovens, fietsen...) die ook als <img> op dezelfde pagina staat.
REAL_PHOTO_ALT_PREFIXES = ("foto van", "photo of")
# Regels van FB zelf ("2 weken geleden geplaatst", "Nu beschikbaar") die niet de
# beschrijving zijn, ook al staan ze in dezelfde soort tekstelementen.
DESC_SKIP_MARKERS = ["geleden geplaatst", " ago", "nu beschikbaar", "now available"]

logger = logging.getLogger("facebook")

COOKIES_FILE = Path(__file__).parent.parent / "fb_cookies.json"
URLS = [
    ("rent",  "https://www.facebook.com/marketplace/curacao/propertyrentals"),
    ("sale",  "https://www.facebook.com/marketplace/curacao/propertyforsale"),
]


class FacebookScraper:
    source_name = "facebook"

    def scrape(self, max_listings: int = 100) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Run: pip install playwright && playwright install chromium")
            return []

        if not COOKIES_FILE.exists():
            logger.error(f"Cookies niet gevonden: {COOKIES_FILE}")
            return []

        source_id = SOURCES[self.source_name]["id"]
        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            SAMESITE_MAP = {
                "no_restriction": "None",
                "unspecified": "Lax",
                "lax": "Lax",
                "strict": "Strict",
                "none": "None",
            }
            with open(COOKIES_FILE) as f:
                raw_cookies = json.load(f)
            cookies = []
            for c in raw_cookies:
                cookie = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c["domain"],
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                    "httpOnly": c.get("httpOnly", False),
                    "sameSite": SAMESITE_MAP.get(c.get("sameSite", "").lower(), "Lax"),
                }
                if c.get("expirationDate"):
                    cookie["expires"] = int(c["expirationDate"])
                cookies.append(cookie)
            ctx.add_cookies(cookies)

            page = ctx.new_page()

            # Sanity check: als de account-locatie niet in Curacao staat, heeft
            # verder scrapen geen zin (levert gegarandeerd verkeerde listings op).
            loc_ok = self._check_location(page)
            if not loc_ok:
                logger.error(
                    "Marketplace-locatie van het account staat niet op Curacao "
                    "(zie module-docstring) — FB-run overgeslagen om geen "
                    "verkeerde listings te schrijven."
                )
                browser.close()
                return []

            for listing_type, url in URLS:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)

                if "login" in page.url.lower():
                    logger.error("Niet ingelogd — cookies verlopen, herexporteer.")
                    break

                seen = set()
                scrolls = max_listings // 12
                for i in range(scrolls):
                    cards = page.query_selector_all("a[href*='/marketplace/item/']")
                    for card in cards:
                        try:
                            listing = self._parse(card, source_id, listing_type)
                            if listing and listing.external_id not in seen:
                                seen.add(listing.external_id)
                                results.append(listing)
                        except Exception:
                            pass
                    logger.info(f"FB {listing_type} scroll {i+1}/{scrolls}: {len(seen)} listings")
                    page.evaluate("window.scrollBy(0, window.innerHeight * 0.85)")
                    time.sleep(random.uniform(1.5, 3.5))

            # Tweede pas: elke advertentie apart openen voor de echte fotos
            # (gefilterd, geen aanbevolen-advertenties van anderen) en de volledige
            # omschrijving. Kost tijd (1 paginabezoek per listing) maar dat is de
            # enige manier om dit betrouwbaar te doen.
            for idx, listing in enumerate(results):
                self._enrich_from_detail(page, listing)
                logger.info(f"FB detail {idx + 1}/{len(results)} verrijkt: {listing.title}")
                time.sleep(random.uniform(1.5, 3))

            browser.close()

        logger.info(f"Facebook: {len(results)} listings total")
        return results

    def _check_location(self, page) -> bool:
        """True als de Marketplace-locatie van het account Curacao is."""
        try:
            page.goto("https://www.facebook.com/marketplace/category/propertyrentals/",
                       wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
            loc_btn = page.query_selector("div[aria-label^='Locatie:'], div[aria-label^='Location:']")
            label = loc_btn.get_attribute("aria-label") if loc_btn else ""
            label = (label or "").lower()
            return "cura" in label or "willemstad" in label
        except Exception as e:
            logger.warning(f"Kon locatie niet checken: {e}")
            return False

    def _enrich_from_detail(self, page, listing: "Listing") -> None:
        """Haalt de volledige beschrijving en de echte fotos van de advertentie op."""
        try:
            page.goto(listing.url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 3.5))

            try:
                more_btn = page.query_selector(
                    "div[role='button']:has-text('Meer weergeven'), "
                    "div[role='button']:has-text('See more')"
                )
                if more_btn:
                    more_btn.click(timeout=3000)
                    time.sleep(0.5)
            except Exception:
                pass

            desc, best_len = None, 0
            for el in page.query_selector_all("span[dir='auto'], div[dir='auto']"):
                try:
                    t = (el.inner_text() or "").strip()
                except Exception:
                    continue
                if not t or len(t) < 20:
                    continue
                low = t.lower()
                if len(t) < 80 and any(m in low for m in DESC_SKIP_MARKERS):
                    continue
                if len(t) > best_len:
                    best_len, desc = len(t), t
            if desc:
                listing.description = desc

            real_imgs = []
            for img in page.query_selector_all("img[alt]"):
                try:
                    alt = (img.get_attribute("alt") or "").strip().lower()
                    src = img.get_attribute("src")
                except Exception:
                    continue
                if src and alt.startswith(REAL_PHOTO_ALT_PREFIXES):
                    real_imgs.append(src)
            if real_imgs:
                listing.images = real_imgs[:15]
        except Exception as e:
            logger.debug(f"Detail-enrich mislukt voor {listing.external_id}: {e}")

    def _parse(self, card, source_id: str, listing_type: str) -> Listing | None:
        href = card.get_attribute("href") or ""
        m = re.search(r"/item/(\d+)", href)
        if not m:
            return None
        ext_id = m.group(1)
        url = f"https://www.facebook.com{href}" if href.startswith("/") else href

        text = card.inner_text().strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Kaartlayout is [prijs, titel, locatie] — lines[0] is dus de PRIJS, niet
        # de titel (was eerder verkeerd om, gaf "US$ 900" als titel).
        title = lines[1] if len(lines) > 1 else (lines[0] if lines else "Facebook listing")
        price_text = next((l for l in lines if any(c in l for c in ["ANG", "$", "NAf", "€"])), "")
        # FB toont bedragen als "US$ 1.000" (punt als duizendtal-scheiding, geen
        # decimalen) — alleen niet-cijfers wegstrippen voorkomt dat "1.000" als
        # 1.0 wordt gelezen (was een factor-1000 bug).
        price_num = re.sub(r"[^\d]", "", price_text)
        price = float(price_num) if price_num else None

        imgs = [img.get_attribute("src") for img in card.query_selector_all("img[src]")]
        neighborhood = lines[2] if len(lines) > 2 else None

        # Deduplicatie: detecteer of dit een makelaar of particulier is
        full_text = " ".join(lines).lower()
        is_private = any(kw in full_text for kw in PRIVATE_KEYWORDS)
        agency_hint = detect_agency(full_text)

        # Als het een bekende makelaar is → markeer als potentieel duplicaat
        # (orchestrator kan later matchen met kas_listings op prijs+buurt)
        if agency_hint and not is_private:
            # Sla op maar markeer — orchestrator doet de match
            pass

        return Listing(
            source_id=source_id,
            external_id=ext_id,
            title=title,
            listing_type=listing_type,
            property_type="house",
            price_ang=price,
            url=url,
            neighborhood=neighborhood,
            # Kaart-thumbnail als voorlopige/fallback-foto — wordt in de
            # detail-enrichment-pas overschreven door de echte, gefilterde fotos.
            images=[i for i in imgs if i][:1],
            description=None,
            bedrooms=None,
            bathrooms=None,
            area_sqm=None,
            latitude=None,
            longitude=None,
            is_private=is_private,
            agency_hint=agency_hint,
        )
