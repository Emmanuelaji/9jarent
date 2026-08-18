# accounts/signals.py
"""
Django signals for the accounts app.

Note: allauth is not currently in INSTALLED_APPS.
If social auth is added later, uncomment the signal handlers below.
"""

# from django.dispatch import receiver
# from allauth.account.signals import user_signed_up
#
# @receiver(user_signed_up)
# def assign_agent_role(request, user, **kwargs):
#     """Assign agent role to users who sign up via social auth."""
#     if not user.role or user.role == 'PUBLIC':
#         user.role = 'MINOR_ADMIN'
#         user.save(update_fields=['role'])