# accounts/emails.py
"""
Email sending for account verification and onboarding.

Sent synchronously via Django's send_mail (using whatever EMAIL_BACKEND is
configured - console in dev, Gmail SMTP in production per .env.example).
Every call is wrapped so a failed/slow email send (e.g. Gmail SMTP hiccup)
never breaks registration or login - it's logged and the user can always
hit "Resend code".
"""

import logging
import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP

logger = logging.getLogger('accounts')

OTP_LENGTH = 6
OTP_VALIDITY_MINUTES = 10


def _generate_code():
    return ''.join(random.choices('0123456789', k=OTP_LENGTH))


def create_and_send_otp(user, purpose=EmailOTP.Purpose.SIGNUP):
    """
    Create a fresh OTP for `user` and email it to them. Any previous unused
    codes for the same purpose are invalidated first, so only the latest
    code works (avoids a stale earlier email still being valid).

    Returns the OTP instance. Never raises - email failures are logged and
    swallowed so signup/login flows are never broken by an SMTP problem.
    """
    EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    otp = EmailOTP.objects.create(
        user=user,
        code=_generate_code(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES),
    )

    subject = "Verify your 9jaRent account"
    message = (
        f"Hi {user.full_name_or_username},\n\n"
        f"Your 9jaRent verification code is: {otp.code}\n\n"
        f"This code expires in {OTP_VALIDITY_MINUTES} minutes. "
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"- The 9jaRent Team"
    )
    _send(subject, message, user.email)
    return otp


def send_welcome_email(user):
    """Send a welcome email once a user's email address is verified."""
    if user.is_agent:
        subject = "Welcome to 9jaRent — you're verified!"
        body_extra = (
            "Your email is verified. Your agent application is still being "
            "reviewed by our team - we'll notify you as soon as it's approved "
            "and you can start listing properties."
        )
    else:
        subject = "Welcome to 9jaRent!"
        body_extra = (
            "You're all set. Browse verified listings, message agents directly, "
            "and request inspections whenever you're ready - "
            "no middlemen, just a WhatsApp message away."
        )

    message = (
        f"Hi {user.full_name_or_username},\n\n"
        f"Welcome to 9jaRent.com.ng! {body_extra}\n\n"
        f"- The 9jaRent Team"
    )
    _send(subject, message, user.email)


def _send(subject, message, to_email):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send email to %s: %s", to_email, subject)