"""
Funkcje do pracy z zamówieniami Binance.
Ten moduł zawiera funkcje do wykonywania operacji handlowych na giełdzie Binance,
w szczególności tworzenie zleceń stop-limit, normalizację cen i ilości zgodnie
z wymaganiami giełdy.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

def execute_stop_limit_order(user, trading_data):
    """
    Tworzy i wysyła zlecenie stop-limit bezpośrednio na Binance.
    
    Args:
        user: Użytkownik wykonujący operację
        trading_data: Słownik z danymi operacji handlowej
        
    Returns:
        dict: Wynik operacji z polami 'success' i 'message'
    """
    logger.info(f"Rozpoczynam przetwarzanie zlecenia stop-limit: {trading_data}")
    
    try:
        from hpcrypto.models import HPCategory, Position, PendingOrder
        
        # Sprawdź czy mamy wszystkie potrzebne dane
        if trading_data['action'] == 'stop_limit_buy':
            # Dla zleceń kupna potrzebujemy: symbol, waluta, limit_price, trigger_price, amount
            required_fields = ["asset", "currency", "limit_price", "trigger_price", "amount"]
            if not all(trading_data.get(field) for field in required_fields):
                missing = [field for field in required_fields if not trading_data.get(field)]
                logger.error(f"Niepełne dane dla zlecenia stop-limit buy. Brakujące pola: {', '.join(missing)}")
                return {
                    'success': False,
                    'message': f"Niepełne dane dla zlecenia stop-limit buy. Brakujące pola: {', '.join(missing)}"
                }
                
        elif trading_data['action'] == 'stop_limit_sell':
            # Dla zleceń sprzedaży potrzebujemy: position_identifier lub (asset + amount), limit_price, trigger_price
            if not trading_data.get("position_identifier") and not trading_data.get("asset"):
                logger.error("Nie podano identyfikatora pozycji ani symbolu kryptowaluty dla zlecenia sprzedaży.")
                return {
                    'success': False,
                    'message': "Nie podano identyfikatora pozycji ani symbolu kryptowaluty dla zlecenia sprzedaży."
                }
                
            if not trading_data.get("limit_price") or not trading_data.get("trigger_price"):
                logger.error("Nie podano ceny limit lub trigger dla zlecenia stop-limit.")
                return {
                    'success': False,
                    'message': "Nie podano ceny limit lub trigger dla zlecenia stop-limit."
                }
                
            # Jeśli mamy identyfikator pozycji, znajdź pozycję
            if trading_data.get("position_identifier"):
                position_id = trading_data.get("position_identifier")
                category_name = trading_data.get("category")
                
                # Znajdź pozycję do sprzedaży
                position_query = Position.objects.filter(user=user, notes__icontains=position_id)
                
                # Jeśli podano kategorię, uwzględnij ją w wyszukiwaniu
                if category_name:
                    category = HPCategory.objects.filter(user=user, name=category_name).first()
                    if category:
                        position_query = position_query.filter(category=category)
                
                # Pobierz pozycję
                position = position_query.first()
                
                if not position:
                    logger.error(f"Nie znaleziono pozycji o identyfikatorze {position_id}" + (f" w kategorii {category_name}" if category_name else ""))
                    return {
                        'success': False,
                        'message': f"Nie znaleziono pozycji o identyfikatorze {position_id}"
                        + (f" w kategorii {category_name}" if category_name else "")
                    }
                
                # Uzupełnij dane transakcji z pozycji
                trading_data['asset'] = position.ticker
                trading_data['amount'] = position.quantity  # ilość aktywów do sprzedaży
                trading_data['position_id'] = position.id
        
        # Sprawdź czy użytkownik ma klucze API Binance
        profile = getattr(user, 'profile', None)
        logger.info(f"Sprawdzam profil użytkownika: {profile}")
        logger.info(f"Klucz API istnieje: {bool(profile and profile.binance_api_key)}")
        logger.info(f"Secret API istnieje: {bool(profile and profile.binance_api_secret_enc)}")
        
        if not profile or not profile.binance_api_key or not profile.binance_api_secret_enc:
            logger.error("Nie skonfigurowano kluczy API Binance. Przejdź do profilu, aby je ustawić.")
            return {
                'success': False,
                'message': "Nie skonfigurowano kluczy API Binance. Przejdź do profilu, aby je ustawić."
            }
        
        # Inicjalizuj klienta Binance
        api_key = profile.binance_api_key
        api_secret = profile.get_binance_api_secret()
        logger.info(f"Inicjalizuję klienta Binance z kluczami: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
        
        client = Client(api_key, api_secret)
        
        # Przygotuj parametry zlecenia
        # Debugowanie symbolu i waluty
        logger.info(f"Asset z trading_data: {trading_data['asset']}")
        logger.info(f"Currency z trading_data: {trading_data.get('currency', 'USDT')}")
        
        # Sprawdź, czy asset nie zawiera już waluty na końcu
        asset = trading_data['asset']
        currency = trading_data.get('currency', 'USDT')
        
        if asset.endswith(currency):
            # Jeśli asset już zawiera walutę (np. PORTALUSDT), używamy go bezpośrednio
            symbol = asset
            logger.info(f"Wykryto walutę już w asset, używam bezpośrednio symbolu: {symbol}")
        else:
            # W przeciwnym razie łączymy asset i currency
            symbol = f"{asset}{currency}"
            logger.info(f"Utworzono symbol handlowy: {symbol}")
            
        # Pobierz informacje o symbolu, aby sprawdzić filtry handlowe
        try:
            symbol_info = client.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Nie znaleziono informacji o symbolu {symbol}")
                return {
                    'success': False,
                    'message': f"Nie znaleziono informacji o symbolu {symbol}. Upewnij się, że para handlowa istnieje na Binance."
                }
                
            # Sprawdź czy handel dla symbolu jest aktywny
            if symbol_info['status'] != 'TRADING':
                logger.error(f"Para handlowa {symbol} nie jest aktualnie dostępna do handlu. Status: {symbol_info['status']}")
                return {
                    'success': False,
                    'message': f"Para handlowa {symbol} nie jest aktualnie dostępna do handlu. Status: {symbol_info['status']}"
                }
        except BinanceAPIException as e:
            logger.error(f"Błąd podczas pobierania informacji o symbolu: {e}")
            return {
                'success': False,
                'message': f"Błąd podczas pobierania informacji o symbolu: {e.message}"
            }
        
        # Pobierz bieżącą cenę rynkową
        ticker_data = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker_data['price'])
        logger.info(f"Bieżąca cena rynkowa: {current_price}")
            
        # Normalizuj ceny do wymagań Binance
        limit_price = float(trading_data['limit_price'])
        trigger_price = float(trading_data['trigger_price'])
        
        # Określ typ zlecenia na podstawie relacji między ceną trigger i aktualną ceną rynkową
        order_type = None
        side = 'BUY' if trading_data['action'] == 'stop_limit_buy' else 'SELL'
        
        if side == 'BUY':
            if trigger_price <= current_price:
                # Take Profit Limit (kupno) - aktywuje się gdy cena SPADNIE do trigger
                order_type = "TAKE_PROFIT_LIMIT"
                logger.info(f"Wykryto zlecenie TAKE_PROFIT_LIMIT (kupno): trigger ({trigger_price}) <= cena rynkowa ({current_price})")
            else:
                # Stop Loss Limit (kupno) - aktywuje się gdy cena WZROŚNIE do trigger
                order_type = "STOP_LOSS_LIMIT"
                logger.info(f"Wykryto zlecenie STOP_LOSS_LIMIT (kupno): trigger ({trigger_price}) > cena rynkowa ({current_price})")
        else:  # SELL
            if trigger_price >= current_price:
                # Take Profit Limit (sprzedaż) - aktywuje się gdy cena WZROŚNIE do trigger
                order_type = "TAKE_PROFIT_LIMIT"
                logger.info(f"Wykryto zlecenie TAKE_PROFIT_LIMIT (sprzedaż): trigger ({trigger_price}) >= cena rynkowa ({current_price})")
            else:
                # Stop Loss Limit (sprzedaż) - aktywuje się gdy cena SPADNIE do trigger
                order_type = "STOP_LOSS_LIMIT"
                logger.info(f"Wykryto zlecenie STOP_LOSS_LIMIT (sprzedaż): trigger ({trigger_price}) < cena rynkowa ({current_price})")
        
        # Zastosuj normalizację cen zgodnie z wymaganiami Binance
        normalized_limit_price = normalize_binance_price(client, symbol, limit_price)
        normalized_trigger_price = normalize_binance_price(client, symbol, trigger_price)
        
        logger.info(f"Oryginalna cena limit: {limit_price}, znormalizowana: {normalized_limit_price}")
        logger.info(f"Oryginalna cena trigger: {trigger_price}, znormalizowana: {normalized_trigger_price}")
        
        # Tworzenie zlecenia stop-limit
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'timeInForce': 'GTC',  # Good Till Cancelled
            'price': str(normalized_limit_price),  # Cena limit znormalizowana
            'stopPrice': str(normalized_trigger_price),  # Cena trigger znormalizowana
        }
        
        # Dodaj ilość lub wartość, zależnie od typu zlecenia
        if trading_data['action'] == 'stop_limit_buy':
            # Oblicz ilość do kupna
            raw_quantity = float(trading_data['amount']) / normalized_limit_price
            
            # Normalizuj ilość zgodnie z wymaganiami Binance dla danego symbolu
            quantity = normalize_binance_quantity(client, symbol, raw_quantity)
            
            # Sprawdź minimalną wartość zlecenia (MIN_NOTIONAL)
            min_notional = None
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'MIN_NOTIONAL':
                    min_notional = float(filter_item['minNotional'])
                    break
            
            estimated_value = quantity * normalized_limit_price
            if min_notional and estimated_value < min_notional:
                logger.error(f"Wartość zlecenia ({estimated_value}) jest poniżej minimalnej wymaganej ({min_notional})")
                return {
                    'success': False,
                    'message': f"Wartość zlecenia ({estimated_value:.8f} {trading_data.get('currency', 'USDT')}) jest poniżej minimalnej wymaganej przez Binance ({min_notional} {trading_data.get('currency', 'USDT')}). Zwiększ kwotę zakupu."
                }
            
            params['quantity'] = str(quantity)
            logger.info(f"Obliczona i znormalizowana ilość do kupna: {quantity} (z {raw_quantity})")
        else:
            # Dla sprzedaży używamy bezpośrednio ilości, ale również ją normalizujemy
            raw_quantity = float(trading_data['amount'])
            quantity = normalize_binance_quantity(client, symbol, raw_quantity)
            params['quantity'] = str(quantity)
            logger.info(f"Znormalizowana ilość do sprzedaży: {quantity} (z {raw_quantity})")
        
        try:
            # Utwórz zlecenie na Binance
            logger.info(f"Wysyłam zlecenie na Binance: {params}")
            
            # Najpierw spróbuj z testowym zleceniem, aby sprawdzić czy parametry są prawidłowe
            logger.info("Sprawdzam zlecenie za pomocą create_test_order")
            test_order = client.create_test_order(**params)
            logger.info(f"Test zlecenia udany: {test_order}")
            
            # Teraz wyślij prawdziwe zlecenie
            binance_order = client.create_order(**params)
            logger.info(f"Zlecenie utworzone na Binance: {binance_order}")
            
            # Utwórz nowe zlecenie stop-limit w naszej bazie danych
            order = PendingOrder(
                user=user,
                order_type=f"{'TP' if order_type == 'TAKE_PROFIT_LIMIT' else 'SL'}_{side[0]}",
                symbol=trading_data['asset'],
                currency=trading_data.get('currency', 'USDT'),
                limit_price=normalized_limit_price,  # Zapisujemy znormalizowane ceny
                trigger_price=normalized_trigger_price,  # Zapisujemy znormalizowane ceny
                amount=quantity,  # Używamy znormalizowanej ilości
                status='CREATED',  # Od razu ustawiamy status CREATED, bo zlecenie jest już na Binance
                binance_order_id=binance_order.get('orderId'),
                binance_client_order_id=binance_order.get('clientOrderId'),
                last_checked=timezone.now(),
                notes=trading_data.get('note', '') or ""
            )
            
            # Jeśli to zlecenie kupna, powiąż z kategorią
            if trading_data['action'] == 'stop_limit_buy':
                category_name = trading_data.get('category', f"{trading_data['asset']} HP")
                category, created = HPCategory.objects.get_or_create(
                    user=user,
                    name=category_name,
                    defaults={'description': "Kategoria utworzona przez system zleceń stop-limit"}
                )
                order.category = category
                
            # Jeśli to zlecenie sprzedaży, powiąż z pozycją
            elif trading_data['action'] == 'stop_limit_sell' and trading_data.get('position_id'):
                order.position = Position.objects.get(id=trading_data['position_id'])
                order.position_identifier = trading_data.get('position_identifier')
                
            # Zapisz zlecenie
            logger.info(f"Zapisuję zlecenie w bazie danych: {order}")
            order.save()
            
            # Formatuj odpowiedź
            if trading_data['action'] == 'stop_limit_buy':
                order_type_pl = "Take Profit Limit" if order_type == "TAKE_PROFIT_LIMIT" else "Stop Loss Limit"
                trigger_condition = "spadnie do" if order_type == "TAKE_PROFIT_LIMIT" else "wzrośnie do"
                return {
                    'success': True,
                    'message': f"Utworzono zlecenie {order_type_pl} kupna dla {quantity} {trading_data['asset']} po cenie {normalized_limit_price} {trading_data.get('currency', 'USDT')}. Zlecenie aktywuje się gdy cena {trigger_condition} {normalized_trigger_price}. Zlecenie zostało wysłane na Binance i będzie monitorowane przez system."
                }
            else:
                order_type_pl = "Take Profit Limit" if order_type == "TAKE_PROFIT_LIMIT" else "Stop Loss Limit"
                trigger_condition = "wzrośnie do" if order_type == "TAKE_PROFIT_LIMIT" else "spadnie do"
                position_info = f" pozycji {trading_data.get('position_identifier', '')}" if trading_data.get('position_identifier') else ""
                return {
                    'success': True,
                    'message': f"Utworzono zlecenie {order_type_pl} sprzedaży{position_info} dla {quantity} {trading_data['asset']} po cenie {normalized_limit_price} {trading_data.get('currency', 'USDT')}. Zlecenie aktywuje się gdy cena {trigger_condition} {normalized_trigger_price}. Zlecenie zostało wysłane na Binance i będzie monitorowane przez system."
                }
                
        except BinanceAPIException as e:
            logger.error(f"Błąd API Binance: {e.message}. Kod błędu: {e.code}")
            
            # Dodatkowa diagnostyka dla typowych błędów
            error_message = str(e.message)
            additional_info = ""
            
            if "MIN_NOTIONAL" in error_message:
                additional_info = " Wartość zlecenia jest zbyt niska. Zwiększ kwotę zakupu."
            elif "LOT_SIZE" in error_message:
                additional_info = " Ilość nie spełnia wymagań LOT_SIZE. Może być zbyt mała lub nieprawidłowo zaokrąglona."
            elif "PRICE_FILTER" in error_message:
                additional_info = " Cena nie spełnia wymagań filtra cenowego. Może być zbyt precyzyjna lub poza dozwolonym zakresem."
            elif "Stop price would trigger immediately" in error_message:
                if order_type == "STOP_LOSS_LIMIT":
                    if side == "BUY":
                        additional_info = " Cena stop jest zbyt niska i spowodowałaby natychmiastowe wykonanie zlecenia. Ustaw wyższą cenę stop (powyżej aktualnej ceny rynkowej)."
                    else:
                        additional_info = " Cena stop jest zbyt wysoka i spowodowałaby natychmiastowe wykonanie zlecenia. Ustaw niższą cenę stop (poniżej aktualnej ceny rynkowej)."
                else:  # TAKE_PROFIT_LIMIT
                    if side == "BUY":
                        additional_info = " Cena stop jest zbyt wysoka i nie spełnia warunku dla zlecenia Take Profit Limit kupna. Powinna być niższa od aktualnej ceny rynkowej."
                    else:
                        additional_info = " Cena stop jest zbyt niska i nie spełnia warunku dla zlecenia Take Profit Limit sprzedaży. Powinna być wyższa od aktualnej ceny rynkowej."
                
            return {
                'success': False,
                'message': f"Błąd API Binance: {e.message}. Kod błędu: {e.code}{additional_info}"
            }
            
        except Exception as e:
            logger.error(f"Wystąpił nieoczekiwany błąd: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f"Wystąpił nieoczekiwany błąd: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f"Wystąpił nieoczekiwany błąd: {str(e)}"
        }

def get_binance_quantity_precision(client, symbol):
    """
    Pobiera informacje o dozwolonej precyzji ilości dla danego symbolu na Binance.
    
    Args:
        client: Instancja klienta Binance
        symbol: Symbol pary handlowej (np. BTCUSDT)
        
    Returns:
        tuple: (min_qty, max_qty, step_size, precyzja zaokrąglenia)
    """
    # Pobierz info o symbolu
    info = client.get_symbol_info(symbol)
    
    # Domyślne wartości
    min_qty = 0.00000001
    max_qty = 9999999.0
    step_size = 0.00000001
    precision = 8  # domyślna precyzja
    
    # Znajdź filtr LOT_SIZE, który określa dozwolone wartości ilości
    if info and 'filters' in info:
        for filter_item in info['filters']:
            if filter_item['filterType'] == 'LOT_SIZE':
                min_qty = float(filter_item['minQty'])
                max_qty = float(filter_item['maxQty'])
                step_size = float(filter_item['stepSize'])
                break
    
    # Oblicz precyzję na podstawie step_size
    if step_size != 0:
        precision = 0
        step_size_str = "{:0.8f}".format(step_size)
        
        # Znajdź liczbę miejsc po przecinku
        if '.' in step_size_str:
            decimal_part = step_size_str.split('.')[1]
            # Usuń końcowe zera
            decimal_part = decimal_part.rstrip('0')
            precision = len(decimal_part)
    
    return min_qty, max_qty, step_size, precision

def normalize_binance_quantity(client, symbol, quantity):
    """
    Normalizuje ilość zgodnie z wymaganiami Binance dla danego symbolu.
    
    Args:
        client: Instancja klienta Binance
        symbol: Symbol pary handlowej (np. BTCUSDT)
        quantity: Ilość do znormalizowania
        
    Returns:
        float: Znormalizowana ilość
    """
    min_qty, max_qty, step_size, precision = get_binance_quantity_precision(client, symbol)
    
    # Ogranicz ilość do dozwolonych wartości min/max
    quantity = max(min_qty, min(max_qty, quantity))
    
    # Zaokrąglij do odpowiedniej precyzji zgodnie z step_size
    quantity = round(quantity - (quantity % step_size), precision)
    
    return quantity

def get_binance_price_precision(client, symbol):
    """
    Pobiera informacje o dozwolonej precyzji cenowej dla danego symbolu na Binance.
    
    Args:
        client: Instancja klienta Binance
        symbol: Symbol pary handlowej (np. BTCUSDT)
        
    Returns:
        tuple: (min_price, max_price, tick_size, precyzja zaokrąglenia)
    """
    # Pobierz info o symbolu
    info = client.get_symbol_info(symbol)
    
    # Domyślne wartości
    min_price = 0.00000001
    max_price = 1000000.0
    tick_size = 0.00000001
    precision = 8  # domyślna precyzja
    
    # Znajdź filtr PRICE_FILTER, który określa dozwolone wartości ceny
    if info and 'filters' in info:
        for filter_item in info['filters']:
            if filter_item['filterType'] == 'PRICE_FILTER':
                min_price = float(filter_item['minPrice'])
                max_price = float(filter_item['maxPrice'])
                tick_size = float(filter_item['tickSize'])
                break
    
    # Oblicz precyzję na podstawie tick_size
    if tick_size != 0:
        precision = 0
        tick_size_str = "{:0.8f}".format(tick_size)
        
        # Znajdź liczbę miejsc po przecinku
        if '.' in tick_size_str:
            decimal_part = tick_size_str.split('.')[1]
            # Usuń końcowe zera
            decimal_part = decimal_part.rstrip('0')
            precision = len(decimal_part)
    
    return min_price, max_price, tick_size, precision

def normalize_binance_price(client, symbol, price):
    """
    Normalizuje cenę zgodnie z wymaganiami Binance dla danego symbolu.
    
    Args:
        client: Instancja klienta Binance
        symbol: Symbol pary handlowej (np. BTCUSDT)
        price: Cena do znormalizowania
        
    Returns:
        float: Znormalizowana cena
    """
    min_price, max_price, tick_size, precision = get_binance_price_precision(client, symbol)
    
    # Ogranicz cenę do dozwolonych wartości min/max
    price = max(min_price, min(max_price, price))
    
    # Zaokrąglij do odpowiedniej precyzji zgodnie z tick_size
    price = round(price - (price % tick_size), precision)
    
    return price 