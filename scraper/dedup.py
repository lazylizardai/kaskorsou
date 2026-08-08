"""
Cross-source duplicate detection voor KasKorsou.

Zelfde woning verschijnt via meerdere bronnen (bv. Facebook-post van een
RE/MAX-listing). Same-source duplicaten bestaan niet (upsert op external_id);
dit module zoekt dus alleen paren uit verschillende bronnen.

Strategieën (gebaseerd op de originele duplicate_detector.py):
  1. exact_url     — genormaliseerde listing-URL identiek (conf 1.0)
  2. image_hash    — perceptual hash (phash) van de eerste foto, hamming <= 8
  3. price_specs   — zelfde prijsbucket + bedrooms (+ oppervlaktebucket), conf op prijsafstand
  4. fuzzy_address — adres/titel-similariteit > drempel binnen zelfde prijsbucket
  5. geo_price     — coördinaten < 120 m uit elkaar + prijs binnen 3%

Canoniek = professionele bron boven Facebook; daarna compleetste record.
Niet-canonieke leden krijgen duplicate_of = canonical id.
"""

import re
import logging
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import BytesIO

import requests

logger = logging.getLogger("dedup")

# Hoe hoger, hoe eerder canoniek. Facebook bewust onderaan: makelaarssite wint.
CANONICAL_PRIORITY = {
    "remax": 90, "athome": 80, "caresto": 70, "livinggoed": 70,
    "century21": 60, "sunbelt": 60, "era": 60, "facebook": 10,
}

PHASH_MAX_DISTANCE = 8
PRICE_BUCKET = 10000          # XCG
ADDRESS_THRESHOLD = 0.85
GEO_MAX_METERS = 120
GEO_PRICE_TOLERANCE = 0.03


@dataclass
class Match:
    id1: str
    id2: str
    confidence: float
    strategy: str
    reason: str


def _normalize_url(url):
    url = (url or "").strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    url = re.sub(r"[?&](utm_|fbclid|gclid).*$", "", url)
    return url.rstrip("/")


