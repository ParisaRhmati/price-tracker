"""Scraper registry. Maps website name -> scraper class."""
from __future__ import annotations

from .base import BaseScraper, ScrapeResult
from .digikala import DigikalaScraper
from .generic import GenericScraper
from .technolife import TechnolifeScraper
from .kasrapars import KasraparsScraper
from .mobile140 import Mobile140Scraper
from .hamrahtel import HamrahtelScraper

# Lookup is case-insensitive and tolerant of small variations.
SCRAPERS: dict[str, type[BaseScraper]] = {
    "digikala": DigikalaScraper,
    "digikala.com": DigikalaScraper,
    "technolife": TechnolifeScraper,
    "techno life": TechnolifeScraper,
    "technolife.com": TechnolifeScraper,
    # mobile140 — every spacing/spelling variation
    "mobile140": Mobile140Scraper,
    "mobile 140": Mobile140Scraper,
    "mobile140.com": Mobile140Scraper,
    "mobile 140.com": Mobile140Scraper,
    "mobile-140": Mobile140Scraper,
    # kasrapars
    "kasrapars": KasraparsScraper,
    "kasra pars": KasraparsScraper,
    "kasrapars.ir": KasraparsScraper,
    "plus.kasrapars.ir": KasraparsScraper,
    "kasra plus": KasraparsScraper,
    "کسری پلاس": KasraparsScraper,
    # hamrahtel
    "hamrahtel": HamrahtelScraper,
    "hamrah tel": HamrahtelScraper,
    "hamrahtel.com": HamrahtelScraper,
    "همراه تل": HamrahtelScraper,
}


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def get_scraper_for(website_name: str, url: str = "") -> BaseScraper:
    """Pick a scraper by website name; fall back to URL host; else generic."""
    key = _normalize(website_name)
    if key in SCRAPERS:
        return SCRAPERS[key]()

    # Also try with spaces removed (so "mobile 140" -> "mobile140").
    key_nospace = key.replace(" ", "")
    if key_nospace in SCRAPERS:
        return SCRAPERS[key_nospace]()

    # Try matching by URL host.
    host = ""
    if url:
        try:
            from urllib.parse import urlparse
            host = urlparse(url if "://" in url else f"https://{url}").hostname or ""
            host = host.lower()
            if host.startswith("www."):
                host = host[4:]
        except Exception:
            host = ""
    if host:
        for known, scraper_cls in SCRAPERS.items():
            known_host = known.replace(" ", "")
            if known_host in host.replace(".", "") or known in host:
                return scraper_cls()
        # Direct host keyword checks
        h = host.replace(".", "").replace("-", "")
        if "mobile140" in h:
            return Mobile140Scraper()
        if "digikala" in host:
            return DigikalaScraper()
        if "technolife" in host:
            return TechnolifeScraper()
        if "kasrapars" in host:
            return KasraparsScraper()
        if "hamrahtel" in host:
            return HamrahtelScraper()

    return GenericScraper()


__all__ = [
    "BaseScraper", "ScrapeResult", "DigikalaScraper", "TechnolifeScraper",
    "GenericScraper", "KasraparsScraper", "Mobile140Scraper", "HamrahtelScraper",
    "SCRAPERS", "get_scraper_for",
]
