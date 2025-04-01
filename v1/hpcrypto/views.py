# hpcrypto/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from .models import HPCategory, Position, PriceAlert
from .forms import HPCategoryForm, PositionForm, PriceAlertForm
from home.models import UserProfile, TelegramConfig
from django.views.decorators.http import require_POST
from .telegram_utils import send_telegram_notification, format_alert_message_for_telegram
import logging
import json
import random
from .models import PendingOrder

logger = logging.getLogger(__name__)

@login_required
def position_list(request):
    """View all positions grouped by HP category"""
    # Get all categories for the user
    categories = HPCategory.objects.filter(user=request.user).prefetch_related('positions')
    
    # Initialize totals
    total_invested = Decimal('0')
    total_current_value = Decimal('0')
    total_profit_loss = Decimal('0')
    active_positions_count = 0
    closed_positions_count = 0
    
    # Calculate totals and prepare data for UI
    for category in categories:
        positions = category.positions.all()
        category_investment = Decimal('0')
        category_current_value = Decimal('0')
        category_pnl_dollar = Decimal('0')
        
        for position in positions:
            # Calculate position data
            entry_amount = position.entry_price * position.quantity
            if position.current_price:
                current_amount = position.current_price * position.quantity
                # Nie przypisujemy do position_size, które jest property
                # Zamiast tego używamy tymczasowego atrybutu current_value
                position.current_value = current_amount
                # Używamy tymczasowego atrybutu pnl_dollar zamiast profit_loss_dollar property
                position.pnl_dollar = current_amount - entry_amount
                if entry_amount > 0:
                    # Używamy tymczasowego atrybutu pnl_percent zamiast profit_loss_percent property
                    position.pnl_percent = (position.pnl_dollar / entry_amount) * 100
                else:
                    position.pnl_percent = Decimal('0')
            else:
                position.current_value = Decimal('0')
                position.pnl_dollar = Decimal('0')
                position.pnl_percent = Decimal('0')
            
            category_investment += entry_amount
            
            # Add to category totals
            if position.current_price:
                category_current_value += current_amount
                category_pnl_dollar += position.pnl_dollar
            
            # Count active/closed positions
            if position.exit_price is None:
                active_positions_count += 1
            else:
                closed_positions_count += 1
        
        # Set category values for template
        category.total_invested = category_investment
        category.current_value = category_current_value
        category.pnl_dollar = category_pnl_dollar
        category.pnl_percent = (category_pnl_dollar / category_investment * 100) if category_investment > 0 else Decimal('0')
        
        # Add to portfolio totals
        total_invested += category_investment
        total_current_value += category_current_value
    
    # Calculate portfolio profit/loss
    total_profit_loss = total_current_value - total_invested
    total_profit_loss_percent = (total_profit_loss / total_invested * 100) if total_invested > 0 else Decimal('0')
    
    context = {
        'categories': categories,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'total_profit_loss_percent': total_profit_loss_percent,
        'active_positions_count': active_positions_count,
        'closed_positions_count': closed_positions_count,
        'now': timezone.now(),
    }
    
    return render(request, 'position_list.html', context)

@login_required
def add_category(request):
    """Add a new HP category"""
    if request.method == 'POST':
        form = HPCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect('position_list')
    else:
        form = HPCategoryForm()
    
    return render(request, 'category_form.html', {
        'form': form,
        'title': 'Add New HP Category'
    })

@login_required
def edit_category(request, category_id):
    """Edit an existing HP category"""
    category = get_object_or_404(HPCategory, id=category_id, user=request.user)
    if request.method == 'POST':
        form = HPCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect('position_list')
    else:
        form = HPCategoryForm(instance=category)
    
    return render(request, 'category_form.html', {
        'form': form,
        'title': f'Edit Category: {category.name}'
    })

