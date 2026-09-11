# accounts/views.py

from datetime import datetime, timedelta

from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView, DetailView, ListView, FormView
from django.db import models
from django.shortcuts import redirect
from django.utils import timezone
from .forms import (
    AgentSignUpStep1Form, OTPVerifyForm, AgentSignUpStep3Form,
    RenterSignUpForm, ProfileCompletionForm, EmailOrPhoneAuthenticationForm, DomainAwarePasswordResetForm,
)
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


class AgentSignUpStep1View(CreateView):
    """
    Step 1 of agent signup: agency info + email.

    Creates the CustomUser row immediately (unusable password,
    email_verified=False) so an EmailOTP - which requires a real user FK -
    can be issued and emailed. The account isn't fully usable until step 3
    sets a real password; if the user abandons the flow here, they're left
    with an unusable-password, unverified account rather than nothing, which
    is an acceptable tradeoff for keeping the OTP model's existing schema
    (EmailOTP.user is a required FK) rather than inventing separate
    pre-account session storage for step 1's data.
    """
    form_class = AgentSignUpStep1Form
    template_name = 'accounts/signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('properties:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        from .emails import create_and_send_otp
        create_and_send_otp(self.object)
        # Rotate the session key before storing anything in it. If an
        # attacker fixated this anonymous session before the victim started
        # signup (session fixation), this makes sure the victim's signup
        # progress lives under a session ID the attacker never saw.
        self.request.session.cycle_key()
        self.request.session['agent_signup_user_id'] = self.object.pk
        return response

    def get_success_url(self):
        return reverse_lazy('accounts:agent_signup_verify')


class AgentSignUpVerifyView(FormView):
    """Step 2: verify the emailed OTP code."""
    form_class = OTPVerifyForm
    template_name = 'accounts/signup_verify.html'

    def _get_pending_user(self):
        user_id = self.request.session.get('agent_signup_user_id')
        if not user_id:
            return None
        return CustomUser.objects.filter(
            pk=user_id, role='MINOR_ADMIN', email_verified=False
        ).first()

    def dispatch(self, request, *args, **kwargs):
        self.pending_user = self._get_pending_user()
        if not self.pending_user:
            messages.info(request, "Let's start your agent registration.")
            return redirect('accounts:agent_signup')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_email'] = self.pending_user.email
        return context

    def form_valid(self, form):
        from .models import EmailOTP
        code = form.cleaned_data['code']
        otp = EmailOTP.objects.filter(
            user=self.pending_user, purpose=EmailOTP.Purpose.SIGNUP,
            code=code, is_used=False, expires_at__gt=timezone.now()
        ).first()
        if not otp:
            form.add_error('code', "That code is invalid or has expired. You can request a new one below.")
            return self.form_invalid(form)
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        self.pending_user.email_verified = True
        self.pending_user.save(update_fields=['email_verified'])
        # Stamp when verification happened - AgentSignUpSetupView uses this
        # to expire the "verified, awaiting password" window (see comment
        # there for why: an unattended browser between these two steps is a
        # narrow account-takeover risk on a shared/public computer).
        self.request.session['agent_signup_verified_at'] = timezone.now().isoformat()
        return redirect('accounts:agent_signup_setup')

    def post(self, request, *args, **kwargs):
        if 'resend' in request.POST:
            from django.core.cache import cache
            from .emails import create_and_send_otp
            cooldown_key = f'otp_resend_cooldown:{self.pending_user.pk}'
            if cache.get(cooldown_key):
                messages.warning(request, "Please wait a minute before requesting another code.")
                return redirect('accounts:agent_signup_verify')
            create_and_send_otp(self.pending_user)
            cache.set(cooldown_key, True, 60)  # 1 resend per minute per user
            messages.success(request, f"A new code has been sent to {self.pending_user.email}.")
            return redirect('accounts:agent_signup_verify')
        return super().post(request, *args, **kwargs)


