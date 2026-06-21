from django.contrib import admin

from .models import CrawlJob, PriceHistory, Product, ProductSource


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("model_name", "display_name", "updated_at")
    search_fields = ("model_name", "display_name")


@admin.register(ProductSource)
class ProductSourceAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "website_name",
        "latest_price",
        "currency",
        "availability_status",
        "crawl_status",
        "last_crawled_at",
    )
    list_filter = ("website_name", "crawl_status", "availability_status")
    search_fields = ("product__model_name", "url")
    readonly_fields = ("last_crawled_at", "consecutive_failures")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("product_source", "price", "availability_status", "crawled_at")
    list_filter = ("availability_status",)
    date_hierarchy = "crawled_at"


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    list_display = ("id", "started_at", "finished_at", "total", "succeeded", "failed")
