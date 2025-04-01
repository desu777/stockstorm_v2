# v1/hpcrypto/telegram_utils.py
import logging
import requests
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from decimal import Decimal

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id, message, parse_mode='HTML'):
    """
    Simple wrapper function for GT app that sends a message to a Telegram chat
    
    Args:
        chat_id (str): Telegram chat ID
        message (str): Message to send
        parse_mode (str): Message parse mode (HTML, Markdown, etc.)
        
    Returns:
        bool: Success status (True/False)
    """
    # Reuse the existing send_telegram_notification function
    success, _ = send_telegram_notification(chat_id, message, parse_mode)
    return success

def send_telegram_notification(chat_id, message, parse_mode='HTML'):
    """
    Send a message to a Telegram chat
    
    Args:
        chat_id (str): Telegram chat ID
        message (str): Message to send
        parse_mode (str): Message parse mode (HTML, Markdown, etc.)
        
    Returns:
        bool: True if successful, False otherwise
        dict: Response data if successful, error message otherwise
    """
    if not hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN is not configured in settings")
        return False, "Telegram bot token is not configured"
    
    bot_token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Rate limiting - don't spam Telegram API
    rate_limit_key = f"telegram_rate_limit_{chat_id}"
    if cache.get(rate_limit_key):
        logger.warning(f"Rate limiting Telegram notification to chat {chat_id}")
        return False, "Rate limited"
    
    # Set short rate limit to avoid spam
    cache.set(rate_limit_key, True, 2)  # 2 second rate limit
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode
    }
    
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.info(f"Telegram notification sent to chat {chat_id}")
            return True, response_data
        else:
            error_msg = f"Telegram API error: {response_data.get('description', 'Unknown error')}"
            logger.error(error_msg)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error sending Telegram notification: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def format_alert_message_for_telegram(alert, with_html=True):
    """
    Format a price alert notification for Telegram with HTML formatting
    
    Args:
        alert (PriceAlert): The alert object
        with_html (bool): Whether to include HTML formatting
        
    Returns:
        str: Formatted message
    """
    try:
        position = alert.position
        ticker = position.ticker
        
        # Ensure proper conversion to Decimal to avoid type errors
        current_price = Decimal(str(position.current_price)) if position.current_price else Decimal('0')
        threshold = Decimal(str(alert.threshold_value))
        
        # Common information
        alert_type = alert.get_alert_type_display()
        entry_price = Decimal(str(position.entry_price)) if position.entry_price else Decimal('0')
        quantity = position.quantity
        position_size = Decimal(str(position.position_size)) if position.position_size else Decimal('0')
        
        # Safe conversion of PnL values
        pnl_dollar = Decimal(str(position.profit_loss_dollar)) if position.profit_loss_dollar is not None else None
        pnl_percent = Decimal(str(position.profit_loss_percent)) if position.profit_loss_percent is not None else None
        
        if with_html:
            # HTML version with formatting
            if alert.alert_type == 'PRICE_ABOVE':
                message = f"🚨 🔔 <b>Alert: {ticker} Price Above Threshold</b> 🔔 🚨\n\n"
                message += f"💹 <b>{ticker}</b> price is now <b>${current_price:.4f}</b>, above your threshold of ${threshold:.4f}! 🎯\n\n"
            elif alert.alert_type == 'PRICE_BELOW':
                message = f"🚨 🔔 <b>Alert: {ticker} Price Below Threshold</b> 🔔 🚨\n\n"
                message += f"📉 <b>{ticker}</b> price is now <b>${current_price:.4f}</b>, below your threshold of ${threshold:.4f}! 🎯\n\n"
            elif alert.alert_type == 'PCT_INCREASE':
                if entry_price == 0:
                    pct_change = Decimal('0')
                else:
                    pct_change = ((current_price - entry_price) / entry_price) * 100
                message = f"🚨 🔔 <b>Alert: {ticker} Price Increase</b> 🔔 🚨\n\n"
                message += f"🚀 <b>{ticker}</b> increased by <b>{pct_change:.2f}%</b>, above your threshold of {threshold:.2f}%! 📈\n\n"
            elif alert.alert_type == 'PCT_DECREASE':
                if entry_price == 0:
                    pct_change = Decimal('0')
                else:
                    pct_change = ((entry_price - current_price) / entry_price) * 100
                message = f"🚨 🔔 <b>Alert: {ticker} Price Decrease</b> 🔔 🚨\n\n"
                message += f"📉 <b>{ticker}</b> decreased by <b>{pct_change:.2f}%</b>, above your threshold of {threshold:.2f}%! ⚠️\n\n"
            else:
                message = f"🚨 🔔 <b>Alert: {ticker} Alert Triggered</b> 🔔 🚨\n\n"
                message += f"⚡ Your <b>{alert_type}</b> alert for <b>{ticker}</b> has been triggered! ⚡\n\n"
                
            # Add position details
            message += "📊 <b>Position Details:</b>\n"
            message += f"💰 Current Price: <b>${current_price:.4f}</b>\n"
            message += f"🏁 Entry Price: <b>${entry_price:.4f}</b>\n"
            message += f"🔢 Quantity: <b>{quantity}</b>\n"
            message += f"💵 Position Size: <b>${position_size:.2f}</b>\n"
            
            # Add notes if available
            if position.notes and position.notes.strip():
                message += f"\n📝 <b>Position Notes:</b>\n{position.notes}\n"
            
            # Add alert notes if available
            if alert.notes and alert.notes.strip():
                message += f"\n🔍 <b>Alert Notes:</b>\n{alert.notes}\n"
            
            # Add P&L information if available
            if pnl_dollar is not None and pnl_percent is not None:
                if pnl_dollar >= 0:
                    profit_or_loss = "Profit"
                    emoji = "🤑 💰"
                else:
                    profit_or_loss = "Loss"
                    emoji = "📉 💸"
                    
                message += f"\n{emoji} <b>Current {profit_or_loss}:</b>\n"
                message += f"💲 ${pnl_dollar:.2f} ({pnl_percent:.2f}%)\n"
        else:
            # Plain text version without HTML
            if alert.alert_type == 'PRICE_ABOVE':
                message = f"🚨 Alert: {ticker} Price Above Threshold 🚨\n\n"
                message += f"💹 {ticker} price is now ${current_price:.4f}, above your threshold of ${threshold:.4f}! 🎯\n\n"
            elif alert.alert_type == 'PRICE_BELOW':
                message = f"🚨 Alert: {ticker} Price Below Threshold 🚨\n\n"
                message += f"📉 {ticker} price is now ${current_price:.4f}, below your threshold of ${threshold:.4f}! 🎯\n\n"
            elif alert.alert_type == 'PCT_INCREASE':
                if entry_price == 0:
                    pct_change = Decimal('0')
                else:
                    pct_change = ((current_price - entry_price) / entry_price) * 100
                message = f"🚨 Alert: {ticker} Price Increase 🚨\n\n"
                message += f"🚀 {ticker} increased by {pct_change:.2f}%, above your threshold of {threshold:.2f}%! 📈\n\n"
            elif alert.alert_type == 'PCT_DECREASE':
                if entry_price == 0:
                    pct_change = Decimal('0')
                else:
                    pct_change = ((entry_price - current_price) / entry_price) * 100
                message = f"🚨 Alert: {ticker} Price Decrease 🚨\n\n"
                message += f"📉 {ticker} decreased by {pct_change:.2f}%, above your threshold of {threshold:.2f}%! ⚠️\n\n"
            else:
                message = f"🚨 Alert: {ticker} Alert Triggered 🚨\n\n"
                message += f"⚡ Your {alert_type} alert for {ticker} has been triggered! ⚡\n\n"
                
            # Add position details
            message += "📊 Position Details:\n"
            message += f"💰 Current Price: ${current_price:.4f}\n"
            message += f"🏁 Entry Price: ${entry_price:.4f}\n"
            message += f"🔢 Quantity: {quantity}\n"
            message += f"💵 Position Size: ${position_size:.2f}\n"
            
            # Add notes if available
            if position.notes and position.notes.strip():
                message += f"\n📝 Position Notes:\n{position.notes}\n"
            
            # Add alert notes if available
            if alert.notes and alert.notes.strip():
                message += f"\n🔍 Alert Notes:\n{alert.notes}\n"
            
            # Add P&L information if available
            if pnl_dollar is not None and pnl_percent is not None:
                if pnl_dollar >= 0:
                    profit_or_loss = "Profit"
                    emoji = "🤑 💰"
                else:
                    profit_or_loss = "Loss"
                    emoji = "📉 💸"
                    
                message += f"\n{emoji} Current {profit_or_loss}:\n"
                message += f"💲 ${pnl_dollar:.2f} ({pnl_percent:.2f}%)\n"
        
        return message
    except Exception as e:
        logger.error(f"Error formatting telegram message: {str(e)}")
        # Return a simple fallback message that won't cause further errors
        return f"🚨 Alert triggered for {alert.position.ticker} ({alert.get_alert_type_display()})" 