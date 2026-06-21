"""Digikala (digikala.com) scraper.

Digikala is a single-page app built on Next.js. The HTML you get from a plain
HTTP request is an empty shell — the product data is loaded by JavaScript
from Digikala's JSON API. Scraping the rendered HTML therefore returns
nothing useful unless you run a real browser.

Instead, we go straight to the JSON API:

    https://api.digikala.com/v1/product/{product_id}/

The product id is in the URL itself (e.g. `dkp-20109389`). We extract it,
hit the API, and read the price from the resulting JSON. This is roughly
50x faster than running a headless browser and far more reliable.

If the API call fails for any reason, we fall back to the old HTML-based
parsing path so this scraper still works on URLs that contain inline data.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Optional

import requests

from .base import (
    BaseScraper,
    ScrapeResult,
    ScraperBlocked,
    ScraperError,
    ScraperRetryable,
    parse_price,
)


# Matches product slugs like 'dkp-20109389' anywhere in a URL.
_PRODUCT_ID_RE = re.compile(r"dkp[-_](\d+)", re.IGNORECASE)

_API_TEMPLATE = "https://api.digikala.com/v2/product/{pid}/"


def _walk(node: Any, keys: tuple[str, ...]) -> Optional[Any]:
    """Find the first occurrence of any of the given keys in a nested JSON."""
    if isinstance(node, dict):
        for key in keys:
            if key in node:
                return node[key]
        for value in node.values():
            found = _walk(value, keys)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _walk(item, keys)
            if found is not None:
                return found
    return None


def _extract_product_id(url: str) -> Optional[str]:
    match = _PRODUCT_ID_RE.search(url or "")
    return match.group(1) if match else None


class DigikalaScraper(BaseScraper):
    name = "digikala"

    # ------------------------------------------------------------------
    # Main entry point. We override `scrape` (not `parse`) because the API
    # path doesn't deal with HTML at all.
    # ------------------------------------------------------------------
    def scrape(self, url: str) -> ScrapeResult:
        product_id = _extract_product_id(url)
        if product_id:
            try:
                return self._scrape_via_api(product_id)
            except (ScraperError, ScraperRetryable, ScraperBlocked):
                # API path failed; fall through to HTML parsing as a backup.
                pass
        # Fallback: download the HTML and try to parse whatever is inline.
        html = self._fetch_with_retry(url)
        return self.parse(html, url)

    # ------------------------------------------------------------------
    # API path
    # ------------------------------------------------------------------
    def _scrape_via_api(self, product_id: str) -> ScrapeResult:
        api_url = _API_TEMPLATE.format(pid=product_id)
        api_headers = {
            **self.headers,
            "Accept": "application/json",
            "X-Web-Client": "desktop",
        }
        try:
            response = requests.get(api_url, headers=api_headers, timeout=self.timeout)
        except requests.Timeout as exc:
            raise ScraperRetryable(f"Timeout calling Digikala API: {exc}") from exc
        except requests.RequestException as exc:
            raise ScraperRetryable(f"Network error calling Digikala API: {exc}") from exc

        if response.status_code in (403, 429):
            raise ScraperBlocked(
                f"Digikala API blocked the request (HTTP {response.status_code})"
            )
        if response.status_code >= 500:
            raise ScraperRetryable(f"Digikala API server error {response.status_code}")
        if response.status_code == 404:
            raise ScraperError(f"Product {product_id} not found on Digikala API")
        if response.status_code >= 400:
            raise ScraperError(f"Digikala API HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ScraperError(f"Digikala API returned non-JSON: {exc}") from exc

        # The payload looks like {"status": 200, "data": {"product": {...}}}.
        product = (
            payload.get("data", {}).get("product")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(product, dict):
            raise ScraperError("Digikala API response missing 'data.product'")

        title = str(product.get("title_fa") or product.get("title_en") or "")

        # The selling price lives under default_variant.price.selling_price.
        # We walk defensively because Digikala has shipped a few shapes over
        # the years.
        variant = product.get("default_variant") or {}
        price_obj = variant.get("price") if isinstance(variant, dict) else None
        if not isinstance(price_obj, dict):
            # Try the top-level 'price' as a fallback.
            price_obj = product.get("price")

        price: Optional[Decimal] = None
        if isinstance(price_obj, dict):
            # In Digikala's API: selling_price = current price; rrp_price = MSRP.
            raw = (
                price_obj.get("selling_price")
                or price_obj.get("discount_price")
                or price_obj.get("rrp_price")
            )
            if raw is not None:
                price = parse_price(str(raw))

        # Last-resort deep walk in case the structure has changed again.
        if price is None:
            raw = _walk(product, ("selling_price", "discount_price", "rrp_price"))
            if raw is not None:
                price = parse_price(str(raw))

        # Availability: Digikala uses several flags. status == "marketable"
        # means in stock; "out_of_stock" or no default_variant means not.
        status = (product.get("status") or "").lower()
        if status == "marketable" and price is not None:
            availability = "in_stock"
        elif status in ("out_of_stock", "unavailable") or price is None:
            availability = "out_of_stock"
        else:
            availability = "in_stock" if price is not None else "unknown"

        if price is None:
            raise ScraperError(
                f"Digikala API gave no usable price for product {product_id}"
            )

        return ScrapeResult(
            price=price, currency="IRR", availability=availability, raw_title=title
        )

    # ------------------------------------------------------------------
    # HTML fallback (used only when the URL has no dkp-* id, or the API
    # call fails for some reason). Same layered strategy as before.
    # ------------------------------------------------------------------
    def parse(self, html: str, url: str) -> ScrapeResult:
        soup = self.soup(html)

        price: Optional[Decimal] = None
        availability = "unknown"
        title = ""

        # JSON-LD
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
            except (ValueError, TypeError):
                continue
            payload = data[0] if isinstance(data, list) and data else data
            if not isinstance(payload, dict):
                continue
            if payload.get("@type") in ("Product", "ProductGroup"):
                title = title or str(payload.get("name") or "")
                offers = payload.get("offers") or {}
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    raw_price = offers.get("price") or offers.get("lowPrice")
                    if raw_price:
                        price = parse_price(str(raw_price)) or price
                    avail = (offers.get("availability") or "").lower()
                    if "instock" in avail:
                        availability = "in_stock"
                    elif "outofstock" in avail or "soldout" in avail:
                        availability = "out_of_stock"

        # __NEXT_DATA__ — Digikala's SSR sometimes embeds the product here.
        if price is None:
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data and next_data.string:
                try:
                    state = json.loads(next_data.string)
                    raw = _walk(state, ("selling_price", "discount_price", "rrp_price"))
                    if raw is not None:
                        price = parse_price(str(raw))
                except ValueError:
                    pass

        # Meta tags
        if price is None:
            for meta_name in ("product:price:amount", "og:price:amount"):
                tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
                    "meta", attrs={"name": meta_name}
                )
                if tag and tag.get("content"):
                    price = parse_price(tag["content"])
                    if price:
                        break

        # Data attributes
        if price is None:
            for attr in ("data-price", "data-selling-price"):
                el = soup.find(attrs={attr: True})
                if el:
                    price = parse_price(el.get(attr, ""))
                    if price:
                        break

        # Final text fallback
        if price is None:
            text = soup.get_text(" ", strip=True)
            match = re.search(
                r"([\d۰-۹٠-٩.,]{4,})\s*(?:تومان|﷼|ریال|toman|rial)", text, re.I
            )
            if match:
                price = parse_price(match.group(1))

        if not title:
            title_tag = soup.find("h1") or soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

        if availability == "unknown":
            body_text = soup.get_text(" ", strip=True)
            if any(kw in body_text for kw in ("ناموجود", "اتمام موجودی")):
                availability = "out_of_stock"
            elif price is not None:
                availability = "in_stock"

        if price is None:
            raise ScraperError(
                "Could not locate price on Digikala page (selectors may have changed)"
            )

        return ScrapeResult(
            price=price, currency="IRR", availability=availability, raw_title=title
        )
