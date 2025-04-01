import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def analyze_bot_data(profit_data, local_bot_id=None, microservice_bot_id=None, bot_name=None):
    """
    Analizuje dane bota i przygotowuje szczegółowe informacje.
    
    Args:
        profit_data: Dane o zyskach botów.
        local_bot_id: Lokalne ID bota.
        microservice_bot_id: ID bota w mikrousłudze.
        bot_name: Nazwa bota.
        
    Returns:
        dict: Słownik z danymi analizy.
    """
    if not profit_data or not profit_data.get("data"):
        print(f"[DEBUG BOT] Brak danych profit_data lub brak profit_data['data']")
        return None
    
    try:
        print(f"[DEBUG BOT] Rozpoczynam analizę z local_bot_id={local_bot_id}, microservice_bot_id={microservice_bot_id}")
        
        # Jeśli podano ID bota, filtruj dane tylko dla tego bota
        bot_data = []
        if local_bot_id or microservice_bot_id:
            original_id = local_bot_id
            mapped_id = microservice_bot_id if microservice_bot_id else local_bot_id
            
            print(f"[DEBUG BOT] Szukam danych dla original_id={original_id}, mapped_id={mapped_id}")
            print(f"[DEBUG BOT] Liczba punktów danych przed filtrowaniem: {len(profit_data['data'])}")
            
            # Szukamy danych dla obu ID - zarówno lokalnego jak i mikrousługowego
            for item in profit_data["data"]:
                item_bot_id = str(item.get("bot_id", ""))
                item_local_id = str(item.get("local_bot_id", ""))
                
                # Sprawdź dokładne dopasowanie lub zawieranie ID
                if ((mapped_id and (item_bot_id == str(mapped_id) or 
                                  item_bot_id.startswith(str(mapped_id)) or 
                                  str(mapped_id) in item_bot_id)) or 
                   (original_id and item_local_id == str(original_id))):
                    print(f"[DEBUG BOT] Znaleziono pasujący punkt danych: {item}")
                    bot_data.append(item)
            
            # Jeśli nie znaleziono danych, spróbuj bardziej elastycznego wyszukiwania
            if len(bot_data) == 0:
                print(f"[DEBUG BOT] Próba elastycznego wyszukiwania (nie znaleziono bezpośrednich dopasowań)")
                for item in profit_data["data"]:
                    item_str = str(item)
                    
                    # Użyj wyrażeń regularnych do znalezienia "51015*"
                    import re
                    if mapped_id and isinstance(mapped_id, str):
                        match = re.search(r'51015\w+-\w+', mapped_id)
                        if match:
                            pattern = match.group(0)
                            if pattern in item_str:
                                print(f"[DEBUG BOT] Znaleziono dopasowanie za pomocą wzorca {pattern}: {item}")
                                bot_data.append(item)
                                continue
                    
                    # Sprawdź czy zawiera ID bota w dowolnej formie
                    if (original_id and str(original_id) in item_str) or (mapped_id and str(mapped_id) in item_str):
                        print(f"[DEBUG BOT] Znaleziono zawierające ID: {item}")
                        bot_data.append(item)
        else:
            # Jeśli nie podano ID bota, użyj wszystkich danych
            bot_data = profit_data["data"]
            print(f"[DEBUG BOT] Brak ID bota, używam wszystkich danych: {len(bot_data)} punktów")
        
        print(f"[DEBUG BOT] Po filtrowaniu znaleziono {len(bot_data)} punktów danych")
        
        if not bot_data:
            print(f"[DEBUG BOT] Nie znaleziono żadnych danych dla bota")
            return None
            
        # Przygotuj szczegółowe dane
        bot_detailed_info = {}
        
        if local_bot_id:
            bot_detailed_info = {
                "id": local_bot_id,
                "name": bot_name or f"Bot {local_bot_id}",
            }
            
            # Oblicz podstawowe statystyki
            total_profit = sum(item.get("profit", 0) for item in bot_data)
            avg_profit = total_profit / len(bot_data) if bot_data else 0
            max_profit = max(item.get("profit", 0) for item in bot_data) if bot_data else 0
            min_profit = min(item.get("profit", 0) for item in bot_data) if bot_data else 0
            
            # Sortuj dane według daty, aby zobaczyć trendy
            sorted_points = sorted(bot_data, key=lambda x: x.get("date", ""))
            
            # Dodaj szczegółowe dane o zyskach
            bot_detailed_info.update({
                "data_points": len(bot_data),
                "total_profit": round(total_profit, 4),
                "average_profit": round(avg_profit, 4),
                "max_profit": round(max_profit, 4),
                "min_profit": round(min_profit, 4),
                "profit_data": sorted_points[:10]  # Pierwsze 10 punktów dla przykładu
            })
            
            # Jeśli mamy tylko 1 punkt danych, zaznacz to
            if len(bot_data) == 1:
                bot_detailed_info["note"] = "Dla tego bota dostępny jest tylko jeden punkt danych. Wykres zawiera dodatkowy punkt (0) dla lepszej wizualizacji."
            
            print(f"[DEBUG BOT] Wygenerowano szczegółowe informacje: {len(bot_data)} punktów, total_profit={total_profit}")
            return bot_detailed_info
        else:
            # Analiza zbiorcza dla wszystkich botów
            unique_bots = set()
            for item in bot_data:
                # Próbuj znaleźć identyfikator bota w różnych polach
                bot_identifier = item.get("bot_id") or item.get("local_bot_id") or item.get("microservice_bot_id")
                if bot_identifier:
                    unique_bots.add(str(bot_identifier))
                    
            result = {
                "total_bots": len(unique_bots),
                "data_points": len(bot_data),
                "summary": profit_data.get("summary", {})
            }
            
            print(f"[DEBUG BOT] Wygenerowano zbiorczą analizę: {len(unique_bots)} botów, {len(bot_data)} punktów")
            return result
            
    except Exception as e:
        logger.error(f"Błąd podczas analizy danych bota: {e}")
        print(f"[DEBUG BOT] Błąd podczas analizy danych bota: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_bot_existence(local_bot_id, microservice_token):
    """
    Sprawdza, czy bot o podanym ID istnieje w mikrousługach.
    
    Args:
        local_bot_id: Lokalne ID bota.
        microservice_token: Token do autoryzacji w mikrousługach.
        
    Returns:
        tuple: (bot_exists, bot_name, bot_data)
    """
    if not local_bot_id or not microservice_token:
        return False, f"Bot {local_bot_id}", None
        
    bot_exists = False
    bot_name = f"Bot {local_bot_id}"
    bot_data = None
    
    # Pobierz informacje o bocie z lokalnej bazy danych
    actual_microservice_id = None
    try:
        from home.models import Bot
        local_bot = Bot.objects.filter(id=local_bot_id).first()
        if local_bot:
            bot_name = local_bot.name or bot_name
            actual_microservice_id = local_bot.microservice_bot_id
            print(f"[DEBUG BOT CHECK] Znaleziono bota w bazie danych: id={local_bot_id}, name={bot_name}, microservice_id={actual_microservice_id}, status={local_bot.status}")
    except Exception as e:
        print(f"[DEBUG BOT CHECK] Błąd podczas pobierania danych bota z bazy: {e}")
    
    # Sprawdź w pierwszej mikrousłudze (5-10-15rei)
    try:
        headers = {"Authorization": f"Token {microservice_token}"}
        
        # Użyj microservice_id jeśli jest dostępne
        query_id = actual_microservice_id if actual_microservice_id else local_bot_id
        print(f"[DEBUG BOT CHECK] Sprawdzam bota w mikrousłudze 5-10-15rei, query_id={query_id}")
        
        check_url = f"{settings.BNB_MICROSERVICE_URL}/get_bot_details/{query_id}/"
        print(f"[DEBUG BOT CHECK] URL zapytania: {check_url}")
        
        response = requests.get(check_url, headers=headers, timeout=5)
        print(f"[DEBUG BOT CHECK] Odpowiedź z pierwszej mikrousługi: status={response.status_code}")
        
        if response.status_code == 200:
            bot_exists = True
            bot_data = response.json()
            bot_name = bot_data.get('name', bot_name)
            print(f"[DEBUG BOT CHECK] Bot {query_id} znaleziony w mikrousłudze 5-10-15rei: {bot_data}")
    except Exception as e:
        print(f"[DEBUG BOT CHECK] Błąd podczas sprawdzania bota {query_id} w mikrousłudze 5-10-15rei: {e}")
    
    # Jeśli nie znaleziono w pierwszej, sprawdź w drugiej (5-10-15)
    if not bot_exists:
        try:
            # Użyj microservice_id jeśli jest dostępne
            query_id = actual_microservice_id if actual_microservice_id else local_bot_id
            print(f"[DEBUG BOT CHECK] Sprawdzam bota w mikrousłudze 5-10-15, query_id={query_id}")
            
            check_url = f"{settings.BNB_MICROSERVICE_URL_2}/get_bot_details/{query_id}/"
            print(f"[DEBUG BOT CHECK] URL zapytania: {check_url}")
            
            response = requests.get(check_url, headers=headers, timeout=5)
            print(f"[DEBUG BOT CHECK] Odpowiedź z drugiej mikrousługi: status={response.status_code}")
            
            if response.status_code == 200:
                bot_exists = True
                bot_data = response.json()
                bot_name = bot_data.get('name', bot_name)
                print(f"[DEBUG BOT CHECK] Bot {query_id} znaleziony w mikrousłudze 5-10-15: {bot_data}")
        except Exception as e:
            print(f"[DEBUG BOT CHECK] Błąd podczas sprawdzania bota {query_id} w mikrousłudze 5-10-15: {e}")
    
    print(f"[DEBUG BOT CHECK] Wynik sprawdzania: bot_exists={bot_exists}, bot_name={bot_name}")
    return bot_exists, bot_name, bot_data

def get_bot_microservice_id(local_bot_id, user_id):
    """
    Sprawdza mapowanie ID lokalnego bota na microservice_bot_id.
    
    Args:
        local_bot_id: Lokalne ID bota.
        user_id: ID użytkownika.
        
    Returns:
        tuple: (microservice_bot_id, bot_name)
    """
    try:
        print(f"[DEBUG ID MAP] Sprawdzanie mapowania dla bota ID={local_bot_id}, user_id={user_id}")
        
        # Import modelu wewnątrz funkcji
        from home.models import Bot
        
        # Poszukaj bota w bazie danych
        local_bot = Bot.objects.filter(id=local_bot_id, user_id=user_id).first()
        if local_bot:
            print(f"[DEBUG ID MAP] Znaleziono bota: ID={local_bot_id}, name={local_bot.name}, microservice_id={local_bot.microservice_bot_id}, status={local_bot.status}, user_id={local_bot.user_id}")
            bot_name = local_bot.name or f"Bot {local_bot_id}"
            
            # Sprawdź czy microservice_bot_id istnieje i nie jest puste
            if local_bot.microservice_bot_id:
                microservice_bot_id = str(local_bot.microservice_bot_id)
                print(f"[DEBUG ID MAP] Znaleziono mapowanie: ID={local_bot_id} -> microservice_bot_id={microservice_bot_id}")
                # Sprawdź czy to string czy liczba
                if microservice_bot_id.isdigit():
                    print(f"[DEBUG ID MAP] Microservice ID jest numerem: {microservice_bot_id}")
                else:
                    print(f"[DEBUG ID MAP] Microservice ID jest stringiem: {microservice_bot_id}")
                return microservice_bot_id, bot_name
            else:
                print(f"[DEBUG ID MAP] Bot {local_bot_id} nie ma microservice_bot_id")
                return None, bot_name
        else:
            # Sprawdź czy istnieje bot o takim ID dla innego użytkownika
            any_bot = Bot.objects.filter(id=local_bot_id).first()
            if any_bot:
                print(f"[DEBUG ID MAP] Bot o ID={local_bot_id} istnieje, ale należy do użytkownika {any_bot.user_id}, a nie {user_id}")
                print(f"[DEBUG ID MAP] Dane bota: name={any_bot.name}, microservice_id={any_bot.microservice_bot_id}, status={any_bot.status}")
            else:
                print(f"[DEBUG ID MAP] Bot o ID={local_bot_id} nie istnieje w bazie danych")
            
            return None, f"Bot {local_bot_id}"
    except Exception as e:
        print(f"[DEBUG ID MAP] Błąd podczas sprawdzania mapowania bota: {e}")
        import traceback
        traceback.print_exc()
        return None, f"Bot {local_bot_id}" 