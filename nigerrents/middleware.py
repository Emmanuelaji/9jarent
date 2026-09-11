# nigerrents/middleware.py
"""Security middleware for 9jaRent."""

import logging
import secrets
import time

from django.core.cache import cache
from django.http import HttpResponseForbidden

logger = logging.getLogger("nigerrents.middleware")


class RateLimitMiddleware:
    """
    Simple rate limiting middleware.
    Protects sensitive endpoints from brute force and abuse.
    """

    # (path_contains, max_requests, window_seconds).
    # path_contains matches substrings of request.path, so URLs must include
    # the mount prefix from the project's root urls.py.
    RATE_LIMITED_ENDPOINTS = [
        ("/accounts/login/", 5, 300),
        ("/accounts/signup/renter/", 3, 300),
        ("/accounts/signup/agent/verify/", 10, 300),
        ("/accounts/signup/agent/", 3, 300),
        ("/accounts/password-reset/", 3, 300),
        ("/messages/", 30, 60),
        ("/inspections/request", 5, 300),
        ("/reports/", 3, 300),
        ("/agent/properties/add", 5, 300),
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for admin surfaces, static/media, and Django's own admin —
        # moderators doing bulk actions shouldn't trip limits meant for
        # untrusted public traffic.
        path = request.path
        if (
            path.startswith("/admin/")
            or path.startswith("/dashboard/")
            or path.startswith("/static/")
            or path.startswith("/media/")
        ):
            return self.get_response(request)

        for endpoint, max_requests, window in self.RATE_LIMITED_ENDPOINTS:
            if endpoint in path:
                client_ip = self._get_client_ip(request)
                cache_key = f"ratelimit:{endpoint}:{client_ip}"

                data = cache.get(cache_key)
                now = time.time()
                if data is None:
                    cache.set(cache_key, {"count": 1, "first_request": now}, window)
                else:
                    data["count"] += 1
                    # Reset with the remaining window, not a fresh `window`,
                    # so a steady stream of requests can't push the expiry
                    # forward indefinitely.
                    remaining = window - (now - data["first_request"])
                    if remaining <= 0:
                        cache.set(cache_key, {"count": 1, "first_request": now}, window)
                        data = {"count": 1}
                    else:
                        cache.set(cache_key, data, remaining)

                    if data["count"] > max_requests:
                        logger.warning(
                            "Rate limit exceeded — endpoint=%s ip=%s count=%s "
                            "window=%ss path=%s",
                            endpoint, client_ip, data["count"], window, path,
                        )
                        return HttpResponseForbidden(
                            "Too many requests. Please try again later.",
                            content_type="text/plain",
                        )
                break

        return self.get_response(request)

    def _get_client_ip(self, request):
        """
        X-Forwarded-For is client-supplied and trivially spoofable — trusting
        it blindly lets anyone bypass rate limiting by sending a different
        fake value per request. Only honor it when TRUST_PROXY_HEADERS is
        enabled, i.e. behind a proxy that OVERWRITES the header.
        """
        from django.conf import settings

        if getattr(settings, "TRUST_PROXY_HEADERS", False):
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Per-request nonce for inline <script> tags. Templates read it via
        # {{ csp_nonce }} (nigerrents.context_processors.csp). Every inline
        # <script> must carry nonce="{{ csp_nonce }}" or it will be blocked.
        request.csp_nonce = secrets.token_urlsafe(16)

        response = self.get_response(request)

        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # script-src uses a per-request nonce, not 'unsafe-inline'. style-src
        # keeps 'unsafe-inline' because templates use inline style=""
        # attributes liberally — a far lower-severity risk than inline script
        # injection, so nonce-ing every style isn't worth the maintenance cost.
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{request.csp_nonce}' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        return response