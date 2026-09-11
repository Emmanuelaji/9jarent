# properties/templatetags/query_extras.py
"""
Small template-tag helpers for the properties app.

querystring_with_page exists so pagination links on filtered listings don't
drop the active filters: a naive `href="?page=2"` wipes ?search=, ?state=,
etc., sending the user back to the unfiltered list mid-pagination.
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def querystring_with_page(context, page_number):
    """
    Rebuild the current querystring with `page` replaced/added. E.g. on
    ?state=5&sort=price_low it returns "?state=5&sort=price_low&page=2".

    Works on any request - if there's no querystring, returns "?page=N".
    """
    request = context.get('request')
    if request is None:
        return f'?page={page_number}'
    qs = request.GET.copy()
    qs['page'] = page_number
    return '?' + qs.urlencode()