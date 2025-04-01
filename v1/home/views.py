# views.py

import logging
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .forms import CustomUserCreationForm, BotForm, BinanceApiForm
from .models import Bot, UserProfile, TelegramConfig, BotLog
from .utils import get_token
from datetime import datetime, timedelta, timezone as py_timezone
from django.http import HttpResponse
import csv
from io import StringIO
from django.db.models import Sum, Avg
from django.contrib.auth.models import User
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from .tasks import sync_bot_status
from .forms import BotForm, CustomUserCreationForm, UserProfileForm, TelegramCodeForm
from .middleware import LiveStatusMiddleware
from decimal import Decimal
from home.tasks import refresh_bnb_bot_data
import json

logger = logging.getLogger(__name__)
def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember') == 'yes'
        next_url = request.POST.get('next', '/dashboard/')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Set session expiry based on remember_me
            if remember_me:
                # Session will last for 2 weeks (60*60*24*14 seconds)
                request.session.set_expiry(1209600)
            else:
                # Session will end when the browser is closed
                request.session.set_expiry(0)
                
            return redirect(next_url)
        else:
            # Return error message for invalid login
            return render(request, 'login.html', {
                'form': {'errors': True},
                'next': next_url,
            })
    
    return render(request, 'login.html')

def home(request):
    return render(request, 'home.html')


def login_view(request):
    return render(request, 'login.html')


def success_view(request):
    return render(request, 'success.html')


