# inspections/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InspectionRequest(models.Model):
    """A renter's request to physically view a property, and the agent's response to it."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    # Statuses that count as "still active" - block a renter from opening
    # a second concurrent request on the same property.
    ACTIVE_STATUSES = (Status.PENDING, Status.ACCEPTED)

    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='inspection_requests'
    )
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inspection_requests_made'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inspection_requests_received'
    )

    requested_date = models.DateField()
    requested_time = models.TimeField()
    renter_message = models.TextField(max_length=500, blank=True)
    agent_response = models.TextField(max_length=500, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['renter', 'status']),
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['property', 'status']),
        ]

    def __str__(self):
        return f"{self.renter} \u2192 {self.property} on {self.requested_date} ({self.status})"

    def clean(self):
        if self.requested_date and self.requested_date < timezone.localdate():
            raise ValidationError({'requested_date': "Requested date cannot be in the past."})

    def is_active(self):
        """True if this request is still pending or accepted (not yet resolved)."""
        return self.status in self.ACTIVE_STATUSES