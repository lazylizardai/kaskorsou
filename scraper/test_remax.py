"""RE/MAX naar Supabase"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.scrapers.remax import RemaxScraper
from scraper import config
from scraper.orchestrator import get_supabase, upsert_listings, log_scrape_run
from datetime import datetime, timezone

config.REQUEST_DELAY = (0.5, 1.0)
config.MAX_RETRIES = 2

print("Scraping RE/MAX...")
s = RemaxScraper()
listings = s.scrape()
print(f"Found: {len(listings)} listings")

print("Upserting to Supabase...")
sb = get_supabase()
inserted, updated = upsert_listings(sb, listings)
print(f"Done: +{inserted} new, ~{updated} updated")

log_scrape_run(sb, "remax", datetime.now(timezone.utc),
               len(listings), inserted, updated)
print("Logged to kas_scrape_logs")
