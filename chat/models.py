# chat/models.py
from django.db import models
from  authorization.models import User

class Chat(models.Model):
    participants = models.ManyToManyField(
        User,
        related_name="chats"
    )
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat {self.id}"


class Message(models.Model):
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    text = models.TextField(blank=True)
    file = models.FileField(upload_to="chat_files/", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg {self.id} from {self.sender}"




