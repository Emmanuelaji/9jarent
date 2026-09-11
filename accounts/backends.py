# accounts/backends.py
"""
Custom authentication backend allowing login via email address OR phone
number.

`AUTHENTICATION_BACKENDS` in settings.py points here, and
`accounts/views.py::RenterSignUpView.form_valid` hardcodes this backend's
path when logging a brand-new renter in.

Every authenticate() call is logged:
  - INFO  on success (auth.log)
  - WARN  on failure with reason (auth.log; also routed to errors.log
          via the 'accounts' logger's ERROR handler for genuine failures)
"""

import logging
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

logger = logging.getLogger("accounts")

UserModel = get_user_model()

# Require at least this many digits before attempting a phone-based match,
# so a mistakenly-short/empty identifier can't loosely match many accounts.
MIN_PHONE_DIGITS = 7


def _digits_only(value):
    return re.sub(r"\D", "", value or "")


def _client_ip(request):
    """Return the client IP from the request, or 'unknown' if there is none.

    Mirrors RateLimitMiddleware._get_client_ip's X-Forwarded-For policy:
    only trust the header when TRUST_PROXY_HEADERS is on.
    """
    if request is None:
        return "unknown"
    from django.conf import settings

    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


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
        identifier = (username or phone or "").strip()
        if not identifier or not password:
            return None

        ip = _client_ip(request)

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
            logger.warning(
                "Login failed — unknown identifier=%r ip=%s", identifier, ip
            )
            return None
        except UserModel.MultipleObjectsReturned:
            # An ambiguous identifier should never happen given email is
            # meant to be unique, but refuse rather than guessing.
            logger.warning(
                "Login failed — ambiguous identifier=%r matched multiple users ip=%s",
                identifier, ip,
            )
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.info(
                "Login success — user=%s ip=%s", user.pk, ip,
            )
            return user

        # Either the password was wrong, or user_can_authenticate() refused
        # (inactive/archived account, etc). Same log line covers both — the
        # distinction isn't actionable from here.
        logger.warning(
            "Login failed — bad credentials user=%s ip=%s", user.pk, ip,
        )
        return None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None