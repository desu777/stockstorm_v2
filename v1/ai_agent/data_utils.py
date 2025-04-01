import requests
import json
import logging
from django.conf import settings
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

def get_bot_profit_data(user_id, microservice_token, bot_id=None, period_days=365, microservice_id=None):
    """
    Pobiera dane o zyskach botów z obu mikrousług.
    """
    
    if not user_id or not microservice_token:
        print(f"[DEBUG] Brak wymaganych danych. user_id: {user_id}, token: {'podany' if microservice_token else 'brak'}")
        return None
        
    # Jeśli podano lokalne ID bota, spróbuj znaleźć odpowiadające microservice_bot_id
    microservice_bot_id = None
    original_bot_id = bot_id  # Zachowaj oryginalne ID bota
    local_bot_details = None
    
    if bot_id:
        try:
            # Import modelu wewnątrz funkcji zamiast na górze
            from home.models import Bot
            bot = Bot.objects.filter(id=bot_id, user_id=user_id).first()
            if bot and bot.microservice_bot_id:
                microservice_bot_id = bot.microservice_bot_id
                print(f"[DEBUG] Znaleziono mapowanie bota: ID={bot_id} -> microservice_bot_id={microservice_bot_id}")
                
                # Zachowaj szczegóły bota
                local_bot_details = {
                    'id': bot_id,
                    'name': bot.name,
                    'instrument': bot.instrument,
                    'status': bot.status,
                    'microservice_bot_id': microservice_bot_id
                }
                print(f"[DEBUG] Szczegóły bota: {json.dumps(local_bot_details, default=str)}")
            else:
                print(f"[DEBUG] Nie znaleziono bota o ID={bot_id} dla użytkownika {user_id} lub brak microservice_bot_id")
                
                # Sprawdź czy istnieje bot o tym ID w bazie danych
                any_bot = Bot.objects.filter(id=bot_id).first()
                if any_bot:
                    print(f"[DEBUG] Bot o ID={bot_id} istnieje, ale należy do innego użytkownika ({any_bot.user_id})")
                    print(f"[DEBUG] Mikrousługa ID: {any_bot.microservice_bot_id}, Status: {any_bot.status}")
                else:
                    print(f"[DEBUG] Bot o ID={bot_id} nie istnieje w bazie danych")
        except Exception as e:
            print(f"[DEBUG] Błąd podczas pobierania microservice_bot_id: {e}")
            import traceback
            traceback.print_exc()
    
    # Jeśli znaleziono microservice_bot_id, użyj go zamiast lokalnego bot_id DO ZAPYTANIA
    # ale zachowaj oryginalne ID dla wyświetlania
    query_bot_id = microservice_bot_id if microservice_bot_id else bot_id

    # Przechowujemy oryginalne ID bota i używamy tylko jednego poziomu mapowania
    merged_data = []
    summary = {
        "total_bots": 0, 
        "strategies": {}, 
        "most_profitable": None, 
        "least_profitable": None,
        "original_bot_id": original_bot_id,  # Lokalne ID bota
        "microservice_bot_id": microservice_bot_id,  # ID bota w mikrousłudze
        "local_bot_details": local_bot_details  # Szczegóły lokalnego bota
    }

    # Przygotuj nagłówki dla żądań HTTP
    headers = {
        "Authorization": f"Token {microservice_token}"
    }
    
    # Pobierz dane z pierwszej mikrousługi (5-10-15rei)
    if microservice_id is None or microservice_id == 'rei':
        try:
            print(f"[DEBUG] Pobieram dane o zyskach botów z mikrousługi 5-10-15rei")
            
            # Jeśli podano konkretne ID bota, sprawdź czy jest to bot z tej mikrousługi
            try_specific_bot = False
            if query_bot_id:
                # Najpierw sprawdź, czy bot istnieje w tej mikrousłudze
                bot_check_endpoint = f"{settings.BNB_MICROSERVICE_URL}/get_bot_details/{query_bot_id}/"
                bot_check_response = requests.get(bot_check_endpoint, headers=headers, timeout=5)
                
                if bot_check_response.status_code == 200:
                    try_specific_bot = True
                    print(f"[DEBUG] Bot {query_bot_id} znaleziony w mikrousłudze 5-10-15rei")
                else:
                    print(f"[DEBUG] Bot {query_bot_id} nie znaleziony w mikrousłudze 5-10-15rei")
            
            # Pobierz dane o zyskach
            if query_bot_id and try_specific_bot:
                endpoint1 = f"{settings.BNB_MICROSERVICE_URL}/get_bot_profits/user/{user_id}/{query_bot_id}/"
            else:
                endpoint1 = f"{settings.BNB_MICROSERVICE_URL}/get_bot_profits/user/{user_id}/"
                
            response1 = requests.get(endpoint1, headers=headers, timeout=10)
            if response1.status_code == 200:
                data1 = response1.json()
                if "profits" in data1:
                    print(f"[DEBUG] Pobrano dane z mikrousługi 5-10-15rei: {len(data1['profits'])} punktów")
                    
                    for item in data1["profits"]:
                        item["strategy"] = "5-10-15rei"
                        
                        # Dodaj identyfikatory bota jeśli ich brakuje
                        if "bot_id" not in item and query_bot_id:
                            item["bot_id"] = query_bot_id
                            print(f"[DEBUG] Dodano brakujące bot_id={query_bot_id} do elementu danych")
                        
                        if "local_bot_id" not in item and original_bot_id:
                            item["local_bot_id"] = original_bot_id
                            print(f"[DEBUG] Dodano brakujące local_bot_id={original_bot_id} do elementu danych")
                        
                        merged_data.append(item)
                    
                    # Aktualizuj podsumowanie
                    summary["strategies"]["5-10-15rei"] = len([p for p in data1["profits"] if p.get("strategy") == "5-10-15rei"])
                else:
                    print(f"[DEBUG] Nieoczekiwany format danych z mikrousługi 5-10-15rei")
            else:
                print(f"[DEBUG] Nieudane pobranie danych z mikrousługi 5-10-15rei: {response1.status_code}")
        except Exception as e:
            print(f"[DEBUG] Błąd podczas pobierania danych z mikrousługi 5-10-15rei: {e}")
            import traceback
            traceback.print_exc()

    # Pobierz dane z drugiej mikrousługi (5-10-15)
    if microservice_id is None or microservice_id == 'no_rei':
        try:
            print(f"[DEBUG] Pobieram dane o zyskach botów z mikrousługi 5-10-15")
            
            # Jeśli podano konkretne ID bota, sprawdź czy jest to bot z tej mikrousługi
            try_specific_bot = False
            if query_bot_id:
                # Najpierw sprawdź, czy bot istnieje w tej mikrousłudze
                bot_check_endpoint = f"{settings.BNB_MICROSERVICE_URL_2}/get_bot_details/{query_bot_id}/"
                bot_check_response = requests.get(bot_check_endpoint, headers=headers, timeout=5)
                
                if bot_check_response.status_code == 200:
                    try_specific_bot = True
                    print(f"[DEBUG] Bot {query_bot_id} znaleziony w mikrousłudze 5-10-15")
                else:
                    print(f"[DEBUG] Bot {query_bot_id} nie znaleziony w mikrousłudze 5-10-15")
            
            # Pobierz dane o zyskach
            if query_bot_id and try_specific_bot:
                endpoint2 = f"{settings.BNB_MICROSERVICE_URL_2}/get_bot_profits/user/{user_id}/{query_bot_id}/"
            else:
                endpoint2 = f"{settings.BNB_MICROSERVICE_URL_2}/get_bot_profits/user/{user_id}/"
                
            response2 = requests.get(endpoint2, headers=headers, timeout=10)
            if response2.status_code == 200:
                data2 = response2.json()
                if "profits" in data2:
                    print(f"[DEBUG] Pobrano dane z mikrousługi 5-10-15: {len(data2['profits'])} punktów")
                    
                    for item in data2["profits"]:
                        item["strategy"] = "5-10-15"
                        
                        # Dodaj identyfikatory bota jeśli ich brakuje
                        if "bot_id" not in item and query_bot_id:
                            item["bot_id"] = query_bot_id
                            print(f"[DEBUG] Dodano brakujące bot_id={query_bot_id} do elementu danych")
                        
                        if "local_bot_id" not in item and original_bot_id:
                            item["local_bot_id"] = original_bot_id
                            print(f"[DEBUG] Dodano brakujące local_bot_id={original_bot_id} do elementu danych")
                        
                        merged_data.append(item)
                    
                    # Aktualizuj podsumowanie
                    summary["strategies"]["5-10-15"] = len([p for p in data2["profits"] if p.get("strategy") == "5-10-15"])
                else:
                    print(f"[DEBUG] Nieoczekiwany format danych z mikrousługi 5-10-15")
            else:
                print(f"[DEBUG] Nieudane pobranie danych z mikrousługi 5-10-15: {response2.status_code}")
        except Exception as e:
            print(f"[DEBUG] Błąd podczas pobierania danych z mikrousługi 5-10-15: {e}")
            import traceback
            traceback.print_exc()
    
    # Zaktualizuj podsumowanie
    summary["total_bots"] = len(set([item.get("bot_id") for item in merged_data]))
    
    # Znajdź najbardziej i najmniej dochodowy bot
    bots_profits = {}
    for item in merged_data:
        bot_id = item.get("bot_id")
        profit = item.get("profit", 0)
        
        if bot_id not in bots_profits:
            bots_profits[bot_id] = {
                "profit": 0,
                "bot_name": item.get("bot_name", f"Bot {bot_id}"),
                "symbol": item.get("symbol", "")
            }
        
        bots_profits[bot_id]["profit"] += profit
    
    if bots_profits:
        most_profitable_id = max(bots_profits.items(), key=lambda x: x[1]["profit"])[0]
        least_profitable_id = min(bots_profits.items(), key=lambda x: x[1]["profit"])[0]
        
        summary["most_profitable"] = {
            "bot_id": most_profitable_id,
            "profit": bots_profits[most_profitable_id]["profit"],
            "bot_name": bots_profits[most_profitable_id]["bot_name"],
            "symbol": bots_profits[most_profitable_id]["symbol"]
        }
        
        summary["least_profitable"] = {
            "bot_id": least_profitable_id,
            "profit": bots_profits[least_profitable_id]["profit"],
            "bot_name": bots_profits[least_profitable_id]["bot_name"],
            "symbol": bots_profits[least_profitable_id]["symbol"]
        }
    
    # Po przetworzeniu danych, dodaj informacje o oryginalnym ID do danych
    if original_bot_id and microservice_bot_id and original_bot_id != microservice_bot_id:
        for item in merged_data:
            if str(item.get("bot_id")) == str(microservice_bot_id):
                # Dodaj informacje o lokalnym ID bota jako metadane
                item["local_bot_id"] = original_bot_id
                item["is_mapped"] = True
    
    print(f"[DEBUG] Łącznie pobrano {len(merged_data)} punktów danych")
    if bot_id:
        bot_data_points = [item for item in merged_data if str(item.get("bot_id")) == str(query_bot_id)]
        print(f"[DEBUG] Dla bota {original_bot_id} (query_id={query_bot_id}) znaleziono {len(bot_data_points)} punktów")
    
    return {
        "data": merged_data,
        "summary": summary
    }

