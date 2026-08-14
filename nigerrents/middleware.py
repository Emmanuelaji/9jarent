# nigerrents/middleware.py
"""Security middleware for 9jaRent."""

import time
from django.http import HttpResponseForbidden
from django.core.cache import cache


class RateLimitMiddleware:
    """
    Simple rate limiting middleware.
    Protects sensitive endpoints from brute force and abuse.
    """

    # Endpoints to rate limit: (path_contains, max_requests, window_seconds)
    RATE_LIMITED_ENDPOINTS = [
        ('/accounts/login/', 5, 300),        # 5 login attempts per 5 minutes
        ('/accounts/register/', 3, 300),     # 3 registrations per 5 minutes
        ('/accounts/agent/register/', 3, 300), # 3 agent registrations per 5 minutes
        ('/accounts/password-reset/', 3, 300), # 3 password resets per 5 minutes
        ('/messages/', 30, 60),              # 30 messages per minute
        ('/inspections/request', 5, 300),    # 5 inspection requests per 5 minutes
        ('/reports/', 3, 300),               # 3 reports per 5 minutes
        ('/agent/properties/add', 5, 300),   # 5 property creations per 5 minutes
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip rate limiting for admin and static/media
        path = request.path
        if path.startswith('/admin/') or path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Check rate limits
        for endpoint, max_requests, window in self.RATE_LIMITED_ENDPOINTS:
            if endpoint in path:
                client_ip = self._get_client_ip(request)
                cache_key = f"ratelimit:{endpoint}:{client_ip}"

                # Get current count
                data = cache.get(cache_key)
                if data is None:
                    cache.set(cache_key, {'count': 1, 'first_request': time.time()}, window)
                else:
                    data['count'] += 1
                    cache.set(cache_key, data, window)

                    if data['count'] > max_requests:
                        return HttpResponseForbidden(
                            "Too many requests. Please try again later.",
                            content_type='text/plain'
                        )
                break

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Get client IP from request, respecting X-Forwarded-For."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # CSP (Content Security Policy)
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        return response
