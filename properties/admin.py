from django.contrib import admin
from .models import State, LGA, Property, PropertyImage

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'state', 'lga', 'price', 'status', 'created_at')
    list_filter = ('status', 'state', 'property_type')
    search_fields = ('title', 'area', 'description')
    inlines = [PropertyImageInline]
    actions = ['approve_properties', 'reject_properties']

    def approve_properties(self, request, queryset):
        queryset.update(status='PUBLISHED')
    approve_properties.short_description = "Approve selected properties"

    def reject_properties(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_properties.short_description = "Reject selected properties"
