# notifications/services.py
"""
Thin service layer for creating notifications.

Kept as plain synchronous DB writes for now (Phase 10: in-app notifications
only). If/when this needs to scale, `notify()` and `notify_admins()` are the
only two call sites that would move to a background task (e.g. Celery) -
none of the calling code elsewhere needs to change.
"""

from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def notify(recipient, category, title, message='', target_url=''):
    """Create a single in-app notification. No-op if recipient is falsy."""
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        category=category,
        title=title,
        message=message,
        target_url=target_url,
    )


def notify_admins(category, title, message='', target_url=''):
    """Notify every admin (staff or SUPER_ADMIN) user."""
    admins = User.objects.filter(models_q_admins())
    Notification.objects.bulk_create([
        Notification(
            recipient=admin,
            category=category,
            title=title,
            message=message,
            target_url=target_url,
        )
        for admin in admins
    ])


def models_q_admins():
    """Q object matching admin users, kept in one place so the definition
    of 'admin' stays consistent with CustomUser.is_admin."""
    from django.db.models import Q
    return Q(is_staff=True) | Q(role='SUPER_ADMIN')