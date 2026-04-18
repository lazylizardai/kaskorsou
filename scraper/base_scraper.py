"""KasKorsou — Base scraper class"""
import re
import time
import random
import logging
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
from .config import HEADERS, REQUEST_DELAY, MAX_RETRIES, TIMEOUT, SOURCES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)


class BaseScraper:
    source_name: str = ""  # override in subclass

    def __init__(self):
        cfg = SOURCES.get(self.source_name, {})
        self.source_id    = cfg.get("id", self.source_name)
        self.base_url     = cfg.get("base_url", "")
        self.listings_url = cfg.get("listings_url", "")
        self.logger       = logging.getLogger(self.source_name or self.__class__.__name__)
        self.session      = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = False  # sommige Curaçao sites hebben SSL hostname mismatch

    def get(self, url: str) -> BeautifulSoup | None:
        for attempt in range(MAX_RETRIES):
            try:
                time.sleep(random.uniform(*REQUEST_DELAY))
                r = self.session.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                return BeautifulSoup(r.text, "lxml")
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5 * (attempt + 1))
        self.logger.error(f"All retries failed for {url}")
        return None

    def scrape(self) -> list:
        raise NotImplementedError

    def parse_price(self, text: str) -> float | None:
        cleaned = re.sub(r"[^\d]", "", text.replace(".", "").replace(",", ""))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def parse_area(self, text: str) -> float | None:
        m = re.search(r"([\d]+[.,]?[\d]*)\s*m", (text or "").replace(",", "."))
        return float(m.group(1)) if m else None

    def parse_int(self, text: str) -> int | None:
        m = re.search(r"\d+", text or "")
        return int(m.group()) if m else None

    def abs_url(self, base_or_path: str, path: str = "") -> str:
        """abs_url(path) or abs_url(base, path)"""
        if path:
            base = base_or_path
        else:
            base = self.base_url
            path = base_or_path
        if path.startswith("http"):
            return path
        return base.rstrip("/") + "/" + path.lstrip("/")
