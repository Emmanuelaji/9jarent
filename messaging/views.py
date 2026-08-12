# messaging/views.py

from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from properties.models import Property
from .forms import MessageForm
from .models import Conversation


def _user_can_access(user, conversation):
    """Only the renter, the assigned agent, or an admin may access a conversation."""
    return (
        conversation.renter_id == user.id
        or conversation.agent_id == user.id
        or user.is_admin
    )


@login_required
def inbox(request, pk=None):
    """
    Combined conversation list + active thread, matching the two-panel
    messaging UI. /messages/ shows the list with no thread selected;
    /messages/<pk>/ shows the list plus the selected conversation.
    """
    user = request.user

    conversations = list(
        Conversation.objects.filter(
            Q(renter=user) | Q(agent=user)
        ).select_related('property', 'renter', 'agent').prefetch_related('messages')
    )
    for convo in conversations:
        convo.other = convo.other_party(user)
        convo.unread = convo.unread_count_for(user)

    active_conversation = None
    thread_messages = None
    form = MessageForm()

    if pk is not None:
        active_conversation = get_object_or_404(Conversation, pk=pk)
        if not _user_can_access(user, active_conversation):
            raise PermissionDenied("You do not have permission to view this conversation.")
        active_conversation.other = active_conversation.other_party(user)

        if request.method == 'POST':
            form = MessageForm(request.POST)
            if form.is_valid():
                msg = form.save(commit=False)
                msg.conversation = active_conversation
                msg.sender = user
                msg.save()
                active_conversation.save(update_fields=['updated_at'])
                return redirect('messaging:detail', pk=active_conversation.pk)
        else:
            # Mark the other party's messages as read now that this user has opened the thread.
            active_conversation.messages.exclude(sender=user).filter(is_read=False).update(is_read=True)

        thread_messages = active_conversation.messages.select_related('sender').all()

    return render(request, 'messaging/inbox.html', {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'thread_messages': thread_messages,
        'form': form,
    })


@login_required
def start_conversation(request, property_id):
    """
    Start (or resume) a conversation with the agent of a property.
    Triggered by the 'Message Agent' button on the property detail page.
    """
    if request.method != 'POST':
        return HttpResponseForbidden("This action requires POST.")

    property_obj = get_object_or_404(Property, pk=property_id, status='PUBLISHED')
    user = request.user

    if user.is_admin:
        django_messages.error(request, "Admin accounts cannot start property conversations.")
        return redirect('properties:detail', slug=property_obj.slug)

    if property_obj.created_by_id == user.id:
        django_messages.error(request, "You cannot message yourself about your own property.")
        return redirect('properties:detail', slug=property_obj.slug)

    conversation, _created = Conversation.objects.get_or_create(
        property=property_obj,
        renter=user,
        defaults={'agent': property_obj.created_by},
    )

    return redirect('messaging:detail', pk=conversation.pk)