"""Database models for the price tracker."""
from __future__ import annotations

from django.db import models
from django.db.models import Min, Max
from django.utils import timezone


class CrawlStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    BLOCKED = "blocked", "Blocked"


class AvailabilityStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    IN_STOCK = "in_stock", "In stock"
    OUT_OF_STOCK = "out_of_stock", "Out of stock"


class Brand(models.Model):
    """A product brand (e.g. Samsung, Xiaomi).

    IDs are meaningful here: the initial data migration seeds Samsung as id=1
    and Xiaomi as id=2. New brands found in the Excel are auto-created with
    the next available id (3, 4, ...).
    """

    name = models.CharField(max_length=120, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """A product model (e.g. 'a07 4/64'). One row per distinct model name."""

    model_name = models.CharField(max_length=255, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    # Nullable so existing rows and rows without a brand in the Excel still
    # work. SET_NULL keeps products around even if a brand is ever deleted.
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["model_name"]

    def __str__(self) -> str:
        return self.model_name

    # --- Computed helpers -------------------------------------------------
    def price_summary(self) -> dict[str, float | None]:
        """Aggregate latest prices across IN-STOCK sources for quick display.

        Out-of-stock sources are excluded from the lowest/highest comparison
        so the "best price" badge never points to a phone you can't buy.
        """
        in_stock = self.sources.exclude(latest_price__isnull=True).exclude(
            availability_status="out_of_stock"
        )
        agg = in_stock.aggregate(
            lowest=Min("latest_price"),
            highest=Max("latest_price"),
        )
        return {
            "lowest_price": agg["lowest"],
            "highest_price": agg["highest"],
            "price_spread": (
                (agg["highest"] - agg["lowest"])
                if agg["lowest"] is not None and agg["highest"] is not None
                else None
            ),
            "source_count": self.sources.count(),
        }


class ProductSource(models.Model):
    """One product as offered on one website."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sources"
    )
    website_name = models.CharField(max_length=120, db_index=True)
    url = models.URLField(max_length=2000)

    latest_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=8, default="IRR")
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.UNKNOWN,
    )

    last_crawled_at = models.DateTimeField(null=True, blank=True)
    crawl_status = models.CharField(
        max_length=20, choices=CrawlStatus.choices, default=CrawlStatus.PENDING
    )
    error_message = models.TextField(blank=True, default="")
    consecutive_failures = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "website_name", "url")
        ordering = ["website_name"]

    def __str__(self) -> str:
        return f"{self.product.model_name} @ {self.website_name}"

    def record_success(self, price, availability: str, currency: str = "IRR") -> None:
        self.latest_price = price
        self.currency = currency
        self.availability_status = availability
        self.crawl_status = CrawlStatus.SUCCESS
        self.error_message = ""
        self.consecutive_failures = 0
        self.last_crawled_at = timezone.now()
        self.save(
            update_fields=[
                "latest_price",
                "currency",
                "availability_status",
                "crawl_status",
                "error_message",
                "consecutive_failures",
                "last_crawled_at",
                "updated_at",
            ]
        )
        # Store at most ONE PriceHistory row per (source, calendar day). If
        # we crawl 5 times today, we update today's row 5 times instead of
        # creating 5 separate rows. This keeps the price-history chart clean
        # (one dot per day per website) without losing the rest of the
        # history. The "calendar day" is anchored to the project's current
        # timezone via timezone.localdate().
        now = timezone.now()
        today = timezone.localdate()
        existing_today = PriceHistory.objects.filter(
            product_source=self, crawled_at__date=today
        ).first()
        if existing_today is not None:
            existing_today.price = price
            existing_today.availability_status = availability
            existing_today.crawled_at = now
            existing_today.save(
                update_fields=["price", "availability_status", "crawled_at"]
            )
        else:
            PriceHistory.objects.create(
                product_source=self,
                price=price,
                availability_status=availability,
            )

    def record_unavailable(self, availability: str = "out_of_stock") -> None:
        """The page loaded fine but the product is out of stock / no price.
        We clear the stored price so comparison logic doesn't treat a stale
        old price as current."""
        self.latest_price = None
        self.availability_status = availability
        self.crawl_status = CrawlStatus.SUCCESS
        self.error_message = ""
        self.consecutive_failures = 0
        self.last_crawled_at = timezone.now()
        self.save(
            update_fields=[
                "latest_price",
                "availability_status",
                "crawl_status",
                "error_message",
                "consecutive_failures",
                "last_crawled_at",
                "updated_at",
            ]
        )

    def record_failure(self, message: str, status: str = CrawlStatus.FAILED) -> None:
        self.crawl_status = status
        self.error_message = (message or "")[:2000]
        self.consecutive_failures += 1
        self.last_crawled_at = timezone.now()
        self.save(
            update_fields=[
                "crawl_status",
                "error_message",
                "consecutive_failures",
                "last_crawled_at",
                "updated_at",
            ]
        )


class PriceHistory(models.Model):
    """Append-only log of every successful price observation."""

    product_source = models.ForeignKey(
        ProductSource, on_delete=models.CASCADE, related_name="price_history"
    )
    price = models.DecimalField(max_digits=14, decimal_places=2)
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.UNKNOWN,
    )
    crawled_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-crawled_at"]
        indexes = [models.Index(fields=["product_source", "-crawled_at"])]

    def __str__(self) -> str:
        return f"{self.product_source} = {self.price} @ {self.crawled_at:%Y-%m-%d %H:%M}"


class CrawlJob(models.Model):
    """A batch crawl run, for dashboard reporting."""

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total = models.PositiveIntegerField(default=0)
    succeeded = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    triggered_by = models.CharField(max_length=80, default="manual")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"CrawlJob #{self.pk} ({self.succeeded}/{self.total})"
