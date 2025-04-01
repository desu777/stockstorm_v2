from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView
from . import bnb_views

urlpatterns = [
    path('login/', views.custom_login_view, name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('forgot/', views.forgot_password_view, name='forgot'),
    path('success/', views.success_view, name='success'),
    path('profile/', views.profile_view, name='profile'),
    path('balance_data/', views.get_balance_data, name='balance_data'),
    path('instrument_price/', views.get_instrument_price, name='get_instrument_price'),
    path('search_instruments/', views.search_instruments, name='search_instruments'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('', views.home, name='home'),
    path('api/stock_status/', views.api_stock_status, name='api_stock_status'),
    path('test/', TemplateView.as_view(template_name='index.html')),
    path('bnb/', bnb_views.bnb_list, name='bnb_list'),
    path('bnb/create/', bnb_views.bnb_create, name='bnb_create'),
    path('bnb/<int:bot_id>/', bnb_views.bnb_detail, name='bnb_detail'),
    path('bnb/<int:bot_id>/status/', bnb_views.bnb_status, name='bnb_status'),
    path('bnb/<int:bot_id>/refresh/', bnb_views.bnb_refresh, name='bnb_refresh'),
    path('bnb/<int:bot_id>/delete/', bnb_views.bnb_delete, name='bnb_delete'),
    path('bnb/<int:bot_id>/export_trades/', bnb_views.export_bnb_trades, name='export_bnb_trades'),
    path('telegram-settings/', views.telegram_settings, name='telegram_settings'),
    path('reset-telegram/', views.reset_telegram, name='reset_telegram'),
]



