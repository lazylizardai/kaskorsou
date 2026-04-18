"""KasKorsou Scraper — Configuration"""

SUPABASE_URL = "https://tbfjlfnahdqfbnpszyyj.supabase.co"
# Service role key voor writes — Supabase dashboard > Settings > API > service_role
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRiZmpsZm5haGRxZmJucHN6eXlqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTg5Mjk0MSwiZXhwIjoyMDgxNDY4OTQxfQ.zCtXe-AXWTeECtSENoqw4nJmlK3KyArWfXScnX1ReTA"

SOURCES = {
    "remax": {
        "name": "RE/MAX Bonbini",
        "base_url": "https://www.realestate-curacao.com",
        "listings_url": "https://www.realestate-curacao.com/nl/woningen/koopwoningen/",
        "type": "traditional",
        "priority": 9,
    },
    "sunbelt": {
        "name": "Sunbelt Realty",
        "base_url": "https://www.sunbelt.an",
        "listings_url": "https://www.sunbelt.an/for-sale",
        "type": "traditional",
        "priority": 9,
    },
    "century21": {
        "name": "Century 21 Curacao",
        "base_url": "https://www.century21curacao.com",
        "listings_url": "https://www.century21curacao.com/properties",
        "type": "traditional",
        "priority": 8,
    },
    "era": {
        "name": "ERA Curacao",
        "base_url": "https://www.eracuracao.com",
        "listings_url": "https://www.eracuracao.com/listings",
        "type": "traditional",
        "priority": 7,
    },
    "facebook": {
        "name": "Facebook Marketplace",
        "base_url": "https://www.facebook.com",
        "listings_url": "https://www.facebook.com/marketplace/curacao/propertyrentals",
        "type": "claude_computer_use",
        "priority": 10,
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

REQUEST_DELAY = (2, 5)  # random seconden tussen requests
MAX_RETRIES   = 3
TIMEOUT       = 30
