"""API views.

Endpoints:
    GET    /api/products/                    list products with summary
    GET    /api/products/?brand=1            filter products by brand id
    GET    /api/products/<id>/               product detail + per-source prices
    GET    /api/products/<id>/history/       full price history grouped by source
    POST   /api/products/<id>/crawl/         trigger crawl for one product
    GET    /api/sources/                     list sources (filterable)
    GET    /api/crawl-jobs/                  recent crawl runs
    POST   /api/crawl/                       crawl all (or filtered) sources
    POST   /api/import/                      upload links.xlsx
    GET    /api/dashboard/                   aggregate dashboard stats (+ brands)
"""
from __future__ import annotations

from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Brand, CrawlJob, CrawlStatus, PriceHistory, Product, ProductSource
from .serializers import (
    BrandSerializer,
    CrawlJobSerializer,
    ExcelUploadSerializer,
    PriceHistorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductSourceSerializer,
)
from .services.crawler import crawl_sources
from .services.excel_exporter import build_report
from .services.excel_importer import import_excel


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related("brand").prefetch_related("sources").all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("model_name", "display_name")
    ordering_fields = ("model_name", "updated_at")
    ordering = ("model_name",)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        website = self.request.query_params.get("website")
        if website:
            qs = qs.filter(sources__website_name__iexact=website).distinct()
        # Brand filter. Accepts a brand id (?brand=1) or a brand name
        # (?brand=Samsung), so the frontend can use whichever is handy.
        brand = self.request.query_params.get("brand")
        if brand:
            if str(brand).isdigit():
                qs = qs.filter(brand_id=int(brand))
            else:
                qs = qs.filter(brand__name__iexact=brand)
        return qs

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        product = self.get_object()
        history = (
            PriceHistory.objects.filter(product_source__product=product)
            .select_related("product_source")
            .order_by("crawled_at")
        )
        grouped: dict[int, dict] = {}
        for entry in history:
            src = entry.product_source
            bucket = grouped.setdefault(
                src.pk,
                {
                    "source_id": src.pk,
                    "website_name": src.website_name,
                    "url": src.url,
                    "points": [],
                },
            )
            bucket["points"].append(
                {
                    "crawled_at": entry.crawled_at,
                    "price": entry.price,
                    "availability_status": entry.availability_status,
                }
            )
        return Response(
            {"product_id": product.pk, "series": list(grouped.values())}
        )

    @action(detail=True, methods=["post"])
    def crawl(self, request, pk=None):
        product = self.get_object()
        job = crawl_sources(
            product.sources.all(),
            triggered_by=f"product:{product.pk}",
            concurrency=request.data.get("concurrency"),
        )
        return Response(CrawlJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class ProductSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductSource.objects.select_related("product").all()
    serializer_class = ProductSourceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ("product__model_name", "website_name", "url")
    ordering_fields = ("latest_price", "last_crawled_at", "website_name")

    def get_queryset(self):
        qs = super().get_queryset()
        website = self.request.query_params.get("website")
        crawl_status = self.request.query_params.get("status")
        if website:
            qs = qs.filter(website_name__iexact=website)
        if crawl_status:
            qs = qs.filter(crawl_status=crawl_status)
        return qs


class CrawlJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrawlJob.objects.all()
    serializer_class = CrawlJobSerializer


@api_view(["POST"])
def trigger_full_crawl(request):
    """Crawl everything, or a filtered subset.

    Body (all optional):
        { "website": "digikala.com", "product_id": 42, "concurrency": 8 }
    """
    queryset = ProductSource.objects.all()
    if (website := request.data.get("website")):
        queryset = queryset.filter(website_name__iexact=website)
    if (product_id := request.data.get("product_id")):
        queryset = queryset.filter(product_id=product_id)
    job = crawl_sources(
        queryset,
        triggered_by="api",
        concurrency=request.data.get("concurrency"),
    )
    return Response(CrawlJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_excel(request):
    serializer = ExcelUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    report = import_excel(serializer.validated_data["file"])
    return Response(report.as_dict(), status=status.HTTP_201_CREATED)


@api_view(["GET"])
def dashboard(request):
    """Aggregate stats for the dashboard page."""
    total_products = Product.objects.count()
    total_sources = ProductSource.objects.count()
    successful = ProductSource.objects.filter(crawl_status=CrawlStatus.SUCCESS).count()
    failed = ProductSource.objects.filter(
        crawl_status__in=(CrawlStatus.FAILED, CrawlStatus.BLOCKED)
    ).count()
    pending = ProductSource.objects.filter(crawl_status=CrawlStatus.PENDING).count()
    last_job = CrawlJob.objects.order_by("-started_at").first()

    # Cheapest products: get top 5 with the lowest non-null price.
    cheapest_qs = (
        Product.objects.annotate(min_price=Min("sources__latest_price"))
        .exclude(min_price__isnull=True)
        .order_by("min_price")[:5]
    )
    cheapest = [
        {"id": p.id, "model_name": p.model_name, "lowest_price": p.min_price}
        for p in cheapest_qs
    ]

    # Recently updated products
    recent_qs = (
        Product.objects.annotate(last=Max("sources__last_crawled_at"))
        .exclude(last__isnull=True)
        .order_by("-last")[:5]
    )
    recent = [
        {"id": p.id, "model_name": p.model_name, "last_crawled_at": p.last}
        for p in recent_qs
    ]

    # Brands with product counts, for the dashboard filter dropdown.
    brands_qs = Brand.objects.annotate(_product_count=Count("products")).order_by("id")
    brands = BrandSerializer(brands_qs, many=True).data

    return Response(
        {
            "total_products": total_products,
            "total_sources": total_sources,
            "successful_crawls": successful,
            "failed_crawls": failed,
            "pending_crawls": pending,
            "cheapest_products": cheapest,
            "recently_updated": recent,
            "brands": brands,
            "last_job": CrawlJobSerializer(last_job).data if last_job else None,
            "generated_at": timezone.now(),
        }
    )


@api_view(["GET"])
def export_excel(request):
    """Generate and stream a .xlsx report.

    Optional query params:
        ?website=digikala.com     limit summary to products on that website
        ?search=a07               limit to products whose model contains text
        ?brand=1                  limit to a brand (id or name)
    """
    from django.http import HttpResponse

    queryset = Product.objects.prefetch_related("sources").all()
    if (search := request.query_params.get("search")):
        queryset = queryset.filter(model_name__icontains=search)
    if (website := request.query_params.get("website")):
        queryset = queryset.filter(sources__website_name__iexact=website).distinct()
    if (brand := request.query_params.get("brand")):
        if str(brand).isdigit():
            queryset = queryset.filter(brand_id=int(brand))
        else:
            queryset = queryset.filter(brand__name__iexact=brand)

    xlsx_bytes = build_report(queryset)
    filename = f"price-tracker-report-{timezone.now():%Y%m%d-%H%M}.xlsx"
    response = HttpResponse(
        xlsx_bytes,
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = str(len(xlsx_bytes))
    return response


@api_view(["POST"])
def check_passcode(request):
    """Validate a passcode submitted by the frontend.

    The PasscodeMiddleware exempts THIS endpoint from the header check so
    the frontend can verify a code before it starts storing it. Body shape:

        {"passcode": "<the code the user typed>"}

    Returns 200 + {ok: true} on a match, 401 + {ok: false} on a miss, or
    200 + {ok: true, disabled: true} if no passcode is configured (which
    is the local-dev case).
    """
    from django.conf import settings
    import hmac

    expected = (getattr(settings, "APP_PASSCODE", "") or "").strip()
    if not expected:
        return Response({"ok": True, "disabled": True})

    provided = ""
    if isinstance(request.data, dict):
        provided = str(request.data.get("passcode") or "")

    if hmac.compare_digest(provided, expected):
        return Response({"ok": True})
    return Response({"ok": False}, status=401)
