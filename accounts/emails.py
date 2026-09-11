# accounts/emails.py
"""
Email sending for account verification and onboarding.

All emails are HTML (branded, using templates/emails/base_email.html) with
a plain-text fallback for clients that don't render HTML. Sent synchronously
via Django's SMTP backend — see settings.py. Failures are caught and logged;
they never break the request that triggered them.
"""

import logging
import random
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import EmailOTP

logger = logging.getLogger("accounts")

OTP_LENGTH = 6
OTP_VALIDITY_MINUTES = 10


def _generate_code():
    return "".join(random.choices("0123456789", k=OTP_LENGTH))


def _site_url():
    """Base URL for CTA buttons, without a trailing slash."""
    return (getattr(settings, "SITE_URL", "") or "").rstrip("/")


def _send_html(subject, to_email, template_name, context, text_fallback):
    """
    Render `template_name` as HTML and send it, with `text_fallback` as
    the plain-text alternative. Single choke point for all account emails —
    a failure here is logged and swallowed, never propagated to the caller.
    """
    try:
        html_body = render_to_string(template_name, context)
    except Exception:
        logger.exception("Failed to render email template %s", template_name)
        return

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_fallback or strip_tags(html_body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send email to %s: %s", to_email, subject)


def create_and_send_otp(user, purpose=EmailOTP.Purpose.SIGNUP):
    """
    Create a fresh OTP for `user` and email it. Invalidates any prior
    unused codes for the same purpose, so only the latest one works.

    Returns the OTP instance. Never raises.
    """
    EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    otp = EmailOTP.objects.create(
        user=user,
        code=_generate_code(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES),
    )

    # Deliberately do not log the code itself — it's an authentication
    # secret. Log only the fact that one was issued.
    logger.info(
        "OTP issued — user=%s purpose=%s expires_in=%smin",
        user.pk, purpose, OTP_VALIDITY_MINUTES,
    )

    subject = "Your 9jaRent verification code"
    text_fallback = (
        f"Hi {user.full_name_or_username},\n\n"
        f"Your 9jaRent verification code is: {otp.code}\n\n"
        f"This code expires in {OTP_VALIDITY_MINUTES} minutes. "
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"- The 9jaRent Team"
    )

    _send_html(
        subject=subject,
        to_email=user.email,
        template_name="emails/otp.html",
        context={
            "user_name": user.full_name_or_username,
            "code": otp.code,
            "expires_in_minutes": OTP_VALIDITY_MINUTES,
        },
        text_fallback=text_fallback,
    )
    return otp


def send_welcome_email(user):
    """
    Send the post-verification welcome email. Different template for agents
    (application pending) vs renters (ready to browse).
    """
    if user.is_agent:
        subject = "Welcome to 9jaRent — application received"
        template_name = "emails/welcome_agent_pending.html"
        text_fallback = (
            f"Hi {user.full_name_or_username},\n\n"
            f"Welcome to 9jaRent.com.ng! Your email is verified and your "
            f"agent application has been submitted for review. An "
            f"administrator will review it within 24-48 hours, and you'll "
            f"be notified as soon as you're approved.\n\n"
            f"- The 9jaRent Team"
        )
    else:
        subject = "Welcome to 9jaRent!"
        template_name = "emails/welcome_renter.html"
        text_fallback = (
            f"Hi {user.full_name_or_username},\n\n"
            f"Welcome to 9jaRent.com.ng! Your account is now active. "
            f"Browse verified listings, message agents directly, and request "
            f"inspections whenever you're ready.\n\n"
            f"- The 9jaRent Team"
        )

    _send_html(
        subject=subject,
        to_email=user.email,
        template_name=template_name,
        context={
            "user_name": user.full_name_or_username,
            "site_url": _site_url(),
        },
        text_fallback=text_fallback,
    )