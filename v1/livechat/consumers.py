import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Dołączenie do grupy czatu - na razie mamy tylko jeden pokój dla wszystkich
        self.room_group_name = 'livechat'
        
        # Dołącz do grupy pokoju
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Opuść grupę pokoju
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Odbieranie wiadomości od WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data['message']
            username = data['username']
            user_id = data['user_id']
            
            # Zapisz wiadomość w bazie danych - użyj bloku try/except do obsługi błędów
            try:
                await self.save_message(user_id, message)
                print(f"Wiadomość zapisana: {message} od użytkownika {username}")
            except Exception as e:
                print(f"BŁĄD przy zapisywaniu wiadomości: {str(e)}")
                print(traceback.format_exc())
            
            # Pobierz URL zdjęcia profilowego użytkownika
            profile_picture_url = await self.get_profile_picture(user_id)
            
            # Wyślij wiadomość do grupy pokoju
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username,
                    'user_id': user_id,
                    'profile_picture': profile_picture_url,
                    'timestamp': None  # Będzie ustawione na bieżący czas po stronie klienta
                }
            )
        except Exception as e:
            print(f"BŁĄD ogólny w receive: {str(e)}")
            print(traceback.format_exc())
    
    # Odbieranie wiadomości od grupy pokoju
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        user_id = event['user_id']
        profile_picture = event.get('profile_picture')
        
        # Wyślij wiadomość do WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'user_id': user_id,
            'profile_picture': profile_picture
        }))
    
    @database_sync_to_async
    def save_message(self, user_id, message):
        try:
            user = User.objects.get(id=user_id)
            chat_message = ChatMessage.objects.create(user=user, message=message)
            print(f"Wiadomość zapisana w DB: ID={chat_message.id}")
            return chat_message.id
        except User.DoesNotExist:
            print(f"Użytkownik o ID {user_id} nie istnieje")
            raise
        except Exception as e:
            print(f"Nieprzewidziany błąd: {str(e)}")
            print(traceback.format_exc())
            raise
            
    @database_sync_to_async
    def get_profile_picture(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            if hasattr(user, 'profile') and user.profile.profile_picture:
                return user.profile.profile_picture.url
            return None
        except User.DoesNotExist:
            return None
        except Exception as e:
            print(f"Błąd przy pobieraniu zdjęcia profilowego: {str(e)}")
            return None
