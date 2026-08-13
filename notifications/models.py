# notifications/models.py

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    A single in-app notification for a user.

    Kept intentionally simple (no generic foreign key) per the product
    principle of not over-engineering: a `target_url` string is enough to
    let the notification link somewhere relevant, without coupling this
    app to every other app's models.
    """

    class Category(models.TextChoices):
        AGENT_APPLICATION_SUBMITTED = 'AGENT_APPLICATION_SUBMITTED', 'Agent Application Submitted'
        AGENT_APPROVED = 'AGENT_APPROVED', 'Agent Approved'
        AGENT_REJECTED = 'AGENT_REJECTED', 'Agent Rejected'
        AGENT_SUSPENDED = 'AGENT_SUSPENDED', 'Agent Suspended'
        AGENT_REACTIVATED = 'AGENT_REACTIVATED', 'Agent Reactivated'
        PROPERTY_SUBMITTED = 'PROPERTY_SUBMITTED', 'Property Submitted'
        PROPERTY_APPROVED = 'PROPERTY_APPROVED', 'Property Approved'
        PROPERTY_REJECTED = 'PROPERTY_REJECTED', 'Property Rejected'
        PROPERTY_RENTED = 'PROPERTY_RENTED', 'Property Rented'
        NEW_MESSAGE = 'NEW_MESSAGE', 'New Message'
        INSPECTION_REQUESTED = 'INSPECTION_REQUESTED', 'Inspection Requested'
        INSPECTION_ACCEPTED = 'INSPECTION_ACCEPTED', 'Inspection Accepted'
        INSPECTION_DECLINED = 'INSPECTION_DECLINED', 'Inspection Declined'
        INSPECTION_CANCELLED = 'INSPECTION_CANCELLED', 'Inspection Cancelled'
        INSPECTION_COMPLETED = 'INSPECTION_COMPLETED', 'Inspection Completed'
        REPORT_SUBMITTED = 'REPORT_SUBMITTED', 'Report Submitted'
        REPORT_RESOLVED = 'REPORT_RESOLVED', 'Report Resolved'
        SYSTEM = 'SYSTEM', 'System'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    category = models.CharField(max_length=32, choices=Category.choices, default=Category.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=500, blank=True)
    target_url = models.CharField(max_length=300, blank=True, help_text="Where clicking this notification should go.")

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} -> {self.recipient}"