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
        "id": "century21",
        "name": "Century 21 Curacao",
        "base_url": "https://century21numberone.com",
        "listings_url": "https://century21numberone.com/en/s/for-sale/",
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
        "id": "facebook",
        "name": "Facebook Marketplace",
        "base_url": "https://www.facebook.com",
        "listings_url": "https://www.facebook.com/marketplace/curacao/propertyrentals",
        "type": "claude_computer_use",
        "priority": 10,
    },
    "athome": {
        "id": "athome",
        "name": "At Home Curaçao",
        "base_url": "https://athomecuracao.com",
        "listings_url": "https://athomecuracao.com/kopen/",
        "type": "traditional",
        "priority": 9,
    },
    "caresto": {
        "id": "caresto",
        "name": "Caresto Real Estate",
        "base_url": "https://www.caresto.com",
        "listings_url": "https://www.caresto.com/wp-json/wp/v2/caresto_property",
        "type": "traditional",
        "priority": 8,
    },
    "livinggoed": {
        "id": "livinggoed",
        "name": "Livinggoed Real Estate",
        "base_url": "https://livinggoed.com",
        "listings_url": "https://livinggoed.com/property-sitemap.xml",
        "type": "traditional",
        "priority": 8,
    },
    "new_winds_realty": {
        "id": "new_winds_realty",
        "name": "New Winds Realty",
        "base_url": "https://www.newwindsrealty.com",
        "listings_url": "https://www.newwindsrealty.com/wp-json/wp/v2/properties",
        "type": "traditional",
        "priority": 8,
    },
    "keller_williams": {
        "id": "keller_williams",
        "name": "Keller Williams Curacao",
        "base_url": "https://kw-curacao.com",
        "listings_url": "https://kw-curacao.com/listings",
        "type": "traditional",
        "priority": 8,
    },
    "curahousecare": {
        "id": "curahousecare",
        "name": "CuraHouseCare",
        "base_url": "https://curahousecare.com",
        "listings_url": "https://curahousecare.com/wp-json/wp/v2/objecten",
        "type": "traditional",
        "priority": 8,
    },
    "international_fine_living": {
        "id": "international_fine_living",
        "name": "International Fine Living",
        "base_url": "https://www.internationalfineliving.com",
        "listings_url": "https://cpl01.ogonline.nl/api/listings",
        "type": "traditional",
        "priority": 8,
    },
    "moret": {
        "id": "moret",
        "name": "Moret Real Estate",
        "base_url": "https://moretrealestate.com",
        "listings_url": "https://moretrealestate.com/kies/kopen/",
        "type": "traditional",
        "priority": 8,
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
