"""Crawler orchestration.

Two ways to run:
- Synchronously, per source or in batches (used by API + management command).
- Concurrently with a thread pool for I/O-bound HTTP fetches.

We don't use async here because requests is sync; for very large workloads,
swap requests for httpx.AsyncClient or move to Celery tasks.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from ..models import CrawlJob, CrawlStatus, ProductSource
from .scrapers import get_scraper_for
from .scrapers.base import ScraperBlocked, ScraperError, ScraperRetryable

logger = logging.getLogger(__name__)


@dataclass
class CrawlOutcome:
    source_id: int
    success: bool
    message: str = ""


def crawl_source(source: ProductSource) -> CrawlOutcome:
    """Crawl a single ProductSource and persist the result."""
    source.crawl_status = CrawlStatus.RUNNING
    source.save(update_fields=["crawl_status", "updated_at"])

    scraper = get_scraper_for(source.website_name, source.url)
    try:
        result = scraper.scrape(source.url)
    except ScraperBlocked as exc:
        msg = f"Blocked: {exc}"
        logger.warning("[%s] %s", source, msg)
        source.record_failure(msg, status=CrawlStatus.BLOCKED)
        return CrawlOutcome(source.pk, False, msg)
    except (ScraperError, ScraperRetryable) as exc:
        msg = f"Scrape failed: {exc}"
        logger.warning("[%s] %s", source, msg)
        source.record_failure(msg)
        return CrawlOutcome(source.pk, False, msg)
    except Exception as exc:  # last-resort guard
        msg = f"Unexpected error: {exc!r}"
        logger.exception("[%s] %s", source, msg)
        source.record_failure(msg)
        return CrawlOutcome(source.pk, False, msg)

    if not result.is_valid:
        # No price found. If the scraper figured out it's out of stock /
        # discontinued, treat that as a successful crawl (the product page
        # really doesn't have a price). Otherwise mark the source failed
        # so we know our parser needs work.
        if result.availability in ("out_of_stock",):
            source.record_unavailable(result.availability)
            return CrawlOutcome(source.pk, True, "out_of_stock")
        msg = "Scraper returned no usable price"
        source.record_failure(msg)
        return CrawlOutcome(source.pk, False, msg)

    # Normalize to toman. Different sites report in different units:
    #   - Digikala API:  rials  (divide by 10)
    #   - Mobile140:     toman already (no conversion)
    #   - Technolife:    toman already
    # Storing everything in toman keeps the frontend math simple.
    price_in_toman = result.price
    website_lower = (source.website_name or "").strip().lower()
    if "digikala" in website_lower:
        price_in_toman = result.price / 10

    source.record_success(price_in_toman, result.availability, result.currency)
    return CrawlOutcome(source.pk, True, "ok")


def crawl_sources(
    sources: Iterable[ProductSource],
    *,
    triggered_by: str = "manual",
    concurrency: int | None = None,
) -> CrawlJob:
    """Crawl many sources concurrently and record a CrawlJob summary."""
    source_list = list(sources)
    job = CrawlJob.objects.create(total=len(source_list), triggered_by=triggered_by)

    if not source_list:
        job.finished_at = timezone.now()
        job.save(update_fields=["finished_at"])
        return job

    workers = concurrency or settings.SCRAPER_CONCURRENCY
    succeeded = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(crawl_source, src): src for src in source_list}
        for future in as_completed(future_map):
            try:
                outcome = future.result()
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Worker crashed: %s", exc)
                failed += 1
                continue
            if outcome.success:
                succeeded += 1
            else:
                failed += 1

    job.succeeded = succeeded
    job.failed = failed
    job.finished_at = timezone.now()
    job.save(update_fields=["succeeded", "failed", "finished_at"])
    return job
