
# Create accounts/permissions.py - decorators and mixins for authorization
"""
Permission decorators and mixins for 9jaRent.

CRITICAL PRINCIPLE: Never rely on frontend hiding buttons.
Always enforce permissions server-side.
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from functools import wraps


# ============================================================================
# MIXINS
# ============================================================================

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin that requires user to be an admin (SUPER_ADMIN or staff)."""
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_admin
    
    def handle_no_permission(self):
        raise PermissionDenied("You do not have permission to access this admin area.")


class ApprovedAgentRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires user to be an APPROVED agent.
    Pending, rejected, or suspended agents are denied.
    """
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_approved_agent
    
    def handle_no_permission(self):
        user = self.request.user
        if user.is_authenticated and user.is_agent:
            if user.is_pending_agent:
                raise PermissionDenied(
                    "Your agent application is pending approval. "
                    "You cannot perform this action yet."
                )
            elif user.is_rejected_agent:
                raise PermissionDenied(
                    "Your agent application was rejected. "
                    "Please check your profile for the rejection reason."
                )
            elif user.is_suspended_agent:
                raise PermissionDenied(
                    "Your agent account has been suspended. "
                    "Please contact support for assistance."
                )
        raise PermissionDenied("You must be an approved agent to access this page.")


class AgentRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires user to have agent role (any status).
    Used for pages that all agents can access (e.g., profile, pending status).
    """
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_agent
    
    def handle_no_permission(self):
        raise PermissionDenied("You must be a registered agent to access this page.")


class PublicOrRenterMixin(UserPassesTestMixin):
    """Mixin that allows public users and renters (non-agents)."""
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.role == 'PUBLIC' or user.is_admin)
    
    def handle_no_permission(self):
        raise PermissionDenied("This feature is for renters only.")


# ============================================================================
# DECORATORS
# ============================================================================

def approved_agent_required(view_func):
    """
    Decorator that requires an APPROVED agent.
    Usage: @approved_agent_required
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("You must be logged in to perform this action.")
        
        if not user.is_approved_agent:
            if user.is_pending_agent:
                raise PermissionDenied(
                    "Your agent application is pending approval. "
                    "You cannot perform this action yet."
                )
            elif user.is_rejected_agent:
                raise PermissionDenied(
                    "Your agent application was rejected. "
                    "Please check your profile for the rejection reason."
                )
            elif user.is_suspended_agent:
                raise PermissionDenied(
                    "Your agent account has been suspended."
                )
            else:
                raise PermissionDenied("You must be an approved agent to perform this action.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    Decorator that requires an admin user.
    Usage: @admin_required
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_admin:
            raise PermissionDenied("You do not have permission to perform this action.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def object_owner_required(model_class, owner_field='created_by'):
    """
    Decorator that ensures the current user owns the object.
    Usage: @object_owner_required(Property, 'created_by')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Get the object pk from URL kwargs
            pk = kwargs.get('pk') or kwargs.get('id')
            if not pk:
                raise PermissionDenied("Object identifier missing.")
            
            try:
                obj = model_class.objects.get(pk=pk)
            except model_class.DoesNotExist:
                raise PermissionDenied("Object not found.")
            
            owner = getattr(obj, owner_field, None)
            if owner != request.user and not request.user.is_admin:
                raise PermissionDenied("You do not have permission to modify this object.")
            
            # Attach object to request for convenience
            request._ownership_checked_object = obj
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator