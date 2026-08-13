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

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user, is_read=False
        ).count()
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