@login_required
def delete_category(request, category_id):
    """Delete an HP category and all associated positions"""
    category = get_object_or_404(HPCategory, id=category_id, user=request.user)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' and all its positions have been deleted.")
        return redirect('position_list')
    
    return render(request, 'confirm_delete.html', {
        'object': category,
        'title': f'Delete Category: {category.name}',
        'message': 'This will delete the category and ALL positions within it. This action cannot be undone.'
    })

@login_required
def add_position(request):
    """Add a new position"""
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            position = form.save(commit=False)
            position.user = request.user
            position.save()
            
            # Try to fetch current price
            try:
                from hpcrypto.utils import get_binance_price
                current_price = get_binance_price(request.user, position.ticker)
                if current_price:
                    position.current_price = current_price
                    position.last_price_update = timezone.now()
                    position.save()
            except Exception as e:
                messages.warning(request, f"Position created, but couldn't fetch price: {str(e)}")
            
            messages.success(request, f"Position for {position.ticker} added successfully.")
            return redirect('position_list')
    else:
        # Only show categories for this user
        form = PositionForm()
        form.fields['category'].queryset = HPCategory.objects.filter(user=request.user)
    
    return render(request, 'position_form.html', {
        'form': form,
        'title': 'Add New Position'
    })

@login_required
def edit_position(request, position_id):
    """Edit an existing position"""
    position = get_object_or_404(Position, id=position_id, user=request.user)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            messages.success(request, f"Position for {position.ticker} updated successfully.")
            return redirect('position_list')
    else:
        form = PositionForm(instance=position)
        form.fields['category'].queryset = HPCategory.objects.filter(user=request.user)
    
    return render(request, 'position_form.html', {
        'form': form,
        'title': f'Edit Position: {position.ticker}',
        'position': position
    })

@login_required
def delete_position(request, position_id):
    """Delete a position"""
    position = get_object_or_404(Position, id=position_id, user=request.user)
    position.delete()
    return redirect('position_list')

@login_required
def add_alert(request, position_id):
    """Add a price alert for a position"""
    position = get_object_or_404(Position, id=position_id, user=request.user)
    
    # Get user's telegram config to show status
    telegram_config = TelegramConfig.objects.filter(user=request.user, is_verified=True).first()
    
    if request.method == 'POST':
        form = PriceAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.position = position
            alert.save()
            messages.success(request, f"Alert for {position.ticker} created successfully.")
            return redirect('position_detail', position_id=position.id)
    else:
        form = PriceAlertForm()
    
    return render(request, 'alert_form.html', {
        'form': form,
        'position': position,
        'telegram_config': telegram_config,
        'title': f'Add Alert for {position.ticker}'
    })

@login_required
def position_detail(request, position_id):
    """Show details of a position and its price alerts"""
    position = get_object_or_404(Position, id=position_id, user=request.user)
    alerts = position.alerts.all()
    
    # For any alerts that are being processed (actively checking), mark them with a waiting status
    # This only affects the template display, not the database
    for alert in alerts:
        if alert.is_active and not alert.triggered:
            # Set a temporary attribute for template display
            alert.is_waiting = True
    
    return render(request, 'position_detail.html', {
        'position': position,
        'alerts': alerts,
    })

