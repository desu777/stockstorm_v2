import json
import logging
from django.conf import settings
import openai

logger = logging.getLogger(__name__)

def get_binance_symbol_info(client, symbol):
    """
    Pobiera informacje o symbolu z Binance, w tym ograniczenia LOT_SIZE.
    
    Args:
        client: Zainicjalizowany klient Binance.
        symbol: Symbol kryptowaluty (np. 'BTCUSDT').
        
    Returns:
        dict: Informacje o symbolu lub None w przypadku błędu.
    """
    try:
        exchange_info = client.get_exchange_info()
        
        for sym_info in exchange_info['symbols']:
            if sym_info['symbol'] == symbol:
                lot_size_filter = None
                min_notional_filter = None
                
                # Znajdź filtry LOT_SIZE i MIN_NOTIONAL
                for filter_info in sym_info['filters']:
                    if filter_info['filterType'] == 'LOT_SIZE':
                        lot_size_filter = filter_info
                    elif filter_info['filterType'] == 'MIN_NOTIONAL':
                        min_notional_filter = filter_info
                        
                return {
                    'baseAsset': sym_info['baseAsset'],
                    'quoteAsset': sym_info['quoteAsset'],
                    'lot_size': lot_size_filter,
                    'min_notional': min_notional_filter
                }
                
        return None
    except Exception as e:
        print(f"[DEBUG] Błąd pobierania informacji o symbolu: {e}")
        return None

