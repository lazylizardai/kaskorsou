"""KasKorsou — Data models"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


KNOWN_AGENCIES = [
    "remax", "re/max", "sunbelt", "century21", "century 21",
    "era ", "coldwell", "makelaar", "makelaardij", "realty",
]

def detect_agency(text: str) -> str | None:
    """Return agency slug if text mentions a known agency, else None."""
    tl = text.lower()
    for ag in KNOWN_AGENCIES:
        if ag in tl:
            return ag.strip()
    return None


@dataclass
class Listing:
    source_id:    str
    external_id:  str
    title:        str
    listing_type: str           # 'sale' | 'rent'
    property_type: str = "house"
    price_ang:    Optional[float] = None
    # Native valuta van de listing zoals de bron 'm toont — XCG (voorheen ANG,
    # zelfde waarde) of USD. Nooit omgerekend voor opslag, wel voor filteren
    # (frontend rekent XCG<->USD om met de vaste koers 1 USD = 1,79 XCG).
    currency:     str = "XCG"
    url:          str = ""
    description:  Optional[str] = None
    bedrooms:     Optional[int] = None
    bathrooms:    Optional[int] = None
    area_sqm:     Optional[float] = None
    neighborhood: Optional[str] = None
    latitude:     Optional[float] = None
    longitude:    Optional[float] = None
    images:       list = field(default_factory=list)
    # Wie de listing aanbiedt — altijd gevuld zodra de bron bekend is (naam van
    # het makelaarskantoor). agent_name is de individuele contactpersoon,
    # alleen gevuld als de bron dat expliciet toont (meestal niet het geval).
    agent_name:    Optional[str] = None
    agent_company: Optional[str] = None
    # Facebook-specific
    is_private:   bool = False   # True = particulier, False = agency/unknown
    agency_hint:  Optional[str] = None  # detected agency slug

    def to_supabase_dict(self) -> dict:
        return {
            "source_id":     self.source_id,
            "external_id":   self.external_id or None,
            "url":           self.url or None,
            "title":         self.title,
            "description":   self.description,
            "price":         self.price_ang,
            "currency":      self.currency,
            "listing_type":  self.listing_type,
            "property_type": self.property_type,
            "bedrooms":      self.bedrooms,
            "bathrooms":     self.bathrooms,
            "area_sqm":      self.area_sqm,
            "neighborhood":  self.neighborhood,
            "latitude":      self.latitude,
            "longitude":     self.longitude,
            "images":        self.images,
            "agent_name":    self.agent_name,
            "agent_company": self.agent_company,
            "status":        "active",
            "last_seen_at":  datetime.now(timezone.utc).isoformat(),
        }
