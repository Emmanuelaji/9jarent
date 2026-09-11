# nigerrents/views.py
"""Project-level views: custom error pages and the legal pages."""

from django.shortcuts import render
from django.views.generic import TemplateView


# --- Error pages ------------------------------------------------------------

def handler400(request, exception=None):
    return render(request, "400.html", status=400)


def handler403(request, exception=None):
    return render(request, "403.html", status=403)


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)


# --- Legal pages ------------------------------------------------------------

class TermsView(TemplateView):
    template_name = "terms.html"


class PrivacyView(TemplateView):
    template_name = "privacy.html"