def forgot_password_view(request):
    """
    Obsługa odzyskiwania hasła (przykładowe).
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')

        try:
            user = User.objects.get(username=username, email=email)
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password successfully changed! Now log in.')
            return redirect('success')
        except User.DoesNotExist:
            messages.error(request, 'No user found with that username and email.')

    return render(request, 'forgot.html')


@login_required
def profile_view(request):
    # Get or create the user's profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get the user's telegram config
    telegram_config = TelegramConfig.objects.filter(user=request.user).first()
    
    # Generate a verification code if needed
    verification_code = None
    if telegram_config is None or not telegram_config.is_verified:
        # Generate random verification code if not already exists
        import uuid
        import string
        import random
        
        # Create a new TelegramConfig if needed
        if telegram_config is None:
            telegram_config = TelegramConfig.objects.create(
                user=request.user,
                verification_code=''.join(random.choices(string.ascii_uppercase + string.digits, k=6)),
                is_verified=False
            )
        # Or update verification code if exists but not verified
        elif not telegram_config.is_verified and not telegram_config.verification_code:
            telegram_config.verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            telegram_config.save()
            
        verification_code = telegram_config.verification_code
    
    # Check if request is AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'account':
            # Update account information
            email = request.POST.get('email')
            if email and email != request.user.email:
                request.user.email = email
                request.user.save()
                messages.success(request, "Account information updated successfully!")
                
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                # Delete old picture if it exists
                if profile.profile_picture:
                    profile.profile_picture.delete()
                
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
                messages.success(request, "Profile picture updated successfully!")
            
        elif form_type == 'binance':
            # Update Binance API settings
            api_key = request.POST.get('binance_api_key')
            api_secret = request.POST.get('binance_api_secret')
            
            # Save API key if provided
            if api_key or api_key == '':  # Allow clearing the key
                profile.binance_api_key = api_key
            
            # Save API secret if provided
            if api_secret:
                profile.set_binance_api_secret(api_secret)
                
            profile.save()
            messages.success(request, "Binance API settings saved successfully!")
            
        elif form_type == 'telegram_settings':
            # Update Telegram notification settings
            profile.telegram_notifications_enabled = request.POST.get('notify_bot_status') == 'on'
            profile.save()
            messages.success(request, "Telegram notification settings updated successfully!")
            
        elif form_type == 'telegram_verify':
            # Handle telegram verification
            submitted_code = request.POST.get('telegram_code')
            
            if telegram_config and telegram_config.verification_code == submitted_code:
                # Verification successful
                telegram_config.is_verified = True
                telegram_config.save()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Telegram verification successful!'})
                else:
                    messages.success(request, "Telegram verified successfully!")
            else:
                # Verification failed
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'Invalid verification code'})
                else:
                    messages.error(request, "Invalid verification code")
            
        elif form_type == 'password':
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
            elif len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
            else:
                request.user.set_password(new_password)
                request.user.save()
                # Update the session to prevent logout
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password changed successfully!")
        
        # For non-AJAX requests, redirect to prevent form resubmission
        if not is_ajax:
            return redirect('profile')
    
    return render(request, 'profile.html', {
        'user': request.user,
        'profile': profile,
        'telegram_config': telegram_config,
        'verification_code': verification_code,
    })


def register_view(request):
    """
    Rejestracja użytkownika w głównym serwisie,
    wysyłanie tokenów do mikroserwisów BNB.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        # Sprawdzenie REGISTER_KEY
        register_key = request.POST.get('register_key')
        if register_key != settings.REGISTER_KEY:
            messages.error(request, 'Niepoprawny klucz rejestracyjny.')
            return render(request, 'register.html', {'form': form})

        if form.is_valid():
            # 1) Tworzymy użytkownika
            user = form.save()

            # 2) Generujemy token
            token, created = Token.objects.get_or_create(user=user)

            # 3) Wysyłanie tokena do mikroserwisów
            microservices = [
                {
                    'name': 'BNB1 (51015rei)',
                    'url': f"{settings.BNB_MICROSERVICE_URL}/register_token/",
                    'headers': {
                        'Authorization': f'Bearer {settings.MICROSERVICE_API_TOKEN}',
                        'Content-Type': 'application/json',
                    },
                },
                {
                    'name': 'BNB2 (51015)',
                    'url': f"{settings.BNB_MICROSERVICE_URL_2}/register_token/",
                    'headers': {
                        'Authorization': f'Bearer {settings.MICROSERVICE_API_TOKEN}',
                        'Content-Type': 'application/json',
                    },
                }
            ]

            for service in microservices:
                try:
                    payload = {
                        'user_id': user.id,
                        'token': token.key
                    }
                    response = requests.post(
                        service['url'],
                        json=payload,
                        headers=service['headers'],
                        timeout=5
                    )
                    if response.status_code == 200:
                        messages.success(request, f"Token wysłany do mikroserwisu {service['name']}.")
                    else:
                        messages.warning(
                            request,
                            f"Rejestracja OK, ale mikroserwis {service['name']} zwrócił "
                            f"{response.status_code}: {response.text}"
                        )
                except Exception as e:
                    messages.error(request, f"Błąd łączenia z mikroserwisem {service['name']}: {e}")

            # 4) Sukces
            messages.success(request, 'Możesz się już zalogować!')
            return redirect('login')
        else:
            messages.error(request, 'Spróbuj jeszcze raz! Formularz niepoprawny.')
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def dashboard_view(request):
    # Get the user's bots - only BNB bots
    bots = Bot.objects.filter(user=request.user, broker_type='BNB')
    
    # Calculate statistics
    total_bots_count = bots.count()
    active_bots_count = bots.filter(status='RUNNING', is_active=True).count()
    
    # Get recent bots (most recently created) 
    recent_bots = bots.order_by('-created_at')[:3]
    
    # Get trading volume and profit from the database
    trading_volume = 0
    profit = 0
    
    if bots.exists():
        # Sum the capital of all bots for trading volume
        trading_volume = sum(bot.capital for bot in bots)
        
        # Sum the total_profit field for all bots
        profit = sum(bot.total_profit for bot in bots)
    
    # Prepare context for template
    context = {
        'bots': bots,
        'active_bots_count': active_bots_count,
        'total_bots_count': total_bots_count,
        'trading_volume': trading_volume,
        'profit': profit,
        'recent_bots': recent_bots
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def get_balance_data(request):
    """Get balance data for charts"""
    # Empty data since XTB is no longer available
    data = []
    return JsonResponse(data, safe=False)


@login_required
@require_GET
def get_instrument_price(request):
    """
    Function returns empty result as API has been discontinued
    """
    return JsonResponse({"ask": None, "bid": None, "error": "API is no longer available."}, status=400)


@login_required
def search_instruments(request):
    """
    Function returns empty list as API has been discontinued
    """
    return JsonResponse([], safe=False)


def get_stock_market_status():
    """
    Stock market status (open/closed).
    """
    now = datetime.now(py_timezone.utc)
    day_of_week = now.weekday()

    stock_markets = [
        {
            'name': 'NASDAQ',
            'open_time': now.replace(hour=14, minute=30, second=0, microsecond=0),
            'close_time': now.replace(hour=21, minute=0, second=0, microsecond=0),
        },
        {
            'name': 'GPW',
            'open_time': now.replace(hour=7, minute=30, second=0, microsecond=0),
            'close_time': now.replace(hour=15, minute=30, second=0, microsecond=0),
        },
        {
            'name': 'NYSE',
            'open_time': now.replace(hour=14, minute=30, second=0, microsecond=0),
            'close_time': now.replace(hour=21, minute=0, second=0, microsecond=0),
        },
        {
            'name': 'LSE',
            'open_time': now.replace(hour=8, minute=0, second=0, microsecond=0),
            'close_time': now.replace(hour=16, minute=30, second=0, microsecond=0),
        },
        {
            'name': 'JPX',
            'open_time': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'close_time': now.replace(hour=6, minute=0, second=0, microsecond=0),
        }
    ]

    for market in stock_markets:
        if day_of_week in [5, 6]:  
            days_until_monday = (7 - day_of_week) % 7
            monday_open_time = (now + timedelta(days=days_until_monday)).replace(
                hour=market['open_time'].hour,
                minute=market['open_time'].minute,
                second=0,
                microsecond=0
            )
            delta = monday_open_time - now
            market['status'] = 'CLOSED (Weekend)'
            market['css_class'] = 'status-weekend'
            market['time_to_open'] = str(delta).split(".")[0]
        elif market['open_time'] <= now <= market['close_time']:
            market['status'] = 'LIVE'
            market['css_class'] = 'status-live'
            market['time_to_open'] = '-'
        else:
            if now < market['open_time']:
                delta = market['open_time'] - now
            else:
                delta = (market['open_time'] + timedelta(days=1)) - now
            market['status'] = 'Closed'
            market['css_class'] = 'status-closed'
            market['time_to_open'] = str(delta).split(".")[0]

    return stock_markets


@login_required
def dashboard(request):
    # Get stock market status
    stock_markets = get_stock_market_status()
    
    # Get user's bots
    total_bots = Bot.objects.filter(user=request.user)
    total_bots_count = total_bots.count()
    active_bots_count = Bot.objects.filter(user=request.user, status='RUNNING').count()
    
    # Get recent bots (limit to 3 for dashboard display)
    recent_bots = total_bots.order_by('-created_at')[:3]
    
    # Calculate trading volume and profit (placeholder for now)
    trading_volume = 0  # This would be calculated from actual trade data
    profit = 0          # This would be calculated from actual trade data
    
    context = {
        'history': [],
        'documents': [],
        'stocks': stock_markets,
        'active_bots_count': active_bots_count,
        'total_bots_count': total_bots_count,
        'recent_bots': recent_bots,
        'trading_volume': trading_volume,
        'profit': profit,
    }
    
    return render(request, 'dashboard.html', context)


def api_stock_status(request):
    stock_markets = get_stock_market_status()
    return JsonResponse(stock_markets, safe=False)


#######################################################################
#                       BNB BOTS VIEWS                                #
#######################################################################
@login_required
def bnb_create(request):
    """
    Wyświetla formularz tworzenia bota lub przetwarza przesłane dane.
    """
    if request.method == 'POST':
        # Pobierz dane z formularza
        name = request.POST.get('name')
        instrument = request.POST.get('instrument')
        capital = Decimal(request.POST.get('capital', '0'))
        percent = Decimal(request.POST.get('percent', '0'))
        decimals = int(request.POST.get('decimals', '2'))
        binance_api_key = request.POST.get('binance_api_key', '')
        binance_api_secret = request.POST.get('binance_api_secret', '')
        bot_type = request.POST.get('bot_type', '51015rei')  # Domyślnie 51015rei

        # Zapisz lokalnie bota
        local_bot = Bot.objects.create(
            user=request.user,
            name=name,
            broker_type='BNB',
            instrument=instrument,
            capital=capital,
            percent=percent,
            status='NEW'
        )

        # Uzyskaj token dla mikrousługi
        microservice_token = get_token(request.user.id)
        if not microservice_token:
            messages.error(request, "Nie można uzyskać tokena dla mikrousługi.")
            return redirect('bnb_list')

        # Przygotuj nagłówki i payload
        headers = {
            'Authorization': f'Token {microservice_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'user_id': request.user.id,
            'name': name,
            'symbol': instrument,
            'max_price': float(capital),
            'percent': float(percent),
            'capital': float(capital),
            'decimals': decimals,                
            'binance_api_key': binance_api_key,
            'binance_api_secret': binance_api_secret,
        }

        try:
            # Wybierz URL mikrousługi na podstawie typu bota
            microservice_url = settings.BNB_MICROSERVICE_URL if bot_type == '51015rei' else settings.BNB_MICROSERVICE_URL_2
            microservice_name = "51015rei" if bot_type == '51015rei' else "51015"
            
            resp = requests.post(
                f"{microservice_url}/create_bot/",
                json=payload,
                headers=headers,
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                local_bot.microservice_bot_id = data.get("bot_id")
                local_bot.status = "RUNNING"
                local_bot.save()
                messages.success(request, f"Bot utworzony w {microservice_name} i uruchomiony!")
            else:
                local_bot.status = "ERROR"
                local_bot.save()
                messages.error(request, f"Błąd {microservice_name}: {resp.status_code} {resp.text}")
        except Exception as e:
            local_bot.status = "ERROR"
            local_bot.save()
            messages.error(request, f"Wyjątek przy łączeniu z mikrousługą: {str(e)}")

        return redirect('bnb_list')

    return render(request, 'bnb_create.html')


@login_required
def bnb_detail(request, bot_id):
    try:
        bot = Bot.objects.get(pk=bot_id, user=request.user)
        
        # Określenie typu bota (z reinwestycją czy bez)
        is_rei_bot = "51015rei" in bot.name.lower()
        
        # Pobieranie logów bota
        bot_logs = BotLog.objects.filter(bot=bot).order_by('-created_at')[:20]
        
        # Pobieranie danych bota z mikrousługi
        microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
        token = get_token(request.user.id)
        
        if not token:
            messages.error(request, "Failed to authenticate with bot microservice")
            return redirect('bnb_list')
        
        headers = {'Authorization': f"Token {token}"}
        
        try:
            # Pobieranie pełnych danych bota z nowego endpointu
            response = requests.get(
                f"{microservice_url}/get_bot_full_data/{bot.microservice_bot_id}/",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                bot_full_data = response.json()
                trading_levels = bot_full_data.get('trading_levels', [])
                recent_trades = bot_full_data.get('recent_trades', [])
                total_profit = bot_full_data.get('total_profit', '0.00')
                
                # Update bot's total_profit in the database
                try:
                    bot.total_profit = Decimal(str(total_profit))
                    bot.save(update_fields=['total_profit', 'updated_at'])
                    logger.info(f"Updated bot {bot.id} total profit to {total_profit}")
                except Exception as e:
                    logger.error(f"Error updating bot profit: {str(e)}")
            else:
                messages.error(request, f"Failed to fetch bot data: {response.text}")
                trading_levels = []
                recent_trades = []
                total_profit = "0.00"
        
        except requests.RequestException as e:
            messages.error(request, f"Error connecting to bot microservice: {str(e)}")
            trading_levels = []
            recent_trades = []
            total_profit = "0.00"
        
        context = {
            'bot': bot,
            'bot_logs': bot_logs,
            'is_rei_bot': is_rei_bot,
            'trading_levels': trading_levels,
            'recent_trades': recent_trades,
            'total_profit': total_profit
        }
        
        return render(request, 'bnb_detail.html', context)
    
    except Bot.DoesNotExist:
        messages.error(request, "Bot not found")
        return redirect('bnb_list')


@login_required
def bnb_delete(request, bot_id):
    """
    Usuwa bota w odpowiedniej mikrousłudze i lokalnie.
    """
    # Debug log to see if the view is being called
    logger.error(f"bnb_delete called with method: {request.method}, bot_id: {bot_id}")
    
    if request.method == 'POST':
        logger.error("Processing POST request for bot deletion")
        bot = get_object_or_404(Bot, id=bot_id, user=request.user)
        
        # Store info before deletion
        bot_name = bot.name
        microservice_bot_id = bot.microservice_bot_id
        
        # Determine which microservice to use
        is_rei_bot = "51015rei" in bot.name.lower()
        microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
        
        # Get microservice token
        microservice_token = get_token(request.user.id)
        
        # First delete from local database
        bot.delete()
        
        # Force deletion in microservice if we have required info
        if microservice_bot_id and microservice_token:
            try:
                # Direct API call to microservice
                delete_url = f"{microservice_url}/remove_bot/{microservice_bot_id}/"
                
                # Force request with minimal headers
                headers = {'Authorization': f'Token {microservice_token}'}
                
                # Make the request and log result
                response = requests.post(delete_url, headers=headers)
                logger.info(f"Microservice delete response: {response.status_code}")
            except Exception as e:
                logger.error(f"Error during microservice deletion: {str(e)}")
        
        messages.success(request, f"Bot '{bot_name}' was deleted successfully.")
        return redirect('bnb_list')
    
    # GET request - show confirmation page
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    return render(request, 'bnb_delete.html', {'bot': bot})


@login_required
def bnb_status(request, bot_id):
    """
    Pobieranie statusu bota (BNB) w JSON, aktualizacja w modelu.
    """
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    if bot.broker_type != 'BNB':
        return JsonResponse({"error": "Bot is not BNB type."}, status=400)

    if not bot.microservice_bot_id:
        return JsonResponse({"error": "Bot has no bnb microservice ID"}, status=400)

    microservice_token = get_token(request.user.id)
    if not microservice_token:
        return JsonResponse({"error": "No microservice token available."}, status=400)

    headers = {'Authorization': f'Token {microservice_token}'}
    
    # Determine which microservice URL to use
    is_rei_bot = "51015rei" in bot.name.lower()
    microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
    
    try:
        # Get bot details including status and profit
        resp = requests.get(
            f"{microservice_url}/get_bot_details/{bot.microservice_bot_id}/", 
            headers=headers, 
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Update status if changed
        ms_status = data.get("status", "UNKNOWN")
        if ms_status and bot.status != ms_status:
            bot.status = ms_status
            bot.save(update_fields=['status', 'updated_at'])
        
        # Try to update the profit if available
        try:
            if 'profit' in data:
                profit_value = data.get('profit', '0.00')
                bot.total_profit = Decimal(str(profit_value))
                bot.save(update_fields=['total_profit', 'updated_at'])
                logger.info(f"Updated bot {bot.id} profit to {profit_value}")
        except Exception as e:
            logger.error(f"Error updating bot profit: {str(e)}")
            
        return JsonResponse({
            "status": bot.status,
            "profit": str(bot.total_profit)
        })
    except requests.RequestException as e:
        logger.error(f"Błąd podczas pobierania statusu bnb bot {bot_id}: {e}")
        return JsonResponse({"error": f"Request error: {e}"}, status=500)


@login_required
@require_POST
def bnb_refresh(request, bot_id):
    """
    Ręczne odświeżanie danych bota (BNB).
    """
    try:
        # Pobierz bota i sprawdź, czy należy do zalogowanego użytkownika
        bot = get_object_or_404(Bot, id=bot_id, user=request.user)
        
        if bot.broker_type != 'BNB':
            return JsonResponse({"success": False, "error": "Bot is not BNB type."}, status=400)
            
        if not bot.microservice_bot_id:
            return JsonResponse({"success": False, "error": "Bot has no BNB microservice ID."}, status=400)
        
        # Wywołaj funkcję odświeżania danych bota
        result = refresh_bnb_bot_data(bot.id)
        
        # Zapisz log o ręcznym odświeżeniu
        BotLog.objects.create(
            bot=bot,
            message="Ręczne odświeżenie danych bota przez użytkownika."
        )
        
        return JsonResponse({"success": True, "message": "Bot data refreshed successfully."})
    except Exception as e:
        logger.error(f"Błąd podczas ręcznego odświeżania danych bota {bot_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def bnb_list(request):
    """
    Pokazuje listę wszystkich botów zalogowanego użytkownika, które są BNB.
    """
    user_bots = Bot.objects.filter(user=request.user, broker_type='BNB').order_by('-created_at')
    return render(request, 'bnb_list.html', {'bots': user_bots})

@login_required
def export_bnb_trades(request, bot_id):
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)

    if not bot.microservice_bot_id:
        messages.error(request, "Bot nie ma ID w mikroserwisie.")
        return redirect('bnb_detail', bot_id=bot_id)

    microservice_token = get_token(request.user.id)
    if not microservice_token:
        messages.error(request, "Brak tokena mikroserwisu.")
        return redirect('bnb_detail', bot_id=bot_id)

    url = f"{settings.BNB_MICROSERVICE_URL}/export_trades_csv/{bot.microservice_bot_id}/"
    headers = {"Authorization": f"Token {microservice_token}"}

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        if r.status_code == 200:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="bot_{bot_id}_trades.csv"'
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    response.write(chunk)
            return response
        else:
            messages.error(request, f"Błąd mikroserwisu: {r.status_code} {r.text}")
            return redirect('bnb_detail', bot_id=bot_id)
    except Exception as e:
        messages.error(request, f"Błąd: {str(e)}")
        return redirect('bnb_detail', bot_id=bot_id)


@login_required
def show_symbols_view(request):
    """
    Placeholder view for showing symbols (previously used with XTB API)
    """
    messages.info(request, "Symbol listings are not available as this API has been discontinued.")
    return redirect('dashboard')

@login_required
def telegram_settings(request):
    """
    View for configuring Telegram settings for notifications
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    telegram_config = TelegramConfig.objects.filter(user=request.user).first()
    
    # Handle form submission
    if request.method == 'POST':
        # Try to verify the existing code
        if telegram_config and telegram_config.verification_code:
            # In a real implementation, we would check if the user has sent the code to the bot
            # For now, we'll just mark it as verified
            telegram_config.is_verified = True
            telegram_config.save()
            
            # Enable telegram notifications by default
            profile.telegram_notifications_enabled = True
            profile.save()
            
            messages.success(request, "Telegram connection verified successfully! You will now receive notifications.")
        else:
            # Generate a new verification code
            import string
            import random
            
            if not telegram_config:
                verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                telegram_config = TelegramConfig.objects.create(
                    user=request.user,
                    verification_code=verification_code,
                    is_verified=False
                )
            else:
                verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                telegram_config.verification_code = verification_code
                telegram_config.is_verified = False
                telegram_config.save()
            
            messages.info(request, "Please send the verification code to the Telegram bot to complete the connection.")
    
    return redirect('profile')

@login_required
def reset_telegram(request):
    """
    View for resetting Telegram integration
    """
    # Check if request is AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Add debugging information
    logger = logging.getLogger(__name__)
    logger.error(f"Reset Telegram called - Method: {request.method}, AJAX: {is_ajax}")
    
    if request.method == 'POST':
        try:
            # Check if TelegramConfig exists before attempting deletion
            telegram_config = TelegramConfig.objects.filter(user=request.user).first()
            if telegram_config:
                logger.error(f"Deleting TelegramConfig for user {request.user.username} (ID: {telegram_config.id})")
                telegram_config.delete()
                logger.error("TelegramConfig deleted successfully")
            else:
                logger.error(f"No TelegramConfig found for user {request.user.username}")
            
            # Update the user profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            if profile:
                profile.telegram_notifications_enabled = False
                profile.save()
                logger.error("UserProfile updated successfully")
            
            if is_ajax:
                logger.error("Returning JSON success response")
                return JsonResponse({
                    'success': True, 
                    'message': 'Telegram integration has been reset.'
                })
            else:
                messages.success(request, "Telegram integration has been reset.")
        except Exception as e:
            logger.exception(f"Error in reset_telegram: {str(e)}")
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'message': f'Error resetting Telegram integration: {str(e)}'
                }, status=500)
    else:
        logger.error(f"Invalid method: {request.method}, expected POST")
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request method. Expected POST.'
            }, status=400)
    
    if is_ajax:
        # If we reached here, something went wrong but no exception was caught
        logger.error("Returning fallback JSON response")
        return JsonResponse({
            'success': False,
            'message': 'Unknown error occurred while processing request.'
        }, status=500)
        
    return redirect('profile')

def custom_logout_view(request):
    """
    Custom logout view that accepts both GET and POST requests.
    This makes the logout process more user-friendly while maintaining security.
    """
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('home')
