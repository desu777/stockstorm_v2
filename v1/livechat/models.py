from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class ChatMessage(models.Model):
    """Model przechowujący wiadomości czatu z automatycznym usuwaniem po 24h"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['timestamp']
        
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."
    
    @property
    def is_expired(self):
        """Sprawdza, czy wiadomość powinna zostać usunięta (starsza niż 24h)"""
        expiration_time = timezone.now() - timezone.timedelta(hours=24)
        return self.timestamp < expiration_time