def parse_trading_command(user_message, openai_client):
    """
    Parsuje komendę handlową używając GPT-4o-mini, aby wyodrębnić szczegóły transakcji.
    
    Args:
        user_message: Wiadomość od użytkownika.
        openai_client: Zainicjalizowany klient OpenAI.
        
    Returns:
        dict: Słownik z danymi transakcji lub None, jeśli nie jest komendą handlową.
    """
    from .intent_detection import check_trading_command
    trading_intent = check_trading_command(user_message)
    
    if not trading_intent:
        return None
    
    try:
        # Zapytaj model o ekstrakcję danych
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
                Jesteś asystentem handlowym. Twoim zadaniem jest wyodrębnienie danych o transakcji z tekstu.
                Zwróć tylko JSON z następującymi polami:
                - action: "buy", "sell", "stop_limit_buy" lub "stop_limit_sell"
                - asset: symbol aktywa (np. "BTC")
                - currency: waluta płatności (np. "USDT")
                - amount: kwota (liczba)
                - category: kategoria (np. "BTC HP")
                - note: treść notatki (np. "HP1")
                - position_identifier: identyfikator pozycji do sprzedaży (np. "HP2" w "sprzedaj mi HP2 z BTC HP")
                - limit_price: cena limit dla zleceń stop-limit (np. 50000)
                - trigger_price: cena trigger dla zleceń stop-limit (np. 49000)
                
                Dla zleceń stop-limit obsługuj komendy typu "ustaw zlecenie stop limit buy na btc cena 83865.56 trigger 83867 za 100 usdc".
                W tym przypadku:
                - action: "stop_limit_buy"
                - asset: "BTC"
                - currency: "USDC"
                - amount: 100
                - limit_price: 83865.56
                - trigger_price: 83867
                
                Podobnie dla zleceń sprzedaży: "ustaw zlecenie stop limit sell na BTC HP hp1 cena 120002 trigger 120001"
                W tym przypadku:
                - action: "stop_limit_sell" 
                - position_identifier: "hp1"
                - category: "BTC HP"
                - limit_price: 120002
                - trigger_price: 120001
                
                Dla poleceń sprzedaży obsługuj formaty typu "sprzedaj mi HP2 z BTC HP", gdzie HP2 to position_identifier, a BTC HP to category.
                
                Jeśli nie podano wyraźnie kategorii, to dla poleceń kupna ustaw category na "<asset> HP" (np. "BTC HP").
                
                Jeśli jakiegoś pola brakuje, ustaw jego wartość na null.
                """}, 
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parsuj odpowiedź do słownika
        trading_data = json.loads(response.choices[0].message.content)
        print(f"[DEBUG] Dane transakcji: {trading_data}")
        
        # Dodatkowa logika dla dopasowania danych
        if trading_data['action'] == 'buy':
            # Jeśli kategoria nie została podana, użyj domyślnego formatu
            if not trading_data.get('category'):
                trading_data['category'] = f"{trading_data['asset']} HP"
                
        return trading_data
    except Exception as e:
        logger.error(f"Błąd podczas parsowania komendy handlowej: {e}")
        print(f"[DEBUG] Błąd podczas parsowania komendy handlowej: {e}")
        return None

def execute_trade(user_id, trading_data):
    """
    Wykonuje transakcję na podstawie danych handlowych i zapisuje w portfolio HP.
    Teraz również wykonuje rzeczywistą transakcję na Binance przy użyciu API.
    
    Args:
        user_id: ID użytkownika.
        trading_data: Dane transakcji (wynik funkcji parse_trading_command).
        
    Returns:
        dict: Wynik operacji z polem 'success' i 'message'.
    """
    try:
        # Jeśli to zlecenie stop-limit, przekaż je do odpowiedniej funkcji
        if trading_data['action'] in ['stop_limit_buy', 'stop_limit_sell']:
            return execute_stop_limit_order(user_id, trading_data)
    
        # Sprawdź czy mamy wszystkie potrzebne dane
        if trading_data['action'] == 'buy':
            if not all([trading_data.get("action"), trading_data.get("asset"), 
                       trading_data.get("amount"), trading_data.get("currency")]):
                return {
                    'success': False, 
                    'message': "Niepełne dane transakcji. Wymagane pola dla kupna: action, asset, amount, currency."
                }
        elif trading_data['action'] == 'sell':
            # Dla sprzedaży potrzebujemy albo identyfikatora pozycji, albo standardowych danych
            if not trading_data.get("position_identifier") and not all([
                trading_data.get("asset"), trading_data.get("amount"), trading_data.get("currency")
            ]):
                return {
                    'success': False, 
                    'message': "Niepełne dane transakcji sprzedaży. Podaj identyfikator pozycji (np. HP1) lub szczegóły aktywa."
                }
        
        # Pobierz użytkownika
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        # Importy modeli dla HP Crypto
        from hpcrypto.models import HPCategory, Position
        from django.utils import timezone
        
        # Pobierz profil użytkownika, który zawiera klucze API
        profile = getattr(user, 'profile', None)
        
        # Sprawdź czy użytkownik ma skonfigurowane klucze API
        has_api_keys = profile and profile.binance_api_key and profile.binance_api_secret_enc
        print(f"[DEBUG] Użytkownik {user.username} ma klucze API: {has_api_keys}")

        # Przygotuj klienta Binance, jeśli mamy klucze API
        binance_client = None
        if has_api_keys:
            try:
                from binance.client import Client
                from binance.exceptions import BinanceAPIException
                
                api_key = profile.binance_api_key
                api_secret = profile.get_binance_api_secret()
                
                # Inicjalizuj klienta Binance
                binance_client = Client(api_key, api_secret)
                print(f"[DEBUG] Inicjalizacja klienta Binance powiodła się")
            except Exception as e:
                print(f"[DEBUG] Błąd inicjalizacji klienta Binance: {e}")
                binance_client = None
        
        # Obsługa sprzedaży przez identyfikator pozycji
        if trading_data['action'] == 'sell' and trading_data.get('position_identifier'):
            position_id = trading_data.get('position_identifier')
            category_name = trading_data.get('category')
            
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
                return {
                    'success': False,
                    'message': f"Nie znaleziono pozycji o identyfikatorze {position_id}"
                    + (f" w kategorii {category_name}" if category_name else "")
                }
            
            print(f"[DEBUG] Znaleziono pozycję: {position.ticker}, ilość: {position.quantity}, cena: {position.current_price}")
            
            # Uzupełnij dane transakcji z pozycji
            trading_data['asset'] = position.ticker
            trading_data['amount'] = position.quantity  # Ilość kryptowaluty do sprzedaży
            trading_data['currency'] = 'USDT'  # Domyślna waluta
            
            # Dodaj domyślną walutę, jeśli nie została określona
            if not trading_data.get('currency'):
                # Sprawdź, czy ticker zawiera już walutę (np. BTCUSDT)
                if position.ticker.endswith('USDT'):
                    trading_data['currency'] = 'USDT'
                elif position.ticker.endswith('USDC'):
                    trading_data['currency'] = 'USDC'
                elif position.ticker.endswith('BUSD'):
                    trading_data['currency'] = 'BUSD'
                elif position.ticker.endswith('BTC'):
                    trading_data['currency'] = 'BTC'
                elif position.ticker.endswith('ETH'):
                    trading_data['currency'] = 'ETH'
                else:
                    # Domyślnie używamy USDT
                    trading_data['currency'] = 'USDT'
                
                print(f"[DEBUG] Ustawiono domyślną walutę: {trading_data['currency']} dla tickera: {position.ticker}")
            
            # Wykonaj rzeczywistą transakcję na Binance, jeśli mamy klienta
            binance_order_result = None
            if binance_client:
                try:
                    # Formatuj symbol zgodnie z wymaganiami Binance
                    symbol = f"{position.ticker}{trading_data['currency']}"
                    
                    print(f"[DEBUG] Próba wykonania transakcji MARKET SELL na Binance: {symbol}, ilość: {position.quantity}")
                    
                    # Pobierz informacje o symbolu, aby sprawdzić ograniczenia
                    symbol_info = get_binance_symbol_info(binance_client, symbol)
                    
                    if symbol_info and symbol_info.get('lot_size'):
                        lot_size = symbol_info['lot_size']
                        min_qty = float(lot_size['minQty'])
                        max_qty = float(lot_size['maxQty'])
                        step_size = float(lot_size['stepSize'])
                        
                        print(f"[DEBUG] Ograniczenia LOT_SIZE dla {symbol}: min={min_qty}, max={max_qty}, step={step_size}")
                        
                        # Sprawdź, czy ilość spełnia minimalne wymagania
                        if float(position.quantity) < min_qty:
                            return {
                                'success': False,
                                'message': f"Ilość {position.quantity} {position.ticker} jest mniejsza niż minimalna wielkość lota ({min_qty}). Nie można wykonać sprzedaży na Binance."
                            }
                            
                        # Dostosuj ilość do krotności step_size
                        if step_size > 0:
                            adjusted_qty = float(int(float(position.quantity) / step_size) * step_size)
                            adjusted_qty = round(adjusted_qty, 8)  # Zaokrąglij do 8 miejsc po przecinku
                            
                            if adjusted_qty != float(position.quantity):
                                print(f"[DEBUG] Dostosowano ilość do step_size: {adjusted_qty} (było: {position.quantity})")
                                if adjusted_qty < min_qty:
                                    return {
                                        'success': False,
                                        'message': f"Po dostosowaniu ilość {adjusted_qty} {position.ticker} jest mniejsza niż minimalna wielkość lota ({min_qty}). Nie można wykonać sprzedaży na Binance."
                                    }
                                position_quantity = adjusted_qty
                            else:
                                position_quantity = float(position.quantity)
                        else:
                            position_quantity = float(position.quantity)
                    else:
                        position_quantity = float(position.quantity)
                        print(f"[DEBUG] Nie udało się pobrać informacji o ograniczeniach dla {symbol}. Używam oryginalnej ilości.")
                    
                    # Wykonaj zlecenie MARKET SELL z dostosowaną ilością
                    binance_order_result = binance_client.create_order(
                        symbol=symbol,
                        side=Client.SIDE_SELL,
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=position_quantity
                    )
                    
                    print(f"[DEBUG] Wykonano transakcję na Binance: {binance_order_result}")
                    
                    # Sprawdź, czy należy zaktualizować ilość ze względu na prowizję
                    if 'fills' in binance_order_result:
                        actual_executed_qty = 0
                        total_commission = 0
                        commission_asset = ""
                        
                        # Zsumuj faktyczną ilość sprzedaną oraz prowizję
                        for fill in binance_order_result['fills']:
                            actual_executed_qty += float(fill.get('qty', 0))
                            commission = float(fill.get('commission', 0))
                            commission_asset = fill.get('commissionAsset', "")
                            total_commission += commission
                        
                        print(f"[DEBUG] Faktycznie sprzedana ilość: {actual_executed_qty} {trading_data['asset']}")
                        print(f"[DEBUG] Prowizja: {total_commission} {commission_asset}")
                    
                except BinanceAPIException as e:
                    print(f"[DEBUG] Błąd API Binance podczas sprzedaży: {e}")
                    # Sprawdź, czy to błąd LOT_SIZE lub inny ważny błąd blokujący transakcję
                    if e.code == -1013 and "LOT_SIZE" in str(e):
                        return {
                            'success': False,
                            'message': f"Błąd sprzedaży na Binance: Ilość {position.quantity} {position.ticker} nie spełnia wymagań minimalnej wielkości lota. Sprawdź minimalne wartości dla tej kryptowaluty."
                        }
                    elif e.code in [-1000, -1001, -1002, -1003, -1010, -1013, -1015, -1016, -1020, -1021, -1022, -2010, -2011, -2013, -2014, -2015]:
                        # Inne krytyczne błędy, które powinny zatrzymać transakcję
                        return {
                            'success': False,
                            'message': f"Błąd transakcji na Binance: {e}. Pozycja nie została sprzedana."
                        }
                    # Dla mniej krytycznych błędów kontynuujemy z symulacją
                except Exception as e:
                    print(f"[DEBUG] Nieoczekiwany błąd podczas sprzedaży na Binance: {e}")
                    # Kontynuujemy z symulacją, mimo błędu
            
            # Zaktualizuj pozycję w bazie danych HP
            position.exit_price = position.current_price
            position.exit_date = timezone.now()
            
            # Dodaj informację o wykonanej transakcji Binance, jeśli była
            if binance_order_result:
                position.notes = position.notes + f" [SPRZEDANE NA BINANCE {timezone.now().strftime('%Y-%m-%d %H:%M')}]"
            else:
                position.notes = position.notes + f" [SPRZEDANE (SYMULACJA) {timezone.now().strftime('%Y-%m-%d %H:%M')}]"
                
            position.save()
            
            print(f"[DEBUG] Pozycja oznaczona jako sprzedana: {position.ticker}, exit_price: {position.exit_price}")
            
            # Przygotuj odpowiednią wiadomość zwrotną
            if binance_order_result:
                return {
                    'success': True, 
                    'message': f"Wykonano sprzedaż pozycji {position_id} ({position.ticker}) o ilości {position.quantity} na Binance. Pozycja została oznaczona jako zamknięta."
                }
            else:
                return {
                    'success': True, 
                    'message': f"Zasymulowano sprzedaż pozycji {position_id} ({position.ticker}) o wartości {float(position.quantity) * float(position.current_price):.2f} {trading_data['currency']}. Pozycja została oznaczona jako zamknięta."
                }
        
        # Obsługa kupna - zawsze tworzymy nową pozycję
        if trading_data['action'] == 'buy':
            # Pobierz bieżącą cenę
            from hpcrypto.utils import get_binance_price
            current_price = get_binance_price(user, trading_data['asset'])
            
            if not current_price:
                return {
                    'success': False, 
                    'message': f"Nie udało się pobrać ceny dla {trading_data['asset']}. Sprawdź nazwę kryptowaluty."
                }
            
            # Oblicz ilość do kupna
            quantity = trading_data['amount'] / current_price
            
            # Wykonaj rzeczywistą transakcję na Binance, jeśli mamy klienta
            binance_order_result = None
            if binance_client:
                try:
                    # Formatuj symbol zgodnie z wymaganiami Binance
                    symbol = f"{trading_data['asset']}{trading_data['currency']}"
                    
                    print(f"[DEBUG] Próba wykonania transakcji MARKET BUY na Binance: {symbol}, kwota: {trading_data['amount']} {trading_data['currency']}")
                    
                    # Pobierz informacje o symbolu, aby sprawdzić ograniczenia
                    symbol_info = get_binance_symbol_info(binance_client, symbol)
                    
                    # Sprawdź ograniczenia MIN_NOTIONAL (minimalna wartość transakcji)
                    if symbol_info and symbol_info.get('min_notional'):
                        min_notional = float(symbol_info['min_notional']['minNotional'])
                        print(f"[DEBUG] Minimalna wartość transakcji dla {symbol}: {min_notional} {trading_data['currency']}")
                        
                        if float(trading_data['amount']) < min_notional:
                            return {
                                'success': False,
                                'message': f"Kwota {trading_data['amount']} {trading_data['currency']} jest mniejsza niż minimalna wartość transakcji ({min_notional}) dla {trading_data['asset']}. Zwiększ kwotę zakupu."
                            }
                    
                    # Wykonaj zlecenie MARKET BUY
                    # Dla BUY możemy użyć quoteOrderQty, który przyjmuje kwotę w walucie kwotowania (np. USDT)
                    binance_order_result = binance_client.create_order(
                        symbol=symbol,
                        side=Client.SIDE_BUY,
                        type=Client.ORDER_TYPE_MARKET,
                        quoteOrderQty=float(trading_data['amount'])  # Kwota w USDT/USDC
                    )
                    
                    print(f"[DEBUG] Wykonano transakcję na Binance: {binance_order_result}")
                    
                    # Pobierz faktyczną ilość zakupionej kryptowaluty z odpowiedzi Binance
                    if binance_order_result and 'executedQty' in binance_order_result:
                        quantity = float(binance_order_result['executedQty'])
                        
                        # Zaktualizuj cenę wejścia na podstawie faktycznej średniej ceny wykonania
                        if 'cummulativeQuoteQty' in binance_order_result and float(binance_order_result['executedQty']) > 0:
                            current_price = float(binance_order_result['cummulativeQuoteQty']) / float(binance_order_result['executedQty'])
                        
                        # Uwzględnij prowizję pobraną przez Binance, jeśli informacje są dostępne
                        if 'fills' in binance_order_result:
                            total_commission = 0
                            for fill in binance_order_result['fills']:
                                # Prowizja jest pobierana z zakupionej kryptowaluty, jeśli waluta prowizji jest taka sama jak kupowana
                                if fill.get('commissionAsset') == trading_data['asset']:
                                    commission = float(fill.get('commission', 0))
                                    total_commission += commission
                                    print(f"[DEBUG] Prowizja: {commission} {fill.get('commissionAsset')}")
                            
                            # Odejmij prowizję od ilości kryptowaluty
                            if total_commission > 0:
                                original_quantity = quantity
                                quantity -= total_commission
                                print(f"[DEBUG] Ilość po odjęciu prowizji: {quantity} (było: {original_quantity}, prowizja: {total_commission} {trading_data['asset']})")
                    
                except BinanceAPIException as e:
                    print(f"[DEBUG] Błąd API Binance podczas kupna: {e}")
                    # Sprawdź, czy to błąd LOT_SIZE lub inny ważny błąd blokujący transakcję
                    if e.code == -1013 and "LOT_SIZE" in str(e):
                        return {
                            'success': False,
                            'message': f"Błąd zakupu na Binance: Kwota {trading_data['amount']} {trading_data['currency']} dla {trading_data['asset']} nie spełnia wymagań minimalnej wielkości lota. Spróbuj zwiększyć kwotę transakcji."
                        }
                    elif e.code in [-1000, -1001, -1002, -1003, -1010, -1013, -1015, -1016, -1020, -1021, -1022, -2010, -2011, -2013, -2014, -2015]:
                        # Inne krytyczne błędy, które powinny zatrzymać transakcję
                        return {
                            'success': False,
                            'message': f"Błąd transakcji na Binance: {e}. Zakup nie został zrealizowany."
                        }
                    # Dla mniej krytycznych błędów kontynuujemy z symulacją
                except Exception as e:
                    print(f"[DEBUG] Nieoczekiwany błąd podczas kupna na Binance: {e}")
                    # Kontynuujemy z symulacją, mimo błędu
            
            # Znajdź lub utwórz kategorię HP
            category_name = trading_data.get('category', f"{trading_data['asset']} HP")
            category, created = HPCategory.objects.get_or_create(
                user=user, 
                name=category_name,
                defaults={'description': "Kategoria utworzona przez AI Agent"}
            )
            
            print(f"[DEBUG] Tworzenie nowej pozycji: {trading_data['asset']}, ilość: {quantity}, cena: {current_price}")
            
            # Przygotuj notatkę dla pozycji
            note = trading_data.get('note', '')
            if not note:
                # Sprawdź istniejące pozycje w tej kategorii, aby ustalić numer
                existing_positions = Position.objects.filter(
                    user=user, 
                    category=category,
                    exit_date__isnull=True  # Tylko aktywne pozycje
                ).count()
                
                position_number = existing_positions + 1
                note = f"{trading_data['asset']} HP{position_number}"
            
            # Dodaj informację o faktycznej transakcji Binance, jeśli była
            if binance_order_result:
                note += f" [ZAKUPIONE NA BINANCE {timezone.now().strftime('%Y-%m-%d %H:%M')}]"
            
            # Utwórz nową pozycję kupna
            position = Position(
                user=user,
                category=category,
                ticker=trading_data['asset'],
                quantity=quantity,
                entry_price=current_price,
                current_price=current_price,
                last_price_update=timezone.now(),
                notes=note
            )
            position.save()
            
            print(f"[DEBUG] Pozycja utworzona: {position.id}, {trading_data['asset']}, ilość: {quantity}, cena: {current_price}")
            
            # Przygotuj odpowiednią wiadomość zwrotną
            if binance_order_result:
                return {
                    'success': True, 
                    'message': f"Wykonano zakup {quantity:.8f} {trading_data['asset']} za {trading_data['amount']} {trading_data['currency']} na Binance. Pozycja utworzona z notatką: {note}."
                }
            else:
                return {
                    'success': True, 
                    'message': f"Zasymulowano zakup {quantity:.8f} {trading_data['asset']} za {trading_data['amount']} {trading_data['currency']} w kategorii {category_name}. Pozycja utworzona z notatką: {note}."
                }
        
        # Dla innych akcji...
        return {'success': False, 'message': f"Nieznana akcja: {trading_data['action']}"}
        
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania transakcji: {e}")
        print(f"[DEBUG] Błąd podczas wykonywania transakcji: {e}")
        return {'success': False, 'message': f"Błąd: {str(e)}"}

def execute_stop_limit_order(user_id, trading_data):
    """
    Tworzy zlecenie stop-limit na podstawie danych handlowych.
    Zapisuje zlecenie w bazie danych i wysyła na Binance jeśli skonfigurowano API.
    
    Args:
        user_id: ID użytkownika.
        trading_data: Dane transakcji (wynik funkcji parse_trading_command).
        
    Returns:
        dict: Wynik operacji z polem 'success' i 'message'.
    """
    try:
        # Pobierz użytkownika
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        
        # Importy modeli
        from hpcrypto.models import HPCategory, Position, PendingOrder
        from django.utils import timezone
        
        # Sprawdź czy mamy wszystkie potrzebne dane
        if trading_data['action'] == 'stop_limit_buy':
            # Dla zleceń kupna potrzebujemy: symbol, waluta, limit_price, trigger_price, amount
            required_fields = ["asset", "currency", "limit_price", "trigger_price", "amount"]
            if not all(trading_data.get(field) for field in required_fields):
                missing = [field for field in required_fields if not trading_data.get(field)]
                return {
                    'success': False,
                    'message': f"Niepełne dane dla zlecenia stop-limit buy. Brakujące pola: {', '.join(missing)}"
                }
                
        elif trading_data['action'] == 'stop_limit_sell':
            # Dla zleceń sprzedaży potrzebujemy: position_identifier lub (asset + amount), limit_price, trigger_price
            if not trading_data.get("position_identifier") and not trading_data.get("asset"):
                return {
                    'success': False,
                    'message': "Nie podano identyfikatora pozycji ani symbolu kryptowaluty dla zlecenia sprzedaży."
                }
                
            if not trading_data.get("limit_price") or not trading_data.get("trigger_price"):
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
                    return {
                        'success': False,
                        'message': f"Nie znaleziono pozycji o identyfikatorze {position_id}"
                        + (f" w kategorii {category_name}" if category_name else "")
                    }
                
                # Uzupełnij dane transakcji z pozycji
                trading_data['asset'] = position.ticker
                trading_data['amount'] = position.quantity  # ilość aktywów do sprzedaży
                trading_data['position_id'] = position.id
                
                # Dodaj domyślną walutę, jeśli nie została określona
                if not trading_data.get('currency'):
                    # Sprawdź, czy ticker zawiera już walutę (np. BTCUSDT)
                    if position.ticker.endswith('USDT'):
                        trading_data['currency'] = 'USDT'
                    elif position.ticker.endswith('USDC'):
                        trading_data['currency'] = 'USDC'
                    elif position.ticker.endswith('BUSD'):
                        trading_data['currency'] = 'BUSD'
                    elif position.ticker.endswith('BTC'):
                        trading_data['currency'] = 'BTC'
                    elif position.ticker.endswith('ETH'):
                        trading_data['currency'] = 'ETH'
                    else:
                        # Domyślnie używamy USDT
                        trading_data['currency'] = 'USDT'
                    
                    print(f"[DEBUG] Ustawiono domyślną walutę: {trading_data['currency']} dla tickera: {position.ticker}")
        
        # Sprawdź czy użytkownik ma ustawione klucze API Binance
        profile = getattr(user, 'profile', None)
        has_api_keys = profile and profile.binance_api_key and profile.binance_api_secret_enc
        print(f"[DEBUG] Użytkownik ma klucze API: {has_api_keys}")
        
        # Jeśli użytkownik ma klucze API, wykonaj zlecenie na Binance
        if has_api_keys:
            # Importuj funkcję realizującą zlecenie na Binance
            from ai_agent.binance_orders import execute_stop_limit_order as execute_binance_stop_limit_order
            
            # Wywołaj funkcję z modułu binance_orders
            print(f"[DEBUG] Wysyłam zlecenie na Binance: {trading_data['action']}, {trading_data['asset']}, trigger: {trading_data['trigger_price']}, limit: {trading_data['limit_price']}")
            
            # Wykonaj zlecenie na Binance
            result = execute_binance_stop_limit_order(user, trading_data)
            
            # Jeśli zlecenie zostało pomyślnie wysłane na Binance, zwróć wynik z Binance
            if result['success']:
                print(f"[DEBUG] Zlecenie pomyślnie wysłane na Binance: {result['message']}")
                return result
            else:
                print(f"[DEBUG] Błąd podczas wysyłania zlecenia na Binance: {result['message']}")
                # Jeśli to błąd związany z API Binance, zwróć go użytkownikowi zamiast tworzyć zlecenie lokalne
                if "Binance" in result['message']:
                    return result
                
                # W przypadku innych błędów, kontynuuj i utwórz zlecenie lokalne
                print("[DEBUG] Tworzę lokalne zlecenie oczekujące zamiast tego.")
                
        # Jeśli użytkownik nie ma kluczy API lub wystąpił nieznany błąd z Binance, 
        # utwórz zlecenie tylko w lokalnej bazie danych
        
        # Utwórz nowe zlecenie stop-limit
        order = PendingOrder(
            user=user,
            order_type='STOP_LIMIT_BUY' if trading_data['action'] == 'stop_limit_buy' else 'STOP_LIMIT_SELL',
            symbol=trading_data['asset'],
            currency=trading_data.get('currency', 'USDT'),
            limit_price=trading_data['limit_price'],
            trigger_price=trading_data['trigger_price'],
            amount=trading_data['amount'],
            status='WAITING',
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
        order.save()
        
        # Informacja o trybie (lokalny czy Binance)
        mode_info = "" if has_api_keys else " (tryb symulacji - nie skonfigurowano kluczy API Binance)"
        
        # Formatuj odpowiedź
        if trading_data['action'] == 'stop_limit_buy':
            return {
                'success': True,
                'message': f"Utworzono zlecenie stop-limit kupna dla {trading_data['asset']} po cenie {trading_data['limit_price']} {trading_data.get('currency', 'USDT')} (trigger: {trading_data['trigger_price']}). Zlecenie zostanie wykonane, gdy cena osiągnie poziom trigger.{mode_info}"
            }
        else:
            position_info = f" pozycji {trading_data.get('position_identifier', '')}" if trading_data.get('position_identifier') else ""
            return {
                'success': True,
                'message': f"Utworzono zlecenie stop-limit sprzedaży{position_info} dla {trading_data['asset']} po cenie {trading_data['limit_price']} {trading_data.get('currency', 'USDT')} (trigger: {trading_data['trigger_price']}). Zlecenie zostanie wykonane, gdy cena osiągnie poziom trigger.{mode_info}"
            }
            
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia zlecenia stop-limit: {e}")
        print(f"[DEBUG] Błąd podczas tworzenia zlecenia stop-limit: {e}")
        return {'success': False, 'message': f"Błąd: {str(e)}"} 