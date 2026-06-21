"""Collapse PriceHistory to at most ONE row per (source, calendar day).

The crawler used to create a fresh history row every time you clicked "Crawl
now". So a single day could end up with many dots stacked on top of each
other in the chart. Going forward the new record_success() upserts today's
row instead of inserting a new one - but EXISTING history still has the
duplicates.

This command groups every source's history rows by calendar day, keeps the
NEWEST row for each day, and deletes the others. The kept row's price and
crawled_at remain whatever they were originally - we don't recompute or
average.

Use it once after installing the "one row per day" patch:

    python manage.py collapse_history_to_daily             # dry run
    python manage.py collapse_history_to_daily --apply     # actually delete

After this, the chart will show at most one dot per day per website.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from products.models import PriceHistory


class Command(BaseCommand):
    help = "Keep only the newest PriceHistory row per (source, day)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually delete duplicates. Without this flag the command "
            "only prints what would be removed.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        tz = timezone.get_current_timezone()

        # Walk every history row newest-first. For each (source, local-date)
        # pair, mark the first one we see as the "keeper" and every later one
        # as a duplicate to delete.
        keeper_ids: set[int] = set()
        delete_ids: list[int] = []
        per_source_per_day: dict[tuple[int, object], int] = {}

        qs = (
            PriceHistory.objects.select_related("product_source")
            .order_by("-crawled_at")
            .iterator()
        )
        for row in qs:
            local_day = row.crawled_at.astimezone(tz).date()
            key = (row.product_source_id, local_day)
            if key in per_source_per_day:
                delete_ids.append(row.id)
            else:
                per_source_per_day[key] = row.id
                keeper_ids.add(row.id)

        # Show a short breakdown - how many sources lose how many rows.
        source_counts: dict[int, int] = defaultdict(int)
        for row in PriceHistory.objects.filter(id__in=delete_ids).only(
            "product_source_id"
        ):
            source_counts[row.product_source_id] += 1

        self.stdout.write(f"Sources with duplicates: {len(source_counts)}")
        if source_counts:
            from products.models import ProductSource

            ids = list(source_counts.keys())[:10]
            for src in ProductSource.objects.filter(id__in=ids).select_related(
                "product"
            ):
                self.stdout.write(
                    f"  {src.product.model_name:>18} @ {src.website_name}: "
                    f"{source_counts[src.id]} rows to remove"
                )
            if len(source_counts) > 10:
                self.stdout.write(f"  ... and {len(source_counts) - 10} more sources")

        self.stdout.write(
            f"\nWill keep {len(keeper_ids):,} rows (one per source per day)."
        )
        self.stdout.write(f"Will delete {len(delete_ids):,} duplicate rows.")

        if not apply:
            self.stdout.write(
                self.style.WARNING("Dry run only. Re-run with --apply to delete.")
            )
            return

        # Delete in chunks to avoid pinning a huge transaction.
        CHUNK = 1000
        total_deleted = 0
        with transaction.atomic():
            for i in range(0, len(delete_ids), CHUNK):
                chunk = delete_ids[i : i + CHUNK]
                deleted, _ = PriceHistory.objects.filter(id__in=chunk).delete()
                total_deleted += deleted

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {total_deleted:,} duplicate rows.")
        )
