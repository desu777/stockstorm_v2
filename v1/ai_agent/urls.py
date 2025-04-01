from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_agent_chat, name='ai_agent_chat'),
    path('send_message/', views.send_message, name='ai_agent_send_message'),
] 