# nigerrents/context_processors.py

def csp(request):
    """Expose the per-request CSP nonce (set by SecurityHeadersMiddleware)
    to every template as {{ csp_nonce }}, for use on inline <script> tags:
        <script nonce="{{ csp_nonce }}"> ... </script>
    """
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
