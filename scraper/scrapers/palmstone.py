"""Palmstone Real Estate scraper (priority 8)
Site: https://palmstone.realestate — SvelteKit-frontend, data draait op
hetzelfde gedeelde makelaars-CMS als International Fine Living
("OG Online"), maar dan op een nieuwere GraphQL-laag
(`cdn.ogonline.nl/v1/amber/...`, opaque per-query hashes — niet direct
aan te roepen). Geen WordPress, geen wp-json, Cloudflare-hosting, geen
blokkade-risico. robots.txt: alles toegestaan (`Allow: /`), sitemap
aanwezig maar bevat ook oude sold/archived listings — niet als bron
gebruikt (zie hieronder).

Methode:
  1. De site rendert server-side (SSR) en embedt de volledige GraphQL-
     response als JSON in `<script type="application/json"
     data-sveltekit-fetched data-url="...">`-tags — geen browser/JS nodig,
     gewone `requests.get` + BeautifulSoup volstaat om de scripts te lezen.
  2. Actieve-listings-lijst: `/listings/for-sale` en `/listings/for-rent`
     (gepagineerd, `?page=N`, 15 per pagina) geven een `data.Listings.docs`
     array — dit ZIJN de listings die de site zelf als actueel aanbod
     toont, dus GEEN aparte sitemap-crawl nodig (de sitemap bevat ook
     tientallen oude sold/rented/archived listings uit het CMS-archief).
     Voor de sale-tak sluiten we defensief alsnog `status` beginnend met
     "sold" uit (1 geval gezien: "sold_ur" tussen de actieve for-sale-
     resultaten). Voor de rent-tak NIET op status filteren: alle
     rental-listings hebben consequent `status: "rented"` staan, ongeacht
     of ze wel degelijk nog te huur worden aangeboden op de eigen
     for-rent-pagina — dat veld is op deze site kennelijk geen
     beschikbaarheids-indicator voor de huurmarkt.
  3. Detailpagina-URL is puur cosmetisch behalve het laatste pad-segment
     (het CMS-ID) — geverifieerd met een expres foute stad/slug die
     gewoon HTTP 200 + de juiste listing teruggaf (zelfde patroon als
     international_fine_living.py). We bouwen 'm toch netjes op met de
     echte stad/slug uit de lijst-JSON voor leesbare URLs.
  4. Op de detailpagina staat de volledige `data.Listing`-graaf met
     `details.bedrooms.amount`, `details.bathrooms.amount` (kan een half
     getal zijn, bv. 2.5 → afgerond voor de integer-kolom),
     `details.surface.amount` (woonoppervlak m²), `price.sales.amount` /
     `price.rentals.amount` + `price.specifications.currency.currency`,
     `address.city` (wijk) en `address.location` — **let op: hier is de
     volgorde [latitude, longitude]**, niet de GeoJSON-standaard
     [lng, lat] (geverifieerd: eerste waarde ligt in het Curaçaose
     breedtegraad-bereik ~12, tweede in het lengtegraad-bereik ~-68/-69).
     Defensief ook op Curaçao-bounding-box gecontroleerd, net als bij
     international_fine_living.py.
  5. Beschrijving zit als Lexical rich-text-boom (`description.full.root`)
     — platte tekst eruit gehaald met een kleine recursieve tekst-walker.
  6. Foto's staan al als volledige `media.ogonline.nl`-URL's in
     `media.images[].url` — geen HTML-scraping nodig.
"""
import re
from ..base_scraper import BaseScraper
from ..models import Listing

BASE = "https://palmstone.realestate"
PAGE_SIZE = 15

TYPE_MAP = {
    "HOUSE": "house",
    "VILLA": "house",
    "APARTMENT": "apartment",
    "PENTHOUSE": "apartment",
    "BUILDLOT": "land",
    "LOT": "land",
    "COMMERCIAL": "commercial",
}


def _slugify(text: str | None) -> str:
    if not text:
        return "listing"
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "listing"


def _rich_text_to_plain(node) -> str:
    """Lexical rich-text-boom (root.children[].children[].text) plat maken."""
    if not isinstance(node, dict):
        return ""
    parts = []
    if node.get("type") == "text" and node.get("text"):
        parts.append(node["text"])
    for child in node.get("children") or []:
        parts.append(_rich_text_to_plain(child))
    joiner = "\n" if node.get("type") in ("root", "paragraph") else ""
    return joiner.join(p for p in parts if p) if joiner else "".join(parts)


