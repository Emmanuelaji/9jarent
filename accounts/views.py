# accounts/views.py

from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView, DetailView, ListView
from django.db import models
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from .forms import AgentSignUpForm, RenterSignUpForm, ProfileCompletionForm, EmailOrPhoneAuthenticationForm
from .models import CustomUser


class RoleBasedLoginView(LoginView):
    """Login view that redirects users based on their role and status."""
    template_name = 'accounts/login.html'
    form_class = EmailOrPhoneAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.POST.get('remember'):
            # Session ends when the browser closes instead of the default 2-week cookie age.
            self.request.session.set_expiry(0)
        return response
    
    def get_success_url(self):
        user = self.request.user
        
        # Super admins go to admin dashboard
        if user.is_admin:
            return reverse_lazy('dashboard:admin')
        
        # Pending agents go to pending page
        if user.is_pending_agent:
            return reverse_lazy('accounts:pending')
        
        # Rejected agents go to pending page (shows rejection reason)
        if user.is_rejected_agent:
            return reverse_lazy('accounts:pending')
        
        # Suspended agents go to pending page (shows suspension message)
        if user.is_suspended_agent:
            return reverse_lazy('accounts:pending')
        
        # Approved agents go to their dashboard
        if user.is_approved_agent:
            return reverse_lazy('properties:mine')
        
        # Public users go to homepage
        return reverse_lazy('properties:home')


class AgentSignUpView(CreateView):
    """
    Agent registration view.
    Creates a PENDING agent account.
    Does NOT auto-login with full privileges.
    """
    form_class = AgentSignUpForm
    template_name = 'accounts/signup.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Prevent already-authenticated users from signing up again
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # CRITICAL: Do NOT auto-login with full agent privileges
        # Instead, show pending message
        messages.success(
            self.request, 
            "Your agent application has been submitted and is awaiting administrator approval. "
            "You will be notified once your application is reviewed."
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('accounts:pending')


class AccountTypeChoiceView(TemplateView):
    """Landing page for 'Sign Up Free' - lets a new user pick renter vs agent."""
    template_name = 'accounts/choose_account_type.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)


class RenterSignUpView(CreateView):
    """
    Renter/public user registration view.
    Renters have no approval workflow - they can browse and use the
    platform (favourites, messaging, inspections) immediately.
    """
    form_class = RenterSignUpForm
    template_name = 'accounts/renter_signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.backend = 'accounts.backends.EmailOrPhoneBackend'
        login(self.request, self.object)
        messages.success(self.request, "Welcome to 9jaRent! Your account has been created.")
        return response

    def get_success_url(self):
        return reverse_lazy('properties:home')


class AgentPendingView(TemplateView):
    """
    Page shown to pending/rejected/suspended agents.
    Displays status and any rejection/suspension reasons.
    """
    template_name = 'accounts/pending.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Allow anonymous users who just signed up (via session)
        # Or authenticated users who are agents
        if request.user.is_authenticated and not request.user.is_agent:
            messages.info(request, "This page is for agent applicants only.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)


class CompleteProfileView(LoginRequiredMixin, UpdateView):
    """View for agents to complete/update their profile."""
    form_class = ProfileCompletionForm
    template_name = 'accounts/complete_profile.html'
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def dispatch(self, request, *args, **kwargs):
        # Only agents can complete this profile
        if not request.user.is_agent:
            messages.error(request, "Only agents can access this page.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        # Redirect based on status
        user = self.request.user
        if user.is_pending_agent:
            return reverse_lazy('accounts:pending')
        if user.is_rejected_agent:
            return reverse_lazy('accounts:pending')
        if user.is_suspended_agent:
            return reverse_lazy('accounts:pending')
        return reverse_lazy('properties:mine')
    
    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


class AgentProfileEditView(LoginRequiredMixin, UpdateView):
    """Ongoing 'Agent Profile' page in the portal sidebar (Settings-style), as
    opposed to CompleteProfileView's one-time post-signup onboarding screen.
    Same form/model - just a different template/URL for after onboarding."""
    form_class = ProfileCompletionForm
    template_name = 'accounts/profile_edit.html'

    def get_object(self, queryset=None):
        return self.request.user

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_agent:
            messages.error(request, "Only agents can access this page.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('accounts:profile_edit')

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


class AgentsDirectoryView(ListView):
    """Public directory of verified/approved agents (Browse Properties > Agents)."""
    model = CustomUser
    template_name = 'accounts/agents_directory.html'
    context_object_name = 'agents'
    paginate_by = 12

    ALLOWED_SORTS = {
        'active': '-approved_at',
        'listings': '-property_count',
        'name': 'company_name',
    }

    def get_queryset(self):
        qs = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='APPROVED'
        ).annotate(
            property_count=models.Count('properties', filter=models.Q(properties__status='PUBLISHED'))
        )

        search = self.request.GET.get('search')
        state = self.request.GET.get('state')
        if search:
            qs = qs.filter(
                models.Q(company_name__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(city__icontains=search)
            )
        if state:
            qs = qs.filter(state=state)

        sort = self.request.GET.get('sort', 'active')
        order_by = self.ALLOWED_SORTS.get(sort, self.ALLOWED_SORTS['active'])
        return qs.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['states'] = CustomUser.objects.filter(
            role='MINOR_ADMIN', agent_status='APPROVED'
        ).exclude(state__isnull=True).exclude(state='').values_list('state', flat=True).distinct().order_by('state')
        return context


class AgentPublicProfileView(DetailView):
    """Public profile page for an approved agent."""
    model = CustomUser
    template_name = 'accounts/agent_public_profile.html'
    context_object_name = 'agent'
    slug_url_kwarg = 'username'
    slug_field = 'username'

    def get_queryset(self):
        # Only show approved agents publicly
        return CustomUser.objects.filter(
            role='MINOR_ADMIN',
            agent_status='APPROVED'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent = self.object
        # Only show published properties
        context['agent_properties'] = agent.properties.filter(
            status='PUBLISHED'
        ).select_related('state', 'lga').order_by('-created_at')
        context['property_count'] = context['agent_properties'].count()
        context['total_views'] = (
            agent.properties.filter(status='PUBLISHED')
            .aggregate(total_views=models.Sum('views'))['total_views'] or 0
        )
        return context


class SignUpSuccessView(TemplateView):
    """Registration success page shown after renter signup."""
    template_name = 'accounts/signup_success.html'