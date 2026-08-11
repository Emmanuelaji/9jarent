from django import forms
from .models import Property, PropertyImage

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
    images = MultipleFileField(required=False)

    class Meta:
        model = Property
        fields = ['title', 'description', 'price', 'state', 'lga', 'area', 'property_type', 'bedrooms', 'bathrooms', 'agent_name', 'agent_whatsapp', 'agent_email', 'video']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }