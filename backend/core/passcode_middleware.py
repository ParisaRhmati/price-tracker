"""Passcode gate middleware.

Lightweight protection so the app can be shared on an office LAN without
exposing it to anyone who happens to stumble onto the IP. Every request
to /api/ must include the header

    X-App-Passcode: <the code>

matching the APP_PASSCODE setting. The /api/auth/check/ endpoint is
exempted so the frontend can verify the code before storing it. If
APP_PASSCODE is empty (default), the middleware does nothing - this
keeps local development friction-free.

We use constant-time string comparison to avoid leaking the code length
via timing attacks. The passcode itself is shipped from the browser as a
plain string in the header, which is fine on a trusted office network
where we control the LAN and only run over HTTP. If we ever expose this
service to the public internet, we should switch to signed tokens.
"""
from __future__ import annotations

import hmac

from django.conf import settings
from django.http import JsonResponse


class PasscodeMiddleware:
    # Paths that bypass the passcode check. Keep this list short: it
    # includes only the endpoint that VERIFIES the passcode and Django's
    # admin (which has its own auth). Everything else under /api/ is
    # protected.
    EXEMPT_PREFIXES = (
        "/api/auth/check/",
        "/admin/",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.expected_code = getattr(settings, "APP_PASSCODE", "") or ""

    def __call__(self, request):
        # If no passcode is configured, skip the gate entirely - this is the
        # opt-in behaviour so local dev "just works".
        if not self.expected_code:
            return self.get_response(request)

        path = request.path or ""
        # Anything outside /api/ falls through (Django admin, static files,
        # etc.). The frontend itself is served by Next.js on a different
        # port, so we don't need to protect non-API Django routes.
        if not path.startswith("/api/"):
            return self.get_response(request)

        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        provided = request.headers.get("X-App-Passcode", "") or ""
        # CORS preflight (OPTIONS) requests don't carry custom headers in
        # the browser. Let them through so the real request can come next.
        if request.method == "OPTIONS":
            return self.get_response(request)

        if not hmac.compare_digest(provided, self.expected_code):
            return JsonResponse(
                {"detail": "Invalid passcode."}, status=401
            )

        return self.get_response(request)
