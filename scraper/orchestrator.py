"""
KasKorsou Scraper Orchestrator
Run: python -m scraper.orchestrator [--sources remax,sunbelt,...]
"""
import argparse
import logging
import time
import uuid
from datetime import datetime, timezone

from supabase import create_client

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY, SOURCES
from .models import Listing
from .scrapers import (
    RemaxScraper,
    SunbeltScraper,
    Century21Scraper,
    ERAScraper,
    FacebookScraper,
    AthomeScraper,
    CarestoScraper,
    LivinggoedScraper,
    NewWindsRealtyScraper,
    KellerWilliamsScraper,
    CuraHouseCareScraper,
    InternationalFineLivingScraper,
    MoretScraper,
    NHRealEstateScraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("orchestrator")

# Priority order (highest first)
ALL_SCRAPERS = [
    FacebookScraper,     # priority 10
    RemaxScraper,        # priority 9
    AthomeScraper,       # priority 9
    SunbeltScraper,      # priority 9
    CarestoScraper,      # priority 8
    LivinggoedScraper,   # priority 8
    NewWindsRealtyScraper,  # priority 8
    KellerWilliamsScraper,  # priority 8
    CuraHouseCareScraper,   # priority 8
    InternationalFineLivingScraper,  # priority 8
    MoretScraper,         # priority 8
    NHRealEstateScraper,  # priority 8
    Century21Scraper,    # priority 8
    ERAScraper,          # priority 7
]


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in config.py"
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upsert_listings(sb, listings: list[Listing]) -> tuple[int, int]:
    """Upsert listings to kas_listings. Returns (inserted, updated)."""
    if not listings:
        return 0, 0

    rows = [l.to_supabase_dict() for l in listings]

    # Supabase upsert on (source_id, external_id)
    result = (
        sb.table("kas_listings")
        .upsert(rows, on_conflict="source_id,external_id")
        .execute()
    )

    inserted = sum(1 for r in result.data if r.get("created_at") == r.get("updated_at"))
    updated = len(result.data) - inserted
    return inserted, updated


def mark_fb_duplicates(sb, fb_listings: list[Listing]):
    """
    Voor FB listings van makelaars: probeer match te vinden in kas_listings
    op basis van prijs (±5%) + neighborhood. Zet duplicate_of als match gevonden.
    Particulieren worden NOOIT gemarkeerd als duplicaat.
    """
    agency_listings = [l for l in fb_listings if l.agency_hint and not l.is_private]
    if not agency_listings:
        return

    logger.info(f"Checking {len(agency_listings)} FB agency listings for duplicates...")

    for fb in agency_listings:
        if not fb.price_ang or fb.price_ang == 0:
            continue
        try:
            margin = fb.price_ang * 0.05
            result = (
                sb.table("kas_listings")
                .select("id, title, source_id")
                .neq("source_id", "facebook")
                .gte("price", fb.price_ang - margin)
                .lte("price", fb.price_ang + margin)
                .execute()
            )
            matches = result.data or []
            if len(matches) == 1:
                # Clear match op prijs → markeer FB listing als duplicaat
                sb.table("kas_listings").update({
                    "duplicate_of": matches[0]["id"],
                    "status": "duplicate",
                }).eq("source_id", "facebook").eq("external_id", fb.external_id).execute()
                logger.debug(f"  Duplicate: FB {fb.external_id} → {matches[0]['source_id']} {matches[0]['id'][:8]}")
        except Exception as e:
            logger.warning(f"Duplicate check failed for {fb.external_id}: {e}")


def log_scrape_run(
    sb,
    source_name: str,
    started_at: datetime,
    listings_found: int,
    listings_new: int,
    listings_updated: int,
    error: str | None = None,
):
    source_id = SOURCES.get(source_name, {}).get("id")
    sb.table("kas_scrape_logs").insert({
        "id": str(uuid.uuid4()),
        "source_id": source_id,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "listings_found": listings_found,
        "listings_new": listings_new,
        "listings_updated": listings_updated,
        "success": error is None,
    }).execute()

    # Update last_scraped_at on the source
    if source_id:
        sb.table("kas_sources").update(
            {"last_scraped_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", source_id).execute()


def run_scraper(sb, scraper_class, dry_run=False) -> dict:
    name = scraper_class.source_name
    started_at = datetime.now(timezone.utc)
    logger.info(f"▶ Starting {name}")
    error = None
    listings = []

    try:
        scraper = scraper_class()
        listings = scraper.scrape()
        logger.info(f"  {name}: {len(listings)} listings found")

        if not dry_run and listings:
            inserted, updated = upsert_listings(sb, listings)
            logger.info(f"  {name}: +{inserted} new, ~{updated} updated")
            # FB: markeer agency-listings als duplicaat waar mogelijk
            if name == "facebook":
                mark_fb_duplicates(sb, listings)

            # Stale-sweep: listings van deze bron die deze run niet gezien zijn -> inactive.
            # Alleen bij een geloofwaardige oogst, zodat een half-kapotte scraper
            # niet de hele bron leegtrekt.
            if len(listings) >= 20:
                try:
                    res = (sb.table("kas_listings")
                           .update({"status": "inactive"})
                           .eq("source_id", name)
                           .eq("status", "active")
                           .lt("last_seen_at", started_at.isoformat())
                           .execute())
                    n_stale = len(res.data or [])
                    if n_stale:
                        logger.info(f"  {name}: {n_stale} verouderde listings -> inactive")
                except Exception as se:
                    logger.warning(f"  {name}: stale-sweep mislukt: {se}")
        else:
            inserted, updated = 0, 0

    except Exception as e:
        error = str(e)
        logger.error(f"  {name} FAILED: {e}")
        inserted, updated = 0, 0

    if not dry_run:
        try:
            log_scrape_run(
                sb, name, started_at,
                listings_found=len(listings),
                listings_new=inserted,
                listings_updated=updated,
                error=error,
            )
        except Exception as le:
            logger.warning(f"  Could not write scrape log: {le}")

    return {
        "source": name,
        "found": len(listings),
        "inserted": inserted,
        "updated": updated,
        "error": error,
    }


def main():
    parser = argparse.ArgumentParser(description="KasKorsou scraper orchestrator")
    parser.add_argument(
        "--sources", "-s",
        help="Comma-separated list of sources to run (default: all)",
        default=None,
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Scrape but do not write to Supabase",
    )
    parser.add_argument(
        "--dedup", action="store_true", default=None,
        help="Run cross-source duplicate detection after scraping (default: on for full runs)",
    )
    parser.add_argument(
        "--no-dedup", dest="dedup", action="store_false",
        help="Skip duplicate detection",
    )
    parser.add_argument(
        "--dedup-only", action="store_true",
        help="Skip scraping, only run duplicate detection",
    )
    args = parser.parse_args()

    # Filter scrapers if --sources specified
    selected = ALL_SCRAPERS
    if args.sources:
        names = [s.strip().lower() for s in args.sources.split(",")]
        selected = [s for s in ALL_SCRAPERS if s.source_name in names]
        if not selected:
            logger.error(f"No scrapers matched: {args.sources}")
            return

    sb = get_supabase()

    if args.dedup_only:
        from .dedup import run_dedup
        run_dedup(sb, dry_run=args.dry_run)
        return

    results = []

    for scraper_cls in selected:
        result = run_scraper(sb, scraper_cls, dry_run=args.dry_run)
        results.append(result)
        time.sleep(2)  # polite delay between sources

    # Summary
    logger.info("=" * 50)
    logger.info("SCRAPE SUMMARY")
    total_found = total_new = total_updated = 0
    for r in results:
        status = "✓" if not r["error"] else "✗"
        logger.info(
            f"  {status} {r['source']}: {r['found']} found, "
            f"+{r['inserted']} new, ~{r['updated']} updated"
            + (f" [ERROR: {r['error'][:60]}]" if r["error"] else "")
        )
        total_found += r["found"]
        total_new += r["inserted"]
        total_updated += r["updated"]

    logger.info(f"TOTAL: {total_found} found | +{total_new} new | ~{total_updated} updated")

    # Cross-source dedup: standaard aan bij een volledige run, of expliciet via --dedup
    run_dedup_now = args.dedup if args.dedup is not None else (args.sources is None)
    if run_dedup_now and not args.dry_run:
        from .dedup import run_dedup
        try:
            n_groups, n_marked = run_dedup(sb)
            logger.info(f"DEDUP: {n_groups} groepen, {n_marked} duplicaten gemarkeerd")
        except Exception as e:
            logger.error(f"Dedup failed (scrape-resultaat blijft geldig): {e}")


if __name__ == "__main__":
    main()
