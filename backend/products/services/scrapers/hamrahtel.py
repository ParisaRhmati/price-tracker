"""Hamrahtel (hamrahtel.com) scraper — uses the Saleor GraphQL API.

hamrahtel.com is a Next.js storefront on the Saleor e-commerce platform. The
product page ships without prices; they load from a GraphQL API afterwards:
    https://core-api.hamrahtel.com/graphql/

We query publicProduct(slug:) and read the variants. Each variant has:
    pricing.price.gross.amount   -> price in TOMAN (e.g. 18499000)
    quantityAvailable            -> >0 means that variant is in stock

We take the cheapest in-stock variant. Prices are already in TOMAN (they match
the site display), so no division is needed.

Product URL: https://hamrahtel.com/products/<slug>
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

GRAPHQL_URL = "https://core-api.hamrahtel.com/graphql/"

_QUERY = """
query getProduct($slug: String!) {
  publicProduct(slug: $slug) {
    id
    name
    isAvailable
    isAvailableForPurchase
    variants {
      quantityAvailable
      pricing {
        price { gross { amount } }
      }
    }
  }
}
""".strip()

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://hamrahtel.com",
    "Referer": "https://hamrahtel.com/",
}


def _extract_slug(url: str) -> str:
    """Pull the product slug from a hamrahtel product URL.

    'https://hamrahtel.com/products/galaxy-a07-64gb-ram-4gb' -> 'galaxy-a07-64gb-ram-4gb'
    """
    if not url:
        raise ScraperError("Hamrahtel: empty URL")
    raw = url.strip()
    if "/" not in raw and "." not in raw:
        return raw
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    parts = [p for p in (parsed.path or "").split("/") if p]
    if not parts:
        raise ScraperError(f"Hamrahtel: no slug in URL: {url}")
    if "products" in parts:
        i = parts.index("products")
        if i + 1 < len(parts):
            return parts[i + 1]
    if "product" in parts:
        i = parts.index("product")
        if i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1]


class HamrahtelScraper(BaseScraper):
    name = "hamrahtel"

    def scrape(self, url: str) -> ScrapeResult:
        slug = _extract_slug(url)
        data = self._fetch_api(slug)
        return self._parse_api(data)

    def parse(self, html: str, url: str) -> ScrapeResult:  # pragma: no cover
        raise NotImplementedError("HamrahtelScraper uses the GraphQL API, not HTML.")

    def _fetch_api(self, slug: str) -> dict:
        body = {"query": _QUERY, "variables": {"slug": slug}}
        try:
            response = requests.post(
                GRAPHQL_URL, json=body, headers=_HEADERS,
                timeout=self.timeout, allow_redirects=True,
            )
        except requests.Timeout as exc:
            raise ScraperRetryable(f"Timeout fetching Hamrahtel API for {slug}") from exc
        except requests.RequestException as exc:
            raise ScraperRetryable(f"Network error fetching Hamrahtel API for {slug}: {exc}") from exc

        if response.status_code in (403, 429):
            raise ScraperBlocked(f"Hamrahtel API blocked (HTTP {response.status_code})")
        if response.status_code >= 500:
            raise ScraperRetryable(f"Hamrahtel API server error HTTP {response.status_code}")
        if response.status_code >= 400:
            raise ScraperError(f"Hamrahtel API HTTP {response.status_code} for {slug}")

        try:
            return response.json()
        except ValueError as exc:
            raise ScraperRetryable(f"Hamrahtel API non-JSON for {slug}") from exc

    def _parse_api(self, data: dict) -> ScrapeResult:
        if not isinstance(data, dict):
            raise ScraperError("Hamrahtel API: unexpected response shape")

        # GraphQL errors come back in an "errors" array.
        product = (data.get("data") or {}).get("publicProduct")
        if not product:
            # No such product (bad slug) -> treat as out of stock rather than crash.
            return ScrapeResult(price=None, currency="TOMAN",
                                availability="out_of_stock", raw_title="")

        title = str(product.get("name") or "")
        variants = product.get("variants") or []

        cheapest: Optional[Decimal] = None
        any_in_stock = False

        for v in variants:
            if not isinstance(v, dict):
                continue
            qty = v.get("quantityAvailable") or 0
            pricing = v.get("pricing") or {}
            price_node = (pricing.get("price") or {}).get("gross") or {}
            amount = price_node.get("amount")

            if qty and qty > 0 and amount is not None:
                # amount is a JSON number (e.g. 21039000.0) already in TOMAN.
                # Convert directly to an integer Decimal. Do NOT use parse_price
                # on str(amount): "21039000.0" would lose the decimal point and
                # be read as 210390000 (10x too big).
                try:
                    price = Decimal(str(amount)).to_integral_value()
                except Exception:
                    price = None
                if price and price > 0:
                    any_in_stock = True
                    if cheapest is None or price < cheapest:
                        cheapest = price

        if cheapest is None:
            # No in-stock variant. Respect the product-level availability flag.
            avail = "out_of_stock"
            if product.get("isAvailable") and not any_in_stock:
                avail = "out_of_stock"
            return ScrapeResult(price=None, currency="TOMAN",
                                availability=avail, raw_title=title)

        # Prices are already TOMAN; return as-is.
        return ScrapeResult(price=cheapest, currency="TOMAN",
                            availability="in_stock", raw_title=title)
