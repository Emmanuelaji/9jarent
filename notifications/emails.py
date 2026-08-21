# notifications/emails.py
"""
Renders templates/emails/notification.html for a Notification and sends it.

Sent synchronously via Django's send_mail machinery (console backend in dev,
SMTP in production per .env.example). Never raises - a failed/slow email
send must not break the request that triggered the notification (an admin
approving a property, a renter messaging an agent, etc). See
notifications/signals.py for what creates Notifications and triggers this.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('notifications')


def send_notification_email(notification):
    """Render templates/emails/notification.html for `notification` and email it."""
    to_email = getattr(notification.user, 'email', None)
    if not to_email:
        return

    link_url = ''
    if notification.link:
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        link_url = f"{site_url}{notification.link}" if site_url else notification.link

    html_body = render_to_string('emails/notification.html', {
        'title': notification.title,
        'message': notification.message,
        'link_url': link_url,
    })
    text_body = strip_tags(html_body)

    try:
        email = EmailMultiAlternatives(
            subject=f"9jaRent: {notification.title}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send notification email to %s: %s", to_email, notification.title)