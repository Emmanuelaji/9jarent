# accounts/backends.py
"""
Custom authentication backend allowing login via email address OR phone
number.

This module is referenced by two places that were previously pointing at a
module which didn't exist anywhere in the repo - `nigerrents/settings.py`
(AUTHENTICATION_BACKENDS) and `accounts/views.py`
(RenterSignUpView.form_valid, which hardcodes the backend path when logging
a brand-new renter in). With no `accounts/backends.py` present, EVERY call
to `authenticate()` - including Django's `client.login()` in tests, the
login form, and the post-signup auto-login - raised
`ModuleNotFoundError: No module named 'accounts.backends'`, i.e. login and
renter registration were completely broken.
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()

# Require at least this many digits before attempting a phone-based match,
# so a mistakenly-short/empty identifier can't loosely match many accounts.
MIN_PHONE_DIGITS = 7


def _digits_only(value):
    return re.sub(r'\D', '', value or '')


class EmailOrPhoneBackend(ModelBackend):
    """
    Authenticates a user against their email, username, or phone/WhatsApp
    number.

    `EmailOrPhoneAuthenticationForm` always resolves the active tab's value
    into a single identifier and passes it as `username` to `authenticate()`
    (see accounts/forms.py), so that's the primary path here. The `phone`
    kwarg is also accepted directly for any other/future callers.
    """

    def authenticate(self, request, username=None, password=None, phone=None, **kwargs):
        identifier = (username or phone or '').strip()
        if not identifier or not password:
            return None

        query = Q(email__iexact=identifier) | Q(username__iexact=identifier)

        digits = _digits_only(identifier)
        if len(digits) >= MIN_PHONE_DIGITS:
            query |= Q(phone__icontains=digits) | Q(whatsapp_number__icontains=digits)

        try:
            user = UserModel._default_manager.filter(query).distinct().get()
        except UserModel.DoesNotExist:
            # Still hash the password so failed logins for a nonexistent
            # identifier take the same time as a wrong-password attempt on
            # a real account (mitigates user enumeration via timing).
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # An ambiguous identifier should never happen given email is
            # meant to be unique, but refuse rather than guessing.
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None