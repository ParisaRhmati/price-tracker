"""Background crawler entry point. Usable as a cron job:

    python manage.py crawl_prices                  # crawl everything
    python manage.py crawl_prices --product 42     # one product
    python manage.py crawl_prices --website digikala.com
    python manage.py crawl_prices --stale-hours 6  # only re-crawl if >6h old
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from products.models import ProductSource
from products.services.crawler import crawl_sources


class Command(BaseCommand):
    help = "Crawl product source URLs and update prices."

    def add_arguments(self, parser):
        parser.add_argument("--product", type=int, help="Limit to a single product id")
        parser.add_argument("--website", type=str, help="Limit to a website name")
        parser.add_argument(
            "--stale-hours",
            type=int,
            default=0,
            help="Only crawl sources older than N hours (0 means crawl all)",
        )
        parser.add_argument(
            "--concurrency", type=int, default=None, help="Override worker count"
        )

    def handle(self, *args, **options):
        queryset = ProductSource.objects.all()
        if options["product"]:
            queryset = queryset.filter(product_id=options["product"])
        if options["website"]:
            queryset = queryset.filter(website_name__iexact=options["website"])
        if options["stale_hours"]:
            cutoff = timezone.now() - timedelta(hours=options["stale_hours"])
            queryset = queryset.filter(
                Q(last_crawled_at__isnull=True) | Q(last_crawled_at__lt=cutoff)
            )

        sources = list(queryset)
        self.stdout.write(self.style.NOTICE(f"Crawling {len(sources)} sources..."))

        job = crawl_sources(
            sources, triggered_by="cli", concurrency=options["concurrency"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Job #{job.pk} done. ok={job.succeeded} fail={job.failed}"
            )
        )
