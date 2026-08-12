"""Vastiva scraper (voorheen/merk "FINA" — makelaars-PORTAAL, geen enkele
eigen makelaar)
Site: https://www.vastiva.nl — Nederlands vastgoedportaal (net als Funda),
géén WordPress (custom PHP/nginx-stack, geen wp-json). Curaçao is één van
de landen die op het portaal wordt aangeboden onder `/fina/` (Curaçao-
landingspagina, merk in de kop-tekst nog "FINA", maar logo/title-tag/
og:site_name zijn overal "Vastiva" — kennelijk een rebranding, "FINA" leeft
alleen nog voort in bestaande paginacopy).

**BELANGRIJK verschil met alle eerdere "traditional"-scrapers: dit is GEEN
losse makelaar met één vast kantoor, maar een PORTAAL waarop meerdere
individuele Nederlandse/Curaçaose makelaars/particuliere aanbieders hun
eigen listings plaatsen** (bevestigd: op de listing-pagina's staat een
`div.medewerker_aanbod`-blok met een WISSELENDE naam + rol, bv. "Edith
Pattinaja — Owner" op de meeste Curaçao-listings, maar ook "Mick Janssens —
Vastgoedspecialist bij Janssens Vastgoed" en "Zyta de Koeijer — Real Estate
Agent" op andere listings van hetzelfde portaal). Net als bij de
Facebook-scraper (agency_hint/is_private) wordt hier dus PER LISTING het
werkelijke kantoor/de werkelijke naam uitgelezen i.p.v. één vaste
AGENT_COMPANY-constante zoals bij alle andere "traditional"-scrapers.
Bewuste keuze om dit ondanks het portaal-karakter toch te bouwen: een deel
van de aanbieders erachter (bv. "Janssens Vastgoed") heeft zelf geen eigen
website, dus dit is voor die aanbieders de ENIGE manier om hun Curaçao-
listings te vangen. Bij "Owner" zonder een "bij <kantoor>"-suffix (de
meeste listings) is er geen apart kantoor vermeld — dan valt agent_company
terug op het portaal-merk "Vastiva" zelf.

Methode:
  1. robots.txt EERST gecheckt: alleen 2 specifieke PHP-scripts en een
     querystring-variant van /maandlasten/ disallowed, verder alles
     toegestaan, geen crawl-delay, geen ClaudeBot/AI-vermelding. Permissief.
  2. Geen wp-json (geen WordPress) — wél een klassieke sitemap-index
     (`/sitemap_index.xml` → `sitemap-aanbod.xml`, ruim 50.000 URLs
     wereldwijd, dus NIET los ophalen zonder filter).
  3. **Valkuil: een kale substring-match op "curacao" in de sitemap-URL's
     geeft false positives** — er staan Nederlandse verhuur-listings tussen
     met een straatnaam "Curacaostraat" (Amsterdam). Filter daarom altijd
     op het EXACTE pad-segment na `/koop/` of `/huur/` (`.../koop/curacao/...`
     of `.../huur/curacao/...`), nooit op een kale substring-check.
  4. Kenmerken staan in een schone `<dl class="kenmerken-list"><dt>Label</dt>
     <dd>Waarde</dd></dl>`-structuur — dt/dd-paren op label matchen i.p.v.
     positie, werkt voor zowel woningaanbod als beleggingspanden (die laatste
     missen soms slaapkamers/badkamers, heeft dan een BAR%-veld i.p.v.).
  5. Prijs-prefix wisselt PER listing tussen een kaal "$"-symbool, het volledig
     uitgeschreven woord "Euro", en een HTML-entity "&euro;" (wordt door
     BeautifulSoup al gewoon als "€"-teken teruggegeven bij get_text()) —
     dezelfde aanpak als Real Estate Caribe/Kostabon/TOP Makelaar: €-prefix
     ×1,95 naar XCG, $-prefix blijft natieve USD, geen prefix → sanity-check
     en anders overslaan (nooit gezien op deze set, voor de zekerheid).
  6. Neighborhood: de "Omschrijving <type> te koop in <plaats>"-kop (h3) is
     betrouwbaarder dan de bovenste portaal-brede breadcrumb-blokken (die
     bij een aantal listings alleen tot "Curacao" komen, niet dieper) —
     regex op die h3-tekst voor de buurt/plaats.
  7. Geen coördinaten op de pagina gevonden — latitude/longitude blijven None.
  8. Alle 22 gevonden Curaçao-listings zijn 'koop' (sale); geen 'huur'
     (rent) Curaçao-listings gezien in de sitemap op controledatum.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.vastiva.nl"
SITEMAP_INDEX = f"{BASE}/sitemap_index.xml"
SITEMAP_AANBOD = f"{BASE}/sitemap-aanbod.xml"

# Alleen paden waar het segment ná /koop/ of /huur/ letterlijk "curacao" is
# (voorkomt false positives zoals "Curacaostraat" in Amsterdam).
CURACAO_PATH_RE = re.compile(r"/(koop|huur)/curacao(/|$)", re.I)

PRICE_RE = re.compile(r"(\$|€|Euro)?\s*([\d.,]+)", re.I)
AREA_NUM_RE = re.compile(r"([\d.,]+)\s*m", re.I)
NEIGHBORHOOD_RE = re.compile(r"te (?:koop|huur) in ([^<\n]+)", re.I)
AGENT_ROLE_RE = re.compile(r"bij\s+(.+)", re.I)

# Property-type keyword-matching gebeurt UITSLUITEND op de "Soort woning"/
# "Soort beleggingspanden"/"Soort vakantiewoning"-WAARDE (dt/dd-paar), nooit
# op de volledige kenmerken-tekst — anders geeft het label "Perceeloppervlakte"
# een valse "land"-hit via de substring "perceel" (bekende valkuil, zelfde
# les als bij eerdere scrapers: eerst op een schoon typeveld, niet op vrije
# tekst met andere labels erin).
APARTMENT_HINTS = ("appartement", "penthouse", "studio")
COMMERCIAL_HINTS = ("beleggingspand", "bedrijfspand", "kantoor", "winkel")
LAND_HINTS = ("bouwgrond", "kavel", "grond", "perceel te koop")
HOUSE_HINTS = ("villa", "woning", "huis")


class VastivaScraper(BaseScraper):
    source_name = "vastiva"
    AGENT_COMPANY_DEFAULT = "Vastiva"

    def scrape(self) -> list[Listing]:
        soup = self.get(SITEMAP_AANBOD)
        if soup is None:
            self.logger.error("sitemap-aanbod.xml niet opgehaald")
            return []

        urls = []
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            m = CURACAO_PATH_RE.search(url)
            if not m:
                continue
            urls.append((url, "sale" if m.group(1).lower() == "koop" else "rent"))

        self.logger.info(f"Vastiva: {len(urls)} Curaçao-listing(s) gevonden in sitemap-aanbod.xml")

        results = []
        for url, listing_type in urls:
            try:
                l = self._scrape_detail(url, listing_type)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Listing error ({url}): {e}")
        return results

    def _scrape_detail(self, url: str, listing_type: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        h1_tag = soup.select_one("h1")
        title = self.clean_text(h1_tag.get_text()) if h1_tag else None
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if not title:
            title = slug.replace("-", " ").title()

        # dt/dd-paren op LABEL in een dict verzamelen (nooit op positie
        # vertrouwen — sommige dl's missen een veld, bv. beleggingspanden
        # zonder slaapkamers/badkamers).
        kenmerken = {}
        for dl in soup.select("dl.kenmerken-list"):
            pairs = dl.find_all(["dt", "dd"])
            i = 0
            while i < len(pairs) - 1:
                if pairs[i].name == "dt" and pairs[i + 1].name == "dd":
                    label = self.clean_text(pairs[i].get_text(" ", strip=True)) or ""
                    value = self.clean_text(pairs[i + 1].get_text(" ", strip=True)) or ""
                    kenmerken[label.lower()] = value
                    i += 2
                else:
                    i += 1

        price = None
        currency = "XCG"
        prijs_val = kenmerken.get("vraagprijs") or kenmerken.get("huurprijs")
        if prijs_val:
            m = PRICE_RE.search(prijs_val)
            if m:
                prefix = (m.group(1) or "").strip()
                amount = self.parse_price(m.group(2))
                if amount is not None:
                    if prefix == "$":
                        price = amount
                        currency = "USD"
                    elif prefix in ("€", "Euro"):
                        price = round(amount * 1.95, 2)
                        currency = "XCG"
                    else:
                        price = amount
                        currency = "XCG"
                if price is not None and price < 5000:
                    price = None  # sanity-ondergrens, zelfde les als eerdere scrapers

        bedrooms = self.parse_int(kenmerken.get("slaapkamers", ""))
        bathrooms = None
        badkamers_val = kenmerken.get("badkamers")
        if badkamers_val:
            try:
                bathrooms = round(float(badkamers_val.replace(",", ".")))
            except ValueError:
                bathrooms = None

        area_sqm = None
        woon_val = kenmerken.get("woonoppervlakte")
        perceel_val = kenmerken.get("perceeloppervlakte")
        m = AREA_NUM_RE.search(woon_val) if woon_val else None
        if m:
            area_sqm = self.parse_area(m.group(0))
        elif perceel_val:
            m = AREA_NUM_RE.search(perceel_val)
            if m:
                area_sqm = self.parse_area(m.group(0))

        # Soort-veld (uitsluitend hierop keyword-matchen voor property_type,
        # zie module-docstring/comment bij de HINTS-constantes hierboven).
        soort_val = (
            kenmerken.get("soort woning")
            or kenmerken.get("soort beleggingspanden")
            or kenmerken.get("soort vakantiewoning")
            or ""
        )

        # Neighborhood uit de "Omschrijving <type> te koop/te huur in <plaats>"-kop.
        neighborhood = None
        h3 = soup.find("h3", string=re.compile(r"^Omschrijving", re.I))
        if h3:
            m = NEIGHBORHOOD_RE.search(h3.get_text(" ", strip=True))
            if m:
                neighborhood = self.clean_text(m.group(1))

        # Beschrijving: het <p>-blok in de fadeout-text-div direct na de
        # Omschrijving-kop.
        description = None
        fadeout = soup.select_one(".fadeout-text")
        if fadeout:
            description = self.clean_text(fadeout.get_text(" ", strip=True))

        # LET OP: `/upload_directory/` bevat portaal-brede menu-iconen en het
        # partner-pasfoto (bekende valkuil, eerst gezien tijdens live-test) —
        # de echte woningfoto's staan in een apart pad `/upload_aanbod/...`
        # met class `aanbod_image`. Site gebruikt ROOT-RELATIEVE src's (geen
        # domein) — altijd absoluut maken vóór clean_images(), anders breekt
        # de galerij in de frontend.
        images = self.clean_images(
            [self.abs_url(BASE, img.get("src")) for img in soup.select("img.aanbod_image") if img.get("src")]
        )

        # Agent/kantoor: div.medewerker_aanbod h4 -> "Naam<br><small>Rol [bij Kantoor]</small>"
        agent_name = None
        agent_company = self.AGENT_COMPANY_DEFAULT
        medewerker = soup.select_one("div.medewerker_aanbod h4")
        if medewerker:
            small = medewerker.select_one("small")
            role_text = self.clean_text(small.get_text()) if small else None
            name_only = medewerker.get_text(" ", strip=True)
            if role_text and name_only.endswith(role_text):
                name_only = name_only[: -len(role_text)].strip()
            agent_name = self.clean_text(name_only)
            if role_text:
                m = AGENT_ROLE_RE.search(role_text)
                if m:
                    agent_company = self.clean_text(m.group(1)) or self.AGENT_COMPANY_DEFAULT

        hint_text = soort_val.lower() or (title or "").lower()
        if any(h in hint_text for h in COMMERCIAL_HINTS):
            property_type = "commercial"
        elif any(h in hint_text for h in APARTMENT_HINTS):
            property_type = "apartment"
        elif any(h in hint_text for h in LAND_HINTS):
            property_type = "land"
        elif any(h in hint_text for h in HOUSE_HINTS):
            property_type = "house"
        else:
            property_type = "house"

        return Listing(
            source_id=self.source_id,
            external_id=slug,
            title=title or "Woning Curaçao",
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
            latitude=None,
            longitude=None,
            images=images,
            agent_name=agent_name,
            agent_company=agent_company,
        )
