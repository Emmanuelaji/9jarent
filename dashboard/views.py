
# dashboard/views.py with agent moderation and POST-based actions

from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from accounts.permissions import AdminRequiredMixin, admin_required
from properties.models import Property
from accounts.models import CustomUser

User = get_user_model()


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Custom admin dashboard with overview metrics and pending items."""
    model = Property
    template_name = 'dashboard/admin.html'
    context_object_name = 'pending_properties'
    paginate_by = 20

    def get_queryset(self):
        return Property.objects.filter(
            status='PENDING_REVIEW'
        ).select_related('created_by', 'state', 'lga').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Property metrics
        context['total_listings'] = Property.objects.count()
        context['published_listings'] = Property.objects.filter(status='PUBLISHED').count()
        context['pending_review_listings'] = Property.objects.filter(status='PENDING_REVIEW').count()
        context['rejected_listings'] = Property.objects.filter(status='REJECTED').count()
        context['rented_listings'] = Property.objects.filter(status='RENTED').count()
        context['archived_listings'] = Property.objects.filter(status='ARCHIVED').count()
        context['featured_listings'] = Property.objects.filter(featured=True).count()
        
        # Agent metrics
        context['total_agents'] = CustomUser.objects.filter(role='MINOR_ADMIN').count()
        context['pending_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='PENDING'
        ).count()
        context['approved_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='APPROVED'
        ).count()
        context['rejected_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='REJECTED'
        ).count()
        context['suspended_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='SUSPENDED'
        ).count()
        
        # User metrics
        context['total_users'] = CustomUser.objects.filter(role='PUBLIC').count()
        context['total_staff'] = CustomUser.objects.filter(is_staff=True).count()
        
        # Recent activity
        context['recent_properties'] = Property.objects.select_related(
            'created_by', 'state'
        ).order_by('-created_at')[:10]
        
        context['recent_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN'
        ).order_by('-date_joined')[:10]
        
        # Pending agent applications
        context['pending_agent_applications'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='PENDING'
        ).order_by('date_joined')[:10]
        
        return context


# ============================================================================
# PROPERTY MODERATION (POST only)
# ============================================================================

@login_required
@require_POST
def approve_property(request, pk):
    """Approve a property and publish it."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    prop = get_object_or_404(Property, pk=pk)
    if prop.status == 'PENDING_REVIEW':
        prop.status = 'PUBLISHED'
        prop.approved_by = request.user
        prop.published_at = timezone.now()
        prop.save(update_fields=['status', 'approved_by', 'published_at', 'updated_at'])
        messages.success(request, f"Property '{prop.title}' approved and published.")
    else:
        messages.warning(request, "Only pending review properties can be approved.")
    return redirect('dashboard:admin')


@login_required
@require_POST
def reject_property(request, pk):
    """Reject a property with reason."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    prop = get_object_or_404(Property, pk=pk)
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "Rejection reason is required.")
        return redirect('dashboard:admin')
    
    if prop.status == 'PENDING_REVIEW':
        prop.status = 'REJECTED'
        prop.rejection_reason = reason
        prop.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        messages.warning(request, f"Property '{prop.title}' rejected.")
    else:
        messages.warning(request, "Only pending review properties can be rejected.")
    return redirect('dashboard:admin')


@login_required
@require_POST
def unpublish_property(request, pk):
    """Unpublish an approved property (e.g., for re-review)."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    prop = get_object_or_404(Property, pk=pk)
    if prop.status == 'PUBLISHED':
        prop.status = 'PENDING_REVIEW'
        prop.published_at = None
        prop.save(update_fields=['status', 'published_at', 'updated_at'])
        messages.success(request, f"Property '{prop.title}' unpublished for re-review.")
    else:
        messages.warning(request, "Only published properties can be unpublished.")
    return redirect('dashboard:admin')


# ============================================================================
# AGENT MODERATION (POST only)
# ============================================================================

@login_required
@require_POST
def approve_agent(request, pk):
    """Approve a pending agent application."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    agent = get_object_or_404(CustomUser, pk=pk, role='MINOR_ADMIN')
    if agent.agent_status == 'PENDING':
        agent.agent_status = 'APPROVED'
        agent.approved_at = timezone.now()
        agent.approved_by = request.user
        agent.rejection_reason = ''
        agent.save(update_fields=[
            'agent_status', 'approved_at', 'approved_by', 'rejection_reason'
        ])
        messages.success(request, f"Agent '{agent.username}' approved successfully.")
    else:
        messages.warning(request, "Only pending agents can be approved.")
    return redirect('dashboard:agents_pending')


@login_required
@require_POST
def reject_agent(request, pk):
    """Reject an agent application with reason."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    agent = get_object_or_404(CustomUser, pk=pk, role='MINOR_ADMIN')
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "Rejection reason is required.")
        return redirect('dashboard:agents_pending')
    
    if agent.agent_status == 'PENDING':
        agent.agent_status = 'REJECTED'
        agent.rejected_at = timezone.now()
        agent.rejected_by = request.user
        agent.rejection_reason = reason
        agent.save(update_fields=[
            'agent_status', 'rejected_at', 'rejected_by', 'rejection_reason'
        ])
        messages.warning(request, f"Agent '{agent.username}' rejected.")
    else:
        messages.warning(request, "Only pending agents can be rejected.")
    return redirect('dashboard:agents_pending')


