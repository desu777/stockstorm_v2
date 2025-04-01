# gt/tasks.py
import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from celery import shared_task
from decimal import Decimal

from home.models import UserProfile, TelegramConfig
from .models import StockPosition, StockPriceAlert, GTCategory
from .utils import get_bulk_stock_prices
from hpcrypto.telegram_utils import send_telegram_notification

User = get_user_model()
logger = logging.getLogger(__name__)

def update_all_stock_prices():
    """
    Update prices for all users with stock positions.
    This is the main entry point for the background price update service.
    """
    logger.info("Starting background stock price update service")
    
    try:
        # Get all users with positions
        users_with_positions = User.objects.filter(
            stockposition__isnull=False
        ).distinct()
        
        user_count = users_with_positions.count()
        logger.info(f"Found {user_count} users with active stock positions")
        
        if user_count == 0:
            logger.info("No users with active stock positions, skipping price update")
            return
        
        updated_positions = 0
        errors = 0
        
        for user in users_with_positions:
            try:
                # Update prices for this user
                updated = update_stock_prices_for_user(user)
                if updated is not None:
                    updated_positions += updated
            except Exception as e:
                logger.error(f"Error updating stock prices for user {user.id}: {str(e)}")
                errors += 1
        
        logger.info(f"Stock price update service completed. Updated {updated_positions} positions for {user_count} users. Errors: {errors}")
        return updated_positions
        
    except Exception as e:
        logger.error(f"Error in stock price update service: {str(e)}")
        return None

def update_stock_prices_for_user(user):
    """
    Update prices for all active stock positions for a specific user.
    Uses Alpha Vantage API to fetch prices.
    
    Args:
        user: User object
        
    Returns:
        int: Number of positions updated or None if error
    """
    try:
        # Get all active positions for this user (without exit_price)
        positions = StockPosition.objects.filter(user=user, exit_price=None)
        if not positions.exists():
            logger.debug(f"User {user.id} has no active stock positions, skipping")
            return 0
        
        # Get all unique tickers
        tickers = positions.values_list('ticker', flat=True).distinct()
        
        # Fetch prices in bulk for all tickers
        prices = get_bulk_stock_prices(tickers)
        if not prices:
            logger.warning(f"Failed to fetch stock prices for user {user.id}")
            return 0
        
        # Update each position with its new price
        updated_count = 0
        for position in positions:
            if position.ticker in prices:
                # Update only the current price and timestamp
                position.current_price = prices[position.ticker]
                position.last_price_update = timezone.now()
                
                # Save the updated position
                position.save(update_fields=['current_price', 'last_price_update'])
                updated_count += 1
                
                # Check if any alerts should be triggered
                check_alerts_for_position(position)
        
        logger.info(f"Updated {updated_count} stock positions for user {user.id}")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error updating stock prices for user {user.id}: {str(e)}")
        return None

def check_alerts_for_position(position):
    """
    Check if any price alerts are triggered for a position.
    If so, mark them as triggered and send notifications.
    
    Args:
        position: StockPosition object with updated current_price
    """
    if not position.current_price:
        return
    
    try:
        # Get all active, non-triggered alerts for this position
        alerts = StockPriceAlert.objects.filter(
            position=position,
            is_active=True,
            triggered=False
        )
        
        if not alerts.exists():
            return
        
        triggered_count = 0
        for alert in alerts:
            is_triggered = False
            
            # Ensure values are of the same type (Decimal)
            current_price = Decimal(str(position.current_price))
            threshold_value = Decimal(str(alert.threshold_value))
            
            if position.entry_price:
                entry_price = Decimal(str(position.entry_price))
            else:
                entry_price = None
            
            # Check if the alert is triggered based on its type
            if alert.alert_type == 'PRICE_ABOVE' and current_price >= threshold_value:
                is_triggered = True
            elif alert.alert_type == 'PRICE_BELOW' and current_price <= threshold_value:
                is_triggered = True
            elif alert.alert_type == 'PCT_INCREASE' and entry_price:
                percent_change = (current_price - entry_price) / entry_price * Decimal('100')
                if percent_change >= threshold_value:
                    is_triggered = True
            elif alert.alert_type == 'PCT_DECREASE' and entry_price:
                percent_change = (entry_price - current_price) / entry_price * Decimal('100')
                if percent_change >= threshold_value:
                    is_triggered = True
            
            if is_triggered:
                # Mark the alert as triggered
                alert.triggered = True
                alert.last_triggered = timezone.now()
                alert.save()
                triggered_count += 1
                
                # Send notification(s)
                send_alert_notification(alert)
        
        if triggered_count > 0:
            logger.info(f"Triggered {triggered_count} alerts for stock position {position.id} ({position.ticker})")
    
    except Exception as e:
        logger.error(f"Error checking alerts for stock position {position.id}: {str(e)}")

