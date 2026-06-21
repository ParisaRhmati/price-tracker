"""Add a trailing slash to /api/ requests in-place, before any 301 redirect.

The problem this solves: when the Next.js dev server proxies /api/ requests to
Django, the trailing slash can get dropped on the way through. Django's
CommonMiddleware (APPEND_SLASH) then answers with a 301 redirect to the slash
version. A browser fetch() arriving through an ngrok tunnel cannot transparently
follow that cross-origin 301, so the call surfaces as "Failed to fetch".

This middleware runs BEFORE CommonMiddleware. For any /api/ path missing a
trailing slash (and that doesn't look like a static file), it rewrites the
path in-place to include the slash. Django then routes the request directly,
returns 200, and no redirect is ever emitted.

Only /api/ paths without a dot in the final segment are touched; everything
else passes through untouched.
"""
from __future__ import annotations


class ApiTrailingSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or ""
        if path.startswith("/api/") and not path.endswith("/"):
            last_segment = path.rsplit("/", 1)[-1]
            if "." not in last_segment:
                request.path_info = path + "/"
                if request.path and not request.path.endswith("/"):
                    request.path = request.path + "/"
        return self.get_response(request)
