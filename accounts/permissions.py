# accounts/permissions.py
"""
Permission decorators and mixins for 9jaRent.

Never rely on frontend hiding buttons — every check here is enforced
server-side.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


# ============================================================================
# MIXINS
# ============================================================================

class AdminRequiredMixin(UserPassesTestMixin):
    """Requires an admin (SUPER_ADMIN or staff)."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_admin

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            # Let LoginRequiredMixin redirect to login instead of leaking 403.
            return super().handle_no_permission()
        raise PermissionDenied("You do not have permission to access this admin area.")


class ApprovedAgentRequiredMixin(UserPassesTestMixin):
    """
    Requires an APPROVED agent.

    Pending, rejected, and suspended agents are redirected to their status
    page (accounts:pending) rather than shown a raw 403 — the status page
    tells them what's happening and what to do next, which a 403 doesn't.
    A non-agent (renter) still gets the 403, since the status page would be
    meaningless to them.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_approved_agent

    def handle_no_permission(self):
        user = self.request.user

        if not user.is_authenticated:
            # LoginRequiredMixin (earlier in the MRO) handles this — but be
            # explicit so the mixin works standalone if used without it.
            return super().handle_no_permission()

        if user.is_agent:
            # Any non-approved agent status lands on the same status page,
            # which renders a different message per status (pending /
            # rejected / suspended).
            if user.is_pending_agent or user.is_rejected_agent or user.is_suspended_agent:
                messages.info(
                    self.request,
                    "You'll be able to list properties once your agent "
                    "application is approved.",
                )
                return redirect(reverse("accounts:pending"))

        # Renter trying to reach an agent-only page — that's a real 403.
        raise PermissionDenied(
            "You must be an approved agent to access this page."
        )


class AgentRequiredMixin(UserPassesTestMixin):
    """Requires an agent account of any status (used for profile pages etc.)."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_agent

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You must be a registered agent to access this page.")


class PublicOrRenterMixin(UserPassesTestMixin):
    """Allows public users and renters (non-agents)."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.role == "PUBLIC" or user.is_admin)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("This feature is for renters only.")


# ============================================================================
# DECORATORS
# ============================================================================

def approved_agent_required(view_func):
    """
    Requires an APPROVED agent.

    Same redirect-vs-403 policy as ApprovedAgentRequiredMixin above — keeps
    the mixin and decorator behaviour identical so a view can't accidentally
    give a worse experience than the other.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            raise PermissionDenied("You must be logged in to perform this action.")

        if user.is_approved_agent:
            return view_func(request, *args, **kwargs)

        if user.is_agent:
            if user.is_pending_agent or user.is_rejected_agent or user.is_suspended_agent:
                messages.info(
                    request,
                    "You'll be able to do this once your agent application "
                    "is approved.",
                )
                return redirect(reverse("accounts:pending"))

        raise PermissionDenied(
            "You must be an approved agent to perform this action."
        )
    return _wrapped_view


def admin_required(view_func):
    """Requires an admin user."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_admin:
            raise PermissionDenied("You do not have permission to perform this action.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def object_owner_required(model_class, owner_field="created_by"):
    """
    Ensures the current user owns the object (or is an admin).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            pk = kwargs.get("pk") or kwargs.get("id")
            if not pk:
                raise PermissionDenied("Object identifier missing.")

            try:
                obj = model_class.objects.get(pk=pk)
            except model_class.DoesNotExist:
                raise PermissionDenied("Object not found.")

            owner = getattr(obj, owner_field, None)
            if owner != request.user and not request.user.is_admin:
                raise PermissionDenied("You do not have permission to modify this object.")

            request._ownership_checked_object = obj
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator