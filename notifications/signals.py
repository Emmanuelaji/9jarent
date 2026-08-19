# notifications/signals.py
"""
Signal handlers to auto-create notifications on key platform events.
Design allows easy migration to background workers (Celery/RQ) later.

State-transition detection: post_save fires AFTER the row is already
written, so `Model.objects.get(pk=instance.pk)` inside a post_save handler
just re-reads the *new* row, not the old one - comparing it against
`instance` can never detect a change. Old field values are captured in a
pre_save handler instead (before the write happens) and stashed onto the
instance for the paired post_save handler to compare against. Do not
"simplify" this back to a single post_save handler with a DB re-fetch -
that reintroduces the bug (transitions silently never notify anyone).
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from accounts.models import CustomUser
from properties.models import Property
from inspections.models import InspectionRequest
from reports.models import Report
from messaging.models import Message
from .models import Notification
from .emails import send_notification_email

User = get_user_model()


# ============================================================================
# Agent status transitions
# ============================================================================

@receiver(pre_save, sender=CustomUser)
def capture_old_agent_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_agent_status = None
        return
    try:
        instance._old_agent_status = CustomUser.objects.only('agent_status').get(pk=instance.pk).agent_status
    except CustomUser.DoesNotExist:
        instance._old_agent_status = None


@receiver(post_save, sender=CustomUser)
def notify_agent_status_change(sender, instance, created, **kwargs):
    """Notify agent when their application status changes."""
    if created:
        return

    old_status = getattr(instance, '_old_agent_status', None)
    if old_status is None or old_status == instance.agent_status:
        return

    if instance.agent_status == 'APPROVED':
        Notification.objects.create(
            user=instance,
            notification_type=Notification.Type.AGENT_APPROVED,
            title='Agent Application Approved',
            message='Congratulations! Your agent application has been approved. You can now list properties.',
            link='/agent/properties/add/',
        )
    elif instance.agent_status == 'REJECTED':
        Notification.objects.create(
            user=instance,
            notification_type=Notification.Type.AGENT_REJECTED,
            title='Agent Application Rejected',
            message=f'Your agent application was rejected. Reason: {instance.rejection_reason or "No reason provided"}',
        )
    elif instance.agent_status == 'SUSPENDED':
        Notification.objects.create(
            user=instance,
            notification_type=Notification.Type.AGENT_SUSPENDED,
            title='Account Suspended',
            message=f'Your agent account has been suspended. Reason: {instance.rejection_reason or "No reason provided"}',
        )


# ============================================================================
# Property status transitions
# ============================================================================

@receiver(pre_save, sender=Property)
def capture_old_property_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    try:
        instance._old_status = Property.objects.only('status').get(pk=instance.pk).status
    except Property.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Property)
def notify_property_status_change(sender, instance, created, **kwargs):
    """Notify agent when their property status changes."""
    if created or not instance.created_by:
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return

    if instance.status == 'PUBLISHED':
        Notification.objects.create(
            user=instance.created_by,
            notification_type=Notification.Type.PROPERTY_APPROVED,
            title='Property Approved',
            message=f'Your property "{instance.title}" has been approved and published.',
            link=f'/properties/{instance.slug}/',
        )
    elif instance.status == 'REJECTED':
        Notification.objects.create(
            user=instance.created_by,
            notification_type=Notification.Type.PROPERTY_REJECTED,
            title='Property Rejected',
            message=f'Your property "{instance.title}" was rejected. Reason: {instance.rejection_reason or "No reason provided"}',
        )


# ============================================================================
# Inspection status transitions
# ============================================================================

@receiver(pre_save, sender=InspectionRequest)
def capture_old_inspection_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    try:
        instance._old_status = InspectionRequest.objects.only('status').get(pk=instance.pk).status
    except InspectionRequest.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=InspectionRequest)
def notify_inspection_status_change(sender, instance, created, **kwargs):
    """Notify renter and agent on inspection status changes."""
    if created:
        # New inspection request - notify agent
        Notification.objects.create(
            user=instance.agent,
            notification_type=Notification.Type.INSPECTION_REQUEST,
            title='New Inspection Request',
            message=f'{instance.renter.full_name_or_username} requested an inspection for "{instance.property.title}" on {instance.requested_date}.',
            link=f'/inspections/{instance.pk}/',
        )
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return

    if instance.status == 'ACCEPTED':
        Notification.objects.create(
            user=instance.renter,
            notification_type=Notification.Type.INSPECTION_ACCEPTED,
            title='Inspection Confirmed',
            message=f'Your inspection request for "{instance.property.title}" has been accepted.',
            link=f'/inspections/{instance.pk}/',
        )
    elif instance.status == 'DECLINED':
        Notification.objects.create(
            user=instance.renter,
            notification_type=Notification.Type.INSPECTION_DECLINED,
            title='Inspection Declined',
            message=f'Your inspection request for "{instance.property.title}" was declined.',
            link=f'/inspections/{instance.pk}/',
        )
    elif instance.status == 'COMPLETED':
        Notification.objects.create(
            user=instance.renter,
            notification_type=Notification.Type.INSPECTION_COMPLETED,
            title='Inspection Completed',
            message=f'Your inspection for "{instance.property.title}" has been marked as completed.',
            link=f'/inspections/{instance.pk}/',
        )


# ============================================================================
# Reports (property/agent reports submitted by users)
# ============================================================================

@receiver(pre_save, sender=Report)
def capture_old_report_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    try:
        instance._old_status = Report.objects.only('status').get(pk=instance.pk).status
    except Report.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Report)
def notify_report_events(sender, instance, created, **kwargs):
    """Notify admins of new reports, and the reporter once their report is resolved."""
    from .services import notify_admins

    if created:
        notify_admins(
            Notification.Type.REPORT_SUBMITTED,
            'New Report Submitted',
            message=f'{instance.reporter.full_name_or_username} reported "{instance.get_target_display()}" ({instance.get_category_display()}).',
            link=instance.get_absolute_url(),
        )
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return

    if instance.status in (Report.Status.RESOLVED, Report.Status.DISMISSED):
        Notification.objects.create(
            user=instance.reporter,
            notification_type=Notification.Type.REPORT_RESOLVED,
            title='Your Report Has Been Reviewed',
            message=f'Your report about "{instance.get_target_display()}" has been {instance.get_status_display().lower()}.',
        )


# ============================================================================
# New message
# ============================================================================

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    """Notify recipient when a new message is received."""
    if not created:
        return

    conversation = instance.conversation
    recipient = conversation.agent if instance.sender == conversation.renter else conversation.renter

    Notification.objects.create(
        user=recipient,
        notification_type=Notification.Type.NEW_MESSAGE,
        title='New Message',
        message=f'New message from {instance.sender.full_name_or_username} about "{conversation.property.title}"',
        link=f'/messages/{conversation.pk}/',
    )


# ============================================================================
# Email delivery - fires for every Notification, regardless of source, so
# individual handlers above never need to remember to email separately.
# ============================================================================

@receiver(post_save, sender=Notification)
def email_on_notification_created(sender, instance, created, **kwargs):
    if created:
        send_notification_email(instance)