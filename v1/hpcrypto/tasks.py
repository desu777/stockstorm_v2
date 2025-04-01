# hpcrypto/tasks.py
import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from celery import shared_task
import json

from home.models import UserProfile, TelegramConfig
from .models import Position, PriceAlert, PendingOrder, HPCategory
from .utils import get_bulk_binance_prices
from .telegram_utils import send_telegram_notification, format_alert_message_for_telegram

User = get_user_model()
logger = logging.getLogger(__name__)

def update_all_prices():
    """
    Update prices for all users with positions.
    This is the main entry point for the background price update service.
    """
    logger.info("Starting background price update service")
    
    try:
        # Get all users with positions
        users_with_positions = User.objects.filter(
            position__isnull=False
        ).distinct()
        
        user_count = users_with_positions.count()
        logger.info(f"Found {user_count} users with active positions")
        
        if user_count == 0:
            logger.info("No users with active positions, skipping price update")
            return
        
        updated_positions = 0
        errors = 0
        
        for user in users_with_positions:
            try:
                # Update prices for this user
                updated = update_prices_for_user(user)
                if updated is not None:
                    updated_positions += updated
            except Exception as e:
                logger.error(f"Error updating prices for user {user.id}: {str(e)}")
                errors += 1
        
        logger.info(f"Price update service completed. Updated {updated_positions} positions for {user_count} users. Errors: {errors}")
        return updated_positions
        
    except Exception as e:
        logger.error(f"Error in price update service: {str(e)}")
        return None

def update_prices_for_user(user):
    """
    Update prices for all active positions for a specific user.
    Uses the user's Binance API credentials to fetch prices.
    If user has no API credentials, falls back to public API.
    
    Args:
        user: User object
        
    Returns:
        int: Number of positions updated or None if error
    """
    try:
        # Get all active positions for this user (pozycje bez exit_price)
        positions = Position.objects.filter(user=user, exit_price=None)
        if not positions.exists():
            logger.debug(f"User {user.id} has no active positions, skipping")
            return 0
        
        # Get all unique tickers
        tickers = positions.values_list('ticker', flat=True).distinct()
        
        # Fetch prices in bulk for all tickers - now falls back to public API if no credentials
        prices = get_bulk_binance_prices(user, tickers)
        if not prices:
            logger.warning(f"Failed to fetch prices for user {user.id}")
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
        
        logger.info(f"Updated {updated_count} positions for user {user.id}")
        return updated_count
        
    except Exception as e:
        logger.error(f"Error updating prices for user {user.id}: {str(e)}")
        return None

