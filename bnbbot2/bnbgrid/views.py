# bnbgrid/views.py

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from decimal import Decimal
import csv
import json
from io import StringIO

from django.conf import settings

from .models import UserProfile, BnbBot, BnbTrade
from .authentication import CustomAuthentication
import logging
from datetime import datetime, timedelta
from rest_framework import status
from django.utils import timezone

logger = logging.getLogger(__name__)



# -------------------------------------------------------
# 1) Rejestracja tokena usera (do weryfikacji z DRF)
# -------------------------------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Endpoint do rejestrowania tokena użytkownika w mikroserwisie.
    Oczekuje nagłówka Authorization: Bearer <MICROSERVICE_API_TOKEN>
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response({'error': 'Missing Authorization header'}, status=401)

    expected_value = f"Bearer {settings.MICROSERVICE_API_TOKEN}"
    if auth_header != expected_value:
        return Response({'error': 'Invalid or missing microservice token'}, status=403)

    user_id = request.data.get('user_id')
    token = request.data.get('token')
    if not user_id or not token:
        return Response({'error': 'user_id and token are required'}, status=400)

    user_profile, created = UserProfile.objects.get_or_create(user_id=user_id)
    user_profile.auth_token = token
    user_profile.save()
    return Response({'status': 'Token saved successfully'})


def generate_levels(max_price, pct, capital, min_price=None, decimals=3):
    """
    Generuje SŁOWNIK zawierający TYLKO:
      - lv1, lv2, ... (właściwe ceny)
      - caps
      - sell_levels
    Nie zwraca flag i buy_price/buy_volume!
    """

    data = {
        "caps": {},
        "sell_levels": {}
    }

    max_p = float(max_price)
    pct_f = float(pct)

    levels = []
    i = 1
    while True:
        lv_price = max_p * (1 - (i - 1) * pct_f / 100.0)
        if lv_price <= 0:
            break
        if min_price and lv_price <= float(min_price):
            break
        if i > 50:
            break

        lv_price = round(lv_price, decimals)
        levels.append(lv_price)
        i += 1

    total_lv_count = len(levels)
    if total_lv_count == 0:
        return data

    portion_per_level = float(capital) / total_lv_count

    # Wypełniamy data (tylko część statyczną: lvX, caps, sell_levels)
    for idx, lv_price in enumerate(levels, start=1):
        lv_name = f"lv{idx}"
        data[lv_name] = lv_price
        data["caps"][lv_name] = round(portion_per_level, 2)

    for idx in range(2, total_lv_count + 1):
        buy_lv = f"lv{idx}"
        sell_lv = f"lv{idx - 1}"
        data["sell_levels"][buy_lv] = sell_lv

    return data


def init_runtime_data(level_names):
    """
    Tworzy słownik z `flags`, `buy_price`, `buy_volume` = 0.
    """
    rd = {
        "flags": {},
        "buy_price": {},
        "buy_volume": {}
    }
    for lv_name in level_names:
        rd["flags"][f"{lv_name}_bought"] = False
        rd["flags"][f"{lv_name}_sold"] = False
        rd["flags"][f"{lv_name}_in_progress"] = False
        rd["buy_price"][lv_name] = 0.0
        rd["buy_volume"][lv_name] = 0.0
    return rd



