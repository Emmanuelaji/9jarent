from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages

from properties.models import Property
from accounts.models import CustomUser
from .models import Report
from .forms import ReportForm


@login_required
def report_property(request, property_id):
    """Submit a report for a specific property."""
    property_obj = get_object_or_404(Property, pk=property_id)

    # Prevent reporting own property
    if property_obj.created_by == request.user:
        messages.error(request, "You cannot report your own property.")
        return redirect('properties:detail', slug=property_obj.slug)

    # Prevent duplicate reports from same user on same property
    existing = Report.objects.filter(
        reporter=request.user,
        property=property_obj,
        status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW]
    ).first()
    if existing:
        messages.warning(request, "You have already submitted a report for this property. An administrator will review it shortly.")
        return redirect('properties:detail', slug=property_obj.slug)

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.property = property_obj
            report.agent = property_obj.created_by
            report.save()
            messages.success(request, "Thank you for your report. Our team will review it shortly.")
            return redirect('properties:detail', slug=property_obj.slug)
    else:
        form = ReportForm()

    return render(request, 'reports/report_form.html', {
        'form': form,
        'target': property_obj,
        'target_type': 'property',
    })


@login_required
def report_agent(request, agent_id):
    """Submit a report for a specific agent."""
    agent = get_object_or_404(CustomUser, pk=agent_id, role='MINOR_ADMIN')

    # Prevent self-reporting
    if agent == request.user:
        messages.error(request, "You cannot report yourself.")
        return redirect('accounts:agent_public_profile', username=agent.username)

    # Prevent duplicate reports
    existing = Report.objects.filter(
        reporter=request.user,
        agent=agent,
        status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW]
    ).first()
    if existing:
        messages.warning(request, "You have already submitted a report for this agent. An administrator will review it shortly.")
        return redirect('accounts:agent_public_profile', username=agent.username)

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.agent = agent
            report.save()
            messages.success(request, "Thank you for your report. Our team will review it shortly.")
            return redirect('accounts:agent_public_profile', username=agent.username)
    else:
        form = ReportForm()

    return render(request, 'reports/report_form.html', {
        'form': form,
        'target': agent,
        'target_type': 'agent',
    })
