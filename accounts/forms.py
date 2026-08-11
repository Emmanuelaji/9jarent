from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class AgentSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used for account recovery and listing notifications.")
    phone = forms.CharField(required=True, max_length=20, label="Phone Number", help_text="e.g. 08012345678")
    whatsapp_number = forms.CharField(required=True, max_length=20, label="WhatsApp Number", help_text="Format: 234XXXXXXXXXX — this is what renters will message.")
    company_name = forms.CharField(required=False, max_length=200, label="Company / Agency Name (optional)")

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'whatsapp_number', 'company_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.whatsapp_number = self.cleaned_data['whatsapp_number']
        user.company_name = self.cleaned_data.get('company_name', '')
        user.role = 'MINOR_ADMIN'
        if commit:
            user.save()
        return user

class ProfileCompletionForm(forms.ModelForm):
    phone = forms.CharField(required=True, max_length=20, label="Phone Number", help_text="e.g. 08012345678")
    whatsapp_number = forms.CharField(required=True, max_length=20, label="WhatsApp Number", help_text="Format: 234XXXXXXXXXX — this is what renters will message.")

    class Meta:
        model = CustomUser
        fields = ['phone', 'whatsapp_number', 'company_name']
