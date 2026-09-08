# nigerrents/middleware.py
"""Security middleware for 9jaRent."""

import secrets
import time
from django.http import HttpResponseForbidden
from django.core.cache import cache


class RateLimitMiddleware:
    """
    Simple rate limiting middleware.
    Protects sensitive endpoints from brute force and abuse.
    """

    # Endpoints to rate limit: (path_contains, max_requests, window_seconds)
    #
    # NOTE: these are matched as `endpoint in request.path` substrings, so
    # they must match the REAL URL, including any prefix from the project's
    # root urls.py (e.g. accounts/ is mounted under /accounts/, see
    # nigerrents/urls.py). Two of these previously didn't match anything -
    # '/accounts/register/' and '/accounts/agent/register/' - because the
    # actual URLs are /accounts/signup/renter/ and /accounts/signup/agent/
    # (see accounts/urls.py). Those two rules silently never fired; signup
    # spam on both forms was effectively unlimited. Fixed below, and added
    # a rule for the OTP verify step, which had no rate limiting at all
    # (a 6-digit code has only 1,000,000 combinations - worth limiting
    # guesses, not just resends).
    RATE_LIMITED_ENDPOINTS = [
        ('/accounts/login/', 5, 300),                  # 5 login attempts per 5 minutes
        ('/accounts/signup/renter/', 3, 300),           # 3 renter registrations per 5 minutes
        ('/accounts/signup/agent/verify/', 10, 300),    # 10 OTP verify attempts per 5 minutes
        ('/accounts/signup/agent/', 3, 300),            # 3 agent registration starts per 5 minutes
        ('/accounts/password-reset/', 3, 300),          # 3 password resets per 5 minutes
        ('/messages/', 30, 60),                         # 30 messages per minute
        ('/inspections/request', 5, 300),               # 5 inspection requests per 5 minutes
        ('/reports/', 3, 300),                          # 3 reports per 5 minutes
        ('/agent/properties/add', 5, 300),              # 5 property creations per 5 minutes
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip rate limiting for Django admin (/admin/), the custom admin
        # dashboard app (/dashboard/ - moderators doing bulk approve/reject/
        # resolve actions shouldn't trip limits meant for untrusted public
        # traffic just because their URL happens to contain a rate-limited
        # substring like /reports/), static/media, and the automated test
        # suite (which shares one process-wide cache across unrelated test
        # methods).
        from django.conf import settings
        if getattr(settings, 'TESTING', False):
            return self.get_response(request)

        path = request.path
        if path.startswith('/admin/') or path.startswith('/dashboard/') or path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Check rate limits
        for endpoint, max_requests, window in self.RATE_LIMITED_ENDPOINTS:
            if endpoint in path:
                client_ip = self._get_client_ip(request)
                cache_key = f"ratelimit:{endpoint}:{client_ip}"

                # Get current count
                data = cache.get(cache_key)
                now = time.time()
                if data is None:
                    cache.set(cache_key, {'count': 1, 'first_request': now}, window)
                else:
                    data['count'] += 1
                    # Re-set with the TIME REMAINING in the original window, not a
                    # fresh `window` seconds - otherwise a steady stream of requests
                    # keeps pushing the expiry forward and the window never closes.
                    remaining = window - (now - data['first_request'])
                    if remaining <= 0:
                        cache.set(cache_key, {'count': 1, 'first_request': now}, window)
                        data = {'count': 1}
                    else:
                        cache.set(cache_key, data, remaining)

                    if data['count'] > max_requests:
                        return HttpResponseForbidden(
                            "Too many requests. Please try again later.",
                            content_type='text/plain'
                        )
                break

        return self.get_response(request)

    def _get_client_ip(self, request):
        """
        Get the client IP from the request.

        X-Forwarded-For is client-supplied and trivially spoofable - trusting it
        blindly lets anyone bypass rate limiting by sending a different fake value
        per request. Only honor it when TRUST_PROXY_HEADERS is explicitly enabled,
        which should only be done when the app sits behind a proxy/load balancer
        that overwrites (never appends to) this header, so the value Django sees
        is guaranteed proxy-set rather than attacker-set.
        """
        from django.conf import settings
        if getattr(settings, 'TRUST_PROXY_HEADERS', False):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Per-request nonce for inline <script> blocks. Exposed to templates
        # as {{ csp_nonce }} via nigerrents.context_processors.csp (see
        # settings.py TEMPLATES). Every inline <script> tag must carry
        # nonce="{{ csp_nonce }}" or the browser will refuse to run it once
        # 'unsafe-inline' is removed from script-src below.
        request.csp_nonce = secrets.token_urlsafe(16)

        response = self.get_response(request)

        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # CSP (Content Security Policy)
        # script-src intentionally does NOT include 'unsafe-inline' - every
        # inline <script> in the templates carries a matching nonce instead,
        # so an attacker who manages to inject a <script> tag via XSS can't
        # get it to execute (they can't guess the per-request nonce).
        # style-src keeps 'unsafe-inline' - the templates use plenty of
        # inline style="" attributes for one-off layout tweaks, and inline
        # style injection is a much lower-severity risk than inline script
        # injection, so nonce-ing every style attribute isn't worth the
        # maintenance cost here.
        response['Content-Security-Policy'] = (
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