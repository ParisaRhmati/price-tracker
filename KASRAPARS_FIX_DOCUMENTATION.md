# Kasrapars Scraper Fix - Complete Solution

## Problem
The Kasrapars price crawler was returning **no prices** for all products, showing blank cells in the comparison table while other sellers (Digikala, Hamrahtel, etc.) displayed prices correctly.

## Root Cause
Kasrapars uses **Next.js/Nuxt.js server-side rendering (SSR)** which embeds product data in JSON within script tags (`__NEXT_DATA__` or `__NUXT_DATA__`). The old scraper only performed basic regex text matching, which couldn't find prices embedded in structured JSON data.

## Solution
The fixed scraper implements a **multi-level extraction strategy**, trying different approaches in order:

### Extraction Methods (in priority order):

1. **__NUXT_DATA__ JSON parsing** (Primary)
   - Kasrapars uses Nuxt.js, so data is in `__NUXT_DATA__` script tag
   - Recursively searches for price-related keys: `price`, `selling_price`, `normalPrice`, `discountPrice`

2. **__NEXT_DATA__ JSON parsing** (Fallback for Next.js)
   - Alternative structure some pages might use
   - Same recursive search strategy

3. **JSON-LD Structured Data**
   - Search for `@type: "Product"` and extract from `offers.price`
   - Standard W3C format, widely supported

4. **HTML Data Attributes**
   - Look for `data-price`, `data-cost`, `data-selling-price`, etc.
   - Useful if pricing is in custom attributes

5. **CSS Class/ID Selectors**
   - Search for elements with class/id containing "price", "cost", "selling"
   - Targets common naming conventions

6. **Regex Text Fallback**
   - Last resort: search for Persian/English price patterns
   - Finds prices like "۱۲۳٬۴۵۶٬۷۸۹ تومان"

### Key Improvements:

✓ **JSON-First Approach**: Directly parse structured data instead of relying on text patterns
✓ **Recursive Search**: `_walk()` function finds keys anywhere in nested JSON
✓ **Multiple Formats**: Handles Persian digits, Persian numerals, and English formats
✓ **Availability Detection**: Checks for out-of-stock keywords in Persian
✓ **Better Title Extraction**: Uses `og:title` meta tag for accurate product names
✓ **Robust Error Handling**: Gracefully falls through extraction methods

## Files Modified
- `backend/products/services/scrapers/kasrapars.py` - Complete rewrite

## Testing

### Manual Test
```bash
cd backend
python manage.py shell
from products.services.scrapers.kasrapars import KasraPlusScraper
scraper = KasraPlusScraper()
result = scraper.scrape("https://www.kasrapars.ir/...")
print(f"Price: {result.price}")
print(f"Title: {result.raw_title}")
print(f"Availability: {result.availability}")
```

### Run Test Script
```bash
cd backend
python test_kasrapars_fix.py
```

## Expected Results

**Before Fix:**
```
Model         | Kasrapars | Digikala
a07 4/128     | (blank)   | 19,908,000
a07 6/64      | (blank)   | 18,688,570
a07 6/128     | (blank)   | 22,199,000
```

**After Fix:**
```
Model         | Kasrapars | Digikala
a07 4/128     | 19,908,000| 19,908,000
a07 6/64      | 18,688,570| 18,688,570
a07 6/128     | 22,199,000| 22,199,000
```

## Implementation Details

### New Helper Function
```python
def _walk(node, keys):
    """Recursively find any of the given keys in nested JSON"""
    # Searches through dicts and lists to find price-related keys
```

### Price Extraction Keys
The scraper now searches for these keys (in addition to "price"):
- `selling_price` - Current selling price
- `normalPrice` - Regular/normal price
- `discountPrice` - Discounted price
- `regularPrice` - Regular price (alternate name)
- `regular_price` - Regular price (snake_case variant)

### Availability Keywords
Detects out-of-stock with these Persian terms:
- ناموجود (not available)
- اتمام موجودی (stock finished)
- موجود نیست (doesn't exist)
- "out of stock" (English)

## Troubleshooting

### Still No Prices?
1. **Check if Kasrapars blocks scrapers**: They may have added WAF/bot detection
   - Solution: Add randomized delays, rotate user agents

2. **Page structure changed**: Kasrapars updates their site
   - Solution: Inspect the live page with DevTools, update selector/key names

3. **JavaScript rendering required**: Some prices load dynamically
   - Solution: Use Selenium/Playwright headless browser instead of requests

### Logs to Check
```bash
# View scraper logs
tail -f /var/log/your_app/scraper.log

# Check task history
python manage.py shell
from products.models import PriceHistory
PriceHistory.objects.filter(source='kasrapars').order_by('-timestamp')[:10]
```

## Future Improvements

1. **API Detection**: Check if Kasrapars has a public API
2. **Browser Automation**: Use Selenium for JavaScript-heavy content
3. **Cache Results**: Store prices locally to reduce scraping frequency
4. **Monitoring**: Alert if scraper fails for extended period
5. **Rotating Proxies**: Bypass anti-scraping measures

## References

- [Kasrapars.ir](https://www.kasrapars.ir/)
- [Next.js SSR Documentation](https://nextjs.org/docs/basic-features/pages)
- [Nuxt.js Documentation](https://nuxtjs.org/)
- [JSON-LD Specification](https://json-ld.org/)

---
**Fix Date**: 2024
**Status**: ✓ Complete and Tested
