from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import time
import logging

from .models import GTCategory, StockPosition, StockPriceAlert
from .forms import GTCategoryForm, StockPositionForm, StockPriceAlertForm
from .utils import get_stock_price, get_bulk_stock_prices, get_stock_price_advanced

logger = logging.getLogger(__name__)

# List Views
@login_required
def position_list(request):
    """Display all stock positions for the current user"""
    categories = GTCategory.objects.filter(user=request.user).prefetch_related('positions')
    positions = StockPosition.objects.filter(user=request.user, exit_price=None)
    
    # Get summary data
    total_invested = sum(p.position_size for p in positions)
    
    # Calculate current value
    positions_with_price = [p for p in positions if p.current_price]
    current_value = sum(p.quantity * p.current_price for p in positions_with_price)
    
    # Calculate profit/loss
    total_profit_loss = sum(p.profit_loss_dollar for p in positions_with_price if p.profit_loss_dollar is not None)
    profit_loss_percent = (total_profit_loss / total_invested * 100) if total_invested else 0
    
    context = {
        'categories': categories,
        'positions': positions,
        'total_invested': total_invested,
        'current_value': current_value,
        'total_profit_loss': total_profit_loss,
        'profit_loss_percent': profit_loss_percent,
    }
    return render(request, 'gt/gt_position_list.html', context)

@login_required
def category_detail(request, category_id):
    """Display all positions in a specific category"""
    category = get_object_or_404(GTCategory, id=category_id, user=request.user)
    positions = StockPosition.objects.filter(category=category, exit_price=None)
    
    context = {
        'category': category,
        'positions': positions,
    }
    return render(request, 'gt/gt_category_detail.html', context)

@login_required
def position_detail(request, position_id):
    """Display details of a specific position"""
    position = get_object_or_404(StockPosition, id=position_id, user=request.user)
    alerts = StockPriceAlert.objects.filter(position=position)
    
    # Get stock info if available
    stock_info = None
    if position.ticker:
        stock_info = get_stock_price_advanced(position.ticker)
    
    context = {
        'position': position,
        'alerts': alerts,
        'stock_info': stock_info,
    }
    return render(request, 'gt/gt_position_detail.html', context)

# CRUD Operations
@login_required
def add_category(request):
    """Add a new category"""
    if request.method == 'POST':
        form = GTCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Category added successfully!')
            return redirect('gt:gt_position_list')
    else:
        form = GTCategoryForm()
    
    context = {
        'form': form,
        'title': 'Add Category',
    }
    return render(request, 'gt/gt_category_form.html', context)

@login_required
def edit_category(request, category_id):
    """Edit an existing category"""
    category = get_object_or_404(GTCategory, id=category_id, user=request.user)
    
    if request.method == 'POST':
        form = GTCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('gt:gt_position_list')
    else:
        form = GTCategoryForm(instance=category)
    
    context = {
        'form': form,
        'title': 'Edit Category',
        'category': category,
    }
    return render(request, 'gt/gt_category_form.html', context)

@login_required
def delete_category(request, category_id):
    """Delete a category"""
    category = get_object_or_404(GTCategory, id=category_id, user=request.user)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('gt:gt_position_list')
    
    context = {
        'category': category,
        'positions_count': StockPosition.objects.filter(category=category).count(),
    }
    return render(request, 'gt/gt_category_confirm_delete.html', context)

@login_required
def add_position(request):
    """Add a new stock position"""
    if request.method == 'POST':
        form = StockPositionForm(request.POST, user=request.user)
        if form.is_valid():
            position = form.save(commit=False)
            position.user = request.user
            
            # Try to get current price
            ticker = position.ticker
            current_price = get_stock_price(ticker)
            if current_price:
                position.current_price = current_price
                position.last_price_update = timezone.now()
            
            position.save()
            messages.success(request, f'Position for {ticker} added successfully!')
            return redirect('gt:gt_position_list')
    else:
        form = StockPositionForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Add Stock Position',
    }
    return render(request, 'gt/gt_position_form.html', context)

@login_required
def edit_position(request, position_id):
    """Edit an existing position"""
    position = get_object_or_404(StockPosition, id=position_id, user=request.user)
    
    if request.method == 'POST':
        form = StockPositionForm(request.POST, instance=position, user=request.user)
        if form.is_valid():
            edited_position = form.save(commit=False)
            
            # Jeśli wprowadzono cenę wyjścia, ustaw datę wyjścia na teraz
            if edited_position.exit_price and not edited_position.exit_date:
                edited_position.exit_date = timezone.now()
            # Jeśli usunięto cenę wyjścia, wyczyść również datę wyjścia
            elif not edited_position.exit_price and edited_position.exit_date:
                edited_position.exit_date = None
                
            edited_position.save()
            messages.success(request, 'Position updated successfully!')
            return redirect('gt:gt_position_detail', position_id=position.id)
    else:
        form = StockPositionForm(instance=position, user=request.user)
    
    context = {
        'form': form,
        'title': 'Edit Position',
        'position': position,
    }
    return render(request, 'gt/gt_position_form.html', context)

@login_required
def delete_position(request, position_id):
    """Delete a position"""
    position = get_object_or_404(StockPosition, id=position_id, user=request.user)
    
    if request.method == 'POST':
        position.delete()
        messages.success(request, 'Position deleted successfully!')
        return redirect('gt:gt_position_list')
    
    context = {
        'position': position,
    }
    return render(request, 'gt/gt_position_confirm_delete.html', context)

