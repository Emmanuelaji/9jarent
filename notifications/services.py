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

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Notification

User = get_user_model()


def notify(user, notification_type, title, message='', link=''):
    """Create a single in-app notification. No-op if user is falsy."""
    if not user:
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
    review. Uses individual .create() calls rather than bulk_create(),
    because bulk_create() bypasses post_save signals entirely in Django -
    that would silently skip the email-on-notification hook in signals.py
    for every admin.
    """
    admins = User.objects.filter(Q(is_staff=True) | Q(role='SUPER_ADMIN'))
    for admin in admins:
        Notification.objects.create(
            user=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )