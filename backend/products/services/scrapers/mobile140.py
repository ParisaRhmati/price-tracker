from __future__ import annotations
import re
from decimal import Decimal
from typing import Optional
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper, ScrapeResult, ScraperBlocked, ScraperRetryable, parse_price

_COOKIE = '_pk_id.1.6310=7aa589a7c0958e48.1778662892.; _ga=GA1.1.1395884273.1778662893; _ga_WH12JYMCD4=GS2.1.s1780216585$o15$g0$t1780216586$j59$l0$h0; analytics_token=fc70cce4-26e2-fd6f-f67f-eddea0bb1972; _yngt_iframe=1; _yngt=9be2dea7-bf11-4aad-4998-0891d598037e; analytics_campaign={%22source%22:%22api.torob.com%22%2C%22medium%22:%22referral%22}; authToken=eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1laWRlbnRpZmllciI6IjUxNTg1NSIsImh0dHA6Ly9zY2hlbWFzLnhtbHNvYXAub3JnL3dzLzIwMDUvMDUvaWRlbnRpdHkvY2xhaW1zL21vYmlsZXBob25lIjoiMDkxOTc3MjQxODkiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoi2b7YsduM2LPYpyDYsdit2YXYqtuMINmG24zYpyIsIkRvbWFpbiI6Im1vYmlsZTE0MC5jb20iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJDdXN0b21lciIsIm5iZiI6MTc4MTUxNTI0MywiZXhwIjoxNzgyNzI0ODQzfQ.Zea1JZ3vhfgApBnZUZ703IDQc4cVSSdh3hmCb2yb7vQ; yektanet_session_last_activity=6/20/2026; _pk_ref.1.6310=%5B%22%22%2C%22%22%2C1781959941%2C%22https%3A%2F%2Fapi.torob.com%2F%22%5D; _pk_ses.1.6310=1; analytics_session_token=c0dd41fd-62c9-8303-3f54-fde65780c00e'

# Insurance/installment prices that mobile140 shows as add-ons.
# Any price matching these exactly is NOT the phone price.
_JUNK_PRICES = {399000, 499000, 599000, 699000, 799000, 899000, 999000,
                1199000, 1299000, 1399000, 1499000, 1599000, 1699000,
                1799000, 1899000, 1999000, 2199000, 2499000, 2999000}

def _is_real_price(p: Decimal) -> bool:
    """Return True if price looks like a phone price, not insurance/installment."""
    v = int(p)
    if v in _JUNK_PRICES:
        return False
    # Phone prices in Iran are at least 5,000,000 toman
    if v < 5_000_000:
        return False
    return True


class Mobile140Scraper(BaseScraper):
    name = "mobile140"

    def scrape(self, url: str) -> ScrapeResult:
        html = self._fetch(url)
        return self.parse(html, url)

    def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cookie": _COOKIE,
        }
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
        except requests.Timeout as exc:
            raise ScraperRetryable(f"Timeout: {url}") from exc
        except requests.RequestException as exc:
            raise ScraperRetryable(f"Network error: {exc}") from exc
        if resp.status_code in (403, 429):
            raise ScraperBlocked(f"Blocked HTTP {resp.status_code}")
        if resp.status_code >= 500:
            raise ScraperRetryable(f"Server error {resp.status_code}")
        return resp.text

    def parse(self, html: str, url: str) -> ScrapeResult:
        if not html:
            return ScrapeResult(price=None, currency="IRR", availability="out_of_stock", raw_title="")

        soup = BeautifulSoup(html, "lxml")
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

        meta_a = soup.find("meta", attrs={"name": "availability"})
        def get_avail(default="in_stock"):
            if meta_a and meta_a.get("content"):
                av = meta_a["content"].strip().lower()
                if "outofstock" in av or "nostock" in av:
                    return "out_of_stock"
                if "instock" in av:
                    return "in_stock"
            return default

        # ── Step 1: meta product_price (toman) ──────────────────────────
        meta_p = soup.find("meta", attrs={"name": "product_price"})
        if meta_p and meta_p.get("content"):
            price = parse_price(meta_p["content"])
            if price and _is_real_price(price):
                return ScrapeResult(price=price, currency="IRR",
                                    availability=get_avail(), raw_title=title)

        # ── Step 2: all price spans, skip junk prices ────────────────────
        # mobile140 renders prices in spans with font-bold class.
        # We collect ALL price-like numbers and take the smallest real one.
        _P = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩","01234567890123456789")
        candidates = []
        for span in soup.find_all("span"):
            txt = span.get_text(strip=True).translate(_P)
            # Remove commas/spaces
            txt = re.sub(r"[,\s]", "", txt)
            if re.fullmatch(r"\d{7,10}", txt):
                p = parse_price(txt)
                if p and _is_real_price(p):
                    candidates.append(p)

        if candidates:
            return ScrapeResult(price=min(candidates), currency="IRR",
                                availability=get_avail(), raw_title=title)

        # ── Step 3: JSON variants blob ───────────────────────────────────
        all_amounts = re.findall(r'"amount"\s*:\s*(\d{7,10})', html)
        real = [Decimal(a) for a in all_amounts if _is_real_price(Decimal(a))]
        if real:
            return ScrapeResult(price=min(real), currency="IRR",
                                availability=get_avail(), raw_title=title)

        # ── No real price found ──────────────────────────────────────────
        return ScrapeResult(price=None, currency="IRR",
                            availability=get_avail("out_of_stock"), raw_title=title)
