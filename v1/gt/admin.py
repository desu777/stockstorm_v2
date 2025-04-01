from django.contrib import admin
from .models import GTCategory, StockPosition, StockPriceAlert

@admin.register(GTCategory)
class GTCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('created_at',)

@admin.register(StockPosition)
class StockPositionAdmin(admin.ModelAdmin):
    list_display = ('ticker', 'user', 'category', 'quantity', 'entry_price', 'current_price', 'created_at')
    search_fields = ('ticker', 'user__username', 'category__name')
    list_filter = ('category', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'last_price_update')

@admin.register(StockPriceAlert)
class StockPriceAlertAdmin(admin.ModelAdmin):
    list_display = ('position', 'alert_type', 'threshold_value', 'is_active', 'triggered', 'created_at')
    search_fields = ('position__ticker', 'position__user__username')
    list_filter = ('alert_type', 'is_active', 'triggered', 'created_at')
    readonly_fields = ('created_at', 'last_triggered', 'last_notification_sent')
