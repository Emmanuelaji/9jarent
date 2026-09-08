# favourites/views.py

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView

from properties.models import Property
from .models import Favourite


def _is_ajax(request):
    """Fetch() calls from app.js set this header explicitly (see initFavouriteToggle);
    a real <form> POST/full page load never sends it, so this safely tells the two apart."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


class FavouriteListView(LoginRequiredMixin, ListView):
    """A renter's own saved properties. Private - scoped to request.user only."""
    model = Favourite
    template_name = 'favourites/list.html'
    context_object_name = 'favourites'
    paginate_by = 12

    def get_queryset(self):
        return Favourite.objects.filter(
            user=self.request.user
        ).select_related(
            'property', 'property__state', 'property__lga'
        ).prefetch_related('property__images')


@login_required
def toggle_favourite(request, property_id):
    """
    Add or remove a property from the current user's favourites.
    POST only. Idempotent-safe against double-clicks via get_or_create.
    """
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")

    property_obj = get_object_or_404(Property, pk=property_id, status='PUBLISHED')

    with transaction.atomic():
        favourite, created = Favourite.objects.get_or_create(
            user=request.user,
            property=property_obj,
        )

        if created:
            Property.objects.filter(pk=property_obj.pk).update(favourite_count=F('favourite_count') + 1)
        else:
            favourite.delete()
            Property.objects.filter(pk=property_obj.pk, favourite_count__gt=0).update(
                favourite_count=Greatest(F('favourite_count') - 1, 0)
            )

    is_favourited = created
    if is_favourited:
        message_text = "Added to your favourites."
    else:
        message_text = "Removed from your favourites."

    if _is_ajax(request):
        # Re-fetch the count so the JSON response reflects the DB state
        # exactly (the F()/Greatest() update above is atomic but doesn't
        # return a value to Python).
        current_count = Property.objects.filter(pk=property_obj.pk).values_list(
            'favourite_count', flat=True
        ).first()
        return JsonResponse({
            'status': 'ok',
            'favourited': is_favourited,
            'favourite_count': current_count,
            'message': message_text,
        })

    messages.success(request, message_text)
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('favourites:list')