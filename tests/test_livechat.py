from django.test import TestCase
from django.contrib.auth.models import User
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import path
from v1.livechat.consumers import ChatConsumer
import json

class ChatConsumerTests(TestCase):
    """
    Test cases for the ChatConsumer WebSocket functionality
    """
    
    async def test_connect(self):
        """Test connection to the chat WebSocket"""
        application = URLRouter([
            path('ws/chat/', ChatConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(application, '/ws/chat/')
        connected, _ = await communicator.connect()
        
        # Check connection is successful
        self.assertTrue(connected)
        
        # Check user count message is received
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'user_count')
        
        # Check chat history is received
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'chat_history')
        
        await communicator.disconnect()
    
    async def test_send_message(self):
        """Test sending and receiving messages"""
        # Create a test user
        user = User.objects.create_user(username='testuser', password='12345')
        
        # Connect to WebSocket
        application = URLRouter([
            path('ws/chat/', ChatConsumer.as_asgi()),
        ])
        
        communicator = WebsocketCommunicator(application, '/ws/chat/')
        await communicator.connect()
        
        # Skip initial user count and chat history messages
        await communicator.receive_json_from()  # user_count
        await communicator.receive_json_from()  # chat_history
        
        # Send a test message
        test_message = {
            'type': 'chat_message',
            'message': 'Hello, test!',
            'user_id': user.id,
            'username': user.username,
            'user_photo': '/static/images/default-avatar.png'
        }
        await communicator.send_json_to(test_message)
        
        # Expect to receive the message back
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'chat_message')
        self.assertEqual(response['message']['content'], 'Hello, test!')
        self.assertEqual(response['message']['username'], 'testuser')
        
        await communicator.disconnect()