class PalmstoneScraper(BaseScraper):
    source_name = "palmstone"
    AGENT_COMPANY = "Palmstone Real Estate"

    def _graphql_data(self, soup, key: str):
        """Zoek in de SSR-embedded <script data-sveltekit-fetched>-tags naar
        de eerste response waarvan data[key] bestaat, en geef die terug."""
        for script in soup.find_all("script", attrs={"data-sveltekit-fetched": True}):
            raw = script.string or script.get_text()
            if not raw or key not in raw:
                continue
            try:
                import json
                outer = json.loads(raw)
                body = json.loads(outer["body"])
            except Exception:
                continue
            data = body.get("data") or {}
            if key in data and data[key]:
                return data[key]
        return None

    def _list_page(self, kind: str, page: int):
        url = f"{BASE}/listings/{kind}?page={page}"
        soup = self.get(url)
        if soup is None:
            return [], 0
        listings = self._graphql_data(soup, "Listings")
        if not listings:
            return [], 0
        return listings.get("docs") or [], listings.get("totalDocs") or 0

    def scrape(self) -> list[Listing]:
        summaries = []
        for kind, listing_type in (("for-sale", "sale"), ("for-rent", "rent")):
            page = 1
            seen_ids = set()
            while True:
                docs, total_docs = self._list_page(kind, page)
                if not docs:
                    break
                for d in docs:
                    if d.get("id") in seen_ids:
                        continue
                    seen_ids.add(d.get("id"))
                    summaries.append((d, listing_type))
                if len(seen_ids) >= total_docs or len(docs) < PAGE_SIZE:
                    break
                page += 1

        self.logger.info(f"Palmstone: {len(summaries)} actieve listings in for-sale/for-rent overzicht")

        results: list[Listing] = []
        for summary, listing_type in summaries:
            try:
                l = self._scrape_detail(summary, listing_type)
                if l:
                    results.append(l)
            except Exception as e:
                self.logger.warning(f"Detail error ({summary.get('id')}): {e}")

        self.logger.info(f"Palmstone: {len(results)} listings verwerkt")
        return results

    def _detail_url(self, summary: dict) -> str:
        city = _slugify((summary.get("address") or {}).get("city"))
        slug = _slugify(summary.get("slug"))
        return f"{BASE}/listing/{city}/{slug}/{summary['id']}"

    def _scrape_detail(self, summary: dict, listing_type: str) -> Listing | None:
        listing_id = summary.get("id")
        if not listing_id:
            return None

        url = self._detail_url(summary)
        soup = self.get(url)
        if soup is None:
            return None

        listing = self._graphql_data(soup, "Listing")
        if not listing:
            return None

        status = (listing.get("status") or "").lower()
        if listing_type == "sale" and status.startswith("sold"):
            return None

        title = self.clean_text(listing.get("title")) or "Woning Curaçao"

        mt = ((listing.get("details") or {}).get("type") or {}).get("mainType") or []
        identifier = mt[0].get("identifier") if mt else None
        property_type = TYPE_MAP.get((identifier or "").upper(), "house")

        details = listing.get("details") or {}
        bedrooms = (details.get("bedrooms") or {}).get("amount")
        bathrooms = (details.get("bathrooms") or {}).get("amount")
        if bathrooms is not None:
            bathrooms = round(bathrooms)
        if bedrooms is not None:
            bedrooms = round(bedrooms)
        area_sqm = (details.get("surface") or {}).get("amount") or (details.get("plotSurface") or {}).get("amount")

        price_block = listing.get("price") or {}
        currency_raw = ((price_block.get("specifications") or {}).get("currency") or {}).get("currency") or "XCG"
        if listing_type == "rent":
            amount = ((price_block.get("rentals") or {}).get("amount"))
        else:
            amount = ((price_block.get("sales") or {}).get("amount"))

        price, currency = None, "XCG"
        if amount:
            if currency_raw == "EUR":
                price, currency = round(amount * 1.95, 2), "XCG"
            elif currency_raw == "USD":
                price, currency = amount, "USD"
            else:
                price, currency = amount, "XCG"

        address = listing.get("address") or {}
        neighborhood = self.clean_text(address.get("city"))

        latitude = longitude = None
        loc = address.get("location")
        if isinstance(loc, list) and len(loc) == 2 and loc[0] is not None and loc[1] is not None:
            lat_candidate, lng_candidate = loc[0], loc[1]
            if 11.9 <= lat_candidate <= 12.5 and -69.3 <= lng_candidate <= -68.5:
                latitude, longitude = lat_candidate, lng_candidate
            else:
                self.logger.warning(
                    f"Coördinaten buiten Curaçao voor {listing_id}: {loc} — genegeerd"
                )

        description = None
        desc_root = ((listing.get("description") or {}).get("full") or {}).get("root")
        if desc_root:
            description = self.clean_text(_rich_text_to_plain(desc_root))
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                description = self.clean_text(og_desc["content"])

        images = []
        for img in ((listing.get("media") or {}).get("images") or []):
            if img.get("url"):
                images.append(img["url"])
        images = self.clean_images(images)

        return Listing(
            source_id=self.source_id,
            external_id=str(listing_id),
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
            latitude=latitude,
            longitude=longitude,
            images=images,
            agent_company=self.AGENT_COMPANY,
        )
