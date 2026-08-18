# notifications/signals.py
"""
Signal handlers to auto-create notifications on key platform events.
Design allows easy migration to background workers (Celery/RQ) later.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from accounts.models import CustomUser
from properties.models import Property
from inspections.models import InspectionRequest
from reports.models import Report
from messaging.models import Message
from .models import Notification

User = get_user_model()


@receiver(post_save, sender=CustomUser)
def notify_agent_status_change(sender, instance, created, **kwargs):
    """Notify agent when their application status changes."""
    if created or not instance.pk:
        return

    # Check if agent_status changed by comparing with DB
    try:
        old = CustomUser.objects.get(pk=instance.pk)
        if old.agent_status != instance.agent_status:
            if instance.agent_status == 'APPROVED':
                Notification.objects.create(
                    user=instance,
                    notification_type='agent_approved',
                    title='Agent Application Approved',
                    message='Congratulations! Your agent application has been approved. You can now list properties.',
                    link='/agent/properties/add/',
                )
            elif instance.agent_status == 'REJECTED':
                Notification.objects.create(
                    user=instance,
                    notification_type='agent_rejected',
                    title='Agent Application Rejected',
                    message=f'Your agent application was rejected. Reason: {instance.rejection_reason or "No reason provided"}',
                )
            elif instance.agent_status == 'SUSPENDED':
                Notification.objects.create(
                    user=instance,
                    notification_type='agent_suspended',
                    title='Account Suspended',
                    message=f'Your agent account has been suspended. Reason: {instance.rejection_reason or "No reason provided"}',
                )
    except CustomUser.DoesNotExist:
        pass


@receiver(post_save, sender=Property)
def notify_property_status_change(sender, instance, created, **kwargs):
    """Notify agent when their property status changes."""
    if not instance.created_by:
        return

    try:
        old = Property.objects.get(pk=instance.pk)
        if old.status != instance.status:
            if instance.status == 'PUBLISHED':
                Notification.objects.create(
                    user=instance.created_by,
                    notification_type='property_approved',
                    title='Property Approved',
                    message=f'Your property "{instance.title}" has been approved and published.',
                    link=f'/properties/{instance.slug}/',
                )
            elif instance.status == 'REJECTED':
                Notification.objects.create(
                    user=instance.created_by,
                    notification_type='property_rejected',
                    title='Property Rejected',
                    message=f'Your property "{instance.title}" was rejected. Reason: {instance.rejection_reason or "No reason provided"}',
                )
    except Property.DoesNotExist:
        pass


@receiver(post_save, sender=InspectionRequest)
def notify_inspection_status_change(sender, instance, created, **kwargs):
    """Notify renter and agent on inspection status changes."""
    if created:
        # New inspection request - notify agent
        Notification.objects.create(
            user=instance.agent,
            notification_type='inspection_request',
            title='New Inspection Request',
            message=f'{instance.renter.full_name_or_username} requested an inspection for "{instance.property.title}" on {instance.requested_date}.',
            link=f'/inspections/{instance.pk}/',
        )
        return

    try:
        old = InspectionRequest.objects.get(pk=instance.pk)
        if old.status != instance.status:
            if instance.status == 'ACCEPTED':
                Notification.objects.create(
                    user=instance.renter,
                    notification_type='inspection_accepted',
                    title='Inspection Confirmed',
                    message=f'Your inspection request for "{instance.property.title}" has been accepted.',
                    link=f'/inspections/{instance.pk}/',
                )
            elif instance.status == 'DECLINED':
                Notification.objects.create(
                    user=instance.renter,
                    notification_type='inspection_declined',
                    title='Inspection Declined',
                    message=f'Your inspection request for "{instance.property.title}" was declined.',
                    link=f'/inspections/{instance.pk}/',
                )
            elif instance.status == 'COMPLETED':
                Notification.objects.create(
                    user=instance.renter,
                    notification_type='inspection_completed',
                    title='Inspection Completed',
                    message=f'Your inspection for "{instance.property.title}" has been marked as completed.',
                    link=f'/inspections/{instance.pk}/',
                )
    except InspectionRequest.DoesNotExist:
        pass


@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    """Notify recipient when a new message is received."""
    if not created:
        return

    conversation = instance.conversation
    recipient = conversation.agent if instance.sender == conversation.renter else conversation.renter

    Notification.objects.create(
        user=recipient,
        notification_type='new_message',
        title='New Message',
        message=f'New message from {instance.sender.full_name_or_username} about "{conversation.property.title}"',
        link=f'/messages/{conversation.pk}/',
    )