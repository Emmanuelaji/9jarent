
# properties/views.py with proper permission enforcement

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from urllib.parse import quote
from django.conf import settings
from django.urls import reverse_lazy

from accounts.permissions import ApprovedAgentRequiredMixin, object_owner_required, admin_required
from .models import Property, State, LGA, PropertyImage
from .forms import PropertyForm


def get_whatsapp_link(agent_whatsapp, property_title, location):
    """Generate a safe WhatsApp click-to-chat link."""
    number = agent_whatsapp.replace('+', '').strip()
    message = settings.WHATSAPP_DEFAULT_MESSAGE.format(title=property_title, location=location)
    return f"https://wa.me/{number}?text={quote(message)}"


# ============================================================================
# PUBLIC VIEWS
# ============================================================================

class PropertyListView(ListView):
    """Public property listing with search and filters."""
    model = Property
    template_name = 'properties/list.html'
    context_object_name = 'properties'
    paginate_by = 12

    def get_queryset(self):
        queryset = Property.objects.filter(status='PUBLISHED').select_related('state', 'lga', 'created_by')
        
        search = self.request.GET.get('search')
        state = self.request.GET.get('state')
        lga = self.request.GET.get('lga')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        property_type = self.request.GET.get('property_type')
        bedrooms = self.request.GET.get('bedrooms')
        sort = self.request.GET.get('sort', '-created_at')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(area__icontains=search)
            )
        if state:
            queryset = queryset.filter(state_id=state)
        if lga:
            queryset = queryset.filter(lga_id=lga)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if property_type:
            queryset = queryset.filter(property_type=property_type)
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=bedrooms)
        
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = State.objects.all()
        context['property_types'] = Property.PROPERTY_TYPES
        return context