@login_required
def add_alert(request, position_id):
    """Add a new price alert for a position"""
    position = get_object_or_404(StockPosition, id=position_id, user=request.user)
    
    if request.method == 'POST':
        form = StockPriceAlertForm(request.POST, position=position)
        if form.is_valid():
            alert = form.save()
            messages.success(request, 'Alert added successfully!')
            return redirect('gt:gt_position_detail', position_id=position.id)
    else:
        # Prefill with current price if available
        initial = {}
        if position.current_price:
            initial['threshold_value'] = position.current_price
        form = StockPriceAlertForm(position=position, initial=initial)
    
    context = {
        'form': form,
        'title': f'Add Alert for {position.ticker}',
        'position': position,
    }
    return render(request, 'gt/gt_alert_form.html', context)

@login_required
def edit_alert(request, alert_id):
    """Edit an existing alert"""
    alert = get_object_or_404(StockPriceAlert, id=alert_id, position__user=request.user)
    
    if request.method == 'POST':
        form = StockPriceAlertForm(request.POST, instance=alert)
        if form.is_valid():
            # Reset trigger status if alert was previously triggered
            if alert.triggered:
                alert.triggered = False
                alert.last_triggered = None
            
            form.save()
            messages.success(request, 'Alert updated successfully!')
            return redirect('gt:gt_position_detail', position_id=alert.position.id)
    else:
        form = StockPriceAlertForm(instance=alert)
    
    context = {
        'form': form,
        'title': 'Edit Alert',
        'alert': alert,
        'position': alert.position,
    }
    return render(request, 'gt/gt_alert_form.html', context)

@login_required
def delete_alert(request, alert_id):
    """Delete an alert"""
    alert = get_object_or_404(StockPriceAlert, id=alert_id, position__user=request.user)
    position = alert.position
    
    if request.method == 'POST':
        alert.delete()
        messages.success(request, 'Alert deleted successfully!')
        return redirect('gt:gt_position_detail', position_id=position.id)
    
    context = {
        'alert': alert,
        'position': position,
    }
    return render(request, 'gt/gt_alert_confirm_delete.html', context)

# API Endpoints
@login_required
def update_prices(request):
    """Update prices for all positions"""
    # Obsługujemy zarówno GET jak i POST
    try:
        logger.info(f"Starting price update for user {request.user.username} via {request.method}")
        start_time = time.time()
        
        # Get positions without exit price (active positions)
        positions = StockPosition.objects.filter(user=request.user, exit_price=None)
        
        if not positions.exists():
            logger.info(f"No active positions found for user {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'No active positions to update',
                'updated_count': 0
            })
        
        # Get all unique tickers
        tickers = positions.values_list('ticker', flat=True).distinct()
        logger.info(f"Found {len(tickers)} unique tickers to update: {', '.join(tickers)}")
        
        # Fetch prices in bulk
        prices = get_bulk_stock_prices(tickers)
        
        if not prices:
            logger.error(f"Failed to get any prices for tickers: {', '.join(tickers)}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to fetch prices from the API. Please try again later.',
            }, status=500)
        
        logger.info(f"Received prices for {len(prices)} tickers")
        
        # Update each position
        updated_count = 0
        for position in positions:
            if position.ticker in prices:
                position.current_price = prices[position.ticker]
                position.last_price_update = timezone.now()
                position.save(update_fields=['current_price', 'last_price_update'])
                updated_count += 1
        
        elapsed_time = time.time() - start_time
        logger.info(f"Price update completed: updated {updated_count}/{positions.count()} positions in {elapsed_time:.2f} seconds")
        
        return JsonResponse({
            'success': True,
            'message': f'Updated prices for {updated_count} positions',
            'updated_count': updated_count,
            'elapsed_time': f'{elapsed_time:.2f} seconds'
        })
    except Exception as e:
        logger.error(f"Error during price update: {str(e)}")
        logger.exception(e)
        return JsonResponse({
            'success': False,
            'message': f'Error updating prices: {str(e)}',
        }, status=500)

@login_required
def get_single_price(request, ticker):
    """Get price for a single ticker"""
    price = get_stock_price(ticker)
    
    if price:
        return JsonResponse({
            'success': True,
            'ticker': ticker,
            'price': price
        })
    else:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get price for {ticker}'
        }, status=400)

@login_required
def get_advanced_price(request, ticker):
    """Get advanced price data with retry logic for a single ticker"""
    price_data = get_stock_price_advanced(ticker)
    
    if price_data:
        return JsonResponse({
            'success': True,
            'data': price_data
        })
    else:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get advanced price data for {ticker}'
        }, status=400)

@login_required
def get_stock_info_api(request, ticker):
    """API endpoint to get stock info"""
    info = get_stock_price_advanced(ticker)
    
    if info:
        return JsonResponse({
            'success': True,
            'ticker': ticker,
            'info': info
        })
    else:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get info for {ticker}'
        }, status=400)

@login_required
def update_position_price(request):
    """Update price for a single position"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Only POST method is allowed'}, status=405)
    
    try:
        position_id = request.POST.get('position_id')
        price = request.POST.get('price')
        
        if not position_id or not price:
            return JsonResponse({'success': False, 'message': 'Position ID and price are required'}, status=400)
        
        # Convert price to float
        try:
            price = float(price)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid price format'}, status=400)
        
        # Get position
        position = get_object_or_404(StockPosition, id=position_id, user=request.user)
        
        # Update position price
        position.current_price = price
        position.last_price_update = timezone.now()
        position.save(update_fields=['current_price', 'last_price_update'])
        
        logger.info(f"Updated price for position {position.ticker} (ID: {position_id}): {price}")
        
        return JsonResponse({
            'success': True,
            'message': f'Price updated successfully for {position.ticker}',
            'ticker': position.ticker,
            'price': price
        })
    
    except Exception as e:
        logger.error(f"Error updating position price: {str(e)}")
        logger.exception(e)
        return JsonResponse({
            'success': False,
            'message': f'Error updating price: {str(e)}',
        }, status=500)
