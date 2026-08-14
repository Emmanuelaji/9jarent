from django import forms
from .models import Report


class ReportForm(forms.ModelForm):
    """Form for submitting a new report."""

    class Meta:
        model = Report
        fields = ['category', 'description']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe the issue in detail...',
            }),
        }
        labels = {
            'category': 'Report Category',
            'description': 'Description',
        }

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 20:
            raise forms.ValidationError('Please provide at least 20 characters describing the issue.')
        return description


class ReportResolutionForm(forms.Form):
    """Form for administrators to resolve or dismiss a report."""

    STATUS_CHOICES = [
        ('resolved', 'Mark as Resolved'),
        ('dismissed', 'Dismiss Report'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Resolution Action'
    )
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add internal notes about this resolution...',
        }),
        required=False,
        label='Admin Notes'
    )
