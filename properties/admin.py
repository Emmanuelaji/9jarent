from django.contrib import admin
from django.utils.html import format_html
from .models import State, LGA, Property, PropertyImage

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name',)

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    readonly_fields = ('thumbnail_preview',)
    
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image.url)
        return "No image"
    thumbnail_preview.short_description = 'Preview'

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'state', 'lga', 'price', 'property_type', 
        'status_colored', 'featured', 'verified', 'views', 'created_at'
    )
    list_filter = (
        'status', 'featured', 'verified', 'state', 'property_type', 
        'rental_period', 'created_at'
    )
    search_fields = ('title', 'area', 'description', 'agent_name', 'created_by__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [PropertyImageInline]
    actions = ['approve_properties', 'reject_properties', 'feature_properties', 'unfeature_properties']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'property_type', 'status')
        }),
        ('Location', {
            'fields': ('state', 'lga', 'area', 'address')
        }),
        ('Details', {
            'fields': ('bedrooms', 'bathrooms', 'toilets', 'property_size')
        }),
        ('Pricing', {
            'fields': (
                'price', 'rental_period',
                'service_charge', 'agency_fee', 'legal_fee', 
                'caution_fee', 'agreement_fee', 'other_fees', 'other_fees_description'
            )
        }),
        ('Amenities', {
            'fields': (
                'has_parking', 'has_water', 'has_electricity', 'has_borehole',
                'has_generator', 'has_security', 'has_fenced_compound',
                'is_furnished', 'has_kitchen', 'has_balcony', 'has_air_conditioning',
                'has_internet', 'has_cctv', 'has_swimming_pool', 'has_gym',
                'other_amenities'
            ),
            'classes': ('collapse',),
        }),
        ('Agent Contact', {
            'fields': ('agent_name', 'agent_whatsapp', 'agent_email')
        }),
        ('Media', {
            'fields': ('video',)
        }),
        ('Moderation', {
            'fields': ('featured', 'verified', 'approved_by', 'rejection_reason')
        }),
        ('Ownership', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at', 'rented_at', 'archived_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('slug', 'views', 'whatsapp_clicks', 'favourite_count', 'created_at', 'updated_at', 'published_at', 'rented_at', 'archived_at')
    
    def status_colored(self, obj):
        colors = {
            'DRAFT': 'gray',
            'PENDING_REVIEW': '#f0ad4e',
            'PUBLISHED': '#5cb85c',
            'REJECTED': '#d9534f',
            'RENTED': '#5bc0de',
            'ARCHIVED': '#777',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def approve_properties(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status='PENDING_REVIEW').update(
            status='PUBLISHED', 
            approved_by=request.user,
            published_at=timezone.now()
        )
        self.message_user(request, f"{count} property(s) approved and published.")
    approve_properties.short_description = "Approve selected properties"
    
    def reject_properties(self, request, queryset):
        count = queryset.exclude(status='REJECTED').update(status='REJECTED')
        self.message_user(request, f"{count} property(s) rejected.")
    reject_properties.short_description = "Reject selected properties"
    
    def feature_properties(self, request, queryset):
        count = queryset.update(featured=True)
        self.message_user(request, f"{count} property(s) featured.")
    feature_properties.short_description = "Feature selected properties"
    
    def unfeature_properties(self, request, queryset):
        count = queryset.update(featured=False)
        self.message_user(request, f"{count} property(s) unfeatured.")
    unfeature_properties.short_description = "Unfeature selected properties"

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'is_primary', 'order_index', 'uploaded_at')
    list_filter = ('is_primary',)
    search_fields = ('property__title',)