def _normalize_text(text):
    text = (text or "").lower().strip()
    text = re.sub(r"\b(straat|street|str\.?|weg|laan|kaya)\b", "", text)
    text = re.sub(r"\b(curacao|curaçao|willemstad|te koop|te huur|for sale|for rent)\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_image(listing):
    imgs = listing.get("images") or []
    if isinstance(imgs, list) and imgs:
        u = imgs[0]
        if isinstance(u, str) and u.startswith("//"):
            u = "https:" + u
        return u if isinstance(u, str) and u.startswith("http") else None
    return None


def _cross_source(l1, l2):
    return l1.get("source_id") != l2.get("source_id")


def _price_bucket(price):
    try:
        return round(float(price) / PRICE_BUCKET)
    except (TypeError, ValueError):
        return None


def _geo_distance_m(l1, l2):
    """Vlakke benadering, prima op eilandschaal."""
    try:
        lat1, lon1 = float(l1["latitude"]), float(l1["longitude"])
        lat2, lon2 = float(l2["latitude"]), float(l2["longitude"])
    except (TypeError, ValueError, KeyError):
        return None
    if not (11.5 < lat1 < 12.8 and 11.5 < lat2 < 12.8):
        return None
    dy = (lat1 - lat2) * 111_320
    dx = (lon1 - lon2) * 108_800  # cos(12°) * 111320
    return (dx * dx + dy * dy) ** 0.5


class CrossSourceDedup:
    def __init__(self, hash_images=True, session=None, threshold=ADDRESS_THRESHOLD):
        self.hash_images = hash_images
        self.threshold = threshold
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        )

    # ── strategieën ──────────────────────────────────────────────

    def _exact_url(self, listings):
        seen = {}
        out = []
        for l in listings:
            u = _normalize_url(l.get("url"))
            if not u:
                continue
            if u in seen and _cross_source(seen[u], l):
                out.append(Match(seen[u]["id"], l["id"], 1.0, "exact_url", f"zelfde url: {u}"))
            else:
                seen.setdefault(u, l)
        return out

    def _image_hash(self, listings):
        try:
            import imagehash
            from PIL import Image
        except ImportError:
            logger.warning("imagehash/Pillow niet geïnstalleerd — image-strategie overgeslagen")
            return []

        from concurrent.futures import ThreadPoolExecutor

        def fetch_hash(l):
            url = _first_image(l)
            if not url:
                return None
            try:
                r = self.session.get(url, timeout=5)
                r.raise_for_status()
                return (imagehash.phash(Image.open(BytesIO(r.content))), l)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=16) as pool:
            hashes = [h for h in pool.map(fetch_hash, listings) if h]
        logger.info("dedup image_hash: %d/%d foto's gehasht", len(hashes), len(listings))

        out = []
        for i, (h1, l1) in enumerate(hashes):
            for h2, l2 in hashes[i + 1:]:
                if not _cross_source(l1, l2):
                    continue
                d = h1 - h2
                if d <= PHASH_MAX_DISTANCE:
                    conf = 0.98 if d <= 2 else 0.90
                    out.append(Match(l1["id"], l2["id"], conf, "image_hash", f"phash-afstand {d}"))
        return out

    def _price_specs(self, listings):
        buckets = defaultdict(list)
        for l in listings:
            pb = _price_bucket(l.get("price"))
            beds = l.get("bedrooms")
            if pb is None or not pb or not beds:
                continue
            area = l.get("area_sqm")
            ab = round(float(area) / 25) if area else "NA"
            buckets[(l.get("listing_type"), pb, int(beds), ab)].append(l)

        out = []
        for group in buckets.values():
            for i, l1 in enumerate(group):
                for l2 in group[i + 1:]:
                    if not _cross_source(l1, l2):
                        continue
                    p1, p2 = float(l1["price"]), float(l2["price"])
                    diff = abs(p1 - p2) / max(p1, p2)
                    conf = 0.88 - diff  # zonder extra bewijs blijft dit onder de auto-drempel
                    out.append(Match(l1["id"], l2["id"], conf, "price_specs",
                                     f"prijs/beds/opp-bucket, prijsverschil {diff:.1%}"))
        return out

    def _fuzzy_address(self, listings):
        # alleen vergelijken binnen dezelfde prijsbucket (of allebei zonder prijs)
        buckets = defaultdict(list)
        for l in listings:
            key = _price_bucket(l.get("price"))
            text = _normalize_text(l.get("address") or l.get("title"))
            if len(text) < 8:
                continue
            buckets[key].append((text, l))

        out = []
        for group in buckets.values():
            for i, (t1, l1) in enumerate(group):
                for t2, l2 in group[i + 1:]:
                    if not _cross_source(l1, l2):
                        continue
                    sim = SequenceMatcher(None, t1, t2).ratio()
                    if sim > self.threshold:
                        out.append(Match(l1["id"], l2["id"], sim, "fuzzy_address",
                                         f"tekst-similariteit {sim:.0%}"))
        return out

    def _geo_price(self, listings):
        with_geo = [l for l in listings if l.get("latitude") and l.get("longitude") and l.get("price")]
        out = []
        for i, l1 in enumerate(with_geo):
            for l2 in with_geo[i + 1:]:
                if not _cross_source(l1, l2):
                    continue
                d = _geo_distance_m(l1, l2)
                if d is None or d > GEO_MAX_METERS:
                    continue
                p1, p2 = float(l1["price"]), float(l2["price"])
                if abs(p1 - p2) / max(p1, p2) <= GEO_PRICE_TOLERANCE:
                    out.append(Match(l1["id"], l2["id"], 0.92, "geo_price",
                                     f"{d:.0f} m uit elkaar, zelfde prijs"))
        return out

    # ── samenvoegen ──────────────────────────────────────────────

    def detect(self, listings):
        strategies = [self._exact_url, self._price_specs, self._fuzzy_address, self._geo_price]
        if self.hash_images:
            strategies.insert(1, self._image_hash)

        all_matches = []
        for fn in strategies:
            found = fn(listings)
            logger.info("dedup %s: %d paren", fn.__name__, len(found))
            all_matches.extend(found)

        # beste match per paar; meerdere strategieën samen = hogere confidence
        pairs = defaultdict(list)
        for m in all_matches:
            pairs[tuple(sorted((m.id1, m.id2)))].append(m)

        merged = []
        for group in pairs.values():
            best = max(group, key=lambda m: m.confidence)
            if len({m.strategy for m in group}) > 1:
                best.confidence = min(1.0, best.confidence + 0.06 * (len(group) - 1))
                best.reason += " + " + ", ".join(sorted({m.strategy for m in group} - {best.strategy}))
            merged.append(best)
        return merged

    @staticmethod
    def groups(matches, min_confidence=0.88):
        graph = defaultdict(set)
        for m in matches:
            if m.confidence >= min_confidence:
                graph[m.id1].add(m.id2)
                graph[m.id2].add(m.id1)
        visited, out = set(), []
        for node in graph:
            if node in visited:
                continue
            stack, comp = [node], []
            while stack:
                n = stack.pop()
                if n in visited:
                    continue
                visited.add(n)
                comp.append(n)
                stack.extend(graph[n] - visited)
            if len(comp) > 1:
                out.append(comp)
        return out

    @staticmethod
    def pick_canonical(group_listings):
        def score(l):
            completeness = sum(1 for f in ("price", "bedrooms", "bathrooms", "area_sqm",
                                           "latitude", "images", "description") if l.get(f))
            return (CANONICAL_PRIORITY.get(l.get("source_id"), 50), completeness,
                    str(l.get("first_seen_at") or ""))
        return max(group_listings, key=score)


def run_dedup(supabase, hash_images=True, min_confidence=0.88, dry_run=False):
    """Detecteer + markeer duplicaten. Retourneert (n_groepen, n_gemarkeerd)."""
    rows = (supabase.table("kas_listings")
            .select("id,source_id,url,title,address,price,listing_type,bedrooms,bathrooms,"
                    "area_sqm,latitude,longitude,images,description,first_seen_at,duplicate_of")
            .eq("status", "active").execute().data)
    logger.info("dedup: %d actieve listings geladen", len(rows))

    detector = CrossSourceDedup(hash_images=hash_images)
    matches = detector.detect(rows)
    groups = detector.groups(matches, min_confidence)

    by_id = {r["id"]: r for r in rows}
    marked = 0
    for group in groups:
        members = [by_id[i] for i in group if i in by_id]
        canonical = detector.pick_canonical(members)
        for m in members:
            if m["id"] == canonical["id"]:
                continue
            if dry_run:
                logger.info("[dry] %s (%s) -> duplicaat van %s (%s)",
                            m["id"], m["source_id"], canonical["id"], canonical["source_id"])
            else:
                supabase.table("kas_listings").update(
                    {"duplicate_of": canonical["id"]}).eq("id", m["id"]).execute()
            marked += 1
        # canoniek expliciet vrijgeven (kan eerder duplicaat zijn geweest)
        if not dry_run and canonical.get("duplicate_of"):
            supabase.table("kas_listings").update(
                {"duplicate_of": None}).eq("id", canonical["id"]).execute()

    logger.info("dedup: %d groepen, %d listings gemarkeerd als duplicaat", len(groups), marked)
    return len(groups), marked
