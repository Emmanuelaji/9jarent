# dashboard/views.py with agent moderation and POST-based actions

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from accounts.permissions import AdminRequiredMixin, admin_required
from properties.models import Property
from accounts.models import CustomUser
from inspections.models import InspectionRequest
from reports.models import Report

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
        context['draft_listings'] = Property.objects.filter(status='DRAFT').count()

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

        # Inspection metrics
        context['total_inspections'] = InspectionRequest.objects.count()
        context['pending_inspections'] = InspectionRequest.objects.filter(
            status=InspectionRequest.Status.PENDING
        ).count()
        context['accepted_inspections'] = InspectionRequest.objects.filter(
            status=InspectionRequest.Status.ACCEPTED
        ).count()
        context['completed_inspections'] = InspectionRequest.objects.filter(
            status=InspectionRequest.Status.COMPLETED
        ).count()
        context['declined_inspections'] = InspectionRequest.objects.filter(
            status=InspectionRequest.Status.DECLINED
        ).count()

        # Report metrics
        context['total_reports'] = Report.objects.count()
        context['pending_reports'] = Report.objects.filter(status=Report.Status.PENDING).count()
        context['under_review_reports'] = Report.objects.filter(status=Report.Status.UNDER_REVIEW).count()
        context['resolved_reports'] = Report.objects.filter(status=Report.Status.RESOLVED).count()
        context['dismissed_reports'] = Report.objects.filter(status=Report.Status.DISMISSED).count()

        # Recent inspection requests
        context['recent_inspections'] = InspectionRequest.objects.select_related(
            'property', 'renter', 'agent'
        ).order_by('-created_at')[:8]

        # Recent reports
        context['recent_reports'] = Report.objects.select_related(
            'reporter', 'property', 'agent'
        ).order_by('-created_at')[:8]

        # Recent activity (combined feed)
        context['recent_activity'] = self._get_recent_activity()

        # Recent properties
        context['recent_properties'] = Property.objects.select_related(
            'created_by', 'state'
        ).order_by('-created_at')[:10]

        # Recent agents
        context['recent_agents'] = CustomUser.objects.filter(
            role='MINOR_ADMIN'
        ).order_by('-date_joined')[:10]

        # Recent users (renters)
        context['recent_users'] = CustomUser.objects.filter(
            role='PUBLIC'
        ).order_by('-date_joined')[:10]

        # Pending agent applications
        context['pending_agent_applications'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='PENDING'
        ).order_by('date_joined')[:10]

        # Reports by category (for summary chart)
        context['reports_by_category'] = Report.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')

        return context

    def _get_recent_activity(self):
        """Build a unified recent activity feed from multiple sources."""
        activities = []

        # Recent properties
        for prop in Property.objects.select_related('created_by').order_by('-created_at')[:8]:
            activities.append({
                'type': 'property',
                'icon': 'home',
                'color': 'primary',
                'title': f'Property "{prop.title}" submitted',
                'user': prop.created_by.full_name_or_username if prop.created_by else 'Unknown',
                'timestamp': prop.created_at,
                'status': prop.status,
                'url': None,
            })

        # Recent agent registrations
        for agent in CustomUser.objects.filter(role='MINOR_ADMIN').order_by('-date_joined')[:8]:
            activities.append({
                'type': 'agent',
                'icon': 'user',
                'color': 'warning',
                'title': f'Agent application from {agent.full_name_or_username}',
                'user': agent.full_name_or_username,
                'timestamp': agent.date_joined,
                'status': agent.agent_status,
                'url': None,
            })

        # Recent inspections
        for insp in InspectionRequest.objects.select_related('renter', 'property').order_by('-created_at')[:8]:
            activities.append({
                'type': 'inspection',
                'icon': 'clipboard-check',
                'color': 'info',
                'title': f'Inspection request for "{insp.property.title}"',
                'user': insp.renter.full_name_or_username,
                'timestamp': insp.created_at,
                'status': insp.status,
                'url': None,
            })

        # Recent reports
        for report in Report.objects.select_related('reporter').order_by('-created_at')[:8]:
            activities.append({
                'type': 'report',
                'icon': 'flag',
                'color': 'danger',
                'title': f'Report: {report.get_category_display()}',
                'user': report.reporter.full_name_or_username,
                'timestamp': report.created_at,
                'status': report.status,
                'url': None,
            })

        # Sort by timestamp descending and return top 15
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:15]


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
# INSPECTION MANAGEMENT VIEWS
# ============================================================================

class InspectionListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin view of all inspection requests."""
    model = InspectionRequest
    template_name = 'dashboard/inspections_list.html'
    context_object_name = 'inspections'
    paginate_by = 20

    def get_queryset(self):
        queryset = InspectionRequest.objects.select_related(
            'property', 'renter', 'agent'
        ).order_by('-created_at')

        status = self.request.GET.get('status')
        if status and status in InspectionRequest.Status.values:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_counts'] = {
            'PENDING': InspectionRequest.objects.filter(status=InspectionRequest.Status.PENDING).count(),
            'ACCEPTED': InspectionRequest.objects.filter(status=InspectionRequest.Status.ACCEPTED).count(),
            'DECLINED': InspectionRequest.objects.filter(status=InspectionRequest.Status.DECLINED).count(),
            'CANCELLED': InspectionRequest.objects.filter(status=InspectionRequest.Status.CANCELLED).count(),
            'COMPLETED': InspectionRequest.objects.filter(status=InspectionRequest.Status.COMPLETED).count(),
            'total': InspectionRequest.objects.count(),
        }
        context['current_status'] = self.request.GET.get('status', '')
        context['status_choices'] = InspectionRequest.Status.choices
        return context


class InspectionDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Admin view of a single inspection request."""
    model = InspectionRequest
    template_name = 'dashboard/inspection_detail.html'
    context_object_name = 'inspection'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return InspectionRequest.objects.select_related(
            'property', 'renter', 'agent'
        )


# ============================================================================
# REPORT MANAGEMENT VIEWS
# ============================================================================

class ReportsListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin view of all user-submitted reports."""
    template_name = 'dashboard/reports_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
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
        context = super().get_context_data(**kwargs)
        context['status_counts'] = {
            'pending': Report.objects.filter(status=Report.Status.PENDING).count(),
            'under_review': Report.objects.filter(status=Report.Status.UNDER_REVIEW).count(),
            'resolved': Report.objects.filter(status=Report.Status.RESOLVED).count(),
            'dismissed': Report.objects.filter(status=Report.Status.DISMISSED).count(),
            'total': Report.objects.count(),
        }
        context['category_counts'] = Report.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class ReportDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Admin view of a single report."""
    template_name = 'dashboard/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return Report.objects.select_related(
            'reporter', 'property', 'agent', 'resolved_by'
        )


@login_required
@admin_required
def resolve_report(request, pk):
    """Admin resolves or dismisses a report."""
    report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        from reports.forms import ReportResolutionForm
        form = ReportResolutionForm(request.POST)
        if form.is_valid():
            report.status = form.cleaned_data['status']
            report.admin_notes = form.cleaned_data['admin_notes']
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.save(update_fields=['status', 'admin_notes', 'resolved_by', 'resolved_at'])

            messages.success(request, f'Report #{report.pk} has been marked as {report.get_status_display()}.')
            return redirect('dashboard:report_detail', pk=report.pk)

    return redirect('dashboard:report_detail', pk=report.pk)
