# routing.py - Create this file in your hpcrypto app folder
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]


# asgi.py - Update your project's asgi.py file

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import hpcrypto.routing  # Adjust this import to match your app name

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockstorm.settings')  # Adjust to your project name

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            hpcrypto.routing.websocket_urlpatterns
        )
    ),
})


# settings.py - Update these settings in your project's settings.py

# Install the required apps
INSTALLED_APPS = [
    # ... other apps
    'channels',
    'hpcrypto',  # Your app
]

# Configure Channels
ASGI_APPLICATION = 'stockstorm.asgi.application'  # Adjust to your project name

# Channel Layers
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        # For production, use Redis:
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {
        #     "hosts": [('127.0.0.1', 6379)],
        # },
    },
}


# User Profile Model - Add this to your models.py if you don't have it already

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    push_notifications_enabled = models.BooleanField(default=False)
    
    @property
    def photo_url(self):
        if self.photo:
            return self.photo.url
        return '/static/images/default-avatar.png'
    
    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)
    instance.profile.save()