@login_required
@require_POST
def update_prices(request):
    """Update prices for all positions and return updated data"""
    try:
        # Get user's positions
        positions = Position.objects.filter(user=request.user)
        
        # Import here to avoid circular imports
        from .utils import get_bulk_binance_prices
        
        # Track updated data
        updated_data = []
        category_totals = {}
        
        # Portfolio summary data
        total_invested = Decimal('0')
        total_current_value = Decimal('0')
        total_profit_loss = Decimal('0')
        active_positions_count = 0
        closed_positions_count = 0
        
        # Extract all unique tickers for bulk price fetching
        tickers = [position.ticker for position in positions]
        
        # Fetch all prices at once from Binance
        ticker_prices = get_bulk_binance_prices(request.user, tickers)
        
        # Update prices for each position
        for position in positions:
            try:
                # Get price from the bulk result
                new_price = ticker_prices.get(position.ticker)
                
                if new_price:
                    position.current_price = Decimal(str(new_price))
                    position.last_price_update = timezone.now()
                    position.save(update_fields=['current_price', 'last_price_update'])
                    
                    # Calculate P&L
                    pnl_dollar = position.profit_loss_dollar
                    pnl_percent = position.profit_loss_percent
                    
                    # Track active/closed positions and calculate portfolio totals
                    if position.exit_price is not None:
                        closed_positions_count += 1
                    else:
                        active_positions_count += 1
                        total_current_value += (position.current_price or 0) * position.quantity
                    
                    # Add to portfolio totals
                    total_invested += position.position_size
                    total_profit_loss += pnl_dollar or 0
                    
                    # Initialize category totals if needed
                    if position.category_id not in category_totals:
                        category_totals[position.category_id] = {
                            'id': position.category_id,
                            'total_investment': Decimal('0'),
                            'total_pnl_dollar': Decimal('0'),
                            'total_pnl_percent': Decimal('0')
                        }
                    
                    # Update category totals
                    category_totals[position.category_id]['total_investment'] += position.position_size
                    category_totals[position.category_id]['total_pnl_dollar'] += pnl_dollar or 0
                    
                    # Add position data to update
                    updated_data.append({
                        'id': position.id,
                        'current_price': float(position.current_price),
                        'pnl_dollar': float(pnl_dollar) if pnl_dollar is not None else 0,
                        'pnl_percent': float(pnl_percent) if pnl_percent is not None else 0,
                        'last_update_timestamp': position.last_price_update.isoformat() if position.last_price_update else None,
                        'quantity': float(position.quantity)
                    })
                else:
                    logger.warning(f"Could not get price for {position.ticker} from Binance")
                
            except Exception as e:
                logger.error(f"Error updating price for position {position.id}: {e}")
        
        # Calculate percentage changes for categories
        for cat_id, cat_data in category_totals.items():
            if cat_data['total_investment'] > 0:
                cat_data['total_pnl_percent'] = (cat_data['total_pnl_dollar'] / cat_data['total_investment'] * 100)
            
            # Convert Decimal to float for JSON serialization
            cat_data['total_investment'] = float(cat_data['total_investment'])
            cat_data['total_pnl_dollar'] = float(cat_data['total_pnl_dollar'])
            cat_data['total_pnl_percent'] = float(cat_data['total_pnl_percent'])
        
        # Calculate percentage change for entire portfolio
        profit_loss_percentage = (total_profit_loss / total_invested * 100) if total_invested else 0
        
        # Check for triggered alerts
        triggered_alerts = check_price_alerts()
        
        # Prepare portfolio summary data
        portfolio_summary = {
            'total_invested': float(total_invested),
            'total_current_value': float(total_current_value),
            'total_profit_loss': float(total_profit_loss),
            'profit_loss_percentage': float(profit_loss_percentage),
            'active_positions_count': active_positions_count,
            'closed_positions_count': closed_positions_count,
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Updated prices for {len(updated_data)} positions',
            'positions_data': updated_data,
            'categories': list(category_totals.values()),
            'portfolio': portfolio_summary,
            'triggered_alerts': triggered_alerts
        })
        
    except Exception as e:
        logger.error(f"Error in update_prices: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

def check_price_alerts():
    """Check all active price alerts and mark triggered ones, send push notifications if configured"""
    # Fetch all active and not-yet-triggered alerts
    alerts = PriceAlert.objects.filter(is_active=True, triggered=False)
    logger.info(f"Checking {alerts.count()} active price alerts")
    triggered = []
    
    for alert in alerts:
        position = alert.position
        if not position.current_price:
            logger.warning(f"Alert {alert.id} for {position.ticker}: No current price available, skipping")
            continue
        
        # Ensure we're working with Decimal objects to avoid floating-point issues
        current_price = Decimal(str(position.current_price))
        entry_price = Decimal(str(position.entry_price))
        threshold = Decimal(str(alert.threshold_value))
        
        # Debug info for all alerts
        logger.info(f"Checking alert {alert.id} for {position.ticker}: type={alert.alert_type}, "
                   f"current={current_price}, entry={entry_price}, threshold={threshold}")
        
        trigger = False
        if alert.alert_type == 'PRICE_ABOVE' and current_price >= threshold:
            trigger = True
            logger.info(f"Alert {alert.id} for {position.ticker}: PRICE_ABOVE triggered, current: {current_price}, threshold: {threshold}")
        elif alert.alert_type == 'PRICE_BELOW' and current_price <= threshold:
            trigger = True
            logger.info(f"Alert {alert.id} for {position.ticker}: PRICE_BELOW triggered, current: {current_price}, threshold: {threshold}")
        elif alert.alert_type == 'PCT_INCREASE':
            if entry_price == 0:
                logger.warning(f"Alert {alert.id} for {position.ticker}: Cannot calculate PCT_INCREASE, entry price is zero")
                continue
                
            pct_change = ((current_price - entry_price) / entry_price) * 100
            logger.info(f"Alert {alert.id} for {position.ticker}: PCT_INCREASE checking, pct_change: {pct_change:.2f}%, threshold: {threshold}%")
            if pct_change >= threshold:
                trigger = True
                logger.info(f"Alert {alert.id} for {position.ticker}: PCT_INCREASE triggered")
        elif alert.alert_type == 'PCT_DECREASE':
            if entry_price == 0:
                logger.warning(f"Alert {alert.id} for {position.ticker}: Cannot calculate PCT_DECREASE, entry price is zero")
                continue
                
            pct_change = ((entry_price - current_price) / entry_price) * 100
            logger.info(f"Alert {alert.id} for {position.ticker}: PCT_DECREASE checking, pct_change: {pct_change:.2f}%, threshold: {threshold}%")
            if pct_change >= threshold:
                trigger = True
                logger.info(f"Alert {alert.id} for {position.ticker}: PCT_DECREASE triggered with decrease of {pct_change:.2f}%")
        
        if trigger:
            logger.info(f"🔔 ALERT TRIGGERED: {alert.id} for {position.ticker} ({alert.alert_type})")
            now = timezone.now()
            alert.triggered = True
            alert.last_triggered = now
            
            # Get user profile for notification settings
            user = position.user
            user_profile = getattr(user, 'userprofile', None)
            notifications_sent = False
            
            # Send Telegram notification if configured
            if alert.notify_telegram and user_profile and user_profile.telegram_notifications_enabled:
                logger.info(f"Sending Telegram notification for alert {alert.id}")
                try:
                    # Try to get the user's Telegram config
                    telegram_config = TelegramConfig.objects.get(user=user, is_verified=True)
                    chat_id = telegram_config.chat_id
                    
                    # Format message for Telegram
                    telegram_message = format_alert_message_for_telegram(alert)
                    
                    # Send the notification
                    success, result = send_telegram_notification(chat_id, telegram_message)
                    if success:
                        notifications_sent = True
                        logger.info(f"Telegram notification sent for alert {alert.id} to chat_id {chat_id}")
                    else:
                        logger.error(f"Failed to send Telegram notification for alert {alert.id}: {result}")
                except TelegramConfig.DoesNotExist:
                    logger.warning(f"User {user.id} has Telegram notifications enabled but no verified Telegram config")
                except Exception as e:
                    logger.error(f"Error sending Telegram notification for alert {alert.id}: {str(e)}")
            
            # Update alert status
            if notifications_sent:
                alert.notification_sent = True
                alert.last_notification_sent = now
            
            alert.save()
            
            # Add to triggered list for response
            triggered.append({
                "id": alert.id,
                "position": position.ticker,
                "type": alert.get_alert_type_display(),
                "threshold": float(alert.threshold_value),
                "current_price": float(position.current_price),
                "notification_sent": alert.notification_sent
            })
    
    logger.info(f"Finished checking price alerts. Triggered {len(triggered)} alerts.")
    return triggered

@login_required
def edit_alert(request, alert_id):
    """Edit an existing price alert"""
    alert = get_object_or_404(PriceAlert, id=alert_id)
    position = alert.position
    
    # Check if this alert belongs to the user
    if position.user != request.user:
        messages.error(request, "You don't have permission to edit this alert.")
        return redirect('position_list')
    
    # Get user's telegram config to show status
    telegram_config = TelegramConfig.objects.filter(user=request.user, is_verified=True).first()
    
    if request.method == 'POST':
        form = PriceAlertForm(request.POST, instance=alert)
        if form.is_valid():
            # Reset triggered status if threshold changed
            if 'threshold_value' in form.changed_data:
                alert = form.save(commit=False)
                alert.triggered = False
                alert.last_triggered = None
                alert.save()
            else:
                form.save()
            
            messages.success(request, f"Alert for {position.ticker} updated successfully.")
            return redirect('position_detail', position_id=position.id)
    else:
        form = PriceAlertForm(instance=alert)
    
    return render(request, 'alert_form.html', {
        'form': form,
        'position': position,
        'telegram_config': telegram_config,
        'title': f'Edit Alert for {position.ticker}'
    })

@login_required
def delete_alert(request, alert_id):
    """Delete a price alert"""
    alert = get_object_or_404(PriceAlert, id=alert_id)
    position = alert.position
    
    # Check if this alert belongs to the user
    if position.user != request.user:
        messages.error(request, "You don't have permission to delete this alert.")
        return redirect('position_list')
    
    if request.method == 'POST':
        ticker = position.ticker
        alert_type = alert.get_alert_type_display()
        alert.delete()
        messages.success(request, f"{alert_type} alert for {ticker} deleted successfully.")
        return redirect('position_detail', position_id=position.id)
    
    return render(request, 'confirm_delete.html', {
        'object': alert,
        'object_name': f"{alert.get_alert_type_display()} alert for {position.ticker}",
        'cancel_url': f'/hpcrypto/position/{position.id}/'
    })

@login_required
def refresh_position_price(request, position_id):
    """Refresh price for a specific position from Binance"""
    position = get_object_or_404(Position, id=position_id, user=request.user)
    
    try:
        # Import here to avoid circular imports
        from .utils import get_binance_price
        
        # Get updated price from Binance
        current_price = get_binance_price(request.user, position.ticker)
        
        if current_price:
            # Convert to Decimal for consistency (since current_price comes as float from Binance)
            current_price_decimal = Decimal(str(current_price))
            
            # Update position with new price
            position.current_price = current_price_decimal
            position.last_price_update = timezone.now()
            position.save()
            
            # Calculate position size and PnL
            position_size = position.quantity * position.current_price
            
            # Calculate profit/loss
            if position.entry_price:
                profit_loss = (position.current_price - position.entry_price) * position.quantity
                profit_loss_percentage = (position.current_price - position.entry_price) / position.entry_price * 100
            else:
                profit_loss = None
                profit_loss_percentage = None
            
            # Check if any alerts are triggered
            from .tasks import check_alerts_for_position
            check_alerts_for_position(position)
            
            # Return success response with data
            return JsonResponse({
                'success': True,
                'message': f'Price for {position.ticker} updated successfully from Binance',
                'current_price': float(position.current_price),
                'position_size': float(position_size),
                'profit_loss': float(profit_loss) if profit_loss is not None else None,
                'profit_loss_percentage': float(profit_loss_percentage) if profit_loss_percentage is not None else None,
                'last_update': position.last_price_update.isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Could not fetch price for {position.ticker} from Binance. Make sure you entered the ticker in the correct format (e.g., BTCUSDT, ETHUSDC).'
            })
    
    except Exception as e:
        logger.error(f"Error refreshing price for position {position_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving price: {str(e)}. Make sure your Binance API credentials are valid and the ticker format is correct.'
        }, status=500)

