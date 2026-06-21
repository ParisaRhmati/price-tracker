"""Base scraper. Each website scraper extends this class.

Design notes:
- Scrapers are stateless. Network I/O happens via the shared `_request` helper.
- They return a ScrapeResult dataclass; they never write to the database. The
  crawler service is responsible for persisting results, so scrapers can be
  unit-tested in isolation.
- Errors that should be retried raise `ScraperRetryable`. Anything else (e.g.
  HTTP 404, structurally missing price) raises `ScraperError` and is recorded
  as a failure without retries.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Permanent failure - do not retry."""


class ScraperRetryable(Exception):
    """Transient failure - retry with backoff."""


class ScraperBlocked(ScraperError):
    """Site is actively blocking us (captcha, 403, WAF page)."""


@dataclass
class ScrapeResult:
    price: Optional[Decimal]
    currency: str = "IRR"
    availability: str = "unknown"  # 'in_stock' | 'out_of_stock' | 'unknown'
    raw_title: str = ""

    @property
    def is_valid(self) -> bool:
        return self.price is not None and self.price > 0


# Persian digit translation table so '۱۲۳' becomes '123'.
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits(text: str) -> str:
    """Convert Persian/Arabic digits to ASCII digits."""
    return (text or "").translate(_PERSIAN_DIGITS)


def parse_price(text: str) -> Optional[Decimal]:
    """Pull a numeric price out of a string. Returns None if nothing usable.

    Handles common shapes:
        '12,300,000 تومان'
        '۱۲٬۳۰۰٬۰۰۰'
        '1.299.000'
        '12300000'
    """
    if not text:
        return None
    cleaned = normalize_digits(text)
    # Strip everything that's not a digit, dot, or comma (currency words, RTL marks).
    candidate = re.sub(r"[^\d.,]", "", cleaned)
    if not candidate:
        return None
    # Strip thousand separators (commas, dots, apostrophes). We treat dots as
    # thousand separators here because Iranian Rial / Toman prices are integers.
    digits_only = re.sub(r"[.,\s']", "", candidate)
    if not digits_only:
        return None
    try:
        value = Decimal(digits_only)
    except InvalidOperation:
        return None
    return value if value > 0 else None


class BaseScraper:
    """Subclass and override `parse`. `fetch` and retry logic come for free."""

    name: str = "base"

    def __init__(self) -> None:
        self.timeout = settings.SCRAPER_TIMEOUT_SECONDS
        self.max_retries = settings.SCRAPER_MAX_RETRIES
        self.headers = {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        }

    # -- public API --------------------------------------------------------
    def scrape(self, url: str) -> ScrapeResult:
        """Fetch the URL with retries and delegate parsing to subclass."""
        html = self._fetch_with_retry(url)
        return self.parse(html, url)

    def parse(self, html: str, url: str) -> ScrapeResult:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- helpers -----------------------------------------------------------
    def _fetch_with_retry(self, url: str) -> str:
        retrying = Retrying(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(ScraperRetryable),
        )
        for attempt in retrying:
            with attempt:
                return self._fetch(url)
        raise ScraperError("Retry loop exited unexpectedly")  # pragma: no cover

    def _fetch(self, url: str) -> str:
        try:
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout, allow_redirects=True
            )
        except requests.Timeout as exc:
            raise ScraperRetryable(f"Timeout fetching {url}") from exc
        except requests.RequestException as exc:
            raise ScraperRetryable(f"Network error fetching {url}: {exc}") from exc

        if response.status_code in (403, 429):
            raise ScraperBlocked(
                f"Site blocked the request (HTTP {response.status_code})"
            )
        if response.status_code >= 500:
            raise ScraperRetryable(f"Server error HTTP {response.status_code}")
        if response.status_code == 404:
            raise ScraperError("Product page not found (HTTP 404)")
        if response.status_code >= 400:
            raise ScraperError(f"Client error HTTP {response.status_code}")
        return response.text

    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")
