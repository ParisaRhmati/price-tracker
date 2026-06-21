"""One-shot data fix for Mobile140 prices.

When Mobile140 support was first added, the crawler assumed mobile140.com
returned prices in rials (like Digikala's API) and divided every result by 10
before saving. Turns out mobile140.com already serves toman, so existing rows
are stored 10x too small.

This command multiplies all Mobile140 prices and price-history rows by 10.
It also identifies the rows it would touch on a dry run first.

Usage:
    python manage.py multiply_mobile140_prices            # dry run
    python manage.py multiply_mobile140_prices --apply    # actually change

Run this ONCE, after installing the crawler.py that no longer divides
Mobile140 by 10. Running it twice will multiply twice and break your data.

Idempotent guard: the command refuses to run if any Mobile140 source already
has a price >= 10,000,000 toman (which would indicate the fix already applied,
since phones rarely cost above 10M toman after a /10 mistake).
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import PriceHistory, ProductSource

# If any Mobile140 source has a price above this, the multiplication has
# almost certainly been done already, and we abort.
ALREADY_DONE_THRESHOLD = Decimal("10_000_000".replace("_", ""))


class Command(BaseCommand):
    help = "Multiply stored Mobile140 prices by 10 (one-time toman fix)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually persist the change. Without this flag, the command "
            "only previews what would be touched.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Multiply even if the data looks like it was already fixed.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        force = options["force"]

        sources = ProductSource.objects.filter(
            website_name__icontains="mobile",
            latest_price__isnull=False,
        )

        if not sources.exists():
            self.stdout.write(self.style.WARNING("No Mobile140 sources found."))
            return

        # Safety check: refuse if it looks like we've already run.
        if not force and sources.filter(latest_price__gte=ALREADY_DONE_THRESHOLD).exists():
            self.stdout.write(
                self.style.ERROR(
                    "Some Mobile140 prices are already >= 10M toman, which "
                    "means this fix was probably already applied.\n"
                    "If you really want to multiply again, re-run with --force."
                )
            )
            return

        touched_sources = 0
        touched_history = 0

        with transaction.atomic():
            for source in sources:
                old = source.latest_price
                if old is None or old <= 0:
                    continue
                new = (old * Decimal(10)).quantize(Decimal("1"))
                self.stdout.write(
                    f"  {source.product.model_name:>18} @ {source.website_name}: "
                    f"{int(old):>14,} -> {int(new):>14,}"
                )
                touched_sources += 1
                if apply:
                    source.latest_price = new
                    source.save(update_fields=["latest_price", "updated_at"])
                    history_qs = PriceHistory.objects.filter(product_source=source)
                    for entry in history_qs:
                        entry.price = (entry.price * Decimal(10)).quantize(Decimal("1"))
                        entry.save(update_fields=["price"])
                        touched_history += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'Updated' if apply else 'Would update'} "
                f"{touched_sources} sources and {touched_history} history rows."
            )
        )
        if not apply:
            self.stdout.write(
                self.style.WARNING("Dry-run only. Re-run with --apply to commit.")
            )
