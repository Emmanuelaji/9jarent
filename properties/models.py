from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinLengthValidator
from .validators import validate_video_file, validate_image_file

class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    def __str__(self): return self.name

class LGA(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='lgas')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    class Meta:
        unique_together = ('state', 'name')
    def __str__(self): return f"{self.name}, {self.state.name}"

class Property(models.Model):
    STATUS_CHOICES = (('PENDING_REVIEW', 'Pending Review'), ('PUBLISHED', 'Published'), ('REJECTED', 'Rejected'), ('DRAFT', 'Draft'))
    PROPERTY_TYPES = (('Mini Flat', 'Mini Flat'), ('Self-Contain', 'Self-Contain'), ('1-Bedroom Flat', '1-Bedroom Flat'), ('2-Bedroom Flat', '2-Bedroom Flat'), ('3-Bedroom Flat', '3-Bedroom Flat'), ('Duplex', 'Duplex'), ('Bungalow', 'Bungalow'), ('Terrace', 'Terrace'), ('Mansion', 'Mansion'), ('Commercial Space', 'Commercial Space'))

    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField(validators=[MinLengthValidator(50)])
    price = models.DecimalField(max_digits=15, decimal_places=2)
    state = models.ForeignKey(State, on_delete=models.PROTECT)
    lga = models.ForeignKey(LGA, on_delete=models.PROTECT)
    area = models.CharField(max_length=200, help_text="Specific Area/Neighborhood")
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPES)
    bedrooms = models.IntegerField(default=1)
    bathrooms = models.IntegerField(default=1)
    agent_name = models.CharField(max_length=200)
    agent_whatsapp = models.CharField(max_length=20, help_text="Format: 234XXXXXXXXXX")
    agent_email = models.EmailField(blank=True, null=True)
    video = models.FileField(upload_to='property_videos/', blank=True, null=True, validators=[validate_video_file])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    featured = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    whatsapp_clicks = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='properties')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_properties')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            import uuid
            self.slug = slugify(f"{self.state.slug}-{self.lga.slug}-{self.property_type}-{uuid.uuid4().hex[:8]}")
        super().save(*args, **kwargs)

    def __str__(self): return self.title

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/', validators=[validate_image_file])
    thumbnail = models.ImageField(upload_to='property_thumbnails/', blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order_index = models.IntegerField(default=0)
    def __str__(self): return f"Image for {self.property.title}"
