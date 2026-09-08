# nigerrents/validators.py
"""Small validators shared across apps.

Kept at the project level (rather than inside accounts/ or properties/)
because both apps need validate_whatsapp_number and neither should have to
depend on the other just to import a string-format check.
"""

from django.core.exceptions import ValidationError


def validate_whatsapp_number(whatsapp):
    """Was previously copy-pasted with identical logic in three places:
    accounts/forms.py (AgentSignUpStep1Form, ProfileCompletionForm) and
    properties/forms.py (PropertyForm.clean_agent_whatsapp). Returns the
    cleaned value; raises ValidationError on failure, same contract as a
    Django form's clean_<field> method, so it can be called directly from one.
    """
    whatsapp = (whatsapp or '').strip()
    if not whatsapp.startswith('234'):
        raise ValidationError("WhatsApp number must start with 234 (e.g. 2348012345678).")
    if len(whatsapp) < 13:
        raise ValidationError("WhatsApp number seems too short. Use format: 234XXXXXXXXXX")
    return whatsapp