@login_required
def cancel_order(request, order_id):
    """Cancel a pending order"""
    order = get_object_or_404(PendingOrder, id=order_id, user=request.user)
    
    try:
        # Jeśli zlecenie jest w stanie CREATED, anuluj je na Binance
        if order.status == 'CREATED' and order.binance_order_id:
            # Pobierz profil użytkownika z kluczami API
            profile = getattr(request.user, 'profile', None)
            
            if profile and profile.binance_api_key and profile.binance_api_secret_enc:
                from binance.client import Client
                from binance.exceptions import BinanceAPIException
                
                # Inicjalizuj klienta Binance
                api_key = profile.binance_api_key
                api_secret = profile.get_binance_api_secret()
                client = Client(api_key, api_secret)
                
                try:
                    # Anuluj zlecenie na Binance
                    client.cancel_order(
                        symbol=order.get_trading_pair,
                        orderId=order.binance_order_id
                    )
                    messages.success(request, "Zlecenie zostało anulowane na Binance.")
                except BinanceAPIException as e:
                    # Jeśli zlecenie nie istnieje na Binance, kontynuuj
                    if "Unknown order" in e.message:
                        messages.warning(request, "Zlecenie nie istnieje już na Binance, ale zostanie oznaczone jako anulowane.")
                    else:
                        messages.error(request, f"Błąd podczas anulowania zlecenia na Binance: {e.message}")
                        # Loguj błąd, ale kontynuuj anulowanie w lokalnej bazie danych
                        logger.error(f"Error cancelling order {order_id} on Binance: {e}")
            else:
                messages.warning(request, "Brak kluczy API Binance, zlecenie zostanie tylko oznaczone jako anulowane w systemie.")
        
        # Zaktualizuj status zlecenia w bazie danych
        order.status = 'CANCELLED'
        order.save()
        
        messages.success(request, "Zlecenie zostało anulowane.")
        
    except Exception as e:
        messages.error(request, f"Wystąpił błąd podczas anulowania zlecenia: {str(e)}")
        logger.error(f"Error in cancel_order view: {e}")
    
    # Przekieruj z powrotem do listy pozycji
    return redirect('position_list')

