# consumers.py - Create this file in your hpcrypto app folder
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    active_users = set()
    
    async def connect(self):
        # Add user to the chat channel group
        await self.channel_layer.group_add(
            'chat_room',
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Add user to active users
        ChatConsumer.active_users.add(self.channel_name)
        
        # Send current active user count to the group
        await self.channel_layer.group_send(
            'chat_room',
            {
                'type': 'user_count',
                'count': len(ChatConsumer.active_users)
            }
        )
        
        # Send chat history to the new user
        chat_history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': chat_history
        }))
    
    async def disconnect(self, close_code):
        # Remove user from active users
        ChatConsumer.active_users.discard(self.channel_name)
        
        # Remove from the group
        await self.channel_layer.group_discard(
            'chat_room',
            self.channel_name
        )
        
        # Update user count
        await self.channel_layer.group_send(
            'chat_room',
            {
                'type': 'user_count',
                'count': len(ChatConsumer.active_users)
            }
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', '')
        
        if message_type == 'chat_message':
            # Save message to database
            message_data = await self.save_message(
                user_id=data['user_id'],
                username=data['username'],
                user_photo=data['user_photo'],
                content=data['message']
            )
            
            # Send message to the group
            await self.channel_layer.group_send(
                'chat_room',
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
    
    # Receive message from group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    # Handle user count updates
    async def user_count(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_count',
            'count': event['count']
        }))
    
    @database_sync_to_async
    def save_message(self, user_id, username, user_photo, content):
        # Get or create the user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Fallback if user doesn't exist
            user = None
        
        # Create message instance
        message = ChatMessage.objects.create(
            user=user,
            content=content
        )
        
        # Return serialized message data
        return {
            'id': message.id,
            'user_id': user_id,
            'username': username,
            'user_photo': user_photo,
            'content': content,
            'timestamp': message.timestamp.strftime('%I:%M %p')
        }
    
    @database_sync_to_async
    def get_chat_history(self, limit=50):
        # Get recent messages with select_related to optymalizacji zapytań
        messages = ChatMessage.objects.select_related('user').order_by('-timestamp')[:limit]
        
        # Prefetch related data to reduce database queries
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Konwersja do listy poza pętlą dla lepszej wydajności
        message_data = []
        
        # Przygotuj domyślne zdjęcie użytkownika
        default_photo = '/static/images/default-avatar.png'
        
        # Reverse the messages once outside the loop (more efficient)
        messages_list = list(reversed(messages))
        
        for message in messages_list:
            user = message.user
            
            # Get user photo URL (or default) - uproszczona logika
            photo_url = default_photo
            if user and hasattr(user, 'profile'):
                profile = user.profile
                if hasattr(profile, 'photo') and profile.photo:
                    photo_url = profile.photo.url
            
            message_data.append({
                'id': message.id,
                'user_id': user.id if user else None,
                'username': user.username if user else 'Unknown',
                'user_photo': photo_url,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%I:%M %p')
            })
        
        return message_data
