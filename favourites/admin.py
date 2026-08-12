# favourites/admin.py

from django.contrib import admin
from .models import Favourite


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'property__title')
    autocomplete_fields = ('user', 'property')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
