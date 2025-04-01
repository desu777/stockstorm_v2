from django.urls import path
from . import views

urlpatterns = [
    path('register_token/', views.register, name='register_token'),
    path('create_bot/', views.create_bot, name='create_bot'),
    path('get_bot_status/<int:bot_id>/', views.get_bot_status, name='get_bot_status'),
    path('get_bot_details/<int:bot_id>/', views.get_bot_details, name='get_bot_details'),
    path('get_bot_full_data/<int:bot_id>/', views.get_bot_full_data, name='get_bot_full_data'),
    path('get_bot_trades/<int:bot_id>/', views.get_bot_trades, name='get_bot_trades'),
    path('get_user_bots/<int:user_id>/', views.get_user_bots, name='get_user_bots'),
    path('get_bot_profits/', views.get_bot_profits, name='get_bot_profits'),
    path('get_bot_profits/<int:bot_id>/', views.get_bot_profits, name='get_bot_profits_single'),
    path('get_bot_profits/user/<int:user_id>/', views.get_bot_profits, name='get_bot_profits_by_user'),
    path('get_bot_profits/user/<int:user_id>/<int:bot_id>/', views.get_bot_profits, name='get_bot_profits_by_user_and_bot'),
    path('remove_bot/<int:bot_id>/', views.remove_bot, name='remove_bot'),
    path('export_bnb_trades_csv/<int:bot_id>/', views.export_bnb_trades_csv, name='export_bnb_trades_csv'),
]