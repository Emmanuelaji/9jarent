from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from urllib.parse import quote
from django.conf import settings
from .models import Property, State, LGA, PropertyImage
from .forms import PropertyForm

def get_whatsapp_link(agent_whatsapp, property_title, location):
    number = agent_whatsapp.replace('+', '').strip()
    message = settings.WHATSAPP_DEFAULT_MESSAGE.format(title=property_title, location=location)
    return f"https://wa.me/{number}?text={quote(message)}"

class PropertyListView(ListView):
    model = Property
    template_name = 'properties/list.html'
    context_object_name = 'properties'
    paginate_by = 12

    def get_queryset(self):
        queryset = Property.objects.filter(status='PUBLISHED').select_related('state', 'lga')
        search = self.request.GET.get('search')
        state = self.request.GET.get('state')
        lga = self.request.GET.get('lga')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        property_type = self.request.GET.get('property_type')
        bedrooms = self.request.GET.get('bedrooms')
        sort = self.request.GET.get('sort', '-created_at')

        if search: queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(area__icontains=search))
        if state: queryset = queryset.filter(state_id=state)
        if lga: queryset = queryset.filter(lga_id=lga)
        if min_price: queryset = queryset.filter(price__gte=min_price)
        if max_price: queryset = queryset.filter(price__lte=max_price)
        if property_type: queryset = queryset.filter(property_type=property_type)
        if bedrooms: queryset = queryset.filter(bedrooms__gte=bedrooms)
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = State.objects.all()
        return context

class PropertyDetailView(DetailView):
    model = Property
    template_name = 'properties/detail.html'
    context_object_name = 'property'

    def get_object(self):
        obj = super().get_object()
        obj.views += 1
        obj.save(update_fields=['views'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['whatsapp_link'] = get_whatsapp_link(self.object.agent_whatsapp, self.object.title, f"{self.object.area}, {self.object.state.name}")
        context['similar_properties'] = Property.objects.filter(state=self.object.state, status='PUBLISHED').exclude(id=self.object.id)[:4]
        return context

class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = 'properties/create.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = 'PENDING_REVIEW'
        response = super().form_valid(form)

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

class MyListingsView(LoginRequiredMixin, ListView):
    model = Property
    template_name = 'properties/mine.html'
    context_object_name = 'my_properties'
    paginate_by = 20

    def get_queryset(self):
        return Property.objects.filter(created_by=self.request.user).select_related('state', 'lga').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_count'] = qs.count()
        context['published_count'] = qs.filter(status='PUBLISHED').count()
        context['pending_count'] = qs.filter(status='PENDING_REVIEW').count()
        context['rejected_count'] = qs.filter(status='REJECTED').count()
        context['total_views'] = sum(p.views for p in qs)
        context['total_whatsapp_clicks'] = sum(p.whatsapp_clicks for p in qs)
        return context
