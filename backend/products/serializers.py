"""DRF serializers."""
from __future__ import annotations

from rest_framework import serializers

from .models import Brand, CrawlJob, PriceHistory, Product, ProductSource


class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ("id", "name", "product_count")

    def get_product_count(self, obj) -> int:
        # Uses the prefetched/annotated count if present, else queries.
        if hasattr(obj, "_product_count"):
            return obj._product_count
        return obj.products.count()


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ("id", "price", "availability_status", "crawled_at")


class ProductSourceSerializer(serializers.ModelSerializer):
    is_lowest = serializers.SerializerMethodField()
    is_highest = serializers.SerializerMethodField()
    diff_vs_lowest = serializers.SerializerMethodField()

    class Meta:
        model = ProductSource
        fields = (
            "id",
            "website_name",
            "url",
            "latest_price",
            "currency",
            "availability_status",
            "last_crawled_at",
            "crawl_status",
            "error_message",
            "consecutive_failures",
            "is_lowest",
            "is_highest",
            "diff_vs_lowest",
        )

    # Aggregates are pre-computed on the parent product when available.
    def _summary(self) -> dict:
        return self.context.get("price_summary") or {}

    def get_is_lowest(self, obj) -> bool:
        summary = self._summary()
        return (
            obj.latest_price is not None
            and summary.get("lowest_price") is not None
            and obj.latest_price == summary["lowest_price"]
        )

    def get_is_highest(self, obj) -> bool:
        summary = self._summary()
        return (
            obj.latest_price is not None
            and summary.get("highest_price") is not None
            and obj.latest_price == summary["highest_price"]
        )

    def get_diff_vs_lowest(self, obj):
        summary = self._summary()
        if obj.latest_price is None or summary.get("lowest_price") is None:
            return None
        return obj.latest_price - summary["lowest_price"]


class ProductListSerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField()
    brand_id = serializers.IntegerField(read_only=True)
    lowest_price = serializers.SerializerMethodField()
    highest_price = serializers.SerializerMethodField()
    price_spread = serializers.SerializerMethodField()
    source_count = serializers.SerializerMethodField()
    last_crawled_at = serializers.SerializerMethodField()
    has_errors = serializers.SerializerMethodField()
    cheapest_source = serializers.SerializerMethodField()
    priciest_source = serializers.SerializerMethodField()
    sources_ranked = serializers.SerializerMethodField()
    prices_by_website = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "model_name",
            "display_name",
            "brand",
            "brand_id",
            "updated_at",
            "lowest_price",
            "highest_price",
            "price_spread",
            "source_count",
            "last_crawled_at",
            "has_errors",
            "cheapest_source",
            "priciest_source",
            "sources_ranked",
            "prices_by_website",
        )

    def get_brand(self, obj):
        # Brand name string (or null). The frontend filter uses brand_id; the
        # name is handy for display.
        return obj.brand.name if obj.brand_id else None

    def _summary(self, obj) -> dict:
        if not hasattr(obj, "_cached_summary"):
            obj._cached_summary = obj.price_summary()
        return obj._cached_summary

    def _priced_sources_sorted(self, obj):
        """Return IN-STOCK sources with a known price, cheapest first.

        Out-of-stock sources are excluded so the "best" / cheapest_source
        signal only points at sites where the product is actually buyable.
        """
        if not hasattr(obj, "_cached_priced"):
            obj._cached_priced = sorted(
                [
                    s
                    for s in obj.sources.all()
                    if s.latest_price is not None
                    and s.availability_status != "out_of_stock"
                ],
                key=lambda s: s.latest_price,
            )
        return obj._cached_priced

    def get_lowest_price(self, obj):
        return self._summary(obj)["lowest_price"]

    def get_highest_price(self, obj):
        return self._summary(obj)["highest_price"]

    def get_price_spread(self, obj):
        return self._summary(obj)["price_spread"]

    def get_source_count(self, obj):
        return self._summary(obj)["source_count"]

    def get_cheapest_source(self, obj):
        priced = self._priced_sources_sorted(obj)
        if not priced:
            return None
        winner = priced[0]
        return {
            "website_name": winner.website_name,
            "price": winner.latest_price,
            "url": winner.url,
        }

    def get_priciest_source(self, obj):
        priced = self._priced_sources_sorted(obj)
        # Only return a "loser" if there's more than one source to compare.
        if len(priced) < 2:
            return None
        loser = priced[-1]
        return {
            "website_name": loser.website_name,
            "price": loser.latest_price,
            "url": loser.url,
        }

    def get_sources_ranked(self, obj):
        """Compact list of all priced sources ordered cheapest-first.
        Lets the frontend draw gold/silver/bronze in one pass."""
        priced = self._priced_sources_sorted(obj)
        return [
            {
                "website_name": s.website_name,
                "price": s.latest_price,
            }
            for s in priced
        ]

    def get_prices_by_website(self, obj):
        """Map of website name -> {price, url, availability}. Used by the
        per-website column layout on the product list. If a product has
        multiple sources from the same website, we keep the cheapest
        in-stock one (or fall back to the cheapest out-of-stock if all
        are out of stock)."""
        result: dict[str, dict] = {}
        for s in obj.sources.all():
            key = s.website_name
            payload = {
                "price": s.latest_price,
                "url": s.url,
                "availability": s.availability_status,
            }
            existing = result.get(key)
            if existing is None:
                result[key] = payload
                continue
            # Prefer the in-stock one. Within the same availability, prefer
            # the cheaper. None price is the worst case.
            existing_in_stock = existing["availability"] != "out_of_stock"
            new_in_stock = s.availability_status != "out_of_stock"
            if new_in_stock and not existing_in_stock:
                result[key] = payload
            elif new_in_stock == existing_in_stock:
                existing_price = existing["price"]
                if existing_price is None or (
                    s.latest_price is not None and s.latest_price < existing_price
                ):
                    result[key] = payload
        return result

    def get_last_crawled_at(self, obj):
        latest = max(
            (s.last_crawled_at for s in obj.sources.all() if s.last_crawled_at),
            default=None,
        )
        return latest

    def get_has_errors(self, obj) -> bool:
        return obj.sources.filter(crawl_status__in=("failed", "blocked")).exists()


class ProductDetailSerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField()
    brand_id = serializers.IntegerField(read_only=True)
    sources = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "model_name",
            "display_name",
            "brand",
            "brand_id",
            "created_at",
            "updated_at",
            "summary",
            "sources",
        )

    def get_brand(self, obj):
        return obj.brand.name if obj.brand_id else None

    def get_summary(self, obj) -> dict:
        return obj.price_summary()

    def get_sources(self, obj):
        summary = obj.price_summary()
        serializer = ProductSourceSerializer(
            obj.sources.all(), many=True, context={"price_summary": summary}
        )
        return serializer.data


class CrawlJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlJob
        fields = (
            "id",
            "started_at",
            "finished_at",
            "total",
            "succeeded",
            "failed",
            "triggered_by",
            "notes",
        )


class ExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        name = (value.name or "").lower()
        if not name.endswith((".xlsx", ".xlsm")):
            raise serializers.ValidationError("Only .xlsx / .xlsm files are accepted")
        return value
