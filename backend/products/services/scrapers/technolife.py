"""Technolife (technolife.com) scraper.

Strategy (most reliable to least):
    1. JSON-LD <script type="application/ld+json"> Product offers.
    2. __NEXT_DATA__ JSON blob, walking for the SELLING price (we now look at
       the key name and prefer 'selling_price' / 'final_price' over the raw
       'price', because 'price' often means MSRP/list price.).
    3. The bold price paragraph in the DOM (class contains
       'text-primary-shade-1' and font-semiBold). We explicitly ignore any
       element whose class list contains 'line-through' (that's the crossed-out
       original price).
    4. Meta tags.
    5. Last-resort text search, also skipping line-through ancestors.

The earlier version of this scraper was occasionally returning a price that
disagreed with what the user saw on the website, because:
  - Technolife shows the original price (line-through) and the selling
    price next to each other, and the generic text regex was sometimes
    matching the wrong one.
  - The __NEXT_DATA__ walker picked the first 'price' field it found, but
    that's often the list price, not the selling price.

This version fixes both by being explicit about WHICH price to take.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Optional

from .base import BaseScraper, ScrapeResult, ScraperError, parse_price


# In Technolife's __NEXT_DATA__ JSON, the SELLING price (after discount) lives
# under these keys. We try them in order. We deliberately put plain 'price'
# LAST because that key is sometimes the list/MSRP price on Technolife.
_PRICE_KEYS_PREFERRED = (
    "selling_price",
    "sellingPrice",
    "final_price",
    "finalPrice",
    "discounted_price",
    "discountedPrice",
    "price_after_discount",
    "priceAfterDiscount",
)
_PRICE_KEYS_FALLBACK = ("price", "amount")


def _walk_for_price(node: Any, keys: tuple[str, ...]) -> Optional[Decimal]:
    """Recursively walk JSON looking for any of the given price keys."""
    if isinstance(node, dict):
        for key in keys:
            if key in node:
                value = node[key]
                if isinstance(value, (int, float, str)):
                    parsed = parse_price(str(value))
                    if parsed and parsed > 1000:  # filter out tiny numbers
                        return parsed
        for value in node.values():
            found = _walk_for_price(value, keys)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _walk_for_price(item, keys)
            if found:
                return found
    return None


def _is_inside_line_through(element) -> bool:
    """Walk up the DOM tree to check if any ancestor has a line-through class."""
    current = element
    while current is not None and getattr(current, "name", None):
        classes = current.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        for cls in classes:
            if "line-through" in cls:
                return True
        current = current.parent
    return False


class TechnolifeScraper(BaseScraper):
    name = "technolife"

    def parse(self, html: str, url: str) -> ScrapeResult:
        soup = self.soup(html)

        price: Optional[Decimal] = None
        availability = "unknown"
        title = ""

        # 1. JSON-LD (most reliable source of truth)
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
                    # Detect overall product availability BEFORE picking any
                    # price. Technolife pages for out-of-stock products often
                    # still list cheap accessory offers in offers[].offers - we
                    # must not pick those as the product's price.
                    overall_avail = (offers.get("availability") or "").lower()
                    if "outofstock" in overall_avail or "soldout" in overall_avail:
                        availability = "out_of_stock"
                    elif "instock" in overall_avail:
                        availability = "in_stock"

                    # Technolife uses AggregateOffer with a nested "offers" list
                    # of individual seller offers. Pick the cheapest INDIVIDUAL
                    # offer that is itself InStock - never an OutOfStock entry,
                    # never an accessory tagged differently.
                    raw_price = None
                    sub_offers = offers.get("offers")
                    saw_usable_subof = False
                    if isinstance(sub_offers, list) and sub_offers:
                        candidate_prices = []
                        any_in_stock = False
                        for item in sub_offers:
                            if not isinstance(item, dict):
                                continue
                            item_avail = (item.get("availability") or "").lower()
                            # Only accept sub-offers whose availability we can
                            # verify is InStock. Skip unknown/OOS entries.
                            if "instock" not in item_avail:
                                continue
                            any_in_stock = True
                            p = item.get("price")
                            if p is not None:
                                parsed = parse_price(str(p))
                                if parsed and parsed > 1000:
                                    candidate_prices.append(parsed)
                                    saw_usable_subof = True
                        if candidate_prices:
                            raw_price = min(candidate_prices)
                        # If sub_offers existed but NONE of them were in stock,
                        # the product itself is effectively unavailable.
                        if not any_in_stock and availability == "unknown":
                            availability = "out_of_stock"

                    # Direct price fields are only safe to use when overall
                    # availability is in_stock (or still unknown). Skip them
                    # entirely on OOS pages so we don't surface a stale MSRP.
                    direct_price_available = False
                    if raw_price is None and availability != "out_of_stock":
                        v = offers.get("price") or offers.get("lowPrice")
                        if v:
                            parsed = parse_price(str(v))
                            if parsed and parsed > 1000:
                                raw_price = parsed
                                direct_price_available = True

                    if raw_price and availability != "out_of_stock":
                        price = raw_price

                    # IMPLICIT OOS DETECTION: Technolife pages for unavailable
                    # products sometimes don't say "OutOfStock" explicitly. They
                    # just leave price/lowPrice null and put a single placeholder
                    # sub-offer with price=0 in the offers list. If after all
                    # the above we have a Product JSON-LD but no usable price
                    # signal at all, treat the page as OOS. This is the bug from
                    # the a56 8/128 page where we picked 2,775,000 from a
                    # __NEXT_DATA__ accessory entry.
                    if (
                        availability == "unknown"
                        and not saw_usable_subof
                        and not direct_price_available
                    ):
                        availability = "out_of_stock"

        # If JSON-LD already told us this is OOS, we're done. Don't fall
        # through to DOM-based fallbacks - those pick up accessory prices.
        if availability == "out_of_stock":
            if not title:
                t = soup.find("h1") or soup.find("title")
                if t:
                    title = t.get_text(strip=True)
            return ScrapeResult(
                price=None,
                currency="IRR",
                availability="out_of_stock",
                raw_title=title,
            )

        # 2. __NEXT_DATA__ - selling-price keys first, then plain 'price'.
        if price is None:
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data and next_data.string:
                try:
                    parsed_state = json.loads(next_data.string)
                    price = (
                        _walk_for_price(parsed_state, _PRICE_KEYS_PREFERRED)
                        or _walk_for_price(parsed_state, _PRICE_KEYS_FALLBACK)
                    )
                except ValueError:
                    pass

        # 3. DOM: the bold selling-price paragraph. Only used when the page
        #    didn't already say "out of stock" - otherwise these classes can
        #    point at accessory prices in "frequently bought together" tiles.
        if price is None:
            candidates = []
            candidates.extend(soup.select("p.text-primary-shade-1.font-semiBold"))
            candidates.extend(soup.select("p.text-primary.font-semiBold"))
            candidates.extend(soup.select('p[class*="text-primary-shade-1"]'))
            candidates.extend(soup.select('p[class*="text-primary"]'))

            seen = set()
            for el in candidates:
                if id(el) in seen:
                    continue
                seen.add(id(el))
                if _is_inside_line_through(el):
                    continue
                text = el.get_text(" ", strip=True)
                digit_count = sum(
                    1 for ch in text if ch.isdigit() or "۰" <= ch <= "۹"
                )
                if digit_count < 4:
                    continue
                candidate = parse_price(text)
                # Filter out tiny numbers that are accessory prices (e.g.
                # screen protectors, cases). Real phones are well above
                # 5,000,000 toman in 2026.
                if candidate and candidate > 5_000_000:
                    price = candidate
                    break

        # 4. Meta tags
        if price is None:
            for meta_name in ("product:price:amount", "og:price:amount"):
                tag = soup.find("meta", attrs={"property": meta_name}) or soup.find(
                    "meta", attrs={"name": meta_name}
                )
                if tag and tag.get("content"):
                    parsed = parse_price(tag["content"])
                    if parsed and parsed > 5_000_000:
                        price = parsed
                        break

        # 5. We intentionally do NOT scan generic body text any more.
        #    That fallback was responsible for picking up accessory prices
        #    on out-of-stock pages. If steps 1-4 didn't find anything, the
        #    product page is missing a usable signal and we treat it as OOS.

        # Title
        if not title:
            title_tag = soup.find("h1") or soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

        # Body text hints for availability (only relevant if we still don't
        # know AND we did find a price).
        if availability == "unknown":
            body_text = soup.get_text(" ", strip=True)
            if any(kw in body_text for kw in ("ناموجود", "اتمام موجودی")):
                availability = "out_of_stock"
            elif price is not None:
                availability = "in_stock"

        # No price found = treat as OOS instead of raising. Aligns with how
        # the Mobile140 scraper handles missing prices and avoids confusing
        # "Scrape failed" rows in the UI.
        if price is None:
            return ScrapeResult(
                price=None,
                currency="IRR",
                availability=(
                    "out_of_stock" if availability == "unknown" else availability
                ),
                raw_title=title,
            )

        return ScrapeResult(
            price=price, currency="IRR", availability=availability, raw_title=title
        )
