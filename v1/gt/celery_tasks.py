from celery import shared_task
import logging
from .models import StockPosition, StockPriceAlert
from .utils import get_bulk_stock_prices
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def update_stock_prices():
    """
    Aktualizuje ceny dla wszystkich aktywnych pozycji (bez exit_price)
    
    Wykorzystuje Alpha Vantage API do pobrania aktualnych cen
    """
    logger.info("Starting scheduled stock price update task")
    
    # Pobierz aktywne pozycje (bez ceny wyjścia)
    positions = StockPosition.objects.filter(exit_price=None)
    position_count = positions.count()
    
    if position_count == 0:
        logger.info("No active positions found, skipping update")
        return
    
    logger.info(f"Found {position_count} active positions to update")
    
    # Pobierz unikalne tickery
    tickers = list(positions.values_list('ticker', flat=True).distinct())
    logger.info(f"Found {len(tickers)} unique tickers to update: {', '.join(tickers)}")
    
    # Pobierz ceny z Alpha Vantage API
    prices = get_bulk_stock_prices(tickers)
    
    if not prices:
        logger.error("Failed to get any prices from Alpha Vantage API")
        return
    
    logger.info(f"Successfully fetched {len(prices)} ticker prices")
    
    # Aktualizuj ceny w bazie
    updated_count = 0
    for position in positions:
        if position.ticker in prices:
            position.current_price = prices[position.ticker]
            position.last_price_update = timezone.now()
            position.save(update_fields=['current_price', 'last_price_update'])
            updated_count += 1
    
    logger.info(f"Updated prices for {updated_count}/{position_count} positions")
    
    # Sprawdź alerty
    check_price_alerts()
    
    return updated_count

@shared_task
def check_price_alerts():
    """
    Sprawdza czy zostały spełnione warunki alertów cenowych
    """
    logger.info("Starting price alert check task")
    
    # Pobierz wszystkie nieuruchomione alerty
    alerts = StockPriceAlert.objects.filter(triggered=False)
    
    if not alerts.exists():
        logger.info("No active price alerts found")
        return
    
    logger.info(f"Found {alerts.count()} active price alerts to check")
    
    # Sprawdź każdy alert
    triggered_count = 0
    for alert in alerts:
        position = alert.position
        
        # Pomiń alerty dla pozycji bez aktualnej ceny
        if not position.current_price:
            continue
        
        current_price = position.current_price
        threshold = alert.threshold_value
        
        # Sprawdź warunki alertu
        triggered = False
        if alert.condition_type == 'above' and current_price >= threshold:
            triggered = True
        elif alert.condition_type == 'below' and current_price <= threshold:
            triggered = True
        
        # Jeśli alert został wywołany, zaktualizuj jego status
        if triggered:
            alert.triggered = True
            alert.last_triggered = timezone.now()
            alert.save(update_fields=['triggered', 'last_triggered'])
            triggered_count += 1
            
            logger.info(f"Alert triggered: {alert.position.ticker} {alert.condition_type} {alert.threshold_value} (current: {current_price})")
    
    logger.info(f"Triggered {triggered_count} price alerts")
    
    return triggered_count 