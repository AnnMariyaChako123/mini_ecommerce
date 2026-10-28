from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "created_at")
    search_fields = ("message", "reply", "user__username")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)