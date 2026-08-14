from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'get_target_display', 'status', 'reporter', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('description', 'admin_notes', 'reporter__username', 'property__title')
    list_select_related = ('reporter', 'property', 'agent', 'resolved_by')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('reporter', 'property', 'agent', 'category', 'description')
        }),
        ('Resolution', {
            'fields': ('status', 'admin_notes', 'resolved_by', 'resolved_at'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
