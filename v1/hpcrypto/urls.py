# hpcrypto/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Portfolio views
    path('', views.position_list, name='position_list'),
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('position/<int:position_id>/', views.position_detail, name='position_detail'),
    
    # CRUD operations
    path('add-category/', views.add_category, name='add_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    path('add-position/', views.add_position, name='add_position'),
    path('edit-position/<int:position_id>/', views.edit_position, name='edit_position'),
    path('delete-position/<int:position_id>/', views.delete_position, name='delete_position'),
    path('add-alert/<int:position_id>/', views.add_alert, name='add_alert'),
    path('edit-alert/<int:alert_id>/', views.edit_alert, name='edit_alert'),
    path('delete-alert/<int:alert_id>/', views.delete_alert, name='delete_alert'),
    
    # Pending orders
    path('orders/', views.order_list, name='order_list'),
    path('order/<int:order_id>/', views.view_order, name='view_order'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # API endpoints
    path('api/update-prices/', views.update_prices, name='update_prices'),
    path('api/get-price/<str:ticker>/', views.get_single_price, name='get_single_price'),
]