@login_required
def view_order(request, order_id):
    """View details of a single order"""
    order = get_object_or_404(PendingOrder, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'order_detail.html', context)

@login_required
def category_detail(request, category_id):
    """View details of a specific category and its positions"""
    category = get_object_or_404(HPCategory, id=category_id, user=request.user)
    positions = category.positions.all()
    
    # Calculate category totals
    total_invested = sum(position.quantity * position.entry_price for position in positions)
    total_current_value = sum(position.quantity * position.current_price for position in positions if position.current_price and position.exit_price is None)
    
    # Set profit/loss data
    if total_invested > 0:
        profit_loss = total_current_value - total_invested
        profit_loss_percent = (profit_loss / total_invested) * 100
    else:
        profit_loss = Decimal('0')
        profit_loss_percent = Decimal('0')
    
    context = {
        'category': category,
        'positions': positions,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'profit_loss': profit_loss,
        'profit_loss_percent': profit_loss_percent,
    }
    
    return render(request, 'category_detail.html', context)

@login_required
def order_list(request):
    """View all pending orders"""
    orders = PendingOrder.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'order_list.html', {'orders': orders})

@login_required
def get_single_price(request, ticker):
    """Get the current price for a single ticker from Binance API"""
    try:
        # Import here to avoid circular imports
        from .utils import get_binance_price
        
        # Get price from Binance
        current_price = get_binance_price(request.user, ticker)
        
        if current_price:
            return JsonResponse({
                'success': True,
                'ticker': ticker,
                'price': float(current_price),
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Could not fetch price for {ticker} from Binance. Make sure the ticker format is correct.'
            }, status=404)
    
    except Exception as e:
        logger.error(f"Error getting price for ticker {ticker}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving price: {str(e)}. Check your API credentials and ticker format.'
        }, status=500)