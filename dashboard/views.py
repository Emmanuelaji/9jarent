from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from properties.models import Property

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Property
    template_name = 'dashboard/admin.html'
    context_object_name = 'pending_properties'

    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'role', '') == 'SUPER_ADMIN'

    def get_queryset(self):
        return Property.objects.filter(status='PENDING_REVIEW').select_related('created_by', 'state', 'lga')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_listings'] = Property.objects.count()
        context['published_listings'] = Property.objects.filter(status='PUBLISHED').count()
        return context

def approve_property(request, pk):
    if request.user.is_staff or getattr(request.user, 'role', '') == 'SUPER_ADMIN':
        prop = get_object_or_404(Property, pk=pk)
        prop.status = 'PUBLISHED'
        prop.approved_by = request.user
        prop.published_at = timezone.now()
        prop.save()
        messages.success(request, "Property approved and published.")
    return redirect('dashboard:admin')

def reject_property(request, pk):
    if request.user.is_staff or getattr(request.user, 'role', '') == 'SUPER_ADMIN':
        prop = get_object_or_404(Property, pk=pk)
        prop.status = 'REJECTED'
        prop.rejection_reason = request.POST.get('reason', 'No reason provided')
        prop.save()
        messages.warning(request, "Property rejected.")
    return redirect('dashboard:admin')
