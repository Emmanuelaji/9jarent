# inspections/admin.py

from django.contrib import admin
from .models import InspectionRequest


@admin.register(InspectionRequest)
class InspectionRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'renter', 'agent', 'requested_date', 'requested_time', 'status', 'created_at')
    list_filter = ('status', 'requested_date', 'created_at')
    search_fields = ('property__title', 'renter__username', 'agent__username')
    autocomplete_fields = ('property', 'renter', 'agent')
    date_hierarchy = 'requested_date'
    readonly_fields = ('created_at', 'updated_at')
