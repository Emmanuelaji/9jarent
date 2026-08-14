from django.conf import settings
from django.db import models
from django.urls import reverse

from properties.models import Property
from accounts.models import CustomUser


class Report(models.Model):
    """User-submitted report for a property or agent."""

    class Category(models.TextChoices):
        FAKE_LISTING = 'fake_listing', 'Fake Listing'
        WRONG_PRICE = 'wrong_price', 'Wrong Price'
        UNAVAILABLE = 'unavailable', 'Unavailable Property'
        SUSPICIOUS_AGENT = 'suspicious_agent', 'Suspicious Agent'
        MISLEADING_INFO = 'misleading_info', 'Misleading Information'
        INAPPROPRIATE_CONTENT = 'inappropriate_content', 'Inappropriate Content'
        OTHER = 'other', 'Other Issue'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        UNDER_REVIEW = 'under_review', 'Under Review'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_received',
        null=True,
        blank=True
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER
    )
    description = models.TextField(
        help_text='Please provide details about the issue.'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    admin_notes = models.TextField(
        blank=True,
        help_text='Internal notes for administrators.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_resolved'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['reporter']),
            models.Index(fields=['property']),
            models.Index(fields=['agent']),
        ]

    def __str__(self):
        target = self.property.title if self.property else (self.agent.full_name_or_username if self.agent else 'Unknown')
        return f"Report: {target} ({self.get_category_display()})"

    def get_absolute_url(self):
        return reverse('dashboard:report_detail', kwargs={'pk': self.pk})

    def get_target_display(self):
        """Human-readable target of this report."""
        if self.property:
            return f'Property: {self.property.title}'
        elif self.agent:
            return f'Agent: {self.agent.full_name_or_username}'
        return 'Unknown target'

    def get_is_pending(self):
        return self.status == self.Status.PENDING

    def get_is_resolved(self):
        return self.status == self.Status.RESOLVED
