"""Celery app. Optional — only used if you start a Celery worker.

Run a worker with:
    celery -A core worker -l info
Run beat (periodic crawls) with:
    celery -A core beat -l info
"""
from __future__ import annotations

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("price_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
