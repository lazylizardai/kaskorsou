"""Burbach Roycroft scraper (priority 6)
Site: https://www.burbachroycroft.com — WordPress + "Mediakanjers"-thema
(page-builder, MK Editor / mk_sectie-classes). Nederlands luxe-makelaarskantoor
met een eigen fysiek kantoor op Curaçao (Rif Fort Village, Willemstad, telefoon
+599-code) naast een NL-vestiging — geadverteerd als "de nummer #1 makelaar
van Curaçao". Gevonden via een nieuw kanaal: gerichte WebSearch op specifieke
wijknamen (Emmastad/Julianadorp/Damacor/Zeelandia/Mahaai) i.p.v. de eerder
uitgeputte generieke "nieuwe makelaar"-zoektermen.

**Belangrijk: de site voert ÉÉN gedeelde WordPress custom-post-type
("woningen") voor ZOWEL Nederlandse/Spaanse/Zwitserse als Curaçaose panden.**
Van de 55 unieke NL-canonieke listing-URL's in `woningen-sitemap.xml` is
ruwweg 22 daadwerkelijk Curaçao (rest: Nederland, Spanje, Zwitserland,
Terschelling e.d.) — dus ALTIJD het `Land`-kenmerk per pagina checken, nooit
op de sitemap zelf filteren.

Methode:
  1. GET `/woningen-sitemap.xml`, alleen de canonieke `/woning/...`-URL's
     nemen (niet de `/en/listing/...`-duplicaten die als apart `<url>`-blok
     in dezelfde sitemap staan — anders dubbele scrapes van dezelfde listing).
  2. Per listing-pagina: `div.woningstatus` bevat de statuslabel-tag
     ("Verkocht", "Huur", "Nieuw" of leeg/afwezig voor gewoon actief-te-koop).
     **Belangrijke valkuil, ontdekt via steekproef: meerdere listings met
     `div.woningstatus` = "Verkocht" hebben het `Status`-kenmerk-veld verderop
     op de pagina alsnog gewoon op "Beschikbaar" staan** (zelfde patroon als
     bij GS Real Estate/Curaçao Houses: kenmerken-tabel niet altijd
     bijgewerkt bij verkoop) — dus ALTIJD op `div.woningstatus` filteren,
     nooit op het `Status`-kenmerk vertrouwen voor sold/actief.
  3. `div.kenmerk`-blokken bevatten steeds een label (`span`/`h5`) + waarde
     (`span`/`strong`)-paar. Elke pagina heeft TWEE keer (bijna) dezelfde set
     kenmerken (één beknopt blok bovenaan, één vollediger blok verderop) —
     een dict die overschrijft bij dubbele labels pakt zo automatisch de
     meest complete waarde (het tweede, uitgebreidere blok wint).
  4. `Land`-kenmerk moet exact "Curaçao" zijn (met of zonder spatie/accent-
     variant) — anders overslaan (Nederlandse/Spaanse/Zwitserse listings op
     dezelfde site).
  5. Prijs: `Vraagprijs` (koop) of `Huurprijs` (huur) kenmerk, vrije tekst
     met wisselende valuta-prefix per listing — bij steekproef gezien: EUR
     ("€ 750.000,-"), USD ("$ 850.000,-") en gemengde labels ("EUR 850.000,-
     Meubels onderhandelbaar"). PRICE_RE (zelfde patroon als andere EUR/USD-
     scrapers in deze set) pakt prefix + cijferblok in één regex-groep om
     duizendtal-scheidingstekens niet te breken. EUR → ×1,95 naar XCG (zelfde
     vaste koers als de rest van de set), USD nativ, geen prefix → XCG.
     Sommige actieve listings tonen "Prijs op aanvraag" i.p.v. een bedrag —
     dan blijft price gewoon None, listing blijft wel actief.
  6. listing_type: `Huurprijs`-kenmerk aanwezig → rent; anders (incl.
     `Vraagprijs` of prijs-op-aanvraag) → sale. `div.woningstatus` == "Huur"
     als extra fallback-signaal.
  7. Oppervlakte: `Woonoppervlakte` (bebouwd) heeft voorrang boven
     `Perceel`/`Perceeloppervlakte` (kavel) — beide bevatten soms extra tekst
     ("425 m² inclusief overdekt terras"), dus alleen het eerste cijferblok
     pakken.
  8. Slaap-/badkamers: `Slaapkamers`/`Badkamers`-kenmerk, badkamers kan een
     halve kamer zijn ("2,5") — Nederlandse komma naar punt, dan `round()`
     naar int (zelfde conventie als de rest van de set, want
     `kas_listings.bathrooms` is integer).
  9. Beschrijving: `div.toptxt` (intro-alinea) + `div.bottomtxt` (rest van de
     verkooptekst) samengevoegd — dit zijn twee aparte containers in de
     page-builder-layout, los van elkaar.
 10. Foto's: fancybox-gallerylinks (`a[data-fancybox]` → `href`), dit zijn al
     de originele hoge-resolutie bestanden, geen aparte media-lookup nodig.
 11. robots.txt: alleen het standaard Yoast-blok, `Disallow:` leeg (alles
     toegestaan), geen crawl-delay opgegeven — dus de standaard
     REQUEST_DELAY van de base-scraper (2-5s) aanhouden. Server is nginx
     (zelf-gehost/CDN), geen WordPress.com/WPCloud — geen verhoogd risico op
     GitHub Actions IP-blokkade.
"""
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

