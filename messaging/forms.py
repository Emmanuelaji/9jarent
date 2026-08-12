# messaging/forms.py

from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Type a message...',
                'class': 'form-control',
            })
        }
        labels = {'message': ''}

    def clean_message(self):
        text = self.cleaned_data['message'].strip()
        if not text:
            raise forms.ValidationError("Message cannot be empty.")
        return text