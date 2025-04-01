from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class GTCategory(models.Model):
    """Model for grouping positions (e.g., Dividend Stocks, Growth Stocks)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    class Meta:
        verbose_name_plural = "GT Categories"
        ordering = ['name']

class StockPosition(models.Model):
    """Model for individual stock positions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(GTCategory, on_delete=models.CASCADE, related_name='positions')
    ticker = models.CharField(max_length=20, help_text="Stock symbol (e.g. AAPL, MSFT)")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    entry_price = models.DecimalField(max_digits=18, decimal_places=4)
    exit_price = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True)
    exit_date = models.DateTimeField(blank=True, null=True)
    current_price = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True)
    last_price_update = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.ticker} - {self.quantity} @ {self.entry_price}"
    
    @property
    def position_size(self):
        """Calculate total position size in dollars"""
        return self.quantity * self.entry_price
    
    @property
    def profit_loss_dollar(self):
        """Calculate profit/loss in dollars - use exit_price if available, otherwise use current_price"""
        if self.exit_price is not None:
            return (self.exit_price - self.entry_price) * self.quantity
        elif self.current_price is not None:
            return (self.current_price - self.entry_price) * self.quantity
        return None
    
    @property
    def profit_loss_percent(self):
        """Calculate profit/loss in percentage - use exit_price if available, otherwise use current_price"""
        if self.exit_price is not None and self.entry_price != 0:
            return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        elif self.current_price is not None and self.entry_price != 0:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        return None
    
    class Meta:
        ordering = ['-created_at']

class StockPriceAlert(models.Model):
    """Model for price alerts on stock positions"""
    ALERT_TYPES = (
        ('PRICE_ABOVE', 'Price Above'),
        ('PRICE_BELOW', 'Price Below'),
        ('PCT_INCREASE', '% Increase'),
        ('PCT_DECREASE', '% Decrease'),
    )
    
    position = models.ForeignKey(StockPosition, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold_value = models.DecimalField(max_digits=18, decimal_places=4)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes for this alert")
    is_active = models.BooleanField(default=True)
    triggered = models.BooleanField(default=False)
    last_triggered = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Notification fields
    notify_telegram = models.BooleanField(default=True, help_text="Send Telegram notification when alert triggered")
    notification_sent = models.BooleanField(default=False)
    last_notification_sent = models.DateTimeField(blank=True, null=True)
    sms_sent = models.BooleanField(default=False)
    
    @property
    def status(self):
        """Returns the alert status as a string for display"""
        if self.triggered:
            return 'triggered'
        elif self.is_active:
            return 'active'
        else:
            return 'inactive'
    
    def __str__(self):
        return f"{self.get_alert_type_display()} @ {self.threshold_value} for {self.position.ticker}"
    
    def format_notification_message(self):
        """Format notification message based on alert type and threshold"""
        position = self.position
        ticker = position.ticker
        
        # Ensure proper conversion to Decimal
        current_price = Decimal(str(position.current_price)) if position.current_price else Decimal('0')
        threshold = Decimal(str(self.threshold_value))
        entry_price = Decimal(str(position.entry_price)) if position.entry_price else Decimal('0')
        
        message = ""
        if self.alert_type == 'PRICE_ABOVE':
            message = f"{ticker} price is now ${current_price:.4f}, above your ${threshold:.4f} threshold."
        elif self.alert_type == 'PRICE_BELOW':
            message = f"{ticker} price is now ${current_price:.4f}, below your ${threshold:.4f} threshold."
        elif self.alert_type == 'PCT_INCREASE':
            if entry_price == 0:
                message = f"{ticker} price alert triggered. Current price: ${current_price:.4f}"
            else:
                pct_change = ((current_price - entry_price) / entry_price) * 100
                message = f"{ticker} increased by {pct_change:.2f}%, above your {threshold:.2f}% threshold. Current price: ${current_price:.4f}"
        elif self.alert_type == 'PCT_DECREASE':
            if entry_price == 0:
                message = f"{ticker} price alert triggered. Current price: ${current_price:.4f}"
            else:
                pct_change = ((entry_price - current_price) / entry_price) * 100
                message = f"{ticker} decreased by {pct_change:.2f}%, above your {threshold:.2f}% threshold. Current price: ${current_price:.4f}"
        else:
            message = f"{ticker} price alert triggered. Current price: ${current_price:.4f}"
        
        # Add notes if available
        if position.notes and position.notes.strip():
            message += f"\n\nNotes: {position.notes}"
            
        return message
