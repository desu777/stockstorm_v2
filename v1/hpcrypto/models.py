# hpcrypto/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class HPCategory(models.Model):
    """Model for grouping positions (e.g., HP1, HP2)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    class Meta:
        verbose_name_plural = "HP Categories"
        ordering = ['name']

class Position(models.Model):
    """Model for individual trading positions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(HPCategory, on_delete=models.CASCADE, related_name='positions')
    ticker = models.CharField(max_length=20)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    entry_price = models.DecimalField(max_digits=18, decimal_places=8)
    exit_price = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)
    exit_date = models.DateTimeField(blank=True, null=True)
    current_price = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)
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


class PendingOrder(models.Model):
    """Model for pending stop-limit orders"""
    ORDER_TYPES = (
        ('STOP_LIMIT_BUY', 'Stop Limit Buy'),
        ('STOP_LIMIT_SELL', 'Stop Limit Sell'),
    )
    
    ORDER_STATUS = (
        ('WAITING', 'Waiting'),
        ('CREATED', 'Created on Binance'),
        ('EXECUTED', 'Executed'),
        ('CANCELLED', 'Cancelled'),
        ('ERROR', 'Error'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    symbol = models.CharField(max_length=20, help_text="Trading symbol (e.g. BTC)")
    currency = models.CharField(max_length=10, default="USDT", help_text="Quote currency (e.g. USDT, USDC)")
    limit_price = models.DecimalField(max_digits=18, decimal_places=8, help_text="Limit price for the order")
    trigger_price = models.DecimalField(max_digits=18, decimal_places=8, help_text="Trigger price to activate the order")
    amount = models.DecimalField(max_digits=18, decimal_places=8, help_text="Amount in quote currency (for buy) or asset quantity (for sell)")
    
    # Fields for Binance API
    binance_order_id = models.CharField(max_length=50, blank=True, null=True, help_text="Order ID on Binance")
    binance_client_order_id = models.CharField(max_length=50, blank=True, null=True, help_text="Client order ID on Binance")
    
    # Order status
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='WAITING')
    last_checked = models.DateTimeField(blank=True, null=True, help_text="Last time this order was checked")
    
    # Error handling
    error_message = models.TextField(blank=True, null=True, help_text="Error message if any")
    retry_count = models.IntegerField(default=0, help_text="Number of retries for order creation/checking")
    
    # For sell orders - reference to position
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, blank=True, null=True, help_text="Related position for sell orders")
    position_identifier = models.CharField(max_length=50, blank=True, null=True, help_text="Position identifier (e.g. HP1)")
    
    # For buy orders - reference to category
    category = models.ForeignKey(HPCategory, on_delete=models.SET_NULL, blank=True, null=True, help_text="Category for buy orders")
    
    # Additional notes
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about this order")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(blank=True, null=True, help_text="When the order was executed")
    
    def __str__(self):
        return f"{self.get_order_type_display()} {self.symbol}{self.currency} @ {self.limit_price} (Trigger: {self.trigger_price})"
    
    @property
    def get_trading_pair(self):
        """Return the trading pair for Binance API (e.g. BTCUSDT)"""
        return f"{self.symbol}{self.currency}"
    
    @property
    def display_amount(self):
        """Format the amount for display"""
        if self.order_type == 'STOP_LIMIT_BUY':
            return f"{self.amount} {self.currency}"
        else:
            return f"{self.amount} {self.symbol}"
    
    @property
    def is_active(self):
        """Check if the order is still active (waiting or created)"""
        return self.status in ['WAITING', 'CREATED']
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pending Order"
        verbose_name_plural = "Pending Orders"


class PriceAlert(models.Model):
    """Model for price alerts on positions"""
    ALERT_TYPES = (
        ('PRICE_ABOVE', 'Price Above'),
        ('PRICE_BELOW', 'Price Below'),
        ('PCT_INCREASE', '% Increase'),
        ('PCT_DECREASE', '% Decrease'),
    )
    
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold_value = models.DecimalField(max_digits=18, decimal_places=8)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes for this alert")
    is_active = models.BooleanField(default=True)
    triggered = models.BooleanField(default=False)
    last_triggered = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Notification fields
    notify_telegram = models.BooleanField(default=True, help_text="Send Telegram notification when alert triggered")
    notification_sent = models.BooleanField(default=False)
    last_notification_sent = models.DateTimeField(blank=True, null=True)
    
    # Add the missing SMS field
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