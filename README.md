# Price Tracker

Compare product prices across multiple e-commerce websites using URLs from an Excel sheet.

The repository contains two services:

- **backend/** — Django 5 + DRF + a pluggable scraper system. Reads `links.xlsx`, crawls each URL, stores prices and history.
- **frontend/** — Next.js 15 (App Router) + TypeScript + Tailwind. Dashboard, product list, detail with price comparison and history chart, crawler management.

---

## Architecture

```
        ┌──────────────┐         ┌──────────────────────┐
        │ links.xlsx   │ ─────▶  │ excel_importer       │
        └──────────────┘         │  (idempotent upsert) │
                                 └──────────┬───────────┘
                                            │
                            ┌───────────────▼──────────────┐
                            │ Product / ProductSource /    │
                            │ PriceHistory / CrawlJob      │
                            └───────────────┬──────────────┘
                                            │
                  ┌─────────────────────────▼──────────────────────────┐
                  │  Crawler service                                   │
                  │   ├─ ThreadPoolExecutor (settings.SCRAPER_         │
                  │   │  CONCURRENCY)                                  │
                  │   ├─ Picks scraper class via website_name / host  │
                  │   └─ Retries via tenacity (exponential backoff)    │
                  └─────────────────────────┬──────────────────────────┘
                                            │
       ┌───────────────────┬────────────────┴────────────────┬──────────┐
       │ DigikalaScraper   │ TechnolifeScraper               │ Generic  │
       │  JSON-LD → meta   │  JSON-LD → __NEXT_DATA__ → meta │ JSON-LD  │
       │   → DOM           │   → DOM                         │  → meta  │
       └───────────────────┴─────────────────────────────────┴──────────┘
                                            │
                                ┌───────────▼──────────┐
                                │ DRF API              │
                                │  /api/products       │
                                │  /api/sources        │
                                │  /api/crawl          │
                                │  /api/crawl-jobs     │
                                │  /api/import         │
                                │  /api/dashboard      │
                                └───────────┬──────────┘
                                            │
                                ┌───────────▼──────────┐
                                │ Next.js frontend     │
                                │  Dashboard           │
                                │  Products / Detail   │
                                │  Crawler management  │
                                └──────────────────────┘
```

The scraper layer is the design hot-spot. Each website gets its own class subclassing `BaseScraper`. They share a layered extraction strategy: **JSON-LD** (most reliable), then **OpenGraph/`product:price` meta tags**, then **DOM/text** fallbacks. If extraction fails the error is stored on `ProductSource.error_message` and surfaced in the UI.

---

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit if needed
python manage.py migrate
python manage.py createsuperuser    # optional
python manage.py import_excel /path/to/links.xlsx
python manage.py runserver
```

### Environment variables (`backend/.env`)

| Variable                   | Default                                     | Notes                                            |
| -------------------------- | ------------------------------------------- | ------------------------------------------------ |
| `DJANGO_SECRET_KEY`        | dev placeholder                             | Override in production                           |
| `DJANGO_DEBUG`             | `True`                                      | Set to `False` for production                    |
| `DJANGO_ALLOWED_HOSTS`     | `localhost,127.0.0.1`                       | Comma-separated                                  |
| `DATABASE_URL`             | empty → SQLite at `backend/db.sqlite3`      | e.g. `postgres://user:pass@localhost:5432/price` |
| `CORS_ALLOWED_ORIGINS`     | `http://localhost:3000`                     | Comma-separated                                  |
| `SCRAPER_TIMEOUT_SECONDS`  | `20`                                        |                                                  |
| `SCRAPER_MAX_RETRIES`      | `3`                                         | Exponential backoff between retries              |
| `SCRAPER_USER_AGENT`       | `Mozilla/5.0 (...) PriceTrackerBot/1.0`     | Identify yourself politely                       |
| `SCRAPER_CONCURRENCY`      | `4`                                         | ThreadPoolExecutor worker count                  |
| `CELERY_BROKER_URL`        | `redis://localhost:6379/0`                  | Only used if you run Celery                      |
| `CELERY_RESULT_BACKEND`    | `redis://localhost:6379/1`                  | Only used if you run Celery                      |

### Run the crawler

Two options. **Pick one.**

**1. Management command (simple, recommended to start).** Schedule with cron:

```bash
python manage.py crawl_prices                  # crawl everything
python manage.py crawl_prices --product 42     # one product
python manage.py crawl_prices --website digikala.com
python manage.py crawl_prices --stale-hours 6  # only sources older than 6h
python manage.py crawl_prices --concurrency 8
```

Example cron — refresh stale prices hourly:

```
0 * * * * cd /path/to/backend && .venv/bin/python manage.py crawl_prices --stale-hours 1 >> crawl.log 2>&1
```

**2. Celery (for high throughput or background scheduling).** Start Redis, then in two shells:

```bash
celery -A core worker -l info
celery -A core beat   -l info   # optional, if you add periodic tasks
```

`products/tasks.py` already defines `crawl_one` and `crawl_all`. Add periodic scheduling via `CELERY_BEAT_SCHEDULE` in `core/settings.py` when you need it.

### REST API

| Method | Path                              | Purpose                                            |
| ------ | --------------------------------- | -------------------------------------------------- |
| GET    | `/api/dashboard/`                 | Aggregate stats for the dashboard                  |
| GET    | `/api/products/`                  | List products with price summary                   |
| GET    | `/api/products/{id}/`             | Product detail + per-source prices                 |
| GET    | `/api/products/{id}/history/`     | Full price history grouped by source               |
| POST   | `/api/products/{id}/crawl/`       | Trigger crawl for a single product                 |
| GET    | `/api/sources/`                   | Sources, filter by `?website=`, `?status=`         |
| GET    | `/api/crawl-jobs/`                | Recent crawl runs                                  |
| POST   | `/api/crawl/`                     | Crawl all (or filtered) sources                    |
| POST   | `/api/import/`                    | Upload `links.xlsx` (multipart)                    |

Filtering on the products list:

```
GET /api/products/?search=a07&ordering=-updated_at&website=digikala.com
```

---

## Frontend setup

```bash
cd frontend
cp .env.local.example .env.local
# edit NEXT_PUBLIC_API_URL if your backend is not on :8000
npm install
npm run dev
```

Then open `http://localhost:3000`.

### Pages

- **`/dashboard`** — totals, success/failure counts, cheapest products, recently updated, last crawl job.
- **`/products`** — searchable, filterable, sortable table.
- **`/products/[id]`** — three hero price cards, full source comparison table (lowest highlighted), price history chart, per-product crawl button.
- **`/crawler`** — Excel upload, manual trigger (all sites or one), recent jobs (auto-refreshing), failed URLs.

---

## Adding a new website scraper

1. Create `backend/products/services/scrapers/myshop.py` and subclass `BaseScraper`:

   ```python
   from .base import BaseScraper, ScrapeResult, ScraperError, parse_price

   class MyShopScraper(BaseScraper):
       name = "myshop"

       def parse(self, html: str, url: str) -> ScrapeResult:
           soup = self.soup(html)
           # 1. Try JSON-LD ld+json blocks
           # 2. Try meta tags
           # 3. Try a specific CSS selector
           price = parse_price(soup.select_one(".price").get_text() if soup.select_one(".price") else "")
           if not price:
               raise ScraperError("price selector missing")
           return ScrapeResult(price=price, currency="IRR", availability="in_stock")
   ```

2. Register it in `backend/products/services/scrapers/__init__.py`:

   ```python
   from .myshop import MyShopScraper

   SCRAPERS = {
       ...,
       "myshop": MyShopScraper,
       "myshop.com": MyShopScraper,
   }
   ```

3. Add a column to the Excel file with the matching header name and re-run `import_excel`.

The crawler routes by `website_name` first, then by URL host, then falls back to `GenericScraper`.

---

## Safe and legal scraping practices

You're responsible for complying with the laws and terms of service that apply to you and the sites you query. The points below are general best practice, not legal advice.

- **Respect `robots.txt`.** It is not legally binding everywhere, but ignoring it invites bans. Add a robots check before crawling new domains.
- **Identify yourself.** Set a descriptive `User-Agent` (`SCRAPER_USER_AGENT`) with a contact email so site operators can reach you instead of blocking blindly.
- **Rate-limit per host.** The default `SCRAPER_CONCURRENCY=4` is conservative. For larger crawls, throttle per-domain (e.g. one request per second per host).
- **Cache aggressively.** Only re-crawl what's actually stale. The `--stale-hours` flag exists for this; combine with a cron schedule that's no more frequent than every 30–60 minutes.
- **Don't bypass anti-bot protection.** If a site serves a captcha or returns 403/429, stop — `ScraperBlocked` is recorded so you can review and decide whether you need an official partnership or feed.
- **Check terms of service.** Some sites permit price aggregation; others don't. When in doubt, ask the site for an affiliate API.
- **Don't republish copyrighted content** — only prices, availability, source URL, and timestamps. Avoid storing product descriptions, photos, or reviews unless you have permission.
- **Personal/internal use lowers but doesn't eliminate risk.** A small internal price-tracking tool is generally tolerated; selling the data or scraping at scale is not.

---

## Improving reliability and price extraction

Ranked by impact.

1. **Prefer structured data over CSS selectors.** Sites change DOM constantly but rarely break their `application/ld+json` Product/Offer markup, OpenGraph product tags, or Next.js `__NEXT_DATA__`. The existing scrapers already check those first.
2. **Stage selectors per site.** When you do need DOM scraping, keep a small ordered list of selectors and try each. New site layouts break one selector at a time.
3. **Switch to `httpx` + HTTP/2** if you hit per-host connection limits, or to **Playwright** for sites that render prices client-side (Digikala's mobile flow occasionally does this).
4. **Add per-host rate limiting and a polite delay** (e.g. `time.sleep(random.uniform(0.5, 1.5))` between requests to the same host) inside the crawler dispatcher.
5. **Run a sanity check on extracted prices.** Reject values that change by more than ±70% vs the previous reading without manual confirmation — that's almost always a parser regression, not a real price change. Store the suspicious value, mark the source `failed`, and surface in the UI.
6. **Persist raw HTML for failures.** When a parser fails, save the page so you can diff against a working capture. A small `RawSnapshot` model with `text` (compressed) is cheap insurance.
7. **Alert on failure rate spikes.** A simple management command that compares the last 24 h's failure rate against the rolling baseline catches site redesigns within hours.
8. **Use a proxy pool** for sites that block by IP. Residential proxies are expensive — start with a free rotating list and graduate to a paid provider only when you must.
9. **Capture both regular and discounted prices** when sites expose both. Schema.org `Offer` has `price` plus often `priceSpecification` for the original price.
10. **Detect currency from the page** rather than hardcoding IRR. The base scraper already returns a `currency` field — populate it from JSON-LD's `priceCurrency` when available, so the system stays international.

---

## Verified locally

Both halves run end-to-end against the supplied `links.xlsx`:

- Excel import: 19 products, 34 source URLs, 2 website columns (`digikala.com`, `techno life`).
- API: dashboard, list, detail, history, filtering, and trigger all return 200s.
- Scraper parsers (Digikala, Technolife, Generic) pass unit tests on synthetic HTML with JSON-LD, OpenGraph, and Persian-digit text fallbacks.
- Frontend build: `next build` succeeds with all 6 routes, zero TypeScript errors.
