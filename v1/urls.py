from django.urls import path, include
from . import views
from .ai_agent import views as ai_views

urlpatterns = [
    # Główne widoki
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # API AI
    path('api/chat/', ai_views.chat_api, name='chat_api'),
    
    # Ścieżki URL dla wykresów
    path('charts/bot/<int:bot_id>/', ai_views.bot_chart_view, name='bot_chart'),
    path('charts/portfolio/', ai_views.portfolio_chart_view, name='portfolio_chart'),
    
    # GT - Giełda Tradycyjna
    path('gt/', include('v1.gt.urls')),
    
    # LiveChat
    path('livechat/', include('v1.livechat.urls')),
]