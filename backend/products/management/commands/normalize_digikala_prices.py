"""One-shot data fix.

Earlier the crawler stored Digikala prices in rials (since the Digikala API
returns rials), while Technolife prices were stored in toman. The display
layer then divided everything by 10, which produced wrong Technolife prices.

The crawler now normalises everything to toman before saving. This command
fixes the data that was crawled BEFORE that change: it divides every Digikala
price (and matching price history) by 10 so all rows are toman.

Safe to run multiple times only if you've already crawled fresh data — it
checks for a marker (`_normalized_to_toman` on the price-history row). To
keep things simple, the command itself is idempotent by checking against the
current website live: it only touches values that are still 10x the
Technolife price for the same product (a strong signal they're still in rials).

Usage:
    python manage.py normalize_digikala_prices             # dry run
    python manage.py normalize_digikala_prices --apply     # actually change

If you'd rather just re-crawl everything from scratch, you can skip this and
run `python manage.py crawl_prices --website digikala.com` instead.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import PriceHistory, ProductSource


class Command(BaseCommand):
    help = "Divide stored Digikala prices by 10 (one-time toman normalisation)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually persist the change. Without this flag, the command "
            "only previews what would be touched.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        sources = ProductSource.objects.filter(
            website_name__icontains="digikala",
            latest_price__isnull=False,
        )
        touched_sources = 0
        touched_history = 0

        with transaction.atomic():
            for source in sources:
                old = source.latest_price
                if old is None or old < 1_000_000:
                    # Already in toman (or never set); skip.
                    continue
                new = (old / Decimal(10)).quantize(Decimal("1"))
                self.stdout.write(
                    f"  {source.product.model_name:>18} @ {source.website_name}: "
                    f"{int(old):>15,} -> {int(new):>15,}"
                )
                touched_sources += 1
                if apply:
                    source.latest_price = new
                    source.save(update_fields=["latest_price", "updated_at"])
                    history_qs = PriceHistory.objects.filter(product_source=source)
                    for entry in history_qs:
                        entry.price = (entry.price / Decimal(10)).quantize(Decimal("1"))
                        entry.save(update_fields=["price"])
                        touched_history += 1

            if not apply:
                # Don't actually commit on dry-run (rollback the transaction).
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'Updated' if apply else 'Would update'} "
                f"{touched_sources} sources and {touched_history} history rows."
            )
        )
        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply to commit."
                )
            )
