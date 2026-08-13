# nigerrents/views.py
"""Project-level views for custom error pages."""

from django.shortcuts import render


def handler403(request, exception=None):
    """Custom 403 Forbidden page."""
    return render(request, '403.html', status=403)


def handler404(request, exception=None):
    """Custom 404 Not Found page."""
    return render(request, '404.html', status=404)


def handler500(request):
    """Custom 500 Server Error page."""
    return render(request, '500.html', status=500)
