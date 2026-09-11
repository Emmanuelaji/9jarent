# nigerrents/context_processors.py

from django.conf import settings


def csp(request):
    """Expose the per-request CSP nonce (set by SecurityHeadersMiddleware)
    to every template as {{ csp_nonce }}, for use on inline <script> tags:
        <script nonce="{{ csp_nonce }}"> ... </script>
    """
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}


def site_url(request):
    """
    Expose settings.SITE_URL to every template as {{ SITE_URL }}.

    Templates that need to build an absolute URL (JSON-LD in property
    detail, notification emails rendered through a view, etc.) can't rely
    on request.get_host()/build_absolute_uri() in production: on cPanel/
    Passenger the WSGI app commonly sees Host: localhost or an internal
    proxy address, so the resulting URL is wrong. SITE_URL is already
    required in production (see settings.py), so use that instead.
    """
    return {'SITE_URL': getattr(settings, 'SITE_URL', '').rstrip('/')}
