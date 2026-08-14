# dashboard/context_processors.py

from django.db.models import Count, Q
from properties.models import Property
from inspections.models import InspectionRequest
from reports.models import Report
from accounts.models import CustomUser


def admin_sidebar_counts(request):
    """Add sidebar badge counts for admin navigation."""
    if not request.user.is_authenticated or not request.user.is_admin:
        return {}

    return {
        'pending_agents_count': CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='PENDING'
        ).count(),
        'pending_properties_count': Property.objects.filter(
            status='PENDING_REVIEW'
        ).count(),
        'pending_inspections_count': InspectionRequest.objects.filter(
            status=InspectionRequest.Status.PENDING
        ).count(),
        'pending_reports_count': Report.objects.filter(
            status=Report.Status.PENDING
        ).count(),
    }
