
# properties/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Property, PropertyImage
import os


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PropertyForm(forms.ModelForm):
    """Form for creating/editing property listings."""
    
    images = MultipleFileField(
        required=False,
        label="Property Images",
        help_text="Upload JPEG or PNG images. Max 5MB each. First image will be primary."
    )
    
    # Agent contact fields (pre-populated from user profile but editable)
    agent_name = forms.CharField(
        max_length=200,
        required=True,
        label="Agent Name",
        help_text="Name displayed to renters."
    )
    agent_whatsapp = forms.CharField(
        max_length=20,
        required=True,
        label="WhatsApp Number",
        help_text="Format: 234XXXXXXXXXX"
    )
    agent_email = forms.EmailField(
        required=False,
        label="Agent Email (optional)"
    )
    
    class Meta:
        model = Property
        fields = [
            'title', 'description', 'price', 'rental_period',
            'state', 'lga', 'area', 'address',
            'property_type', 'bedrooms', 'bathrooms', 'toilets', 'property_size',
            'service_charge', 'agency_fee', 'legal_fee', 'caution_fee', 
            'agreement_fee', 'other_fees', 'other_fees_description',
            'has_parking', 'has_water', 'has_electricity', 'has_borehole',
            'has_generator', 'has_security', 'has_fenced_compound', 
            'is_furnished', 'has_kitchen', 'has_balcony', 'has_air_conditioning',
            'has_internet', 'has_cctv', 'has_swimming_pool', 'has_gym',
            'other_amenities',
            'agent_name', 'agent_whatsapp', 'agent_email',
            'video'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe the property in detail (min 50 characters)...'}),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Full street address...'}),
            'other_amenities': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any other amenities not listed above...'}),
            'other_fees_description': forms.TextInput(attrs={'placeholder': 'e.g. Estate levy, waste management fee...'}),
            'property_size': forms.TextInput(attrs={'placeholder': 'e.g. 500 sqm, 3 plots...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # rental_period has a model-level default ('yearly'); don't force the
        # agent to pick it on every submit - an omitted value falls back to
        # the model default in clean_rental_period().
        self.fields['rental_period'].required = False
        
        # Pre-populate agent fields from user profile if creating new property
        if self.user and not self.instance.pk:
            self.fields['agent_name'].initial = self.user.full_name_or_username
            self.fields['agent_whatsapp'].initial = self.user.whatsapp_number or ''
            self.fields['agent_email'].initial = self.user.email
    
    def clean_rental_period(self):
        return self.cleaned_data.get('rental_period') or Property._meta.get_field('rental_period').default

    def clean_agent_whatsapp(self):
        whatsapp = self.cleaned_data['agent_whatsapp'].strip()
        if not whatsapp.startswith('234'):
            raise ValidationError("WhatsApp number must start with 234 (e.g. 2348012345678).")
        if len(whatsapp) < 13:
            raise ValidationError("WhatsApp number seems too short.")
        return whatsapp
    
    def clean_images(self):
        images = self.cleaned_data.get('images', [])
        if images:
            if len(images) > 10:
                raise ValidationError("Maximum 10 images allowed per property.")
            for image in images:
                if image.size > 5 * 1024 * 1024:
                    raise ValidationError(f"Image '{image.name}' exceeds 5MB limit.")
                ext = os.path.splitext(image.name)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png']:
                    raise ValidationError(f"Image '{image.name}' must be JPEG or PNG.")
        return images
    
    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price