class AgentSignUpSetupView(FormView):
    """Step 3: set name + password, finalizing the account."""
    form_class = AgentSignUpStep3Form
    template_name = 'accounts/signup_setup.html'

    # How long after OTP verification the account can sit "verified, no
    # password yet" before we require the user to prove it's still them by
    # re-verifying. Without this, on a shared/public computer, anyone who
    # uses the browser after a legitimate user verifies but before they set
    # a password could set the password themselves and take the account.
    # 15 minutes is generous for a normal single sitting but small enough to
    # make that window impractical to exploit opportunistically.
    VERIFIED_WINDOW_MINUTES = 15

    def _get_pending_user(self):
        user_id = self.request.session.get('agent_signup_user_id')
        if not user_id:
            return None

        verified_at_raw = self.request.session.get('agent_signup_verified_at')
        if not verified_at_raw:
            return None
        try:
            verified_at = datetime.fromisoformat(verified_at_raw)
        except (TypeError, ValueError):
            return None
        if timezone.now() - verified_at > timedelta(minutes=self.VERIFIED_WINDOW_MINUTES):
            return None

        return CustomUser.objects.filter(pk=user_id, role='MINOR_ADMIN', email_verified=True).first()

    def dispatch(self, request, *args, **kwargs):
        self.pending_user = self._get_pending_user()
        if not self.pending_user:
            request.session.pop('agent_signup_user_id', None)
            request.session.pop('agent_signup_verified_at', None)
            messages.info(request, "Your session has expired for security. Please start your agent registration again.")
            return redirect('accounts:agent_signup')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.pending_user
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data.get('last_name', '')
        user.set_password(form.cleaned_data['password1'])
        user.save(update_fields=['first_name', 'last_name', 'password'])

        from .emails import send_welcome_email
        send_welcome_email(user)

        self.request.session.pop('agent_signup_user_id', None)
        self.request.session.pop('agent_signup_verified_at', None)
        messages.success(
            self.request,
            "Your agent application has been submitted and is awaiting administrator approval. "
            "You will be notified once your application is reviewed."
        )
        return super().form_valid(form)

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


class SettingsView(LoginRequiredMixin, TemplateView):
    """Account settings: notification prefs, password change, delete account.

    Delete account is intentionally NOT offered to any admin (is_staff or
    role='SUPER_ADMIN' - see CustomUser.is_admin) - self-service deletion of
    an admin account is a real way to lock everyone out of the dashboard,
    so removing an admin account stays a Django-Admin-only action performed
    by a superuser. This is deliberately checked via `is_admin`, not just
    `is_superuser` - a staff user who isn't (yet) a superuser is still an
    admin for this purpose.

    For everyone else, deletion is a REQUEST, not an immediate delete: it
    sets deletion_requested_at and waits for an admin to approve it (see
    dashboard/views.py::approve_account_deletion). See the comment on
    CustomUser.deletion_requested_at for why this isn't a hard delete.
    """

    def get_template_names(self):
        if self.request.user.is_superuser:
            return ['accounts/settings.html']
        return ['accounts/settings.html']

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.forms import PasswordChangeForm

        action = request.POST.get('action')

        if action == 'notifications':
            user = request.user
            user.email_notifications_enabled = 'email_notifications' in request.POST
            user.push_notifications_enabled = 'push_notifications' in request.POST
            user.save(update_fields=[
                'email_notifications_enabled',
                'push_notifications_enabled',
            ])
            messages.success(request, "Notification preferences updated.")
            return redirect('accounts:settings')

        elif action == 'password':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect('accounts:settings')
            return self.render_to_response(self.get_context_data(password_form=form))

        elif action == 'delete_account':
            if request.user.is_admin:
                messages.error(request, "Admin accounts can't be self-deleted here. This has to be done from Django Admin by a superuser.")
                return redirect('accounts:settings')
            if request.user.has_pending_deletion_request:
                messages.info(request, "You already have a pending deletion request awaiting admin review.")
                return redirect('accounts:settings')
            if request.POST.get('confirm_delete') != 'DELETE':
                messages.error(request, 'Type "DELETE" exactly to confirm your deletion request.')
                return redirect('accounts:settings')

            user = request.user
            user.deletion_requested_at = timezone.now()
            user.deletion_reason = request.POST.get('deletion_reason', '').strip()
            user.save(update_fields=['deletion_requested_at', 'deletion_reason'])

            from notifications.services import notify, notify_admins
            from notifications.models import Notification
            notify_admins(
                Notification.Type.ACCOUNT_DELETION_REQUESTED,
                'Account Deletion Requested',
                message=f'{user.full_name_or_username} ({user.get_role_display()}) requested to delete their account.',
                link='/dashboard/accounts/deletion-requests/',
            )
            notify(
                user,
                Notification.Type.SYSTEM,
                'Deletion Request Received',
                message="We've received your account deletion request. An admin will review it shortly - "
                        "you can keep using your account until then, and cancel the request any time from Settings.",
            )
            messages.success(request, "Your deletion request has been submitted and is pending admin approval.")
            return redirect('accounts:settings')

        elif action == 'cancel_deletion_request':
            if request.user.has_pending_deletion_request:
                request.user.deletion_requested_at = None
                request.user.deletion_reason = ''
                request.user.save(update_fields=['deletion_requested_at', 'deletion_reason'])
                messages.success(request, "Your deletion request has been cancelled.")
            return redirect('accounts:settings')

        return redirect('accounts:settings')


class SignUpSuccessView(TemplateView):
    """Registration success page shown after renter signup."""
    template_name = 'accounts/signup_success.html'