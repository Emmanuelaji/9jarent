# messaging/admin.py

from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'message', 'created_at', 'is_read')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'renter', 'agent', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('property__title', 'renter__username', 'agent__username')
    autocomplete_fields = ('property', 'renter', 'agent')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('message', 'sender__username')
    autocomplete_fields = ('conversation', 'sender')
    readonly_fields = ('created_at',)
