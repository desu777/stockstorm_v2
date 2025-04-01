# gt/urls.py
from django.urls import path
from . import views

app_name = 'gt'  # Definicja app_name dla przestrzeni nazw

urlpatterns = [
    # Portfolio views
    path('', views.position_list, name='gt_position_list'),
    path('category/<int:category_id>/', views.category_detail, name='gt_category_detail'),
    path('position/<int:position_id>/', views.position_detail, name='gt_position_detail'),
    
    # CRUD operations
    path('add-category/', views.add_category, name='gt_add_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='gt_edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='gt_delete_category'),
    path('add-position/', views.add_position, name='gt_add_position'),
    path('edit-position/<int:position_id>/', views.edit_position, name='gt_edit_position'),
    path('delete-position/<int:position_id>/', views.delete_position, name='gt_delete_position'),
    path('add-alert/<int:position_id>/', views.add_alert, name='gt_add_alert'),
    path('edit-alert/<int:alert_id>/', views.edit_alert, name='gt_edit_alert'),
    path('delete-alert/<int:alert_id>/', views.delete_alert, name='gt_delete_alert'),
    
    # API endpoints
    path('api/update-prices/', views.update_prices, name='gt_update_prices'),
    path('api/update-position-price/', views.update_position_price, name='gt_update_position_price'),
    path('api/get-price/<str:ticker>/', views.get_single_price, name='gt_get_single_price'),
    path('api/get-advanced-price/<str:ticker>/', views.get_advanced_price, name='gt_get_advanced_price'),
    path('api/stock-info/<str:ticker>/', views.get_stock_info_api, name='gt_get_stock_info'),
    path('api/stock-price-advanced/<str:ticker>/', views.get_stock_info_api, name='gt_get_stock_price_advanced'),
] 