from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    RoleBasedLoginView, AgentSignUpStep1View, AgentSignUpVerifyView, AgentSignUpSetupView,
    RenterSignUpView, AccountTypeChoiceView,
    CompleteProfileView, AgentProfileEditView, AgentPendingView, AgentPublicProfileView,
    AgentsDirectoryView, SignUpSuccessView, SettingsView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', AccountTypeChoiceView.as_view(), name='signup'),
    path('signup/agent/', AgentSignUpStep1View.as_view(), name='agent_signup'),
    path('signup/agent/verify/', AgentSignUpVerifyView.as_view(), name='agent_signup_verify'),
    path('signup/agent/setup/', AgentSignUpSetupView.as_view(), name='agent_signup_setup'),
    path('signup/renter/', RenterSignUpView.as_view(), name='renter_signup'),
    path('signup/success/', SignUpSuccessView.as_view(), name='signup_success'),
    path('pending/', AgentPendingView.as_view(), name='pending'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete_profile'),
    path('profile/', AgentProfileEditView.as_view(), name='profile_edit'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('agents/', AgentsDirectoryView.as_view(), name='agents_directory'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('agents/<slug:username>/', AgentPublicProfileView.as_view(), name='agent_public_profile'),
]