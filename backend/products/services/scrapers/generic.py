"""Generic fallback scraper.

Used when we don't have a dedicated scraper for the website. It tries the
universally-supported structured-data signals (JSON-LD, OpenGraph meta tags)
and then a text-based heuristic.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Optional

from .base import BaseScraper, ScrapeResult, ScraperError, parse_price


class GenericScraper(BaseScraper):
    name = "generic"

    def parse(self, html: str, url: str) -> ScrapeResult:
        soup = self.soup(html)

        price: Optional[Decimal] = None
        availability = "unknown"
        title = ""

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
                    elif "outofstock" in avail:
                        availability = "out_of_stock"

        if price is None:
            for meta_name in ("product:price:amount", "og:price:amount"):
                tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
                    "meta", attrs={"name": meta_name}
                )
                if tag and tag.get("content"):
                    price = parse_price(tag["content"])
                    if price:
                        break

        if price is None:
            text = soup.get_text(" ", strip=True)
            match = re.search(
                r"([\d۰-۹٠-٩.,]{4,})\s*(?:تومان|﷼|ریال|toman|rial|USD|EUR|\$)",
                text,
                re.I,
            )
            if match:
                price = parse_price(match.group(1))

        if not title:
            title_tag = soup.find("h1") or soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

        if availability == "unknown" and price is not None:
            availability = "in_stock"

        if price is None:
            raise ScraperError(
                "Generic scraper could not locate a price. Consider writing a "
                "dedicated scraper for this website."
            )

        return ScrapeResult(
            price=price, currency="IRR", availability=availability, raw_title=title
        )
