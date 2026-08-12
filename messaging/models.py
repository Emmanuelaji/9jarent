# messaging/models.py

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """
    A property-specific conversation between a renter and the agent
    who listed that property. One conversation per (property, renter) pair.
    """
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_renter'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_agent'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['property', 'renter'], name='unique_property_renter_conversation')
        ]
        indexes = [
            models.Index(fields=['renter', '-updated_at']),
            models.Index(fields=['agent', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.renter} <-> {self.agent} on {self.property}"

    def other_party(self, user):
        """Return the participant on the other side of this conversation from `user`."""
        return self.agent if user.id == self.renter_id else self.renter

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        return self.messages.exclude(sender=user).filter(is_read=False).count()


class Message(models.Model):
    """A single message within a Conversation."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['conversation', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender}: {self.message[:40]}"
