# inspections/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from properties.models import Property
from .forms import InspectionRequestForm
from .models import InspectionRequest


def _can_access(user, inspection):
    return (
        inspection.renter_id == user.id
        or inspection.agent_id == user.id
        or user.is_admin
    )


@login_required
def my_inspections(request):
    """
    Renters see the inspections they've requested; agents see requests
    made against their own properties. Filterable by status tab.
    """
    user = request.user
    status_filter = request.GET.get('status', 'ALL')

    if user.is_agent:
        qs = InspectionRequest.objects.filter(agent=user)
    else:
        qs = InspectionRequest.objects.filter(renter=user)

    qs = qs.select_related('property', 'renter', 'agent')
    total_count = qs.count()

    if status_filter != 'ALL' and status_filter in InspectionRequest.Status.values:
        qs = qs.filter(status=status_filter)

    return render(request, 'inspections/list.html', {
        'inspections': qs,
        'status_filter': status_filter,
        'statuses': InspectionRequest.Status.choices,
        'total_count': total_count,
    })


@login_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(
        InspectionRequest.objects.select_related('property', 'renter', 'agent'), pk=pk
    )
    if not _can_access(request.user, inspection):
        raise PermissionDenied("You do not have permission to view this inspection request.")
    return render(request, 'inspections/detail.html', {'inspection': inspection})


@login_required
def request_inspection(request, property_id):
    property_obj = get_object_or_404(Property, pk=property_id, status='PUBLISHED')
    user = request.user

    if user.is_admin:
        messages.error(request, "Admin accounts cannot request inspections.")
        return redirect('properties:detail', slug=property_obj.slug)

    if property_obj.created_by_id == user.id:
        messages.error(request, "You cannot request an inspection on your own property.")
        return redirect('properties:detail', slug=property_obj.slug)

    existing_active = InspectionRequest.objects.filter(
        property=property_obj, renter=user, status__in=InspectionRequest.ACTIVE_STATUSES
    ).first()
    if existing_active:
        messages.info(request, "You already have an active inspection request for this property.")
        return redirect('inspections:detail', pk=existing_active.pk)

    if request.method == 'POST':
        form = InspectionRequestForm(request.POST)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.property = property_obj
            inspection.renter = user
            inspection.agent = property_obj.created_by
            inspection.save()
            messages.success(request, "Your inspection request has been sent to the agent.")
            return redirect('inspections:detail', pk=inspection.pk)
    else:
        form = InspectionRequestForm()

    return render(request, 'inspections/request_form.html', {'form': form, 'property': property_obj})


@login_required
def accept_inspection(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    inspection = get_object_or_404(InspectionRequest, pk=pk, agent=request.user)
    if inspection.status != InspectionRequest.Status.PENDING:
        messages.error(request, "Only pending requests can be accepted.")
        return redirect('inspections:detail', pk=inspection.pk)

    inspection.agent_response = request.POST.get('agent_response', '').strip()
    inspection.status = InspectionRequest.Status.ACCEPTED
    inspection.save(update_fields=['status', 'agent_response', 'updated_at'])
    messages.success(request, "Inspection request accepted.")
    return redirect('inspections:detail', pk=inspection.pk)


@login_required
def decline_inspection(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    inspection = get_object_or_404(InspectionRequest, pk=pk, agent=request.user)
    if inspection.status != InspectionRequest.Status.PENDING:
        messages.error(request, "Only pending requests can be declined.")
        return redirect('inspections:detail', pk=inspection.pk)

    inspection.agent_response = request.POST.get('agent_response', '').strip()
    inspection.status = InspectionRequest.Status.DECLINED
    inspection.save(update_fields=['status', 'agent_response', 'updated_at'])
    messages.success(request, "Inspection request declined.")
    return redirect('inspections:detail', pk=inspection.pk)


@login_required
def complete_inspection(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    inspection = get_object_or_404(InspectionRequest, pk=pk, agent=request.user)
    if inspection.status != InspectionRequest.Status.ACCEPTED:
        messages.error(request, "Only accepted requests can be marked completed.")
        return redirect('inspections:detail', pk=inspection.pk)

    inspection.status = InspectionRequest.Status.COMPLETED
    inspection.save(update_fields=['status', 'updated_at'])
    messages.success(request, "Inspection marked as completed.")
    return redirect('inspections:detail', pk=inspection.pk)


@login_required
def cancel_inspection(request, pk):
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    inspection = get_object_or_404(InspectionRequest, pk=pk, renter=request.user)
    if inspection.status not in InspectionRequest.ACTIVE_STATUSES:
        messages.error(request, "Only pending or accepted requests can be cancelled.")
        return redirect('inspections:detail', pk=inspection.pk)

    inspection.status = InspectionRequest.Status.CANCELLED
    inspection.save(update_fields=['status', 'updated_at'])
    messages.success(request, "Inspection request cancelled.")
    return redirect('inspections:detail', pk=inspection.pk)