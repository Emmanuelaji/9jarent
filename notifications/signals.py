"""
Notification signals.

These create in-app notifications when key platform events occur.
Email notifications can be added later via Celery tasks.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from accounts.models import CustomUser
from properties.models import Property
from inspections.models import InspectionRequest
from messaging.models import Message
from .models import Notification


def _create_notification(user, notification_type, title, message, link=None):
    """Helper to create a notification safely."""
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )


# ============================================================================
# AGENT NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=CustomUser)
def notify_agent_status_change(sender, instance, created, **kwargs):
    """Notify agent when their application status changes."""
    if created or not instance.is_agent:
        return

    # Only notify on actual status changes (not every save)
    # We use a simple heuristic: if approved_at/rejected_at/suspended_at
    # was just set, send notification. For production, consider using
    # a dedicated signal or tracking previous state.
    pass  # Handled in dashboard views for explicit control


# ============================================================================
# PROPERTY NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=Property)
def notify_property_status_change(sender, instance, created, **kwargs):
    """Notify agent when their property status changes."""
    if created:
        # New property submitted - notify agent
        if instance.created_by:
            _create_notification(
                instance.created_by,
                Notification.Type.PROPERTY_PUBLISHED,
                'Property Submitted for Review',
                f'Your property "{instance.title}" has been submitted and is pending review.',
            )
        return

    # For status changes, we rely on explicit creation in dashboard views
    # to avoid duplicate notifications on every save.


# ============================================================================
# INSPECTION NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=InspectionRequest)
def notify_inspection_change(sender, instance, created, **kwargs):
    """Notify relevant parties when inspection status changes."""
    if created:
        # Notify agent of new inspection request
        _create_notification(
            instance.agent,
            Notification.Type.INSPECTION_REQUEST,
            'New Inspection Request',
            f'{instance.renter.full_name_or_username} requested an inspection for "{instance.property.title}" on {instance.requested_date}.',
        )
        return


# ============================================================================
# MESSAGE NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    """Notify recipient when a new message is received."""
    if not created:
        return

    conversation = instance.conversation
    # Notify the other party
    recipient = conversation.agent if instance.sender_id == conversation.renter_id else conversation.renter

    _create_notification(
        recipient,
        Notification.Type.NEW_MESSAGE,
        f'New message from {instance.sender.full_name_or_username}',
        f'Re: {conversation.property.title}',
        link=f'/messages/{conversation.pk}/'
    )
