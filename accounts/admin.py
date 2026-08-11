
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Enhanced admin for CustomUser with agent status management."""
    
    list_display = (
        'username', 'full_name_or_username', 'email', 'role', 'agent_status_colored',
        'phone', 'company_name', 'state', 'is_staff', 'date_joined'
    )
    list_filter = ('role', 'agent_status', 'is_staff', 'is_active', 'state', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'company_name')
    date_hierarchy = 'date_joined'
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'whatsapp_number')
        }),
        ('Agent Profile', {
            'fields': (
                'company_name', 'bio', 'profile_photo', 
                'state', 'city', 'office_address'
            ),
            'classes': ('collapse',),
            'description': 'Agent-specific profile information'
        }),
        ('Role & Status', {
            'fields': ('role', 'agent_status', 'rejection_reason'),
            'description': 'CRITICAL: Changing role or status affects user permissions'
        }),
        ('Audit Trail', {
            'fields': (
                'approved_at', 'approved_by',
                'rejected_at', 'rejected_by',
                'suspended_at', 'suspended_by'
            ),
            'classes': ('collapse',),
            'description': 'Moderation history (read-only)'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'agent_status'),
        }),
    )
    
    readonly_fields = (
        'approved_at', 'approved_by',
        'rejected_at', 'rejected_by',
        'suspended_at', 'suspended_by',
        'last_login', 'date_joined'
    )
    
    actions = ['approve_agents', 'reject_agents', 'suspend_agents', 'reactivate_agents']
    
    def agent_status_colored(self, obj):
        """Display agent status with color coding."""
        if not obj.is_agent:
            return format_html('<span style="color: gray;">—</span>')
        
        colors = {
            'PENDING': '#f0ad4e',    # Orange
            'APPROVED': '#5cb85c',   # Green
            'REJECTED': '#d9534f',   # Red
            'SUSPENDED': '#d9534f',  # Red
        }
        color = colors.get(obj.agent_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_agent_status_display()
        )
    agent_status_colored.short_description = 'Agent Status'
    agent_status_colored.admin_order_field = 'agent_status'
    
    def full_name_or_username(self, obj):
        return obj.full_name_or_username
    full_name_or_username.short_description = 'Name'
    
    # ============================================================================
    # ADMIN ACTIONS
    # ============================================================================
    
    def approve_agents(self, request, queryset):
        """Bulk approve selected agents."""
        from django.utils import timezone
        count = 0
        for user in queryset:
            if user.is_agent and user.agent_status != 'APPROVED':
                user.agent_status = 'APPROVED'
                user.approved_at = timezone.now()
                user.approved_by = request.user
                user.rejection_reason = ''
                user.save(update_fields=[
                    'agent_status', 'approved_at', 'approved_by', 'rejection_reason'
                ])
                count += 1
        self.message_user(request, f"{count} agent(s) approved successfully.")
    approve_agents.short_description = "Approve selected agents"
    
    def reject_agents(self, request, queryset):
        """Bulk reject selected agents."""
        from django.utils import timezone
        count = 0
        for user in queryset:
            if user.is_agent and user.agent_status != 'REJECTED':
                user.agent_status = 'REJECTED'
                user.rejected_at = timezone.now()
                user.rejected_by = request.user
                # Set a default reason if none provided
                if not user.rejection_reason:
                    user.rejection_reason = "Application rejected by administrator."
                user.save(update_fields=[
                    'agent_status', 'rejected_at', 'rejected_by', 'rejection_reason'
                ])
                count += 1
        self.message_user(request, f"{count} agent(s) rejected.")
    reject_agents.short_description = "Reject selected agents"
    
    def suspend_agents(self, request, queryset):
        """Bulk suspend selected agents."""
        from django.utils import timezone
        count = 0
        for user in queryset:
            if user.is_agent and user.agent_status != 'SUSPENDED':
                user.agent_status = 'SUSPENDED'
                user.suspended_at = timezone.now()
                user.suspended_by = request.user
                if not user.rejection_reason:
                    user.rejection_reason = "Account suspended by administrator."
                user.save(update_fields=[
                    'agent_status', 'suspended_at', 'suspended_by', 'rejection_reason'
                ])
                count += 1
        self.message_user(request, f"{count} agent(s) suspended.")
    suspend_agents.short_description = "Suspend selected agents"
    
    def reactivate_agents(self, request, queryset):
        """Bulk reactivate suspended agents back to APPROVED."""
        from django.utils import timezone
        count = 0
        for user in queryset:
            if user.is_agent and user.agent_status == 'SUSPENDED':
                user.agent_status = 'APPROVED'
                user.approved_at = timezone.now()
                user.approved_by = request.user
                user.rejection_reason = ''
                user.save(update_fields=[
                    'agent_status', 'approved_at', 'approved_by', 'rejection_reason'
                ])
                count += 1
        self.message_user(request, f"{count} agent(s) reactivated.")
    reactivate_agents.short_description = "Reactivate suspended agents"