@login_required
@require_POST
def suspend_agent(request, pk):
    """Suspend an approved agent."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    agent = get_object_or_404(CustomUser, pk=pk, role='MINOR_ADMIN')
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, "Suspension reason is required.")
        return redirect('dashboard:agents_approved')
    
    if agent.agent_status == 'APPROVED':
        agent.agent_status = 'SUSPENDED'
        agent.suspended_at = timezone.now()
        agent.suspended_by = request.user
        agent.rejection_reason = reason
        agent.save(update_fields=[
            'agent_status', 'suspended_at', 'suspended_by', 'rejection_reason'
        ])
        messages.warning(request, f"Agent '{agent.username}' suspended.")
    else:
        messages.warning(request, "Only approved agents can be suspended.")
    return redirect('dashboard:agents_approved')


@login_required
@require_POST
def reactivate_agent(request, pk):
    """Reactivate a suspended agent."""
    if not request.user.is_admin:
        raise PermissionDenied("Admin access required.")
    
    agent = get_object_or_404(CustomUser, pk=pk, role='MINOR_ADMIN')
    if agent.agent_status == 'SUSPENDED':
        agent.agent_status = 'APPROVED'
        agent.approved_at = timezone.now()
        agent.approved_by = request.user
        agent.rejection_reason = ''
        agent.save(update_fields=[
            'agent_status', 'approved_at', 'approved_by', 'rejection_reason'
        ])
        messages.success(request, f"Agent '{agent.username}' reactivated.")
    else:
        messages.warning(request, "Only suspended agents can be reactivated.")
    return redirect('dashboard:agents_suspended')


# ============================================================================
# AGENT LIST VIEWS
# ============================================================================

class PendingAgentsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List pending agent applications."""
    model = CustomUser
    template_name = 'dashboard/agents_pending.html'
    context_object_name = 'agents'
    paginate_by = 20

    def get_queryset(self):
        return CustomUser.objects.filter(
            role='MINOR_ADMIN', 
            agent_status='PENDING'
        ).order_by('date_joined')


class ApprovedAgentsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List approved agents."""
    model = CustomUser
    template_name = 'dashboard/agents_approved.html'
    context_object_name = 'agents'
    paginate_by = 20

    def get_queryset(self):
        return CustomUser.objects.filter(
            role='MINOR_ADMIN', 
            agent_status='APPROVED'
        ).order_by('-approved_at')


class RejectedAgentsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List rejected agents."""
    model = CustomUser
    template_name = 'dashboard/agents_rejected.html'
    context_object_name = 'agents'
    paginate_by = 20

    def get_queryset(self):
        return CustomUser.objects.filter(
            role='MINOR_ADMIN', 
            agent_status='REJECTED'
        ).order_by('-rejected_at')


class SuspendedAgentsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List suspended agents."""
    model = CustomUser
    template_name = 'dashboard/agents_suspended.html'
    context_object_name = 'agents'
    paginate_by = 20

    def get_queryset(self):
        return CustomUser.objects.filter(
            role='MINOR_ADMIN', 
            agent_status='SUSPENDED'
        ).order_by('-suspended_at')


class AgentDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Admin view of agent details."""
    model = CustomUser
    template_name = 'dashboard/agent_detail.html'
    context_object_name = 'agent'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent = self.object
        context['agent_properties'] = Property.objects.filter(
            created_by=agent
        ).select_related('state', 'lga').order_by('-created_at')
        context['property_counts'] = {
            'total': Property.objects.filter(created_by=agent).count(),
            'published': Property.objects.filter(created_by=agent, status='PUBLISHED').count(),
            'pending': Property.objects.filter(created_by=agent, status='PENDING_REVIEW').count(),
            'rejected': Property.objects.filter(created_by=agent, status='REJECTED').count(),
            'rented': Property.objects.filter(created_by=agent, status='RENTED').count(),
        }
        return context



# ============================================================================
# REPORT MANAGEMENT VIEWS
# ============================================================================

class ReportsListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin view of all user-submitted reports."""
    template_name = 'dashboard/reports_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        from reports.models import Report
        queryset = Report.objects.select_related(
            'reporter', 'property', 'agent', 'resolved_by'
        ).order_by('-created_at')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def get_context_data(self, **kwargs):
        from reports.models import Report
        context = super().get_context_data(**kwargs)
        context['status_counts'] = {
            'pending': Report.objects.filter(status=Report.Status.PENDING).count(),
            'under_review': Report.objects.filter(status=Report.Status.UNDER_REVIEW).count(),
            'resolved': Report.objects.filter(status=Report.Status.RESOLVED).count(),
            'dismissed': Report.objects.filter(status=Report.Status.DISMISSED).count(),
            'total': Report.objects.count(),
        }
        context['current_status'] = self.request.GET.get('status', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class ReportDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Admin view of a single report."""
    template_name = 'dashboard/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        from reports.models import Report
        return Report.objects.select_related(
            'reporter', 'property', 'agent', 'resolved_by'
        )


@login_required
@admin_required
def resolve_report(request, pk):
    """Admin resolves or dismisses a report."""
    from reports.forms import ReportResolutionForm
    report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        form = ReportResolutionForm(request.POST)
        if form.is_valid():
            report.status = form.cleaned_data['status']
            report.admin_notes = form.cleaned_data['admin_notes']
            report.resolved_by = request.user
            from django.utils import timezone
            report.resolved_at = timezone.now()
            report.save(update_fields=['status', 'admin_notes', 'resolved_by', 'resolved_at'])

            messages.success(request, f'Report #{report.pk} has been marked as {report.get_status_display()}.')
            return redirect('dashboard:report_detail', pk=report.pk)

    return redirect('dashboard:report_detail', pk=report.pk)
