#accounts/forms.py

import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser


def generate_unique_username(email, first_name=''):
    """
    Neither signup form collects a username (the design has no username
    field) - derive one from the email's local part, falling back to the
    name, and disambiguate with a numeric suffix on collision.
    """
    base = re.sub(r'[^a-zA-Z0-9]', '', (email.split('@')[0] if email else first_name)).lower()
    base = base or 'user'
    candidate = base
    suffix = 1
    while CustomUser.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


class EmailOrPhoneAuthenticationForm(AuthenticationForm):
    """
    Login form backing the Email/Phone tabbed login page. Whichever tab is
    active submits its value under a different field name (`username` for
    the email tab, `phone` for the phone tab); this form accepts either and
    passes whichever was actually filled in through to authenticate() as
    the identifier, which EmailOrPhoneBackend then resolves.
    """
    phone = forms.CharField(required=False, label="Phone Number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['username'].label = "Email Address"

    def clean(self):
        identifier = (self.data.get('username') or self.data.get('phone') or '').strip()
        password = self.cleaned_data.get('password')

        if identifier and password:
            self.user_cache = self.get_user_cache(identifier, password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def get_user_cache(self, identifier, password):
        from django.contrib.auth import authenticate
        return authenticate(self.request, username=identifier, password=password)


class AgentSignUpStep1Form(forms.ModelForm):
    """Step 1 of agent signup: agency info + email. Creates a PENDING agent
    account with an unusable password and email_verified=False - the account
    only becomes fully usable once steps 2 (email verification) and 3
    (password creation) complete."""

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
        required=True,
        max_length=200,
        label="Agency / Company Name"
    )
    state = forms.CharField(required=True, max_length=100, label="State")
    city = forms.CharField(required=True, max_length=100, label="City")
    office_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label="Office Address",
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        label="Agency Description",
        help_text="Tell renters about your experience and services."
    )

    class Meta:
        model = CustomUser
        fields = ['company_name', 'state', 'city', 'office_address', 'phone', 'whatsapp_number', 'email', 'bio']

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_whatsapp_number(self):
        whatsapp = self.cleaned_data['whatsapp_number'].strip()
        if not whatsapp.startswith('234'):
            raise ValidationError("WhatsApp number must start with 234 (e.g. 2348012345678).")
        if len(whatsapp) < 13:
            raise ValidationError("WhatsApp number seems too short. Use format: 234XXXXXXXXXX")
        return whatsapp

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = generate_unique_username(self.cleaned_data['email'])
        user.role = 'MINOR_ADMIN'
        user.agent_status = 'PENDING'
        user.email_verified = False
        user.set_unusable_password()
        if commit:
            user.save()
        return user


class OTPVerifyForm(forms.Form):
    """Step 2: enter the 6-digit code emailed in step 1."""
    code = forms.CharField(
        max_length=6, min_length=6, required=True, label="Verification Code",
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code', 'placeholder': '123456'})
    )


class AgentSignUpStep3Form(forms.Form):
    """Step 3: name + password, finalizing the account created in step 1."""
    first_name = forms.CharField(max_length=150, required=True, label="Full Name")
    last_name = forms.CharField(max_length=150, required=False, label="Last Name")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        p1, p2 = cleaned_data.get('password1'), cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("The two password fields didn't match.")
        if p1:
            from django.contrib.auth.password_validation import validate_password
            validate_password(p1)
        return cleaned_data


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
        fields = ['first_name', 'email', 'phone', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = generate_unique_username(self.cleaned_data['email'], self.cleaned_data['first_name'])
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