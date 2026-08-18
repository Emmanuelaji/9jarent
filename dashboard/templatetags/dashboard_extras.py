"""Custom template filters for the admin dashboard."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dictionary lookup: {{ status_counts|get_item:value }}.

    Templates can't subscript a dict with a variable key, so dashboard
    templates use this filter to read per-status counts.
    """
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None