def get_local_bots(user_id):
    """
    Pobiera boty użytkownika bezpośrednio z modelu Bot w głównej aplikacji.
    """
    try:
        # Import modelu wewnątrz funkcji
        from home.models import Bot
        
        # Pobierz wszystkie boty użytkownika
        bots = Bot.objects.filter(user_id=user_id)
        
        print(f"[DEBUG] Pobrano {len(bots)} botów z lokalnej bazy danych")
        
        # Przetwórz na format zgodny z tym, czego oczekują inne funkcje
        bots_data = []
        for bot in bots:
            bots_data.append({
                'id': bot.id,
                'name': bot.name,
                'symbol': bot.instrument,
                'capital': float(bot.capital),
                'status': bot.status,
                'total_profit': float(bot.total_profit),
                'max_price': float(bot.max_price),
                'percent': bot.percent,
                'created_at': bot.created_at.isoformat() if bot.created_at else None,
                'updated_at': bot.updated_at.isoformat() if bot.updated_at else None
            })
        
        return bots_data
    except Exception as e:
        logger.error(f"Błąd podczas pobierania botów z lokalnej bazy: {e}")
        print(f"[DEBUG ERROR] Błąd podczas pobierania botów z lokalnej bazy: {str(e)}")
        return []

def analyze_portfolio(user_id=None, microservice_token=None, profit_data=None):
    """
    Analizuje portfolio użytkownika, pobierając dane o wszystkich botach i ich zyskach.
    Może przyjąć bezpośrednio dane o zyskach (profit_data) zamiast pobierać je przez API.
    
    Args:
        user_id: ID użytkownika (wymagane jeśli nie podano profit_data)
        microservice_token: Token mikrousługi (wymagane jeśli nie podano profit_data)
        profit_data: Opcjonalnie - dane o zyskach (jeśli podane, parametry user_id i microservice_token są ignorowane)
        
    Returns:
        dict: Wyniki analizy portfolio
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Jeśli nie podano danych o zyskach, pobierz je z mikrousługi
        if not profit_data:
            if not user_id or not microservice_token:
                logger.error("Brak wymaganych parametrów: user_id, microservice_token lub profit_data")
                return None
                
            profit_data = get_bot_profit_data(user_id, microservice_token)
            
        if not profit_data or not profit_data.get("data"):
            logger.warning("Brak danych o zyskach do analizy portfolio")
            return None
            
        # DEBUG - Pokaż format otrzymanych danych
        print(f"[DEBUG PORTFOLIO] Otrzymano dane profit_data: {json.dumps(profit_data.get('summary', {}), default=str)}")
        print(f"[DEBUG PORTFOLIO] Liczba punktów danych: {len(profit_data.get('data', []))}")
        print(f"[DEBUG PORTFOLIO] Przykładowy punkt danych: {json.dumps(profit_data.get('data', [])[0] if profit_data.get('data') else {}, default=str)}")
            
        # Wyliczmy statystyki dla botów
        bot_data = {}
        bot_performance = {}
        total_profit = 0
        
        # Grupujemy zyski wg botów
        for item in profit_data["data"]:
            # Wyświetl każdy element danych dla debugowania
            print(f"[DEBUG PORTFOLIO] Przetwarzanie elementu danych: {json.dumps(item, default=str)}")
            
            # Bardziej elastyczne wyodrębnianie ID bota
            bot_id = item.get("bot_id") or item.get("local_bot_id") or item.get("microservice_bot_id")
            if not bot_id:
                # Próba wyodrębnienia z innych pól
                item_str = str(item)
                # Szukaj wzorców typu "51015rei-bot"
                import re
                match = re.search(r'51015\w+-\w+', item_str)
                if match:
                    bot_id = match.group(0)
                    print(f"[DEBUG PORTFOLIO] Znaleziono ID bota za pomocą regex: {bot_id}")
                else:
                    print(f"[DEBUG PORTFOLIO] Nie można zidentyfikować ID bota dla elementu: {item_str}")
                    continue
                    
            bot_id = str(bot_id)
            profit = item.get("profit", 0)
            date = item.get("date")
            
            print(f"[DEBUG PORTFOLIO] Zidentyfikowano bota: id={bot_id}, profit={profit}, date={date}")
            
            if bot_id not in bot_data:
                bot_data[bot_id] = {
                    "profits": [],
                    "dates": [],
                    "total_profit": 0,
                    "name": item.get("bot_name", f"Bot {bot_id}")
                }
                
            bot_data[bot_id]["profits"].append(profit)
            bot_data[bot_id]["dates"].append(date)
            bot_data[bot_id]["total_profit"] += profit
            total_profit += profit
            
        # Wyświetl licznik znalezionych botów
        print(f"[DEBUG PORTFOLIO] Znaleziono {len(bot_data)} unikalnych botów")
        for bot_id, data in bot_data.items():
            print(f"[DEBUG PORTFOLIO] Bot {bot_id}: {len(data['profits'])} punktów danych, łączny zysk: {data['total_profit']}")
        
        # Obliczamy statystyki dla każdego bota
        for bot_id, data in bot_data.items():
            # Tylko jeśli mamy wystarczającą ilość danych
            if len(data["profits"]) > 0:
                avg_profit = sum(data["profits"]) / len(data["profits"])
                max_profit = max(data["profits"]) if data["profits"] else 0
                min_profit = min(data["profits"]) if data["profits"] else 0
                contribution = (data["total_profit"] / total_profit * 100) if total_profit != 0 else 0
                
                bot_performance[bot_id] = {
                    "name": data["name"],
                    "bot_id": bot_id,
                    "total_profit": data["total_profit"],
                    "avg_profit": avg_profit,
                    "max_profit": max_profit,
                    "min_profit": min_profit,
                    "data_points": len(data["profits"]),
                    "contribution": contribution
                }
        
        # Sortujemy boty według całkowitego zysku (malejąco)
        sorted_bots = sorted(
            bot_performance.values(),
            key=lambda x: x["total_profit"],
            reverse=True
        )
        
        # Zwracamy wyniki analizy
        result = {
            "total_profit": total_profit,
            "active_bots": len(bot_data),
            "bot_performance": sorted_bots,
            "best_bot": sorted_bots[0] if sorted_bots else None,
            "worst_bot": sorted_bots[-1] if sorted_bots else None
        }
        
        return result
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Wyjątek w analyze_portfolio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def analyze_hp_positions(data, user_id):
    """
    Analizuje pozycje HP dla danego użytkownika.
    """
    try:
        # Implementacja analizy HP
        return {
            "summary": "Analiza pozycji HP jest w trakcie rozwoju.",
            "data": data
        }
    except Exception as e:
        logger.error(f"Błąd podczas analizy pozycji HP: {e}")
        return None

def get_hp_positions(user_id):
    """
    Pobiera informacje o pozycjach HP (Hold Profit) użytkownika z aplikacji hpcrypto.
    
    Args:
        user_id: ID użytkownika
        
    Returns:
        Dane o kategoriach i pozycjach HP
    """
    try:
        # Import modeli wewnątrz funkcji
        from hpcrypto.models import HPCategory, Position
        
        # Pobierz wszystkie kategorie HP użytkownika
        categories = HPCategory.objects.filter(user_id=user_id)
        
        hp_data = {
            'strategy': 'Handel poziomami',
            'strategy_description': 'Aktywna strategia handlu z wykorzystaniem poziomów wsparcia i oporu. W przeciwieństwie do podejścia HODL, zakłada aktywne zarządzanie pozycjami na podstawie analizy technicznych poziomów cenowych.',
            'total_categories': len(categories),
            'total_positions': 0,
            'total_investment': 0,
            'current_value': 0,
            'profit_loss': 0,
            'profit_loss_percent': 0,
            'categories': []
        }
        
        # Dla każdej kategorii pobierz pozycje
        for category in categories:
            positions = Position.objects.filter(category=category)
            
            category_data = {
                'name': category.name,
                'description': category.description,
                'positions_count': len(positions),
                'total_value': 0,
                'profit_loss': 0,
                'positions': []
            }
            
            # Agreguj dane pozycji
            for position in positions:
                position_size = float(position.position_size)
                profit_loss = float(position.profit_loss_dollar or 0)
                current_value = position_size + profit_loss
                
                category_data['positions'].append({
                    'ticker': position.ticker,
                    'quantity': float(position.quantity),
                    'entry_price': float(position.entry_price),
                    'current_price': float(position.current_price or position.entry_price),
                    'position_size': position_size,
                    'profit_loss': profit_loss,
                    'profit_loss_percent': float(position.profit_loss_percent or 0),
                    'notes': position.notes or ''
                })
                
                category_data['total_value'] += current_value
                category_data['profit_loss'] += profit_loss
                
                hp_data['total_positions'] += 1
                hp_data['total_investment'] += position_size
                hp_data['current_value'] += current_value
                hp_data['profit_loss'] += profit_loss
            
            hp_data['categories'].append(category_data)
        
        # Oblicz całkowity procent zysku/straty
        if hp_data['total_investment'] > 0:
            hp_data['profit_loss_percent'] = (hp_data['profit_loss'] / hp_data['total_investment']) * 100
            
        return hp_data
    except Exception as e:
        logger.error(f"Błąd podczas pobierania danych HP: {e}")
        print(f"[DEBUG ERROR] Błąd podczas pobierania danych HP: {str(e)}")
        return None 