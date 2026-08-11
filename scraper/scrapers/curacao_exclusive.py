"""Curaçao Exclusive Real Estate scraper (priority 8)
Site: https://www.curacao-exclusive-realestate.com — WordPress (Salient-thema
+ WPBakery), gewone Apache-hosting (géén WPCloud-signaal). robots.txt: alles
toegestaan. wp-json bereikbaar, maar de `rem_property` REST-response bevat
alleen ruwe shortcode-tekst (geen ACF-velden voor prijs/bed/bath) — dus de
REST API wordt alleen gebruikt om snel alle 42 listing-links + WP post-ID's
op te halen, en per listing wordt de gerenderde HTML-detailpagina gebruikt
voor de echte data (zelfde aanpak als moret.py/sunset_realtors.py).

Methode:
  1. `/wp-json/wp/v2/properties?per_page=100&_fields=id,link,slug` (rest_base
     van de `rem_property` CPT is `properties`) geeft in 1 request alle 42
     actieve listings (alleen publish-status komt uit de publieke REST API).
  2. Per detailpagina een `div.xc-card` met titel "Eigenschappen": daarin
     `div.xc-prop` met `xc-prop-l` (label, soms met een `€`/`$`-icoon-span
     ervoor) en `xc-prop-r` (waarde) — Vraagprijs/Huurprijs, Woonoppervlakte,
     Bebouwd oppervlak, Perceeloppervlakte, Slaapkamers, Badkamers (kan een
     halve badkamer zijn, bv. "6.5").
  3. Geen expliciete "verkocht"-status gevonden op de site — alles wat de
     publieke REST API teruggeeft wordt als actief beschouwd (zelfde aanname
     als bij andere WP-sites zonder ACF-statusveld).
  4. Geen betrouwbaar property_type-veld op de pagina (de "xc-badge-type"
     komt maar sporadisch voor, bv. bij multi-unit complexen) — daarom een
     keyword-heuristiek op titel+slug (villa/woning/huis->house,
     appartement/penthouse/condo->apartment, kavel/perceel/land->land,
     kantoor/commercieel->commercial), met Slaapkamers-aanwezigheid als
     terugval naar house.
  5. Geen coördinaten beschikbaar (de `rem_property_map`-JS-variabele had bij
     alle steekproeflistings lege latitude/longitude/address).
  6. Prijzen altijd met een €-icoon getoond (geen $-listings gezien in de
     steekproef) -> aangenomen EUR, omgerekend ×1,95 naar XCG net als de
     andere scrapers. Als ooit een $-icoon voorkomt: dan native USD, geen
     omrekening (zelfde conventie als elders).
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://www.curacao-exclusive-realestate.com"
LIST_API = f"{BASE}/wp-json/wp/v2/properties?per_page=100&_fields=id,link,slug"
EUR_TO_XCG = 1.95

LAND_HINTS = ("kavel", "perceel", "land", "kavels")
APARTMENT_HINTS = ("appartement", "penthouse", "condominium", "condo")
COMMERCIAL_HINTS = ("kantoor", "commercieel", "bedrijfspand", "kantoorruimte")


class CuracaoExclusiveScraper(BaseScraper):
    source_name = "curacao_exclusive"
    AGENT_COMPANY = "Curaçao Exclusive Real Estate"

    def _get_json(self, url: str):
        r = self.session.get(url, timeout=40)
        r.raise_for_status()
        return r.json()

    def scrape(self) -> list[Listing]:
        try:
            items = self._get_json(LIST_API)
        except Exception as e:
            self.logger.error(f"REST-lijst niet op te halen: {e}")
            return []

        self.logger.info(f"Curaçao Exclusive: {len(items)} listing-links in REST-lijst")

        results: list[Listing] = []
        for item in items:
            try:
                l = self._scrape_detail(item["link"], str(item["id"]))
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({item.get('link')}): {e}")

        self.logger.info(f"Curaçao Exclusive: {len(results)} listings verwerkt")
        return results

    def _infer_property_type(self, title: str, slug: str, has_bedrooms: bool) -> str:
        t = f"{title} {slug}".lower()
        if any(h in t for h in COMMERCIAL_HINTS):
            return "commercial"
        if any(h in t for h in APARTMENT_HINTS):
            return "apartment"
        if any(h in t for h in LAND_HINTS):
            return "land"
        return "house"

    def _scrape_detail(self, url: str, external_id: str) -> Listing | None:
        page_soup = self.get(url)
        if page_soup is None:
            return None

        h1 = page_soup.find("h1")
        title = self.clean_text(h1.get_text()) if h1 else None
        if not title:
            return None

        fields: dict[str, str] = {}
        currency_symbol = None
        price_label = None
        for card in page_soup.find_all("div", class_="xc-card"):
            card_title = card.find("div", class_="xc-card-title")
            if not card_title or "eigenschappen" not in card_title.get_text(strip=True).lower():
                continue
            for prop in card.find_all("div", class_="xc-prop"):
                l_div = prop.find("div", class_="xc-prop-l")
                r_div = prop.find("div", class_="xc-prop-r")
                if not l_div or not r_div:
                    continue
                cur_ico = l_div.find(class_="xc-cur-ico")
                # Bij een prijsveld zit het valuta-icoon (€/$) ALS TEKST vóór
                # het label in dezelfde xc-prop-l div — die eerst wegknippen,
                # anders wordt de dict-key "€ vraagprijs" i.p.v. "vraagprijs"
                # en matcht de price-lookup hieronder nooit.
                if cur_ico:
                    cur_ico.extract()
                label = self.clean_text(l_div.get_text(" "))
                value = self.clean_text(r_div.get_text(" "))
                if label:
                    fields[label.lower()] = value
                    if cur_ico:
                        currency_symbol = self.clean_text(cur_ico.get_text())
                        price_label = label.lower()

        listing_type = "rent" if price_label and "huur" in price_label else "sale"

        price = None
        currency = "XCG"
        for key in ("vraagprijs", "huurprijs", "koopprijs", "prijs"):
            if key in fields and fields[key]:
                price_raw = self.parse_price(fields[key])
                if price_raw is None:
                    continue
                if currency_symbol == "$":
                    price = price_raw
                    currency = "USD"
                else:
                    # standaard: €-icoon (of geen icoon gevonden) -> EUR-aanname
                    price = round(price_raw * EUR_TO_XCG, 2)
                    currency = "XCG"
                break

        bedrooms = None
        if fields.get("slaapkamers"):
            bedrooms = self.parse_int(fields["slaapkamers"])
        bathrooms = None
        if fields.get("badkamers"):
            # kas_listings.bathrooms is integer in Supabase — een halve
            # badkamer ("6.5") naar beneden afronden, geen aparte
            # decimale kolom beschikbaar.
            bathrooms = self.parse_int(fields["badkamers"])

        area_text = fields.get("woonoppervlakte") or fields.get("bebouwd oppervlak") or fields.get("perceeloppervlakte")
        area_sqm = self.parse_area(area_text) if area_text else None

        slug = url.rstrip("/").split("/")[-1]
        property_type = self._infer_property_type(title, slug, bedrooms is not None)

        description = None
        og_desc = page_soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = self.clean_text(og_desc["content"])

        images = []
        for img in page_soup.find_all("img", src=True):
            src = img["src"]
            if "/wp-content/uploads/" in src:
                images.append(src)
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
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
