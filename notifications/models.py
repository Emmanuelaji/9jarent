from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification for users."""

    class Type(models.TextChoices):
        AGENT_APPROVED = 'agent_approved', 'Agent Approved'
        AGENT_REJECTED = 'agent_rejected', 'Agent Rejected'
        AGENT_SUSPENDED = 'agent_suspended', 'Agent Suspended'
        PROPERTY_APPROVED = 'property_approved', 'Property Approved'
        PROPERTY_REJECTED = 'property_rejected', 'Property Rejected'
        PROPERTY_PUBLISHED = 'property_published', 'Property Published'
        NEW_MESSAGE = 'new_message', 'New Message'
        INSPECTION_REQUEST = 'inspection_request', 'Inspection Request'
        INSPECTION_ACCEPTED = 'inspection_accepted', 'Inspection Accepted'
        INSPECTION_DECLINED = 'inspection_declined', 'Inspection Declined'
        INSPECTION_COMPLETED = 'inspection_completed', 'Inspection Completed'
        SYSTEM = 'system', 'System'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.SYSTEM
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.user}: {self.title}"

    def mark_read(self):
        """Mark notification as read."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])