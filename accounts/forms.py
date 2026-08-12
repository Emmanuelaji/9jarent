#accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser

class AgentSignUpForm(UserCreationForm):
    """Form for agent registration. Creates a PENDING agent account."""
    
    first_name = forms.CharField(
        max_length=150, 
        required=True, 
        label="Full Name",
        help_text="Your full name as it will appear to renters."
    )
    last_name = forms.CharField(
        max_length=150, 
        required=False, 
        label="Last Name"
    )
    email = forms.EmailField(
        required=True, 
        help_text="Used for account recovery and listing notifications."
    )
    phone = forms.CharField(
        required=True, 
        max_length=20, 
        label="Phone Number", 
        help_text="e.g. 08012345678"
    )
    whatsapp_number = forms.CharField(
        required=True, 
        max_length=20, 
        label="WhatsApp Number", 
        help_text="Format: 234XXXXXXXXXX — this is what renters will message."
    )
    company_name = forms.CharField(
        required=False, 
        max_length=200, 
        label="Company / Agency Name (optional)"
    )
    state = forms.CharField(
        required=True, 
        max_length=100, 
        label="State",
        help_text="e.g. Lagos, Abuja, Oyo"
    )
    city = forms.CharField(
        required=True, 
        max_length=100, 
        label="City / LGA",
        help_text="e.g. Lekki, Ikeja, Wuse"
    )
    office_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Office Address (optional)",
        help_text="Your physical office address."
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label="About You / Agency Description",
        help_text="Tell renters about your experience and services."
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email', 
            'phone', 'whatsapp_number', 'company_name',
            'state', 'city', 'office_address', 'bio',
            'password1', 'password2'
        ]
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username
    
    def clean_whatsapp_number(self):
        whatsapp = self.cleaned_data['whatsapp_number'].strip()
        # Basic validation: should start with country code
        if not whatsapp.startswith('234'):
            raise ValidationError("WhatsApp number must start with 234 (e.g. 2348012345678).")
        if len(whatsapp) < 13:
            raise ValidationError("WhatsApp number seems too short. Use format: 234XXXXXXXXXX")
        return whatsapp
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone = self.cleaned_data['phone']
        user.whatsapp_number = self.cleaned_data['whatsapp_number']
        user.company_name = self.cleaned_data.get('company_name', '')
        user.state = self.cleaned_data['state']
        user.city = self.cleaned_data['city']
        user.office_address = self.cleaned_data.get('office_address', '')
        user.bio = self.cleaned_data.get('bio', '')
        user.role = 'MINOR_ADMIN'
        user.agent_status = 'PENDING'  # CRITICAL: Always pending on signup
        
        if commit:
            user.save()
        return user


class RenterSignUpForm(UserCreationForm):
    """Form for renter/public user registration. No approval workflow needed."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Full Name"
    )
    email = forms.EmailField(
        required=True,
        help_text="Used for account recovery and notifications."
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        label="Phone Number (optional)",
        help_text="e.g. 08012345678"
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.phone = self.cleaned_data.get('phone', '')
        user.role = 'PUBLIC'
        if commit:
            user.save()
        return user


class ProfileCompletionForm(forms.ModelForm):
    """Form for completing/updating agent profile."""
    
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=False, label="Last Name")
    phone = forms.CharField(
        required=True, 
        max_length=20, 
        label="Phone Number", 
        help_text="e.g. 08012345678"
    )
    whatsapp_number = forms.CharField(
        required=True, 
        max_length=20, 
        label="WhatsApp Number", 
        help_text="Format: 234XXXXXXXXXX"
    )
    company_name = forms.CharField(
        required=False, 
        max_length=200, 
        label="Company / Agency Name"
    )
    state = forms.CharField(required=True, max_length=100, label="State")
    city = forms.CharField(required=True, max_length=100, label="City / LGA")
    office_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label="Office Address"
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label="About You / Agency"
    )
    profile_photo = forms.ImageField(
        required=False,
        label="Profile Photo",
        help_text="Upload a professional photo. Max 5MB."
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone', 'whatsapp_number',
            'company_name', 'state', 'city', 'office_address', 'bio', 'profile_photo'
        ]
    
    def clean_whatsapp_number(self):
        whatsapp = self.cleaned_data['whatsapp_number'].strip()
        if not whatsapp.startswith('234'):
            raise ValidationError("WhatsApp number must start with 234 (e.g. 2348012345678).")
        if len(whatsapp) < 13:
            raise ValidationError("WhatsApp number seems too short.")
        return whatsapp
    
    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise ValidationError("Profile photo must be less than 5MB.")
            # Validate file extension
            import os
            ext = os.path.splitext(photo.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                raise ValidationError("Only JPEG and PNG images are allowed.")
        return photo