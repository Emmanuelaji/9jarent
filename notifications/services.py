# notifications/services.py
"""
Thin service layer for creating notifications from code paths that aren't
already covered by a model signal (signals.py handles the model
status-transition events; this covers everything else, like admin-wide
alerts for a new report).

Kept as plain synchronous DB writes. If this ever needs to move to a
background task (e.g. Celery), `notify()` and `notify_admins()` are the
only two call sites that would change - nothing calling them would.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Notification

logger = logging.getLogger('notifications')

User = get_user_model()


def notify(user, notification_type, title, message='', link=''):
    if not user:
        return None
    if not getattr(user, 'push_notifications_enabled', True):
        return None
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def notify_admins(notification_type, title, message='', link=''):
    """
    Notify every admin (staff or SUPER_ADMIN) user - e.g. a new report to
    review.

    In-app notifications are created with bulk_create(), which deliberately
    bypasses the post_save signal in signals.py that would otherwise send
    one email per admin (so a single report submission was sending N
    synchronous SMTP round-trips inside the request cycle). One email is
    then sent to the whole group via BCC, so admins' addresses stay private
    and the report's request/response path pays exactly one SMTP cost
    regardless of how many admins there are.
    """
    admins = list(User.objects.filter(Q(is_staff=True) | Q(role='SUPER_ADMIN')))
    if not admins:
        return

    Notification.objects.bulk_create([
        Notification(
            user=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )
        for admin in admins
    ])

    recipients = [
        admin.email for admin in admins
        if admin.email and getattr(admin, 'email_notifications_enabled', True)
    ]
    if not recipients:
        return

    site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
    link_url = f"{site_url}{link}" if link and site_url else (link or '')

    html_body = render_to_string('emails/notification.html', {
        'title': title,
        'message': message,
        'link_url': link_url,
    })
    text_body = strip_tags(html_body)

    try:
        email = EmailMultiAlternatives(
            subject=f"9jaRent: {title}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],
            bcc=recipients,
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send admin notification email: %s", title)