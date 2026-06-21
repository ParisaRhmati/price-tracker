from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CrawlJobViewSet,
    ProductSourceViewSet,
    ProductViewSet,
    check_passcode,
    dashboard,
    export_excel,
    trigger_full_crawl,
    upload_excel,
)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"sources", ProductSourceViewSet, basename="source")
router.register(r"crawl-jobs", CrawlJobViewSet, basename="crawl-job")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", dashboard, name="dashboard"),
    path("crawl/", trigger_full_crawl, name="crawl-trigger"),
    path("import/", upload_excel, name="excel-import"),
    path("export/", export_excel, name="excel-export"),
    path("auth/check/", check_passcode, name="auth-check"),
    # Some frontend builds called this without the trailing slash. Register
    # the no-slash form too so a stale frontend still works without a 500.
    path("auth/check", check_passcode),
]
