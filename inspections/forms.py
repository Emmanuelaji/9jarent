# inspections/forms.py

from django import forms
from django.utils import timezone

from .models import InspectionRequest


class InspectionRequestForm(forms.ModelForm):
    requested_date = forms.DateField(
        label="Preferred Date",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    requested_time = forms.TimeField(
        label="Preferred Time",
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    renter_message = forms.CharField(
        label="Your Message (Optional)",
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': "I am interested in this property and would like to schedule a physical inspection. Please let me know if the selected date and time works for you."
        }),
        max_length=500,
    )

    class Meta:
        model = InspectionRequest
        fields = ['requested_date', 'requested_time', 'renter_message']

    def clean_requested_date(self):
        date = self.cleaned_data['requested_date']
        if date < timezone.localdate():
            raise forms.ValidationError("Please choose a date that is today or later.")
        return date

    def clean(self):
        """
        Same-day requests are allowed only if the chosen time is still in
        the future — otherwise "request a 9am inspection" submitted at 3pm
        sails through validation and the agent just has to decline it.
        """
        cleaned = super().clean()
        date = cleaned.get('requested_date')
        time = cleaned.get('requested_time')
        if date and time and date == timezone.localdate():
            if time < timezone.localtime().time():
                self.add_error(
                    'requested_time',
                    "Please choose a time later than now for a same-day inspection.",
                )
        return cleaned