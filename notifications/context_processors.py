"""Context processor to add unread notification count to all templates."""

from .models import Notification


def unread_notifications(request):
    """Add unread notification count to template context."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    count = Notification.objects.filter(user=user, is_read=False).count()
    return {
        'unread_notification_count': count,
        'has_unread_notifications': count > 0,
    }
