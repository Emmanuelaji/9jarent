from django.dispatch import receiver
from allauth.account.signals import user_signed_up

@receiver(user_signed_up)
def assign_agent_role(request, user, **kwargs):
    # Anyone who signs up through the public flow (including Google) is an agent.
    if not user.role or user.role == 'PUBLIC':
        user.role = 'MINOR_ADMIN'
        user.save(update_fields=['role'])
