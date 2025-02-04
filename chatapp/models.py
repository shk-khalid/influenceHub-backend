from django.db import models

class ChatMessage(models.Model):
    text = models.TextField()
    sender = models.CharField(max_length=10)  # 'user' or 'bot'
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100)

    class Meta:
        ordering = ['timestamp']