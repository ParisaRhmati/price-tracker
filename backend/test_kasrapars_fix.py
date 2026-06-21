#!/usr/bin/env python
"""Test script for Kasrapars scraper fix."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from products.services.scrapers.kasrapars import KasraPlusScraper
from products.services.scrapers.base import ScraperError

def test_kasrapars_scraper():
    """Test the Kasrapars scraper with a real product URL."""
    scraper = KasraPlusScraper()
    
    # Test URLs (popular Samsung models on Kasrapars)
    test_urls = [
        "https://www.kasrapars.ir/موبایل-سامسونگ-مدل-گلکسی-a07-4g-حافظه-128-گیگابایت",
        "https://www.kasrapars.ir/product/samsung-galaxy-a07-4g",
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print('='*60)
        try:
            result = scraper.scrape(url)
            print(f"✓ Price: {result.price:,.0f} {result.currency}")
            print(f"✓ Title: {result.raw_title}")
            print(f"✓ Availability: {result.availability}")
            print(f"✓ Valid: {result.is_valid}")
            return True
        except ScraperError as e:
            print(f"✗ ScraperError: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {type(e).__name__}: {e}")
    
    return False

if __name__ == "__main__":
    print("Kasrapars Scraper Fix Test")
    print("=" * 60)
    success = test_kasrapars_scraper()
    sys.exit(0 if success else 1)