def check_alerts_for_position(position):
    """
    Check if any price alerts are triggered for a position.
    If so, mark them as triggered and send notifications.
    
    Args:
        position: Position object with updated current_price
    """
    if not position.current_price:
        return
    
    try:
        # Get all active, non-triggered alerts for this position
        alerts = PriceAlert.objects.filter(
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
            logger.info(f"Triggered {triggered_count} alerts for position {position.id} ({position.ticker})")
    
    except Exception as e:
        logger.error(f"Error checking alerts for position {position.id}: {str(e)}")

def send_alert_notification(alert):
    """
    Send notification for a triggered alert.
    Currently supports Telegram notifications.
    
    Args:
        alert: PriceAlert object that was triggered
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
                logger.info(f"Sent Telegram notification for alert {alert.id} to user {user.id}")
        
        # Add support for other notification channels here (email, push, etc.)
        
    except Exception as e:
        logger.error(f"Error sending notification for alert {alert.id}: {str(e)}")

@shared_task
def check_pending_orders():
    """
    Sprawdza status oczekujących zleceń stop-limit na Binance.
    - Pobiera wszystkie aktywne zlecenia
    - Sprawdza ich status na Binance
    - Aktualizuje status zleceń w bazie danych
    - Dla wykonanych zleceń dodaje pozycje do HP Crypto
    """
    logger.info("Rozpoczynam sprawdzanie oczekujących zleceń stop-limit")
    
    try:
        # Pobierz wszystkie aktywne zlecenia
        active_orders = PendingOrder.objects.filter(
            status__in=['WAITING', 'CREATED']
        ).select_related('user', 'position', 'category')
        
        if not active_orders.exists():
            logger.info("Brak aktywnych zleceń do sprawdzenia")
            return 0
            
        logger.info(f"Znaleziono {active_orders.count()} aktywnych zleceń")
        
        # Zliczanie wyników
        orders_created = 0
        orders_executed = 0
        orders_with_errors = 0
        
        # Dla każdego aktywnego zlecenia
        for order in active_orders:
            try:
                # Pobierz użytkownika i jego profil
                user = order.user
                profile = getattr(user, 'profile', None)
                
                # Sprawdź czy użytkownik ma klucze API
                if not profile or not profile.binance_api_key or not profile.binance_api_secret_enc:
                    logger.warning(f"Użytkownik {user.id} nie ma skonfigurowanych kluczy API Binance")
                    order.status = 'ERROR'
                    order.error_message = "Brak kluczy API Binance"
                    order.save()
                    orders_with_errors += 1
                    continue
                
                # Import klienta Binance
                from binance.client import Client
                from binance.exceptions import BinanceAPIException
                
                # Inicjalizuj klienta Binance
                api_key = profile.binance_api_key
                api_secret = profile.get_binance_api_secret()
                client = Client(api_key, api_secret)
                
                # Sprawdź status zlecenia
                if order.status == 'WAITING':
                    # Zlecenie czeka na utworzenie na Binance
                    try:
                        # Przygotuj parametry zlecenia
                        symbol = order.get_trading_pair
                        
                        # Tworzenie zlecenia stop-limit
                        params = {
                            'symbol': symbol,
                            'side': 'BUY' if order.order_type == 'STOP_LIMIT_BUY' else 'SELL',
                            'type': 'STOP_LIMIT',
                            'timeInForce': 'GTC',  # Good Till Cancelled
                            'price': str(order.limit_price),  # Cena limit
                            'stopPrice': str(order.trigger_price),  # Cena trigger
                        }
                        
                        # Dodaj ilość lub wartość, zależnie od typu zlecenia
                        if order.order_type == 'STOP_LIMIT_BUY':
                            # Oblicz ilość do kupna
                            ticker_data = client.get_symbol_ticker(symbol=symbol)
                            current_price = float(ticker_data['price'])
                            quantity = float(order.amount) / current_price
                            
                            # Zaokrąglij ilość zgodnie z wymaganiami Binance
                            # Tutaj można dodać dodatkową logikę do dostosowania precyzji
                            quantity = round(quantity, 6)
                            
                            params['quantity'] = str(quantity)
                        else:
                            # Dla sprzedaży używamy bezpośrednio ilości
                            params['quantity'] = str(order.amount)
                        
                        # Utwórz zlecenie na Binance
                        binance_order = client.create_order(**params)
                        
                        # Aktualizuj dane zlecenia
                        order.status = 'CREATED'
                        order.binance_order_id = binance_order.get('orderId')
                        order.binance_client_order_id = binance_order.get('clientOrderId')
                        order.last_checked = timezone.now()
                        order.save()
                        
                        logger.info(f"Utworzono zlecenie na Binance: {order.binance_order_id}")
                        orders_created += 1
                        
                    except BinanceAPIException as e:
                        # Obsługa błędów z API Binance
                        order.status = 'ERROR'
                        order.error_message = f"Błąd API Binance: {e.message}"
                        order.retry_count += 1
                        order.save()
                        logger.error(f"Błąd podczas tworzenia zlecenia: {e.message}")
                        orders_with_errors += 1
                        
                elif order.status == 'CREATED':
                    # Zlecenie istnieje na Binance, sprawdź jego status
                    try:
                        # Pobierz status zlecenia z Binance
                        binance_order = client.get_order(
                            symbol=order.get_trading_pair,
                            orderId=order.binance_order_id
                        )
                        
                        # Aktualizuj czas ostatniego sprawdzenia
                        order.last_checked = timezone.now()
                        
                        # Sprawdź status zlecenia
                        binance_status = binance_order.get('status')
                        
                        if binance_status == 'FILLED':
                            # Zlecenie zostało wykonane
                            
                            # Pobierz szczegóły wykonanego zlecenia
                            executed_qty = float(binance_order.get('executedQty', 0))
                            executed_price = float(binance_order.get('price', order.limit_price))
                            
                            # Aktualizuj status zlecenia
                            order.status = 'EXECUTED'
                            order.executed_at = timezone.now()
                            order.save()
                            
                            # Obsługa kupna/sprzedaży i dodanie/aktualizacja pozycji w HP Crypto
                            if order.order_type == 'STOP_LIMIT_BUY':
                                # Znajdź lub utwórz kategorię
                                category = order.category
                                if not category:
                                    # Utwórz domyślną kategorię jeśli nie istnieje
                                    category_name = f"{order.symbol} HP"
                                    category, _ = HPCategory.objects.get_or_create(
                                        user=user,
                                        name=category_name,
                                        defaults={'description': "Kategoria utworzona automatycznie przez system zleceń"}
                                    )
                                
                                # Utwórz nową pozycję
                                position = Position(
                                    user=user,
                                    category=category,
                                    ticker=order.symbol,
                                    quantity=Decimal(str(executed_qty)),
                                    entry_price=Decimal(str(executed_price)),
                                    current_price=Decimal(str(executed_price)),
                                    last_price_update=timezone.now(),
                                    notes=f"Pozycja utworzona przez zlecenie stop-limit (ID: {order.id})"
                                )
                                position.save()
                                
                                logger.info(f"Utworzono nową pozycję dla zlecenia {order.id}")
                                
                            elif order.order_type == 'STOP_LIMIT_SELL':
                                # Aktualizuj istniejącą pozycję
                                position = order.position
                                if position:
                                    position.exit_price = Decimal(str(executed_price))
                                    position.exit_date = timezone.now()
                                    position.notes = (position.notes or "") + f" [Sprzedano przez zlecenie stop-limit {order.id}]"
                                    position.save()
                                    
                                    logger.info(f"Zaktualizowano pozycję {position.id} po sprzedaży")
                                else:
                                    logger.warning(f"Nie znaleziono pozycji dla zlecenia sprzedaży {order.id}")
                            
                            orders_executed += 1
                            
                        elif binance_status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                            # Zlecenie zostało anulowane lub odrzucone
                            order.status = 'CANCELLED'
                            order.error_message = f"Zlecenie na Binance ma status: {binance_status}"
                            order.save()
                            
                    except BinanceAPIException as e:
                        # Obsługa błędów z API Binance
                        order.retry_count += 1
                        
                        # Jeśli błąd dotyczy nieistniejącego zlecenia, oznacz jako anulowane
                        if "Order does not exist" in e.message:
                            order.status = 'CANCELLED'
                            order.error_message = "Zlecenie nie istnieje na Binance"
                        else:
                            order.error_message = f"Błąd API Binance: {e.message}"
                        
                        order.save()
                        logger.error(f"Błąd podczas sprawdzania zlecenia: {e.message}")
                        orders_with_errors += 1
                
            except Exception as e:
                # Obsługa innych błędów
                logger.error(f"Nieoczekiwany błąd dla zlecenia {order.id}: {str(e)}")
                order.error_message = f"Nieoczekiwany błąd: {str(e)}"
                order.retry_count += 1
                order.save()
                orders_with_errors += 1
        
        logger.info(f"Zakończono sprawdzanie zleceń. Utworzono: {orders_created}, Wykonano: {orders_executed}, Błędy: {orders_with_errors}")
        return orders_executed
        
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania zadania check_pending_orders: {str(e)}")
        return 0

@shared_task
def update_crypto_prices():
    """
    Celery task to update cryptocurrency prices for all positions.
    This is called periodically by the Celery beat scheduler.
    
    Returns:
        int or None: Number of positions updated or None if error
    """
    logger.info("Starting scheduled cryptocurrency price update task")
    return update_all_prices()