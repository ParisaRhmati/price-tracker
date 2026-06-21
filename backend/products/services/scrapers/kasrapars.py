"""Kasrapars (plus.kasrapars.ir) scraper — calls the JSON API directly.

The product page is a Nuxt SPA whose prices load from an API afterwards, so we
call that API instead of scraping HTML.

CRITICAL: the API only returns the `varieties` (seller offers, with prices)
when the request carries these headers that the web app sends:
    b2b: 1
    client-id: mobit_hamkar
Without them the API returns the product but with an EMPTY varieties list, which
looks like "out of stock". With them, the sellers + prices come through.

Prices are in RIALS (e.g. price_off "180000000"); the app stores TOMAN, so we
divide by 10 -> 18,000,000 toman.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse

import requests

from .base import (
    BaseScraper,
    ScrapeResult,
    ScraperError,
    ScraperRetryable,
    ScraperBlocked,
    parse_price,
)

API_BASE = "https://api.kasrapars.ir/api/web/v10/product/slug"
EXPAND = "varieties,varieties.company,varieties.color,varieties.pack,activeVarietyId"

# Headers the kasrapars web app sends. The b2b + client-id pair is what makes
# the API include seller prices in the response.
_API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
    "authorization": "Bearer null",
    "b2b": "1",
    "client-id": "mobit_hamkar",
    "device": "1",
    "Origin": "https://plus.kasrapars.ir",
    "Referer": "https://plus.kasrapars.ir/",
}


def _extract_slug(url: str) -> str:
    """Pull the product slug from a kasrapars product URL."""
    if not url:
        raise ScraperError("Kasrapars: empty URL")
    raw = url.strip()
    if "/" not in raw and "." not in raw:
        return raw
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    parts = [p for p in (parsed.path or "").split("/") if p]
    if not parts:
        raise ScraperError(f"Kasrapars: no slug in URL: {url}")
    if "product" in parts:
        i = parts.index("product")
        if i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1]


class KasraparsScraper(BaseScraper):
    name = "kasrapars"

    def scrape(self, url: str) -> ScrapeResult:
        slug = _extract_slug(url)
        data = self._fetch_api(slug)
        return self._parse_api(data)

    def parse(self, html: str, url: str) -> ScrapeResult:  # pragma: no cover
        raise NotImplementedError("KasraparsScraper uses the JSON API, not HTML.")

    def _fetch_api(self, slug: str) -> dict:
        params = {"slug": slug, "expand": EXPAND}
        try:
            response = requests.get(
                API_BASE, params=params, headers=_API_HEADERS,
                timeout=self.timeout, allow_redirects=True,
            )
        except requests.Timeout as exc:
            raise ScraperRetryable(f"Timeout fetching Kasrapars API for {slug}") from exc
        except requests.RequestException as exc:
            raise ScraperRetryable(f"Network error fetching Kasrapars API for {slug}: {exc}") from exc

        if response.status_code in (403, 429):
            raise ScraperBlocked(f"Kasrapars API blocked (HTTP {response.status_code})")
        if response.status_code >= 500:
            raise ScraperRetryable(f"Kasrapars API server error HTTP {response.status_code}")
        if response.status_code in (404, 410):
            # 410 = product removed. Treat as out of stock rather than hard error.
            raise ScraperError(f"Kasrapars product gone (HTTP {response.status_code}): {slug}")
        if response.status_code >= 400:
            raise ScraperError(f"Kasrapars API HTTP {response.status_code} for {slug}")

        try:
            return response.json()
        except ValueError as exc:
            raise ScraperRetryable(f"Kasrapars API non-JSON for {slug}") from exc

    def _parse_api(self, data: dict) -> ScrapeResult:
        if not isinstance(data, dict):
            raise ScraperError("Kasrapars API: unexpected response shape")

        title = str(data.get("short_name") or data.get("product_name") or "")
        varieties = data.get("varieties") or []

        if not isinstance(varieties, list) or not varieties:
            return ScrapeResult(price=None, currency="TOMAN",
                                availability="out_of_stock", raw_title=title)

        cheapest: Optional[Decimal] = None
        any_in_stock = False

        for v in varieties:
            if not isinstance(v, dict):
                continue
            status = v.get("status") or {}
            code = status.get("code")
            can_buy = status.get("can_buy")
            status_available = v.get("status_available")
            visible = v.get("visible")

            in_stock = (
                (code == 1 or status_available == 1)
                and can_buy is not False
                and visible != 0
            )
            if not in_stock:
                continue

            raw_off = v.get("price_off")
            raw_main = v.get("price_main")
            price = parse_price(str(raw_off)) if raw_off not in (None, "", "0") else None
            if price is None and raw_main not in (None, "", "0"):
                price = parse_price(str(raw_main))
            if price is None or price <= 0:
                continue

            any_in_stock = True
            if cheapest is None or price < cheapest:
                cheapest = price

        if cheapest is None:
            return ScrapeResult(price=None, currency="TOMAN",
                                availability="out_of_stock" if not any_in_stock else "unknown",
                                raw_title=title)

        # Rials -> toman.
        toman = (cheapest / Decimal(10)).to_integral_value()
        return ScrapeResult(price=toman, currency="TOMAN",
                            availability="in_stock", raw_title=title)
