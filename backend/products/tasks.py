"""Optional Celery tasks. Skip if you're using management commands instead."""
from __future__ import annotations

from celery import shared_task

from .models import ProductSource
from .services.crawler import crawl_source, crawl_sources


@shared_task(name="products.crawl_one")
def crawl_one(source_id: int) -> dict:
    source = ProductSource.objects.get(pk=source_id)
    outcome = crawl_source(source)
    return {"source_id": outcome.source_id, "success": outcome.success}


@shared_task(name="products.crawl_all")
def crawl_all() -> dict:
    job = crawl_sources(ProductSource.objects.all(), triggered_by="celery")
    return {"job_id": job.pk, "succeeded": job.succeeded, "failed": job.failed}
