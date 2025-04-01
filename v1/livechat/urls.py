from django.urls import path
from . import views

app_name = 'livechat'

urlpatterns = [
    path('messages/', views.get_chat_messages, name='get_chat_messages'),
]
