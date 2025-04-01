from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    """Model przechowujący historię konwersacji użytkownika z AI agentem."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Konwersacja {self.id} - {self.title or 'Bez tytułu'} ({self.user.username})"

class Message(models.Model):
    """Model przechowujący pojedyncze wiadomości w konwersacji."""
    ROLE_CHOICES = (
        ('user', 'Użytkownik'),
        ('assistant', 'Asystent'),
    )
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Pole do przechowywania zakodowanego obrazu wykresu (base64)
    chart_image = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}{'...' if len(self.content) > 50 else ''}"