def send_alert_notification(alert):
    """
    Send notification for a triggered alert.
    Currently supports Telegram notifications.
    
    Args:
        alert: StockPriceAlert object that was triggered
    """
    try:
        # Get the user and their telegram config
        user = alert.position.user
        
        # Check if the user has Telegram notifications enabled
        telegram_config = TelegramConfig.objects.filter(user=user, is_verified=True).first()
        if telegram_config and telegram_config.chat_id:
            # Get the user's profile to check notification settings
            profile = UserProfile.objects.get(user=user)
            if profile.telegram_notifications_enabled:
                # Format and send the Telegram message
                message = format_alert_message_for_telegram(alert)
                send_telegram_notification(telegram_config.chat_id, message)
                logger.info(f"Sent Telegram notification for stock alert {alert.id} to user {user.id}")
        
        # Add support for other notification channels here (email, push, etc.)
        
    except Exception as e:
        logger.error(f"Error sending notification for stock alert {alert.id}: {str(e)}")

def format_alert_message_for_telegram(alert):
    """Format alert message for Telegram"""
    position = alert.position
    ticker = position.ticker
    alert_time = alert.last_triggered.strftime("%Y-%m-%d %H:%M:%S") if alert.last_triggered else timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"🔔 *Stock Alert Triggered* 🔔\n\n"
    
    # Różne emotki dla różnych typów alertów
    if alert.alert_type == 'PRICE_ABOVE':
        message += f"📈 *{ticker}* - Price Above\n"
        message += f"⚠️ Threshold: ${alert.threshold_value:.2f}\n"
        message += f"💰 Current Price: ${position.current_price:.2f}\n"
    elif alert.alert_type == 'PRICE_BELOW':
        message += f"📉 *{ticker}* - Price Below\n"
        message += f"⚠️ Threshold: ${alert.threshold_value:.2f}\n"
        message += f"💰 Current Price: ${position.current_price:.2f}\n"
    elif alert.alert_type == 'PCT_INCREASE':
        message += f"🚀 *{ticker}* - % Increase\n"
        message += f"⚠️ Threshold: {alert.threshold_value:.2f}%\n"
        if position.entry_price:
            pct_change = ((position.current_price - position.entry_price) / position.entry_price) * 100
            message += f"📈 Increase: {pct_change:.2f}%\n"
    elif alert.alert_type == 'PCT_DECREASE':
        message += f"💸 *{ticker}* - % Decrease\n"
        message += f"⚠️ Threshold: {alert.threshold_value:.2f}%\n"
        if position.entry_price:
            pct_change = ((position.entry_price - position.current_price) / position.entry_price) * 100
            message += f"📉 Decrease: {pct_change:.2f}%\n"
    
    # Dodajemy szczegóły pozycji (Position Details)
    message += f"\n📊 *Position Details:*\n"
    message += f"💰 Current Price: *${position.current_price:.2f}*\n"
    if position.entry_price:
        message += f"🏁 Entry Price: *${position.entry_price:.2f}*\n"
    if position.quantity:
        message += f"🔢 Quantity: *{position.quantity}*\n"
    
    # Obliczamy i dodajemy wielkość pozycji (Position Size)
    if position.entry_price and position.quantity:
        position_size = position.entry_price * position.quantity
        message += f"💵 Position Size: *${position_size:.2f}*\n"
    
    # Dodajemy informacje o P&L jeśli możliwe
    if position.entry_price and position.current_price:
        pnl_dollar = (position.current_price - position.entry_price) * position.quantity
        if position.entry_price != 0:
            pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100
            
            if pnl_dollar >= 0:
                profit_or_loss = "Profit"
                emoji = "🤑 💰"
            else:
                profit_or_loss = "Loss"
                emoji = "📉 💸"
                
            message += f"\n{emoji} *Current {profit_or_loss}:*\n"
            message += f"💲 *${pnl_dollar:.2f} ({pnl_percent:.2f}%)*\n"
    
    # Dodajemy notatki z alertu (jeśli istnieją)
    if hasattr(alert, 'notes') and alert.notes:
        message += f"\n📝 *Alert Notes:* {alert.notes}\n"
    else:
        message += f"\n📝 *Alert Notes:* No notes available\n"
    
    # Dodajemy notatki z pozycji (jeśli istnieją)
    if position.notes:
        message += f"📋 *Position Notes:* {position.notes}\n"
    else:
        message += f"📋 *Position Notes:* No notes available\n"
    
    # Dodajemy informację o czasie wyzwolenia alertu
    message += f"\n🕒 Alert triggered at: {alert_time} ⏰"
    
    return message

@shared_task
def update_stock_prices():
    """
    Celery task to update all stock prices.
    Runs every 4 minutes.
    """
    logger.info("Running scheduled stock price update task")
    updated = update_all_stock_prices()
    return f"Updated {updated} stock positions" if updated is not None else "Error updating stock prices" 