"""Clean old price-history entries that pre-date a unit normalization.

When Digikala prices were briefly stored in rials (10x too big), each crawl
created a PriceHistory row at the inflated value. After we switched to storing
toman, the live prices look correct, but the chart's y-axis still has to fit
those old huge dots - making every product chart look like a vertical cliff.

This command deletes PriceHistory rows older than a cutoff date. Use the
cutoff to pick the moment when prices became reliable:

    python manage.py purge_old_history --before 2026-06-04           # dry run
    python manage.py purge_old_history --before 2026-06-04 --apply   # commit

You can also delete rows above a price threshold (handy if some old rials
values slipped through after the cutoff):

    python manage.py purge_old_history --above 500000000              # dry run
    python manage.py purge_old_history --above 500000000 --apply     # commit

Or combine both filters - rows must match BOTH to be deleted:

    python manage.py purge_old_history --before 2026-06-04 --above 500000000 --apply

The latest_price stored on each ProductSource isn't touched. Only the chart's
historical samples are removed.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from products.models import PriceHistory


class Command(BaseCommand):
    help = "Delete PriceHistory rows before a date and/or above a price."

    def add_arguments(self, parser):
        parser.add_argument(
            "--before",
            type=str,
            default=None,
            help="Delete rows crawled before this date. Format: YYYY-MM-DD "
            "(e.g. 2026-06-04). The whole date is included.",
        )
        parser.add_argument(
            "--above",
            type=int,
            default=None,
            help="Delete rows whose price is at or above this value (in the "
            "unit stored in the database, i.e. toman after normalization).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually delete. Without this flag the command only shows "
            "what would be deleted.",
        )

    def handle(self, *args, **options):
        before_str = options.get("before")
        above = options.get("above")
        apply = options.get("apply")

        if before_str is None and above is None:
            raise CommandError(
                "Specify at least one of --before YYYY-MM-DD or --above PRICE."
            )

        qs = PriceHistory.objects.all()

        if before_str:
            try:
                cutoff = datetime.strptime(before_str, "%Y-%m-%d")
            except ValueError as exc:
                raise CommandError(
                    f"--before must be YYYY-MM-DD, got {before_str!r}"
                ) from exc
            # Make timezone-aware so the comparison against crawled_at is correct.
            cutoff = timezone.make_aware(cutoff, timezone.get_current_timezone())
            qs = qs.filter(crawled_at__lt=cutoff)
            self.stdout.write(f"Filter: crawled_at < {cutoff.isoformat()}")

        if above is not None:
            qs = qs.filter(price__gte=Decimal(above))
            self.stdout.write(f"Filter: price >= {above:,}")

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No matching rows. Nothing to do."))
            return

        # Summarize what we'd delete grouped by website, so the user can sanity
        # check before committing.
        from django.db.models import Count, Min, Max

        by_site = (
            qs.values("product_source__website_name")
            .annotate(
                rows=Count("id"),
                min_price=Min("price"),
                max_price=Max("price"),
            )
            .order_by("-rows")
        )
        self.stdout.write("\nBreakdown of rows that match:")
        for row in by_site:
            site = row["product_source__website_name"]
            self.stdout.write(
                f"  {site:>14}: {row['rows']:>6} rows, "
                f"price range {int(row['min_price']):>15,} .. {int(row['max_price']):>15,}"
            )

        self.stdout.write(f"\nTotal: {total:,} rows.")

        if not apply:
            self.stdout.write(
                self.style.WARNING("Dry run only. Re-run with --apply to delete.")
            )
            return

        with transaction.atomic():
            deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted:,} rows."))
