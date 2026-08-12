# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    RoleBasedLoginView, AgentSignUpView, RenterSignUpView, AccountTypeChoiceView,
    CompleteProfileView, AgentPendingView,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', AccountTypeChoiceView.as_view(), name='signup'),
    path('signup/agent/', AgentSignUpView.as_view(), name='agent_signup'),
    path('signup/renter/', RenterSignUpView.as_view(), name='renter_signup'),
    path('pending/', AgentPendingView.as_view(), name='pending'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete_profile'),
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
]