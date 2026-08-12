"""Proverties scraper
Site: https://proverties.com — WordPress + JetEngine (custom `listings`-CPT
met `fsfr`- en `property-type`-taxonomieën i.p.v. een herkenbaar vastgoed-
plugin-thema zoals ERE/Houzez/RealHomes). Nieuw platformpatroon in deze set.

Bijzonderheden:
  1. **REST API werkt gewoon en heeft een SCHOON `title.rendered`-veld**
     (in tegenstelling tot B.CON Real Estate op hetzelfde soort custom-CMS-
     patroon, waar title altijd leeg was) — dus geen title-fallback nodig.
  2. **`fsfr`-taxonomie (Engelse afkorting, vermoedelijk "for sale/for rent")
     bepaalt listing_type**: term 7 = "For sale", term 8 = "For rent",
     term 9 = "Short-term rental" — **term 9 bewust NIET meenemen** (28 van de
     43 items!): korte-termijn/vakantieverhuur, buiten aggregator-scope,
     zelfde reden als de vacation-rental-taxonomie bij B.CON Real Estate.
  3. **`property-type`-taxonomie**: 2 = Commercial, 3 = Residential, 4 = Lot.
     "Residential" onderscheidt zelf geen huis/appartement — daarvoor alsnog
     een titel-keyword-check nodig (villa/appartement/studio/etc.), net als
     bij de meeste andere scrapers in deze set.
  4. **Nette Gutenberg-lijststructuur in `content.rendered`**
     (`<h3>Rental Information</h3><ul><li>Rent: XCG 6.750 per month</li>
     <li>3 Bedrooms</li>...`) — prijs/slaapkamers/badkamers zitten in
     losse `<li>`-items, maar nog steeds als vrije tekst (geen apart
     structureel veld) — dus nog steeds regex op de platte tekst, alleen
     een stuk schoner dan B.CON's kale alinea's.
  5. **Val: een prijs kan een PER-M²-huurtarief zijn i.p.v. een totaalbedrag**
     (nieuw gezien: een kantoorpand-listing toont "Rent: XCG 45 per m² /
     month" voor twee verdiepingen met elk een eigen tarief, geen
     totaalbedrag) — een prijsmatch die direct gevolgd wordt door "per m²"/
     "per m2"/"/m²" wordt overgeslagen (net zo onbetrouwbaar als geen prijs,
     beter dan een absurd laag totaalbedrag opslaan).
  6. **Cijfer-eenheid kan zonder spatie met een koppelteken vastzitten**
     ("3-bedroom", "2-bathroom") — de bedrooms/bathrooms-regex staat zowel
     een spatie als een koppelteken toe tussen cijfer en eenheid.
  7. Foto's via `/wp-json/wp/v2/media?parent=<id>` (featured-media-embed
     alleen de hoofdfoto, dit endpoint levert de volledige galerij — 25
     foto's bij een steekproef).
  8. Van de 43 totaal-items zijn er 15 `for-sale`/`for-rent` (niet
     short-term) — vergelijkbare actieve-setgrootte als B.CON Real Estate.
"""
import re
import unicodedata
from ..base_scraper import BaseScraper
from ..models import Listing

API_BASE = "https://proverties.com/wp-json/wp/v2"
FSFR_FOR_SALE = 7
FSFR_FOR_RENT = 8
# FSFR_SHORT_TERM = 9  # bewust uitgesloten — vakantieverhuur, buiten scope
PTYPE_COMMERCIAL = 2
PTYPE_RESIDENTIAL = 3
PTYPE_LOT = 4
EUR_TO_XCG = 1.95

PRICE_RE = re.compile(
    r"(XCG|ANG|NAF|NAf|ƒ|EURO|EUR|€|US\s*\$|USD|\$)\.?\s*([\d][\d.,]{1,14})", re.I
)
# LET OP: "m" alleen is niet genoeg als grens — "per month" begint ook met
# "per m" en zou een normale maandprijs anders ten onrechte als per-m2-tarief
# wegfilteren. Vereis expliciet een "2" of "²" direct na de "m".
PER_M2_AFTER_RE = re.compile(r"^\s*(per\s*m[²2]|/\s*m[²2])", re.I)
# Tot 20 niet-cijfer tekens tussen het getal en "bedroom"/"bathroom" toestaan
# — vangt zowel "3-bedroom" (koppelteken) als "3 spacious bedrooms" (los
# bijvoeglijk naamwoord ertussen) in dezelfde regex.
BED_RE = re.compile(r"(\d+)[^\d.]{0,20}bedroom", re.I)
BATH_RE = re.compile(r"(\d+(?:[.,]5)?)[^\d.]{0,20}bathroom", re.I)