SITEMAP = "https://www.burbachroycroft.com/woningen-sitemap.xml"
EUR_TO_XCG = 1.95

PRICE_RE = re.compile(r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\s*([\d][\d.,]{1,14})", re.I)
AREA_RE = re.compile(r"([\d]+(?:[.,]\d+)?)\s*m")

SOLD_STATUS_WORDS = ("verkocht", "verhuurd", "onder optie", "in optie", "sold", "rented")

TYPE_KEYWORDS = (
    ("commercial", ("commercieel", "kantoor", "bedrijfspand", "winkelpand", "warehouse")),
    ("land", ("kavel", "bouwgrond", "perceel", "bouwperceel", "lot")),
    ("apartment", ("appartement", "penthouse", "studio")),
    ("house", ("villa", "woning", "huis", "landhuis", "boerderij", "chalet", "bungalow")),
)


class BurbachRoycroftScraper(BaseScraper):
    source_name = "burbach_roycroft"
    AGENT_COMPANY = "Burbach Roycroft"

    def scrape(self) -> list[Listing]:
        try:
            r = self.session.get(SITEMAP, timeout=40)
            r.raise_for_status()
        except Exception as e:
            self.logger.error(f"Sitemap niet op te halen: {e}")
            return []

        urls = re.findall(r"<url>\s*<loc>([^<]+)</loc>", r.text)
        # Alleen de NL-canonieke /woning/-URL's — /en/listing/-varianten staan
        # als apart <url>-blok voor dezelfde listing (hreflang-duplicaat).
        urls = [u for u in urls if "/woning/" in u]
        self.logger.info(f"Burbach Roycroft: {len(urls)} listing-URL('s) in sitemap")

        results: list[Listing] = []
        for url in urls:
            try:
                l = self._scrape_detail(url)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({url}): {e}")

        self.logger.info(f"Burbach Roycroft: {len(results)} actieve Curaçao-listings")
        return results

    def _scrape_detail(self, url: str) -> Listing | None:
        soup = self.get(url)
        if soup is None:
            return None

        status_el = soup.find("div", class_="woningstatus")
        status_text = self.clean_text(status_el.get_text()) if status_el else ""
        if status_text and any(w in status_text.lower() for w in SOLD_STATUS_WORDS):
            return None  # verkocht/verhuurd, blijft in sitemap staan maar is niet actief

        kv: dict[str, str] = {}
        for k in soup.find_all("div", class_="kenmerk"):
            fields = k.find_all(["span", "strong", "h5"])
            if len(fields) >= 2:
                label = fields[0].get_text(strip=True)
                value = fields[1].get_text(strip=True)
                if label and value:
                    kv[label] = value  # tweede (vollediger) blok overschrijft het eerste

        land = kv.get("Land", "")
        land_norm = unicodedata.normalize("NFKD", land).encode("ascii", "ignore").decode().lower()
        if "curacao" not in land_norm:
            return None  # NL/ES/CH-listing op dezelfde site, buiten scope

        woning_id_el = soup.find("div", class_="woningid")
        external_id = None
        if woning_id_el:
            m = re.search(r"WONING ID:\s*([A-Za-z0-9-]+)", woning_id_el.get_text())
            if m:
                external_id = m.group(1)
        if not external_id:
            external_id = url.rstrip("/").split("/")[-1]

        h1 = soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        title_tag = soup.find("title")
        if not title and title_tag:
            title = self.clean_text(title_tag.get_text().split("|")[0])
        if not title:
            return None

        listing_type = "rent" if "Huurprijs" in kv else "sale"
        if listing_type == "sale" and status_text.lower() == "huur":
            listing_type = "rent"

        price_raw = kv.get("Huurprijs") or kv.get("Vraagprijs")
        price, currency = None, "XCG"
        if price_raw:
            pm = PRICE_RE.search(price_raw)
            if pm:
                cur_raw = re.sub(r"\s+", "", pm.group(1)).upper()
                amount = self.parse_price(pm.group(2))
                if amount:
                    if cur_raw in ("EURO", "EUR", "€"):
                        price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
                    elif cur_raw in ("US$", "USD", "$"):
                        price, currency = amount, "USD"
                    else:
                        price, currency = amount, "XCG"
            else:
                amount = self.parse_price(price_raw)
                if amount and amount >= 100:
                    price, currency = amount, "XCG"

        area_sqm = self._parse_area(kv.get("Woonoppervlakte")) or self._parse_area(
            kv.get("Perceel") or kv.get("Perceeloppervlakte")
        )

        bedrooms = self.parse_int(kv.get("Slaapkamers") or "")
        bathrooms = None
        bam = re.search(r"[\d]+(?:[.,][\d]+)?", kv.get("Badkamers") or "")
        if bam:
            try:
                bathrooms = round(float(bam.group().replace(",", ".")))
            except ValueError:
                bathrooms = None

        neighborhood = self.clean_text(kv.get("Locatie"))

        type_source = f"{kv.get('Soort woning', '')} {kv.get('Type woning', '')} {title}"
        type_haystack = unicodedata.normalize("NFKD", type_source).lower()
        property_type = "house"
        for ptype, words in TYPE_KEYWORDS:
            if any(w in type_haystack for w in words):
                property_type = ptype
                break

        toptxt = soup.find("div", class_="toptxt")
        bottomtxt = soup.find("div", class_="bottomtxt")
        desc_parts = []
        if toptxt:
            desc_parts.append(toptxt.get_text(" "))
        if bottomtxt:
            desc_parts.append(bottomtxt.get_text(" "))
        description = self.clean_text(" ".join(desc_parts)) if desc_parts else None
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        images = self.clean_images(
            [a.get("href") for a in soup.find_all("a", attrs={"data-fancybox": True}) if a.get("href")]
        )

        return Listing(
            source_id=self.source_id,
            external_id=str(external_id),
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
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )

    def _parse_area(self, raw: str | None) -> float | None:
        if not raw:
            return None
        m = AREA_RE.search(raw.replace(".", "").replace(",", "."))
        if not m:
            return None
        try:
            v = float(m.group(1))
            return v if 5 <= v <= 1_000_000 else None
        except ValueError:
            return None
