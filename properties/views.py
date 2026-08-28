# properties/views.py with proper permission enforcement and DRAFT support

from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from urllib.parse import quote
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.urls import reverse_lazy

from accounts.permissions import ApprovedAgentRequiredMixin, AgentRequiredMixin, object_owner_required
from .models import Property, State, PropertyImage
from .forms import PropertyForm


def get_whatsapp_link(agent_whatsapp, property_title, location):
    """Generate a safe WhatsApp click-to-chat link."""
    number = agent_whatsapp.replace('+', '').strip()
    message = settings.WHATSAPP_DEFAULT_MESSAGE.format(title=property_title, location=location)
    return f"https://wa.me/{number}?text={quote(message)}"


def _get_favourited_ids(user, properties):
    """Return the set of property IDs (from the given iterable) the user has favourited."""
    if not user.is_authenticated:
        return set()
    from favourites.models import Favourite
    property_ids = [p.id for p in properties]
    if not property_ids:
        return set()
    return set(
        Favourite.objects.filter(user=user, property_id__in=property_ids).values_list('property_id', flat=True)
    )


# ============================================================================
# PUBLIC VIEWS
# ============================================================================

class PropertyListView(ListView):
    """Public property listing with search and filters. ONLY PUBLISHED properties."""
    model = Property
    template_name = 'properties/list.html'
    context_object_name = 'properties'
    paginate_by = 12

    # Explicit whitelist - never pass a raw `?sort=` query value into .order_by()
    ALLOWED_SORTS = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price_low': 'price',
        'price_high': '-price',
    }

    def get_queryset(self):
        queryset = Property.objects.filter(status='PUBLISHED').select_related('state', 'lga', 'created_by')

        search = self.request.GET.get('search')
        state = self.request.GET.get('state')
        lga = self.request.GET.get('lga')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        property_type = self.request.GET.get('property_type')
        bedrooms = self.request.GET.get('bedrooms')
        sort = self.request.GET.get('sort', 'newest')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) | 
                Q(area__icontains=search)
            )
        if state and state.isdigit():
            queryset = queryset.filter(state_id=state)
        if lga and lga.isdigit():
            queryset = queryset.filter(lga_id=lga)
        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (InvalidOperation, ValueError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (InvalidOperation, ValueError):
                pass
        if property_type:
            queryset = queryset.filter(property_type=property_type)
        if bedrooms and bedrooms.isdigit():
            queryset = queryset.filter(bedrooms__gte=int(bedrooms))

        order_by = self.ALLOWED_SORTS.get(sort, self.ALLOWED_SORTS['newest'])
        return queryset.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = State.objects.all()
        context['property_types'] = Property.PROPERTY_TYPES
        context['favourited_ids'] = _get_favourited_ids(self.request.user, context['properties'])
        return context


class PropertyDetailView(DetailView):
    """Public property detail page. ONLY PUBLISHED properties."""
    model = Property
    template_name = 'properties/detail.html'
    context_object_name = 'property'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Only show published properties publicly
        return Property.objects.filter(status='PUBLISHED').select_related('state', 'lga', 'created_by')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Atomic DB-side increment - a Python `obj.views += 1; obj.save()` here
        # would race under concurrent requests and lose increments.
        Property.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        obj.refresh_from_db(fields=['views'])
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

        context['is_favourited'] = property_obj.id in _get_favourited_ids(self.request.user, [property_obj])

        return context


# ============================================================================
# AGENT VIEWS (Require APPROVED agent)
# ============================================================================

class PropertyCreateView(LoginRequiredMixin, ApprovedAgentRequiredMixin, CreateView):
    """
    Create a new property listing.
    ONLY approved agents can access this.
    Supports "Save as Draft" and "Submit for Review".
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/create.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # Check if user clicked "Save as Draft" or "Submit for Review"
        action = self.request.POST.get('action', 'submit')
        if action == 'draft':
            form.instance.status = 'DRAFT'
            messages.success(self.request, "Property saved as draft.")
        else:
            form.instance.status = 'PENDING_REVIEW'
            messages.success(self.request, "Property submitted successfully! Pending admin approval.")

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

        return response

    def get_success_url(self):
        return reverse_lazy('properties:mine')


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing property.
    Only the owner agent or admin can edit.
    Supports "Save as Draft" for DRAFT properties.
    """
    model = Property
    form_class = PropertyForm
    template_name = 'properties/edit.html'
    pk_url_kwarg = 'pk'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('properties:mine')

    def form_valid(self, form):
        # Check if user clicked "Save as Draft" or "Submit for Review"
        action = self.request.POST.get('action', 'save')
        obj = self.object

        if action == 'draft':
            # Keep as draft or revert to draft
            form.instance.status = 'DRAFT'
            messages.success(self.request, "Property saved as draft.")
        elif action == 'submit' and obj.status == 'DRAFT':
            form.instance.status = 'PENDING_REVIEW'
            messages.success(self.request, "Property submitted for review.")
        elif action == 'resubmit' and obj.status == 'REJECTED':
            form.instance.status = 'PENDING_REVIEW'
            form.instance.rejection_reason = ''
            messages.success(self.request, "Property resubmitted for review.")
        else:
            messages.success(self.request, "Property updated successfully.")

        response = super().form_valid(form)

        # Append any newly uploaded images
        images = self.request.FILES.getlist('images')
        if images:
            existing_count = self.object.images.count()
            for index, image_file in enumerate(images):
                PropertyImage.objects.create(
                    property=self.object,
                    image=image_file,
                    is_primary=(existing_count == 0 and index == 0),
                    order_index=existing_count + index,
                )

        return response


class AgentDashboardView(LoginRequiredMixin, AgentRequiredMixin, ListView):
    """Agent portal home: stat cards + a preview of recent listings."""
    model = Property
    template_name = 'properties/agent_dashboard.html'
    context_object_name = 'recent_properties'
    paginate_by = None

    def get_queryset(self):
        return Property.objects.filter(
            created_by=self.request.user
        ).select_related('state', 'lga').prefetch_related('images').order_by('-created_at')[:5]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['agent_status'] = user.agent_status
        context['rejection_reason'] = user.rejection_reason if user.is_rejected_agent else None

        qs = Property.objects.filter(created_by=user)
        context['total_count'] = qs.count()
        context['published_count'] = qs.filter(status='PUBLISHED').count()
        context['pending_count'] = qs.filter(status='PENDING_REVIEW').count()
        context['rejected_count'] = qs.filter(status='REJECTED').count()
        context['rented_count'] = qs.filter(status='RENTED').count()

        from inspections.models import InspectionRequest
        context['inspection_requests_count'] = InspectionRequest.objects.filter(agent=user).count()

        return context


class MyListingsView(LoginRequiredMixin, AgentRequiredMixin, ListView):
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
        context['draft_count'] = qs.filter(status='DRAFT').count()

        # Use database aggregation instead of Python sum
        stats = qs.aggregate(
            total_views=Sum('views'),
            total_whatsapp=Sum('whatsapp_clicks')
        )
        context['total_views'] = stats['total_views'] or 0
        context['total_whatsapp_clicks'] = stats['total_whatsapp'] or 0

        return context


class DraftListView(LoginRequiredMixin, AgentRequiredMixin, ListView):
    """Agent's draft properties."""
    model = Property
    template_name = 'properties/drafts.html'
    context_object_name = 'drafts'
    paginate_by = 20

    def get_queryset(self):
        return Property.objects.filter(
            created_by=self.request.user,
            status='DRAFT'
        ).select_related('state', 'lga').order_by('-updated_at')


# ============================================================================
# PROPERTY STATUS ACTIONS (POST only)
# ============================================================================

@login_required 
@object_owner_required(Property, 'created_by')
def submit_property(request, pk):
    """Submit a DRAFT property for admin review."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")

    prop = get_object_or_404(Property, pk=pk, created_by=request.user)
    if prop.status == 'DRAFT':
        prop.status = 'PENDING_REVIEW'
        prop.save(update_fields=['status', 'updated_at'])
        messages.success(request, "Property submitted for review.")
    else:
        messages.warning(request, "Only draft properties can be submitted for review.")
    return redirect('properties:mine')


@login_required 
@object_owner_required(Property, 'created_by')
def resubmit_property(request, pk):
    """Resubmit a REJECTED property after edits."""
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
    """Mark a PUBLISHED property as rented."""
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
def delete_property_image(request, pk, image_id):
    """Delete one image from a property. Owner or admin only, POST only."""
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")

    prop = get_object_or_404(Property, pk=pk)
    if prop.created_by != request.user and not request.user.is_admin:
        raise PermissionDenied("You do not have permission to modify this property's images.")

    image = get_object_or_404(PropertyImage, pk=image_id, property=prop)
    was_primary = image.is_primary
    image.delete()

    # Promote the next remaining image to primary if we just removed the primary one
    if was_primary:
        next_image = prop.images.order_by('order_index', 'uploaded_at').first()
        if next_image:
            next_image.is_primary = True
            next_image.save(update_fields=['is_primary'])

    messages.success(request, "Image removed.")
    return redirect('properties:edit', pk=prop.pk)


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