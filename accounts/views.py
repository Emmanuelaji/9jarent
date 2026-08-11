from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from .forms import AgentSignUpForm, ProfileCompletionForm

class RoleBasedLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') == 'SUPER_ADMIN':
            return reverse_lazy('dashboard:admin')
        return reverse_lazy('properties:mine')

class AgentSignUpView(CreateView):
    form_class = AgentSignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('properties:mine')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to 9jaRent! Your agent account is ready — list your first property below.")
        return response

class CompleteProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileCompletionForm
    template_name = 'accounts/complete_profile.html'
    success_url = reverse_lazy('properties:mine')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile completed — you're ready to list properties.")
        return super().form_valid(form)
