"""Baia Vista scraper (priority 6)
Site: https://baiavista.com — WordPress, zelf-gehost (nginx, gebouwd door
"The Web Bakery") — GEEN WordPress.com/WPCloud, dus geen verhoogd risico op
GitHub Actions IP-blokkade zoals bij New Winds Realty. Nieuwbouw-appartementen-
/penthousecomplex in Santa Catharina (Hòfi Saint George, 292 Road to Santa
Catharina, Westpunt-regio) — eigen doorlopende te-koop-inventaris, zelfde
categorie als Kings View Residences/Blue Bay Hills Residences/Mambo Developers.

Gevonden via gerichte WebSearch op "vastgoed investering Curaçao 2026" — het
nieuwbouw-projectgerichte kanaal (nog niet uitgeput, in tegenstelling tot het
al-uitgeputte generieke makelaarsnaam-kanaal).

**Belangrijk, eerst gecheckt vóór bouwen: dit project wordt AL deels vermarkt
via de bestaande Vastiva-scraper (2 units in Supabase, "Baia Vista nieuwbouw
appartement, begane grond/eerste verdieping fase 2"), maar baiavista.com zelf
(de ontwikkelaarsite) heeft een VEEL vollediger eigen inventaris — 100
unit-URL's in `home-sitemap.xml` t.o.v. 2 via Vastiva. Dus GEEN pure
duplicatie zoals bij Metro Residences/Grand View Residences (waar de
bestaande scraper de volledige inventaris al had) — hier voegt een aparte
scraper substantieel nieuwe listings toe.**

Methode:
  1. GET `/home-sitemap.xml` (custom "woning"-CPT, Yoast-sitemap) — 100
     unit-URL's (`/woning/<slug>/`). Geen paginering (`sitemap_index.xml`
     noemt maar één `home-sitemap.xml`).
  2. Per unit-pagina (Nederlandstalige default-versie, geen `/en/`-prefix
     nodig): `dl.home-type__details` bevat een schone `<dt>`/`<dd>`-
     label/waarde-lijst: Woningnummer, Type woning, Etage, Fase,
     Vloeroppervlakte, Terrasoppervlakte, Oriëntatie, Aantal slaapkamers,
     Beschikbaarheid, (alleen bij status Beschikbaar) Koopsom. ALTIJD als
     dict per label parsen (dt/dd-paren), zelfde conventie als GS Real
     Estate/Burbach Roycroft.
  3. **Status-valkuil, bevestigd via volledige crawl van alle 100 units:
     "Beschikbaarheid" kent VIJF waarden — "Beschikbaar" (25, actief),
     "Onder optie" (6), "Verkocht" (38), "Verkocht onder voorbehoud" (1) en
     "Binnenkort beschikbaar" (30, nog niet in verkoop).** "Binnenkort
     beschikbaar" bevat het woord "beschikbaar" als SUBSTRING maar betekent
     NIET actief-te-koop — dus altijd een EXACTE match op "beschikbaar"
     (lowercase, getrimd) vereist, nooit een substring-check, anders lekken
     de 30 nog-niet-actieve units mee als actief.
  4. Koopsom-veld alleen aanwezig bij status "Beschikbaar", bv.
     "XCG 1.300.000,-" of "XCG 850.000.-" (wisselende leesteken-notatie
     tussen units, punt-of-komma vóór het streepje) — altijd native XCG,
     `self.parse_price()` (die toch alle non-digits strip) werkt hier voor
     beide varianten identiek correct.
  5. Titel: `<h1>` op de pagina (bv. "Appartement C2" / "Penthouse K5").
  6. Property-type: "Type woning" = "Appartement" of "Penthouse" → beide
     "apartment" (zelfde conventie als Blue Bay Hills Residences, dat
     penthouses ook als apartment-subtype behandelt binnen één complex).
  7. Badkamers: geen apart dt/dd-veld — staat alleen in de vrije
     Kenmerken-tekst ("Twee/Drie badkamers en-suite"). Nederlandse
     telwoorden (een/twee/drie/vier/vijf) → int via regex, zelfde aanpak
     als de Nederlandse-komma-badkamer-afronding elders in de set.
  8. Beschrijving: intro-tagline (`div.header__intro p`) + Kenmerken-lijst
     (`ul.details__list li.details__item`) samengevoegd.
  9. Foto's: `div.header__slider img` (grote headerfoto) +
     `div.home-type--slider img` (swiper-slides) — `src`-attribuut bevat al
     de grootste variant, geen aparte resolutie-selectie nodig.
 10. Geen coördinaten op de pagina gevonden — latitude/longitude blijven
     None. Neighborhood = "Santa Catharina" (bevestigde bestaande waarde in
     `kas_listings`, matcht het "292 Road to Santa Catharina"-adres in de
     footer).
 11. robots.txt: standaard Yoast-blok, `Disallow:` leeg (alles toegestaan),
     geen crawl-delay opgegeven — standaard REQUEST_DELAY (2-5s) aanhouden.
     100 detail-requests per run duurt daardoor langer dan de meeste andere
     scrapers (~5-8 minuten), ruim binnen het GH Actions-timeoutbudget
     (240 min totaal, deze staat achteraan in `DEFAULT_SOURCES` vóór
     century21).
 12. `external_id` = woningnummer (bv. "C2", "K5") — uniek per unit,
     bevestigd geen duplicaten in de sitemap (100 unieke slugs = 100 unieke
     woningnummers).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

SITEMAP = "https://baiavista.com/home-sitemap.xml"
PROJECT_NAME = "Baia Vista"

NL_NUM = {"een": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6}
BATHROOM_RE = re.compile(r"\b(een|twee|drie|vier|vijf|zes)\b\s+badkamer", re.I)


class BaiaVistaScraper(BaseScraper):
    source_name = "baia_vista"
    AGENT_COMPANY = "Baia Vista"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<url>\s*<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if "/woning/" in u]
        self.logger.info(f"Baia Vista: {len(urls)} unit-URL('s) in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Baia Vista: {len(results)} actieve units van {len(urls)} totaal")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        dl = soup.find("dl", class_="home-type__details")
        if dl is None:
            return None

        details: dict[str, str] = {}
        for dt in dl.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                label = self.clean_text(dt.get_text())
                value = self.clean_text(dd.get_text(" "))
                if label and value:
                    details[label] = value

        # EXACTE match — "Binnenkort beschikbaar" bevat "beschikbaar" als
        # substring maar is NIET actief-te-koop (zie docstring punt 3).
        status = (details.get("Beschikbaarheid") or "").strip().lower()
        if status != "beschikbaar":
            return None

        external_id = details.get("Woningnummer") or url.rstrip("/").split("/")[-1]

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else f"{PROJECT_NAME} {external_id}"
        if not title:
            title = f"{PROJECT_NAME} {external_id}"

        price = None
        koopsom = details.get("Koopsom")
        if koopsom:
            price = self.parse_price(koopsom)

        area_sqm = self.parse_area(details.get("Vloeroppervlakte"))
        bedrooms = self.parse_int(details.get("Aantal slaapkamers"))

        features = [self.clean_text(li.get_text()) for li in soup.select("ul.details__list li.details__item")]
        features = [f for f in features if f]
        features_text = " ".join(features)

        bathrooms = None
        bm = BATHROOM_RE.search(features_text)
        if bm:
            bathrooms = NL_NUM.get(bm.group(1).lower())

        desc_parts = []
        tagline_el = soup.select_one("div.header__intro p")
        if tagline_el:
            tagline = self.clean_text(tagline_el.get_text(" "))
            if tagline:
                desc_parts.append(tagline)
        if features:
            desc_parts.append(" / ".join(features))
        fase = details.get("Fase")
        if fase:
            desc_parts.append(f"{fase}.")
        description = self.clean_text(" ".join(desc_parts)) if desc_parts else None

        images = self.clean_images(
            [
                img.get("src")
                for img in soup.select("div.header__slider img, div.home-type--slider img")
                if img.get("src")
            ]
        )

        return Listing(
            source_id=self.source_id,
            external_id=str(external_id),
            title=title,
            listing_type="sale",
            property_type="apartment",
            price_ang=price,
            currency="XCG",
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,
            neighborhood="Santa Catharina",
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