class PropertyDetailView(DetailView):
    """Public property detail page."""
    model = Property
    template_name = 'properties/detail.html'
    context_object_name = 'property'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Only show published properties publicly
        return Property.objects.filter(status='PUBLISHED').select_related('state', 'lga', 'created_by')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view counter
        obj.views += 1
        obj.save(update_fields=['views'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property_obj = self.object
        
        # Use agent's profile WhatsApp if available, fallback to property field
        whatsapp_number = property_obj.created_by.whatsapp_number if property_obj.created_by else property_obj.agent_whatsapp
        context['whatsapp_link'] = get_whatsapp_link(
            whatsapp_number or property_obj.agent_whatsapp,
            property_obj.title,
            f"{property_obj.area}, {property_obj.state.name}"
        )
        
        # Similar properties
        context['similar_properties'] = Property.objects.filter(
            state=property_obj.state, 
            status='PUBLISHED'
        ).exclude(id=property_obj.id).select_related('state', 'lga')[:4]
        
        # Agent verification status
        if property_obj.created_by and property_obj.created_by.is_approved_agent:
            context['agent_verified'] = True
        else:
            context['agent_verified'] = False
            
        return context


# ============================================================================
# AGENT VIEWS (Require APPROVED agent)
# ============================================================================

class PropertyCreateView(LoginRequiredMixin, ApprovedAgentRequiredMixin, CreateView):
    """
    Create a new property listing.
    ONLY approved agents can access this.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/create.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = 'PENDING_REVIEW'
        
        # Use agent's profile data instead of form fields where appropriate
        user = self.request.user
        if not form.instance.agent_name:
            form.instance.agent_name = user.full_name_or_username
        if not form.instance.agent_whatsapp:
            form.instance.agent_whatsapp = user.whatsapp_number or ''
        if not form.instance.agent_email:
            form.instance.agent_email = user.email
            
        response = super().form_valid(form)

        # Handle image uploads
        images = self.request.FILES.getlist('images')
        for index, image_file in enumerate(images):
            PropertyImage.objects.create(
                property=self.object,
                image=image_file,
                is_primary=(index == 0),
                order_index=index,
            )

        messages.success(self.request, "Property submitted successfully! Pending admin approval.")
        return response
    
    def get_success_url(self):
        return reverse_lazy('properties:mine')


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing property.
    Only the owner agent or admin can edit.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/edit.html'
    pk_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Server-side ownership check
        if obj.created_by != request.user and not request.user.is_admin:
            messages.error(request, "You do not have permission to edit this property.")
            raise PermissionDenied("You can only edit your own properties.")
        # Only allow editing if not RENTED or ARCHIVED (unless admin)
        if obj.status in ['RENTED', 'ARCHIVED'] and not request.user.is_admin:
            messages.error(request, "Rented or archived properties cannot be edited.")
            return redirect('properties:mine')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('properties:mine')
    
    def form_valid(self, form):
        messages.success(self.request, "Property updated successfully.")
        return super().form_valid(form)


class MyListingsView(LoginRequiredMixin, ListView):
    """Agent's own property listings dashboard."""
    model = Property
    template_name = 'properties/mine.html'
    context_object_name = 'my_properties'
    paginate_by = 20

    def get_queryset(self):
        return Property.objects.filter(
            created_by=self.request.user
        ).select_related('state', 'lga').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Agent status messaging
        context['agent_status'] = user.agent_status
        context['agent_status_display'] = user.get_agent_status_display() if user.is_agent else None
        context['rejection_reason'] = user.rejection_reason if user.is_rejected_agent else None
        
        # Statistics - use efficient aggregation
        qs = self.get_queryset()
        context['total_count'] = qs.count()
        context['published_count'] = qs.filter(status='PUBLISHED').count()
        context['pending_count'] = qs.filter(status='PENDING_REVIEW').count()
        context['rejected_count'] = qs.filter(status='REJECTED').count()
        context['rented_count'] = qs.filter(status='RENTED').count()
        context['archived_count'] = qs.filter(status='ARCHIVED').count()
        
        # Use database aggregation instead of Python sum
        from django.db.models import Sum
        stats = qs.aggregate(
            total_views=Sum('views'),
            total_whatsapp=Sum('whatsapp_clicks')
        )
        context['total_views'] = stats['total_views'] or 0
        context['total_whatsapp_clicks'] = stats['total_whatsapp'] or 0
        
        return context


# ============================================================================
# PROPERTY STATUS ACTIONS (POST only)
# ============================================================================

@login_required 
@object_owner_required(Property, 'created_by')
def submit_property(request, pk):
    """Submit a draft property for admin review."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    
    prop = get_object_or_404(Property, pk=pk, created_by=request.user)
    if prop.status == 'DRAFT':
        prop.status = 'PENDING_REVIEW'
        prop.save(update_fields=['status', 'updated_at'])
        messages.success(request, "Property submitted for review.")
    else:
        messages.warning(request, "Only draft properties can be submitted.")
    return redirect('properties:mine')


@login_required 
@object_owner_required(Property, 'created_by')
def resubmit_property(request, pk):
    """Resubmit a rejected property after edits."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    
    prop = get_object_or_404(Property, pk=pk, created_by=request.user)
    if prop.status == 'REJECTED':
        prop.status = 'PENDING_REVIEW'
        prop.rejection_reason = ''
        prop.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        messages.success(request, "Property resubmitted for review.")
    else:
        messages.warning(request, "Only rejected properties can be resubmitted.")
    return redirect('properties:mine')


@login_required 
@object_owner_required(Property, 'created_by')
def mark_property_rented(request, pk):
    """Mark a published property as rented."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    
    prop = get_object_or_404(Property, pk=pk, created_by=request.user)
    if prop.status == 'PUBLISHED':
        prop.status = 'RENTED'
        prop.save(update_fields=['status', 'updated_at'])
        messages.success(request, "Property marked as rented.")
    else:
        messages.warning(request, "Only published properties can be marked as rented.")
    return redirect('properties:mine')


@login_required 
@object_owner_required(Property, 'created_by')
def archive_property(request, pk):
    """Archive a property (removes from public view but keeps record)."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")
    
    prop = get_object_or_404(Property, pk=pk, created_by=request.user)
    if prop.status in ['PUBLISHED', 'REJECTED', 'RENTED']:
        prop.status = 'ARCHIVED'
        prop.save(update_fields=['status', 'updated_at'])
        messages.success(request, "Property archived.")
    else:
        messages.warning(request, "This property cannot be archived.")
    return redirect('properties:mine')