@api_view(['POST'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def create_bot(request):
    user_id = request.data.get("user_id")
    symbol = request.data.get("symbol", "BTCUSDT")
    max_price = float(request.data.get("max_price", 20000))
    percent = float(request.data.get("percent", 2))
    capital = float(request.data.get("capital", 1000))
    decimals = int(request.data.get("decimals", 2))
    binance_key = request.data.get("binance_api_key", "")
    binance_secret = request.data.get("binance_api_secret", "")

    bot = BnbBot.objects.create(
        user_id=user_id,
        name=request.data.get("name", "MyGridBot"),
        symbol=symbol,
        max_price=max_price,
        percent=percent,
        capital=capital,
        status='RUNNING',
        binance_api_key=binance_key
    )
    if binance_secret:
        bot.set_binance_api_secret(binance_secret)
        bot.save()

    # 1) Tylko statyczna konfiguracja:
    data = generate_levels(max_price, percent, capital, decimals=decimals)
    bot.save_levels_data(data)

    # 2) Inicjalizacja runtime:
    #    *level_names* to klucze lv1..lvN wygenerowane przez generate_levels
    level_names = [k for k in data.keys() if k.startswith("lv")]
    runtime = init_runtime_data(level_names)
    bot.save_runtime_data(runtime)

    bot.save()
    return Response({
        "bot_id": bot.id,
        "message": "Bot created successfully"
    })



# -------------------------------------------------------
# 4) Szczegóły bota
# -------------------------------------------------------
@api_view(['GET'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def get_bot_details(request, bot_id):
    bot = get_object_or_404(BnbBot, pk=bot_id, user_id=request.user.id)
    raw_data = bot.get_levels_data()

    # wczytaj FILLED transakcje
    trades = BnbTrade.objects.filter(bot=bot, status='FILLED')

    # Zbuduj obiekt levels
    levels = {}
    for k, v in raw_data.items():
        if k.startswith("lv"):
            levels[k] = {
                "price": float(v),
                "capital": float(raw_data.get("caps", {}).get(k, 0.0)),
                "tp": 0,
                "profit": 0.0,
            }

    total_profit = 0.0
    for lv_key, info in levels.items():
        sells = trades.filter(level=lv_key, side='SELL')
        tp_count = sells.count()
        lv_profit = sum(float(t.profit or 0) for t in sells)

        info["tp"] = tp_count
        info["profit"] = round(lv_profit, 2)
        total_profit += lv_profit

    resp = {
        "bot_id": bot.id,
        "status": bot.status,
        "symbol": bot.symbol,
        "levels": levels,
        "capital": float(bot.capital),
        "total_profit": round(total_profit, 2)
    }
    return Response(resp)


# -------------------------------------------------------
# 5) Usunięcie bota
# -------------------------------------------------------
@api_view(['POST'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def remove_bot(request, bot_id):
    """
    Usuwa bota z bazy – ale najpierw zatrzymuje go i rozłącza z Binance.
    """
    try:
        bot = get_object_or_404(BnbBot, pk=bot_id, user_id=request.user.id)
        
        # Log deletion attempt
        logger.info(f"Attempting to delete bot {bot_id} for user {request.user.id}")
        
        # First update status to STOPPED to ensure no new trades are created
        bot.status = 'STOPPED'
        bot.save()
        
        # Delete all related trades first
        from .models import BnbTrade
        trades_count = BnbTrade.objects.filter(bot=bot).count()
        BnbTrade.objects.filter(bot=bot).delete()
        logger.info(f"Deleted {trades_count} trades for bot {bot_id}")
        
        # Now delete the bot
        bot.delete()
        logger.info(f"Successfully deleted bot {bot_id}")
        
        return Response({"message": f"Bot {bot_id} and all related trades ({trades_count}) removed successfully."})
    except Exception as e:
        logger.error(f"Error deleting bot {bot_id}: {str(e)}")
        return Response({"error": f"Failed to delete bot: {str(e)}"}, status=500)

# -------------------------------------------------------
# 6) Status bota
# -------------------------------------------------------
@api_view(['GET'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def get_bot_status(request, bot_id):
    bot = get_object_or_404(BnbBot, pk=bot_id, user_id=request.user.id)
    return Response({
        "bot_id": bot.id,
        "status": bot.status,
        "symbol": bot.symbol
    })


# -------------------------------------------------------
# 7) Eksport transakcji do CSV
# -------------------------------------------------------
@api_view(['GET'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def export_bnb_trades_csv(request, bot_id):
    try:
        bot = BnbBot.objects.get(id=bot_id, user_id=request.user.id)
    except BnbBot.DoesNotExist:
        return Response({"error": "Bot not found or not owned by user"}, status=404)

    trades = BnbTrade.objects.filter(bot=bot).order_by('created_at')

    output = StringIO()
    writer = csv.writer(output, delimiter=';')

    # Definicja nagłówka CSV - pomijamy pola związane z id
    header = [
        "Level", 
        "Side",
        "Quantity",
        "Open Price",
        "Close Price",
        "Profit",
        "Binance Order Id",
        "Buy Type",
        "Sell Type",
        "Status",
        "Open Time",
        "Close Time"
    ]
    writer.writerow(header)

    for trade in trades:
        quantity = str(trade.quantity).replace('.', ',') if trade.quantity is not None else ""
        open_price = str(trade.open_price).replace('.', ',') if trade.open_price is not None else ""
        close_price = str(trade.close_price).replace('.', ',') if trade.close_price is not None else ""
        profit = str(trade.profit).replace('.', ',') if trade.profit is not None else ""
        
        binance_order_id = trade.binance_order_id or ""
        buy_type = trade.buy_type or ""
        sell_type = trade.sell_type or ""
        side = trade.side or ""

        open_time = trade.created_at.strftime("%Y-%m-%d %H:%M") if trade.created_at else ""
        # Jeżeli posiadasz pole 'filled_at' (np. jako moment zamknięcia transakcji)
        close_time = ""
        if hasattr(trade, 'filled_at') and trade.filled_at:
            close_time = trade.filled_at.strftime("%Y-%m-%d %H:%M")

        writer.writerow([
            trade.level,
            side,
            quantity,
            open_price,
            close_price,
            profit,
            binance_order_id,
            buy_type,
            sell_type,
            trade.status,
            open_time,
            close_time,
        ])

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="bot_{bot_id}_trades.csv"'
    return response


# -------------------------------------------------------
# 8) Pobranie pełnych danych bota (nowy endpoint)
# -------------------------------------------------------
@api_view(['GET'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def get_bot_full_data(request, bot_id):
    """
    Zwraca pełne dane bota, włącznie z poziomami handlowymi, statusem i historią transakcji.
    """
    try:
        bot = BnbBot.objects.get(id=bot_id, user_id=request.user.id)
    except BnbBot.DoesNotExist:
        return Response({"error": "Bot not found or not owned by user"}, status=404)
    
    # Pobierz dane poziomów
    levels_data = bot.get_levels_data()
    runtime_data = bot.get_runtime_data()
    
    # Pobierz transakcje
    trades = BnbTrade.objects.filter(bot=bot).order_by('-created_at')[:20]  # Ostatnie 20 transakcji
    
    # Przygotuj dane transakcji
    trades_data = []
    for trade in trades:
        trades_data.append({
            "level": trade.level,
            "side": trade.side,
            "quantity": float(trade.quantity) if trade.quantity else 0,
            "open_price": float(trade.open_price) if trade.open_price else 0,
            "close_price": float(trade.close_price) if trade.close_price else 0,
            "profit": float(trade.profit) if trade.profit else 0,
            "status": trade.status,
            "created_at": trade.created_at.isoformat() if trade.created_at else None,
        })
    
    # Oblicz zysk całkowity
    total_profit = sum(float(t.profit or 0) for t in BnbTrade.objects.filter(bot=bot, side='SELL'))
    
    # Przygotuj dane poziomów handlowych w bardziej przyjaznej formie
    trading_levels = []
    for k, v in levels_data.items():
        if k.startswith("lv"):
            level_price = float(v)
            level_capital = float(levels_data.get("caps", {}).get(k, 0))
            level_bought = runtime_data.get("flags", {}).get(f"{k}_bought", False)
            level_buy_price = float(runtime_data.get("buy_price", {}).get(k, 0))
            level_buy_volume = float(runtime_data.get("buy_volume", {}).get(k, 0))
            
            # Calculate tp count and profit for this level
            sells = BnbTrade.objects.filter(bot=bot, level=k, side='SELL', status='FILLED')
            tp_count = sells.count()
            level_profit = sum(float(t.profit or 0) for t in sells)
            
            trading_levels.append({
                "name": k,
                "price": level_price,
                "capital": level_capital,
                "is_bought": level_bought,
                "buy_price": level_buy_price,
                "buy_volume": level_buy_volume,
                "tp": tp_count,
                "profit": round(level_profit, 2)
            })
    
    # Sortuj poziomy według ceny (od najwyższej do najniższej)
    trading_levels.sort(key=lambda x: x["price"], reverse=True)
    
    response_data = {
        "bot_id": bot.id,
        "name": bot.name,
        "symbol": bot.symbol,
        "status": bot.status,
        "capital": float(bot.capital),
        "max_price": float(bot.max_price),
        "percent": float(bot.percent),
        "total_profit": round(total_profit, 2),
        "trading_levels": trading_levels,
        "recent_trades": trades_data,
        "raw_levels_data": levels_data,
        "raw_runtime_data": runtime_data
    }
    
    return Response(response_data)


@api_view(['GET'])
@authentication_classes([CustomAuthentication])
@permission_classes([IsAuthenticated])
def get_bot_trades(request, bot_id):
    """
    Pobiera i zwraca listę transakcji dla danego bota.
    """
    try:
        bot = BnbBot.objects.get(id=bot_id, user_id=request.user.id)
    except BnbBot.DoesNotExist:
        return Response({"error": "Bot not found or not owned by user"}, status=404)
    
    # Pobierz transakcje
    trades = BnbTrade.objects.filter(bot=bot).order_by('-created_at')[:20]  # Ostatnie 20 transakcji
    
    # Przygotuj dane transakcji
    trades_list = []
    for trade in trades:
        trades_list.append({
            "id": trade.id,
            "level": trade.level,
            "side": trade.side,
            "quantity": float(trade.quantity) if trade.quantity else 0,
            "open_price": float(trade.open_price) if trade.open_price else 0,
            "close_price": float(trade.close_price) if trade.close_price else 0,
            "profit": float(trade.profit) if trade.profit else 0,
            "status": trade.status,
            "created_at": trade.created_at.isoformat() if trade.created_at else None,
        })
    
    # Oblicz zysk całkowity
    total_profit = sum(float(t.profit or 0) for t in BnbTrade.objects.filter(bot=bot, side='SELL', status='FILLED'))
    
    response_data = {
        "trades": trades_list,
        "total_profit": round(total_profit, 2),
        "bot_id": bot.id
    }
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomAuthentication])
def get_user_bots(request, user_id):
    """
    Pobiera wszystkie boty danego użytkownika wraz z ich szczegółami.
    """
    try:
        # Znajdź wszystkie boty należące do podanego użytkownika
        bots = BnbBot.objects.filter(user_id=user_id)
        
        if not bots.exists():
            return Response([], status=status.HTTP_200_OK)
        
        # Przygotuj dane wszystkich botów
        bots_data = []
        
        for bot in bots:
            # Przygotuj podstawowe dane
            bot_data = {
                'id': bot.id,
                'symbol': bot.symbol,
                'capital': bot.capital,
                'status': bot.status,
                'created_at': bot.created_at,
                'updated_at': bot.updated_at,
                'total_profit': "0.0",  # Domyślna wartość
            }
            
            # Dodaj całkowity zysk, jeśli istnieją transakcje
            trades = BnbTrade.objects.filter(bot=bot)
            if trades.exists():
                total_profit = sum(trade.profit for trade in trades if trade.profit is not None)
                bot_data['total_profit'] = str(round(total_profit, 8))
            
            bots_data.append(bot_data)
        
        return Response(bots_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([CustomAuthentication])
def get_bot_profits(request, bot_id=None, user_id=None):
    """
    Pobiera historyczne zyski botów dla danego użytkownika.
    Jeśli podano bot_id, pobiera tylko zyski tego konkretnego bota.
    """
    try:
        # Pobierz user_id z parametru URL lub z uwierzytelniania
        if user_id is None:
            # Próbuj pobrać z query params (jeśli został przekazany jako parametr)
            user_id = request.query_params.get('user_id')
            
            # Jeśli nadal None, spróbuj z auth
            if user_id is None and hasattr(request, 'auth') and hasattr(request.auth, 'user_id'):
                user_id = request.auth.user_id
        
        if not user_id:
            return Response({'error': 'Nie podano user_id'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Konwersja na int (jeśli user_id jest stringiem)
        try:
            user_id = int(user_id)
        except ValueError:
            return Response({'error': 'Nieprawidłowy format user_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Określ zakres dat (domyślnie 30 dni)
        days_param = request.query_params.get('days', '30')
        try:
            days = int(days_param)
        except ValueError:
            days = 30
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Filtruj boty według user_id i opcjonalnie bot_id
        if bot_id:
            bot_trades = BnbTrade.objects.filter(
                bot__user_id=user_id,
                bot_id=bot_id,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('created_at')
        else:
            bot_trades = BnbTrade.objects.filter(
                bot__user_id=user_id,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('created_at')
        
        # Zgrupuj zyski według daty
        daily_profits = {}
        bot_summary = {}
        total_profit = 0
        
        for trade in bot_trades:
            # Zysk z transakcji
            profit = trade.profit or 0
            total_profit += profit
            
            # Grupowanie zysków według dnia
            date_key = trade.created_at.date().isoformat()
            if date_key not in daily_profits:
                daily_profits[date_key] = 0
            daily_profits[date_key] += profit
            
            # Grupowanie zysków według botów
            bot_key = f"{trade.bot.symbol}_{trade.bot.id}"
            if bot_key not in bot_summary:
                bot_summary[bot_key] = {
                    "bot_id": trade.bot.id,
                    "symbol": trade.bot.symbol,
                    "total_profit": 0,
                    "trade_count": 0
                }
            bot_summary[bot_key]["total_profit"] += profit
            bot_summary[bot_key]["trade_count"] += 1
        
        # Uporządkuj dane według dat
        profit_history = [
            {"date": date, "profit": round(profit, 8)}
            for date, profit in sorted(daily_profits.items())
        ]
        
        # Uporządkuj podsumowanie botów według zysków (od najwyższych)
        bot_performance = sorted(
            bot_summary.values(),
            key=lambda x: x["total_profit"],
            reverse=True
        )
        
        response_data = {
            "profits": profit_history,
            "summary": {
                "total_profit": round(total_profit, 8),
                "trade_count": len(bot_trades),
                "period_days": days,
                "bots": bot_performance
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

