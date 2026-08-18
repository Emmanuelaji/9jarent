# accounts/models.py 
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('MINOR_ADMIN', 'Agent'),
        ('PUBLIC', 'Public User'),
    )
    
    AGENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PUBLIC')
    agent_status = models.CharField(
        max_length=20, 
        choices=AGENT_STATUS_CHOICES, 
        default='PENDING',
        help_text="Approval status for agent accounts"
    )
    
    # Contact & Profile
    phone = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to='agent_photos/', blank=True, null=True)
    office_address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Verification
    email_verified = models.BooleanField(default=False)
    
    # Audit fields for agent moderation
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection or suspension")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_agents'
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='rejected_agents'
    )
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='suspended_agents'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['agent_status']),
            models.Index(fields=['role', 'agent_status']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        """Check if user is any kind of administrator."""
        return self.is_staff or self.role == 'SUPER_ADMIN'
    
    @property
    def is_agent(self):
        """Check if user has agent role."""
        return self.role == 'MINOR_ADMIN'
    
    @property
    def is_approved_agent(self):
        """Check if user is an approved agent."""
        return self.role == 'MINOR_ADMIN' and self.agent_status == 'APPROVED'
    
    @property
    def is_pending_agent(self):
        """Check if user is a pending agent."""
        return self.role == 'MINOR_ADMIN' and self.agent_status == 'PENDING'
    
    @property
    def is_rejected_agent(self):
        """Check if user is a rejected agent."""
        return self.role == 'MINOR_ADMIN' and self.agent_status == 'REJECTED'
    
    @property
    def is_suspended_agent(self):
        """Check if user is a suspended agent."""
        return self.role == 'MINOR_ADMIN' and self.agent_status == 'SUSPENDED'
    
    @property
    def can_list_properties(self):
        """Check if user can create/list properties."""
        return self.is_approved_agent
    
    @property
    def agent_display_status(self):
        """Human-readable agent status with styling hint."""
        if not self.is_agent:
            return None
        return {
            'PENDING': {'label': 'Pending Approval', 'class': 'warning'},
            'APPROVED': {'label': 'Verified Agent', 'class': 'success'},
            'REJECTED': {'label': 'Application Rejected', 'class': 'danger'},
            'SUSPENDED': {'label': 'Account Suspended', 'class': 'danger'},
        }.get(self.agent_status)
    
    @property
    def full_name_or_username(self):
        """Return full name if available, otherwise username."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username