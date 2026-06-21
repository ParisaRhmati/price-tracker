"""Diagnostic for the mobile140 scraper.

Run INSIDE the backend container:
    docker compose exec backend python diag_mobile140.py

It fetches a couple of mobile140 product URLs exactly the way the scraper does,
then reports:
  - whether the new (fixed) scraper code is loaded
  - the HTTP fetch result (length of HTML received)
  - whether the authoritative <meta name="product_price"> tag is present
  - what price the scraper extracts

This tells us whether the scraper is (a) running new code and (b) actually
receiving the real product page (vs a bot-blocked / stripped page).
"""
import os
import sys

# Make Django importable so the scraper's settings load.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django  # noqa: E402

django.setup()

from products.services.scrapers.mobile140 import Mobile140Scraper  # noqa: E402

# A few product URLs that were showing the wrong (insurance) price.
TEST_URLS = [
    "https://mobile140.com/product-single/samsung-galaxy-a36-128gb-ram-8gb-vietnam",
    "https://mobile140.com/product-single/samsung-galaxy-a17-128gb-6gb-mobile-phone",
]

# Allow passing a URL on the command line.
if len(sys.argv) > 1:
    TEST_URLS = sys.argv[1:]


def main() -> None:
    scraper = Mobile140Scraper()

    # 1. Is the NEW code loaded? The fixed version has this comment string.
    import inspect

    src = inspect.getsource(Mobile140Scraper.parse)
    has_fix = "do not let the" in src or "AUTHORITATIVE" in src
    print("=" * 60)
    print("NEW FIX LOADED IN CONTAINER:", "YES" if has_fix else "NO  <-- PROBLEM")
    print("=" * 60)

    for url in TEST_URLS:
        print(f"\nURL: {url}")
        # Fetch raw HTML using the scraper's own fetch path.
        try:
            html = scraper._fetch_with_retry(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  FETCH FAILED: {type(exc).__name__}: {exc}")
            continue

        print(f"  HTML length: {len(html):,} chars")
        has_meta = 'name="product_price"' in html or "name='product_price'" in html
        print(f"  <meta product_price> present: {'YES' if has_meta else 'NO'}")
        if has_meta:
            import re

            m = re.search(
                r'<meta[^>]*name=["\']product_price["\'][^>]*content=["\']([^"\']+)["\']',
                html,
            )
            if not m:
                m = re.search(
                    r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']product_price["\']',
                    html,
                )
            if m:
                print(f"  meta product_price value: {m.group(1)}")

        has_insurance_hint = "بیمه" in html
        print(f"  insurance widget (بیمه) in page: {has_insurance_hint}")

        # Now run the actual scraper parse.
        try:
            result = scraper.parse(html, url)
            print(f"  --> SCRAPER RESULT price: {result.price}")
            print(f"  --> availability: {result.availability}")
        except Exception as exc:  # noqa: BLE001
            print(f"  --> SCRAPER PARSE ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
