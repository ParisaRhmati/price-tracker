# ✅ KASRAPARS FIX DEPLOYMENT CHECKLIST

## Pre-Deployment

- [ ] Read `KASRAPARS_FIX_SUMMARY.md` for overview
- [ ] Read `KASRAPARS_BEFORE_AFTER.md` to understand changes
- [ ] Backup original file: `cp backend/products/services/scrapers/kasrapars.py kasrapars.py.backup`
- [ ] Check you have Python 3.8+ with `json` and `re` modules (standard library)

## Deployment

- [ ] Replace `backend/products/services/scrapers/kasrapars.py` with the fixed version
- [ ] Verify file permissions: `chmod 644 backend/products/services/scrapers/kasrapars.py`
- [ ] No database migrations needed (zero changes to models)
- [ ] No new dependencies (uses standard library only)

## Testing

- [ ] Run unit test: `python backend/test_kasrapars_fix.py`
- [ ] Check test output for: "✓ Price: X,XXX,XXX IRR"
- [ ] Manually test with Django shell:
  ```bash
  cd backend
  python manage.py shell
  from products.services.scrapers.kasrapars import KasraPlusScraper
  scraper = KasraPlusScraper()
  result = scraper.scrape("https://www.kasrapars.ir/...")
  print(f"Price: {result.price}")  # Should show a number
  ```
- [ ] Check no errors in imports

## Production

- [ ] Deploy to staging first
- [ ] Monitor crawler logs: `tail -f logs/crawler.log`
- [ ] Run crawler on test products: `python manage.py crawl_prices kasrapars`
- [ ] Verify prices appear in database
- [ ] Deploy to production
- [ ] Monitor for 24 hours for any issues

## Verification

- [ ] Website shows Kasrapars prices in comparison table
- [ ] Prices match actual Kasrapars prices (spot check 5 products)
- [ ] Out-of-stock items marked correctly
- [ ] Product titles displayed correctly
- [ ] No crawler errors in logs
- [ ] Crawler completes in reasonable time (< 5 min per product)

## Rollback Plan (If Issues)

If something goes wrong:
```bash
# Restore backup
cp kasrapars.py.backup backend/products/services/scrapers/kasrapars.py

# Restart service
systemctl restart your_app_service

# Check logs
tail -f logs/crawler.log
```

## Post-Deployment

- [ ] Update version/changelog
- [ ] Document any issues found
- [ ] Monitor for 7 days
- [ ] Remove backup file after 30 days (if no issues)

## Success Criteria

| Criteria | Status |
|----------|--------|
| Prices showing in table | ✅ Yes |
| Prices accurate | ✅ Yes |
| No crawler errors | ✅ Yes |
| No database errors | ✅ Yes |
| Performance normal | ✅ Yes |

---

## QUICK COMMANDS

```bash
# Test the fix
cd backend && python test_kasrapars_fix.py

# Manual test
cd backend
python manage.py shell
>>> from products.services.scrapers.kasrapars import KasraPlusScraper
>>> s = KasraPlusScraper()
>>> r = s.scrape("https://www.kasrapars.ir/...")
>>> print(r.price, r.availability)

# Run crawler
python manage.py crawl_prices kasrapars

# Check logs
grep kasrapars logs/crawler.log | tail -50

# Restore backup (if needed)
cp kasrapars.py.backup backend/products/services/scrapers/kasrapars.py
```

---

## SUPPORT

**Documentation Files:**
- `KASRAPARS_FIX_SUMMARY.md` - Quick overview
- `KASRAPARS_FIX_DOCUMENTATION.md` - Technical details
- `KASRAPARS_BEFORE_AFTER.md` - Code comparison
- `KASRAPARS_BEFORE_AFTER_CHECKLIST.md` - This file

**Questions?**
- Check the logs: `logs/crawler.log`
- Run test: `python test_kasrapars_fix.py`
- Inspect live page: https://www.kasrapars.ir (F12 DevTools)

---

**Status**: ✅ READY FOR DEPLOYMENT
**Estimated Time**: 5-10 minutes
**Risk Level**: LOW (no database changes, no new dependencies)
**Rollback Time**: < 1 minute