TYPE_KEYWORDS = (
    ("land", ("lot", "kavel", "bouwgrond", "perceel")),
    ("house", ("villa", "woning", "huis", "house", "bungalow", "townhouse")),
    ("apartment", ("apartment", "appartement", "studio", "penthouse", "duplex")),
)
LOOSE_START_WORDS = {"villa", "woning"}
LOOSE_END_WORDS = {"appartement", "apartment", "kavel"}


def _word_matches(haystack: str, word: str) -> bool:
    start = "" if word in LOOSE_START_WORDS else r"\b"
    end = "" if word in LOOSE_END_WORDS else r"\b"
    return re.search(start + re.escape(word) + end, haystack) is not None


class ProvertiesScraper(BaseScraper):
    source_name = "proverties"
    AGENT_COMPANY = "Proverties"

    def scrape(self) -> list[Listing]:
        items = self._fetch_all_listings()
        self.logger.info(f"Proverties: {len(items)} items totaal via REST")

        results: list[Listing] = []
        for item in items:
            try:
                fsfr = item.get("fsfr") or []
                if FSFR_FOR_RENT in fsfr:
                    listing_type = "rent"
                elif FSFR_FOR_SALE in fsfr:
                    listing_type = "sale"
                else:
                    continue  # short-term-rental (9) of ongeclassificeerd

                l = self._parse_item(item, listing_type)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Item error (id={item.get('id')}): {e}")

        self.logger.info(f"Proverties: {len(results)} actieve rent/sale-listings")
        return results

    def _fetch_all_listings(self) -> list[dict]:
        try:
            r = self.session.get(f"{API_BASE}/listings?per_page=100", timeout=40)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.logger.error(f"REST-lijst niet op te halen: {e}")
            return []

    def _parse_item(self, item: dict, listing_type: str) -> Listing | None:
        post_id = item.get("id")
        url = item.get("link") or f"https://proverties.com/?p={post_id}"
        title = self.clean_text(item.get("title", {}).get("rendered")) or None
        if not title:
            return None

        content_html = item.get("content", {}).get("rendered", "") or ""
        full_text = self.clean_text(
            re.sub(r"<[^>]+>", " ", content_html).replace("&nbsp;", " ")
        ) or ""
        description = full_text or None

        price, currency = None, "XCG"
        for pm in PRICE_RE.finditer(full_text):
            after = full_text[pm.end(): pm.end() + 15]
            if PER_M2_AFTER_RE.search(after):
                continue  # per-m2-tarief, geen totaalbedrag — overslaan
            cur_raw = re.sub(r"\s+", "", pm.group(1)).upper()
            amount = self.parse_price(pm.group(2))
            if not amount:
                continue
            if cur_raw in ("EURO", "EUR", "€"):
                price, currency = round(amount * EUR_TO_XCG, 2), "XCG"
            elif cur_raw in ("US$", "USD", "$"):
                price, currency = amount, "USD"
            else:
                price, currency = amount, "XCG"  # XCG/ANG/NAF/NAf/ƒ
            break

        bedrooms = None
        bm = BED_RE.search(full_text)
        if bm:
            bedrooms = int(bm.group(1))
        bathrooms = None
        bam = BATH_RE.search(full_text)
        if bam:
            bathrooms = round(float(bam.group(1).replace(",", ".")))

        ptypes = item.get("property-type") or []
        title_haystack = unicodedata.normalize("NFKD", title).lower()
        full_haystack = unicodedata.normalize("NFKD", full_text).lower()
        if PTYPE_COMMERCIAL in ptypes:
            property_type = "commercial"
        elif PTYPE_LOT in ptypes:
            property_type = "land"
        else:
            property_type = "house"
            matched = False
            for ptype, words in TYPE_KEYWORDS:
                if any(_word_matches(title_haystack, w) for w in words):
                    property_type = ptype
                    matched = True
                    break
            if not matched:
                for ptype, words in TYPE_KEYWORDS:
                    if any(_word_matches(full_haystack, w) for w in words):
                        property_type = ptype
                        break

        images = self._fetch_images(post_id)

        return Listing(
            source_id=self.source_id,
            external_id=str(post_id),
            title=title,
            listing_type=listing_type,
            property_type=property_type,
            price_ang=price,
            currency=currency,
            url=url,
            description=description,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=None,
            neighborhood=None,
            latitude=None,
            longitude=None,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )

    def _fetch_images(self, post_id) -> list[str]:
        try:
            r = self.session.get(f"{API_BASE}/media?parent={post_id}&per_page=40", timeout=30)
            r.raise_for_status()
            urls = [m.get("source_url") for m in r.json() if m.get("source_url")]
            return self.clean_images(urls)
        except Exception as e:
            self.logger.warning(f"Media-fetch mislukt voor id={post_id}: {e}")
            return []
