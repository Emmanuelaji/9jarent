from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView
from django.views.decorators.http import require_POST

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """User's notification inbox."""
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    CATEGORY_TYPES = {
        'messages': [Notification.Type.NEW_MESSAGE],
        'inspections': [
            Notification.Type.INSPECTION_REQUEST, Notification.Type.INSPECTION_ACCEPTED,
            Notification.Type.INSPECTION_DECLINED, Notification.Type.INSPECTION_COMPLETED,
        ],
        'properties': [
            Notification.Type.PROPERTY_APPROVED, Notification.Type.PROPERTY_REJECTED,
            Notification.Type.PROPERTY_PUBLISHED,
        ],
        'agents': [
            Notification.Type.AGENT_APPROVED, Notification.Type.AGENT_REJECTED, Notification.Type.AGENT_SUSPENDED,
        ],
        'reports': [Notification.Type.REPORT_SUBMITTED, Notification.Type.REPORT_RESOLVED],
        'system': [Notification.Type.SYSTEM],
    }

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        category = self.request.GET.get('category', 'all')
        if category == 'unread':
            qs = qs.filter(is_read=False)
        elif category in self.CATEGORY_TYPES:
            qs = qs.filter(notification_type__in=self.CATEGORY_TYPES[category])
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = Notification.objects.filter(user=self.request.user)
        context['unread_count'] = base_qs.filter(is_read=False).count()
        context['total_count'] = base_qs.count()
        context['category'] = self.request.GET.get('category', 'all')
        context['category_counts'] = {
            name: base_qs.filter(notification_type__in=types).count()
            for name, types in self.CATEGORY_TYPES.items()
        }
        return context


@login_required
@require_POST
def mark_notification_read(request, pk):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_read()
    return JsonResponse({'status': 'ok', 'unread_count': _unread_count(request.user)})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True
    )
    return JsonResponse({'status': 'ok', 'unread_count': 0})


@login_required
def notification_redirect(request, pk):
    """Mark notification read and redirect to its link."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_read()
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


def _unread_count(user):
    """Helper to get unread count."""
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, is_read=False).count()