# messaging/context_processors.py

from django.db.models import Q

from .models import Conversation, Message


def unread_messages(request):
    """Adds `unread_message_count` to every template context for the nav badge."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    count = Message.objects.filter(
        conversation__in=Conversation.objects.filter(Q(renter=user) | Q(agent=user)),
        is_read=False,
    ).exclude(sender=user).count()
    return {'unread_message_count': count}
