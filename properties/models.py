
# properties/models.py

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinLengthValidator
from .validators import validate_video_file, validate_image_file


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'State'
        verbose_name_plural = 'States'
    
    def __str__(self): 
        return self.name


class LGA(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='lgas')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    
    class Meta:
        unique_together = ('state', 'name')
        ordering = ['name']
        verbose_name = 'LGA'
        verbose_name_plural = 'LGAs'
    
    def __str__(self): 
        return f"{self.name}, {self.state.name}"


class Property(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('PUBLISHED', 'Published'),
        ('REJECTED', 'Rejected'),
        ('RENTED', 'Rented'),
        ('ARCHIVED', 'Archived'),
    )
    
    PROPERTY_TYPES = (
        ('Mini Flat', 'Mini Flat'),
        ('Self-Contain', 'Self-Contain'),
        ('1-Bedroom Flat', '1-Bedroom Flat'),
        ('2-Bedroom Flat', '2-Bedroom Flat'),
        ('3-Bedroom Flat', '3-Bedroom Flat'),
        ('4-Bedroom Flat', '4-Bedroom Flat'),
        ('5+-Bedroom Flat', '5+ Bedroom Flat'),
        ('Duplex', 'Duplex'),
        ('Bungalow', 'Bungalow'),
        ('Terrace', 'Terrace'),
        ('Mansion', 'Mansion'),
        ('Commercial Space', 'Commercial Space'),
        ('Office Space', 'Office Space'),
        ('Warehouse', 'Warehouse'),
        ('Shop', 'Shop'),
    )
    
    RENTAL_PERIOD_CHOICES = (
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
    )

    # Basic Info
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField(validators=[MinLengthValidator(50)])
    
    # Property Details
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES)
    bedrooms = models.IntegerField(default=1)
    bathrooms = models.IntegerField(default=1)
    toilets = models.IntegerField(default=1, blank=True, null=True)
    property_size = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 500 sqm")
    
    # Location
    state = models.ForeignKey(State, on_delete=models.PROTECT, related_name='properties')
    lga = models.ForeignKey(LGA, on_delete=models.PROTECT, related_name='properties')
    area = models.CharField(max_length=200, help_text="Specific Area/Neighborhood")
    address = models.TextField(blank=True, null=True, help_text="Full street address")
    
    # Pricing
    price = models.DecimalField(max_digits=15, decimal_places=2)
    rental_period = models.CharField(max_length=20, choices=RENTAL_PERIOD_CHOICES, default='yearly')
    
    # Fee Breakdown (Financial Transparency)
    service_charge = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    agency_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    legal_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    caution_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    agreement_fee = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    other_fees = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    other_fees_description = models.CharField(max_length=200, blank=True, null=True)
    
    # Amenities (Boolean flags for common features)
    has_parking = models.BooleanField(default=False)
    has_water = models.BooleanField(default=False)
    has_electricity = models.BooleanField(default=False)
    has_borehole = models.BooleanField(default=False)
    has_generator = models.BooleanField(default=False)
    has_security = models.BooleanField(default=False)
    has_fenced_compound = models.BooleanField(default=False)
    is_furnished = models.BooleanField(default=False)
    has_kitchen = models.BooleanField(default=False)
    has_balcony = models.BooleanField(default=False)
    has_air_conditioning = models.BooleanField(default=False)
    has_internet = models.BooleanField(default=False)
    has_cctv = models.BooleanField(default=False)
    has_swimming_pool = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    other_amenities = models.TextField(blank=True, null=True, help_text="Other amenities not listed above")
    
    # Agent Contact (denormalized for performance, but synced from user profile)
    agent_name = models.CharField(max_length=200)
    agent_whatsapp = models.CharField(max_length=20, help_text="Format: 234XXXXXXXXXX")
    agent_email = models.EmailField(blank=True, null=True)
    
    # Media
    video = models.FileField(upload_to='property_videos/', blank=True, null=True, validators=[validate_video_file])
    
    # Status & Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    featured = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    
    # Analytics
    views = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)
    favourite_count = models.PositiveIntegerField(default=0)
    
    # Ownership & Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='properties'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_properties'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    rented_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Property'
        verbose_name_plural = 'Properties'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['state']),
            models.Index(fields=['lga']),
            models.Index(fields=['property_type']),
            models.Index(fields=['price']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'state']),
            models.Index(fields=['status', 'property_type']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['featured', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            import uuid
            base_slug = slugify(f"{self.state.slug}-{self.lga.slug}-{self.property_type}")
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
    
    def __str__(self): 
        return self.title
    
    @property
    def is_available(self):
        """Check if property is available for rent."""
        return self.status == 'PUBLISHED'
    
    @property
    def is_publicly_visible(self):
        """Check if property should appear in public search."""
        return self.status == 'PUBLISHED'
    
    @property
    def location_display(self):
        """Human-readable location string."""
        parts = [self.area, self.lga.name, self.state.name]
        return ', '.join(filter(None, parts))
    
    @property
    def total_move_in_cost(self):
        """Calculate estimated total move-in cost."""
        fees = [
            self.price or 0,
            self.service_charge or 0,
            self.agency_fee or 0,
            self.legal_fee or 0,
            self.caution_fee or 0,
            self.agreement_fee or 0,
            self.other_fees or 0,
        ]
        return sum(fees)
    
    @property
    def primary_image(self):
        """Get the primary image or first available image."""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.first()
    
    @property
    def agent_is_verified(self):
        """Check if the listing agent is verified."""
        if self.created_by:
            return self.created_by.is_approved_agent
        return False


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/', validators=[validate_image_file])
    thumbnail = models.ImageField(upload_to='property_thumbnails/', blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order_index', 'uploaded_at']
    
    def __str__(self): 
        return f"Image for {self.property.title}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per property
        if self.is_primary:
            PropertyImage.objects.filter(property=self.property, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)
