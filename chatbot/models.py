from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session_key = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )
    message = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Chat {self.id} - {self.created_at}"
