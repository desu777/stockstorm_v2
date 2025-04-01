from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Bot, BotLog
from .forms import BotForm
import json
import logging
from django.conf import settings
import requests
from decimal import Decimal
from .utils import get_token
from django.views.decorators.http import require_POST
import time

logger = logging.getLogger(__name__)

@login_required
def bnb_list(request):
    """View for listing all bots for the current user"""
    bots = Bot.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'bnb_list.html', {'bots': bots})

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
        max_price = Decimal(request.POST.get('max_price', '0'))
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
            percent=int(percent),  # Konwersja z Decimal na int
            max_price=max_price,  # Używam wartości z formularza
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
            'max_price': float(max_price),
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
    """
    Szczegóły bota BNB – łączymy się z odpowiednią mikrousługą.
    """
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    
    # Sprawdź czy bot ma poprawny typ i ID w mikrousłudze
    if bot.broker_type != 'BNB':
        messages.error(request, "Ten widok dotyczy bota BNB, a bot nie jest typu BNB.")
        return redirect('bnb_list')
    
    if not bot.microservice_bot_id:
        messages.error(request, "Ten bot nie ma przypisanego ID w mikrousłudze.")
        return redirect('bnb_list')
    
    # Określ typ bota na podstawie nazwy
    is_rei_bot = "51015rei" in bot.name.lower()
    microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
    
    # Pobierz token dla mikrousługi
    microservice_token = get_token(request.user.id)
    if not microservice_token:
        messages.error(request, "Brak tokena mikroserwisu do pobrania detali bota.")
        return redirect('bnb_list')
    
    # Pobierz logi z bazy danych
    bot_logs = BotLog.objects.filter(bot=bot).order_by('-created_at')[:20]
    
    # Przygotuj nagłówki
    headers = {
        'Authorization': f'Token {microservice_token}',
        'Content-Type': 'application/json'
    }
    
    # Ustaw wartości domyślne
    trading_levels = []
    recent_trades = []
    total_profit = "0.00"
    debug_info = {}  # Dodajemy informacje debugujące
    
    try:
        # Pełna ścieżka URL do debugowania
        full_url = f"{microservice_url}/get_bot_details/{bot.microservice_bot_id}/"
        debug_info['full_url'] = full_url
        
        # Pobierz dane z mikrousługi
        logger.info(f"Pobieranie danych bota z URL: {full_url}")
        resp = requests.get(
            full_url,
            headers=headers,
            timeout=10  # Zwiększamy timeout
        )
        
        # Zapisz kod odpowiedzi do debugowania
        debug_info['status_code'] = resp.status_code
        
        if resp.status_code == 200:
            # Zapisz odpowiedź do debugowania
            bot_data = resp.json()
            debug_info['raw_response'] = bot_data
            
            # Szczegółowe logowanie
            logger.info(f"Otrzymano dane bota: {bot_data}")
            
            # NOWY FORMAT ODPOWIEDZI - parsowanie z formatu {'bot_id': 2, 'status': 'RUNNING', 'symbol': 'LTCUSDC', 'levels': {'lv1': {...}, 'lv2': {...}}}
            if 'levels' in bot_data and isinstance(bot_data['levels'], dict):
                levels_data = bot_data['levels']
                debug_info['levels_data'] = levels_data
                
                # Przygotuj dane poziomów handlowych z nowego formatu
                for level_name, level_data in levels_data.items():
                    if level_name.startswith("lv") and isinstance(level_data, dict):
                        try:
                            trading_levels.append({
                                "name": level_name,
                                "price": float(level_data.get('price', 0)),
                                "capital": float(level_data.get('capital', 0)),
                                "is_bought": bool(level_data.get('is_bought', False)),
                                "buy_price": float(level_data.get('buy_price', 0)) if level_data.get('buy_price') else 0,
                                "buy_volume": float(level_data.get('volume', 0)) if level_data.get('volume') else 0,
                                "tp": level_data.get('tp', 0),
                                "profit": float(level_data.get('profit', 0))
                            })
                        except Exception as e:
                            logger.error(f"Błąd przetwarzania poziomu {level_name}: {str(e)}")
                            continue
                
                # Sortuj poziomy według ceny (od najwyższej do najniższej)
                trading_levels.sort(key=lambda x: x["price"], reverse=True)
                
                # Spróbujmy obliczyć całkowity zysk z poziomów
                try:
                    total_profit = sum(float(level.get('profit', 0)) for level in levels_data.values())
                    total_profit = round(total_profit, 2)
                    
                    # Update the bot's total_profit in the database
                    try:
                        bot.total_profit = Decimal(str(total_profit))
                        bot.save(update_fields=['total_profit'])
                        logger.info(f"Updated bot {bot.id} total profit to {total_profit}")
                    except Exception as e:
                        logger.error(f"Error updating bot total_profit in database: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Błąd obliczania zysku: {str(e)}")
                    total_profit = 0.0
                
                # Dodaj log informacyjny o poziomach
                try:
                    BotLog.objects.create(
                        bot=bot,
                        message=f"Pobrano {len(trading_levels)} poziomów handlowych."
                    )
                except Exception as e:
                    logger.error(f"Błąd przy zapisywaniu logu: {str(e)}")
            
            # Pobierz transakcje z mikrousługi - osobne zapytanie
            try:
                trades_url = f"{microservice_url}/get_bot_trades/{bot.microservice_bot_id}/"
                trades_resp = requests.get(
                    trades_url,
                    headers=headers,
                    timeout=10
                )
                
                if trades_resp.status_code == 200:
                    trades_data = trades_resp.json()
                    debug_info['trades_data'] = trades_data
                    
                    if 'trades' in trades_data and isinstance(trades_data['trades'], list):
                        recent_trades = trades_data['trades']
                    
                    if 'total_profit' in trades_data:
                        total_profit = float(trades_data.get('total_profit', 0))
                else:
                    logger.warning(f"Nie udało się pobrać transakcji: {trades_resp.status_code}")
            except Exception as e:
                logger.error(f"Błąd podczas pobierania transakcji: {str(e)}")
            
            # Aktualizuj status bota, jeśli się zmienił
            if bot_data.get('status') and bot.status != bot_data['status']:
                bot.status = bot_data['status']
                bot.save()
        else:
            logger.error(f"Błąd pobierania danych bota: {resp.status_code} {resp.text}")
            messages.warning(request, f"Nie udało się pobrać aktualnych danych bota: {resp.status_code}")
            debug_info['error_response'] = resp.text
    except Exception as e:
        logger.error(f"Wyjątek podczas pobierania danych bota: {str(e)}")
        messages.warning(request, f"Problem z komunikacją z mikrousługą: {str(e)}")
        debug_info['exception'] = str(e)
    
    # Przygotuj kontekst
    context = {
        'bot': bot,
        'bot_logs': bot_logs,
        'is_rei_bot': is_rei_bot,
        'trading_levels': trading_levels,
        'recent_trades': recent_trades,
        'total_profit': total_profit,
        'debug_info': debug_info  # Dodajemy informacje debugujące do kontekstu
    }
    
    return render(request, 'bnb_detail.html', context)

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

    # Określ typ bota na podstawie nazwy
    is_rei_bot = "51015rei" in bot.name.lower()
    microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2

    microservice_token = get_token(request.user.id)
    if not microservice_token:
        return JsonResponse({"error": "No microservice token available."}, status=400)

    headers = {'Authorization': f'Token {microservice_token}'}
    
    try:
        resp = requests.get(
            f"{microservice_url}/get_bot_status/{bot.microservice_bot_id}/",
            headers=headers,
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        ms_status = data.get("status", "UNKNOWN")
        if ms_status and bot.status != ms_status:
            bot.status = ms_status
            bot.save()
        return JsonResponse({"status": bot.status})
    except requests.RequestException as e:
        logger.error(f"Błąd podczas pobierania statusu bnb bot {bot_id}: {e}")
        return JsonResponse({"error": f"Request error: {e}"}, status=500)

@login_required
def bnb_delete(request, bot_id):
    """View for deleting a bot and cleaning up in microservice"""
    logger.error(f"bnb_delete called in bnb_views.py with method: {request.method}, bot_id: {bot_id}")
    
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    
    if request.method == 'POST':
        # Save important data before deletion
        bot_name = bot.name
        microservice_bot_id = bot.microservice_bot_id
        
        # Determine which microservice to use
        is_rei_bot = "51015rei" in bot.name.lower()
        microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
        
        # Delete from microservice if possible
        if microservice_bot_id:
            try:
                # Get token for microservice
                microservice_token = get_token(request.user.id)
                
                if microservice_token:
                    # Prepare request
                    delete_url = f"{microservice_url}/remove_bot/{microservice_bot_id}/"
                    headers = {'Authorization': f'Token {microservice_token}'}
                    
                    # Log request details
                    logger.error(f"Calling microservice delete: {delete_url}")
                    logger.error(f"With headers: {headers}")
                    
                    # Make request to microservice
                    response = requests.post(
                        delete_url,
                        headers=headers,
                        timeout=10
                    )
                    
                    # Log response
                    logger.error(f"Microservice response: {response.status_code} - {response.text[:200]}")
            except Exception as e:
                logger.error(f"Error during microservice deletion: {str(e)}")
        
        # Now delete locally
        bot.delete()
        
        messages.success(request, f'Bot "{bot_name}" was deleted successfully!')
        return redirect('bnb_list')
    
    return render(request, 'bnb_delete.html', {'bot': bot})

@login_required
def bnb_start(request, bot_id):
    """View for starting a bot"""
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    
    # Check if bot can be started
    if bot.status in ['NEW', 'FINISHED', 'ERROR']:
        bot.status = 'RUNNING'
        bot.is_active = True
        bot.save()
        
        # Here you would add logic to actually start the bot's trading process
        # This might involve starting a background task, etc.
        
        messages.success(request, f'Bot "{bot.name}" has been started!')
    else:
        messages.error(request, f'Bot "{bot.name}" cannot be started from its current state.')
    
    return redirect('bnb_detail', bot_id=bot.id)

@login_required
def bnb_stop(request, bot_id):
    """View for stopping a bot"""
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)
    
    # Check if bot can be stopped
    if bot.status == 'RUNNING':
        bot.status = 'FINISHED'
        bot.is_active = False
        bot.save()
        
        # Here you would add logic to actually stop the bot's trading process
        
        messages.success(request, f'Bot "{bot.name}" has been stopped!')
    else:
        messages.error(request, f'Bot "{bot.name}" is not currently running.')
    
    return redirect('bnb_detail', bot_id=bot.id)

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
        
        # Określ typ bota na podstawie nazwy
        is_rei_bot = "51015rei" in bot.name.lower()
        microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2
        
        # Pobierz token dla mikrousługi
        microservice_token = get_token(request.user.id)
        if not microservice_token:
            return JsonResponse({"success": False, "error": "No microservice token available."}, status=400)
        
        # Przygotuj nagłówki
        headers = {
            'Authorization': f'Token {microservice_token}',
            'Content-Type': 'application/json'
        }
        
        # Pobierz dane z mikrousługi
        resp = requests.get(
            f"{microservice_url}/get_bot_details/{bot.microservice_bot_id}/",
            headers=headers,
            timeout=5
        )
        
        if resp.status_code == 200:
            bot_data = resp.json()
            
            # Aktualizuj status bota, jeśli się zmienił
            if bot_data.get('status') and bot.status != bot_data['status']:
                bot.status = bot_data['status']
                bot.save()
            
            # Zapisz log o ręcznym odświeżeniu
            BotLog.objects.create(
                bot=bot,
                message="Ręczne odświeżenie danych bota przez użytkownika."
            )
            
            return JsonResponse({"success": True, "message": "Bot data refreshed successfully."})
        else:
            # Zapisz log o błędzie
            BotLog.objects.create(
                bot=bot,
                message=f"Błąd podczas ręcznego odświeżania danych: {resp.status_code}"
            )
            return JsonResponse({"success": False, "error": f"Microservice error: {resp.status_code} {resp.text}"}, status=500)
    except Exception as e:
        logger.error(f"Błąd podczas ręcznego odświeżania danych bota {bot_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
def export_bnb_trades(request, bot_id):
    """
    Exportuje transakcje bota do pliku CSV.
    """
    bot = get_object_or_404(Bot, id=bot_id, user=request.user)

    if not bot.microservice_bot_id:
        messages.error(request, "Bot nie ma ID w mikroserwisie.")
        return redirect('bnb_detail', bot_id=bot_id)

    microservice_token = get_token(request.user.id)
    if not microservice_token:
        messages.error(request, "Brak tokena mikroserwisu.")
        return redirect('bnb_detail', bot_id=bot_id)

    # Określ typ bota na podstawie nazwy
    is_rei_bot = "51015rei" in bot.name.lower()
    microservice_url = settings.BNB_MICROSERVICE_URL if is_rei_bot else settings.BNB_MICROSERVICE_URL_2

    headers = {"Authorization": f"Token {microservice_token}"}

    try:
        r = requests.get(
            f"{microservice_url}/export_bnb_trades_csv/{bot.microservice_bot_id}/",
            headers=headers,
            stream=True,
            timeout=10
        )
        if r.status_code == 200:
            from django.http import HttpResponse
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