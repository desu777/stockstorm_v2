# Add this to your models.py file

from django.db import models
from django.contrib.auth.models import User

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),  # Indeks dla sortowania od najnowszych
        ]

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{username}: {self.content[:50]}"


# Add this to your urls.py file

from django.urls import path
from . import views

urlpatterns = [
    # Other URLs...
    path('chat/', views.chat_view, name='chat'),
]


# Add this to your views.py file

from django.shortcuts import render

def chat_view(request):
    return render(request, 'chat.html', {'title': 'Live Chat'})
