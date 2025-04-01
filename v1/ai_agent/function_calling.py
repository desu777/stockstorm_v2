"""
Moduł function_calling.py obsługuje mechanizm function calling z modelem LLM.

Główne funkcje tego modułu:
- Definiowanie dostępnych funkcji z ich opisami i parametrami
- Przekształcanie komunikacji z modelem w wywołania funkcji
- Obsługa odpowiedzi zwrotnych z funkcji do modelu
"""

import json
import logging
import functools
import os
import traceback
from django.conf import settings
from typing import Dict, List, Any, Optional, Callable
import openai
from decimal import Decimal
from .services import DecimalJSONEncoder

logger = logging.getLogger(__name__)

# Import funkcji, które będą wywoływane przez model
from .hp_analysis import analyze_hp_portfolio
from .capital_analysis import analyze_capital_allocation
from .data_utils import analyze_portfolio, get_hp_positions, get_bot_profit_data
from .trading import parse_trading_command, execute_trade, execute_stop_limit_order
from .chart_utils import (
    generate_profit_chart, 
    generate_example_chart_for_bot,
    generate_bot_profit_chart,
    generate_simple_chart,
    example_chart,
    generate_minimal_chart,
    # Nowe funkcje Chart.js
    generate_bot_chartjs,
    generate_profit_chartjs,
    example_chartjs
)
from .bot_analysis import analyze_bot_data, check_bot_existence, get_bot_microservice_id
# Import nowych funkcji do zarządzania portfelem GT
from .gt_portfolio_management import (
    get_gt_portfolio,
    get_gt_categories,
    add_stock_position,
    add_price_alert,
    get_position_details
)

# Bezpieczny import funkcji z search_utils
try:
    from .search_utils import search_knowledge_base, get_embedding
    has_search_utils = True
    logger.info("Pomyślnie zaimportowano moduły search_utils dla function_calling")
except ImportError:
    has_search_utils = False
    logger.warning("Nie można zaimportować modułów search_utils w function_calling.py")
    
    # Puste funkcje zastępcze
    def search_knowledge_base(query, **kwargs):
        return []
        
    def get_embedding(text, **kwargs):
        return None

# Dekoratory pomocnicze
def with_error_handling(func: Callable) -> Callable:
    """Dekorator obsługujący błędy wykonania funkcji"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania {func.__name__}: {str(e)}")
            return {
                "success": False,
                "message": f"Wystąpił błąd podczas wykonywania operacji: {str(e)}"
            }
    return wrapper

def with_microservice_token(func: Callable) -> Callable:
    """Dekorator zapewniający dostępność tokenu mikrousługi"""
    @functools.wraps(func)
    def wrapper(user_id, microservice_token=None, *args, **kwargs):
        if not microservice_token and user_id:
            try:
                from home.utils import get_token
                microservice_token = get_token(user_id)
                logger.info(f"Pobrano token mikrousługi dla użytkownika {user_id}")
            except Exception as e:
                logger.error(f"Nie udało się pobrać tokenu mikrousługi: {str(e)}")
                
        if not microservice_token:
            return {
                "success": False,
                "message": "Brak tokenu mikrousługi. Nie można wykonać operacji."
            }
            
        return func(user_id, microservice_token, *args, **kwargs)
    return wrapper

def requires_user_id(func: Callable) -> Callable:
    """Dekorator sprawdzający, czy podano ID użytkownika"""
    @functools.wraps(func)
    def wrapper(user_id=None, *args, **kwargs):
        if not user_id:
            return {
                "success": False,
                "message": "Brak ID użytkownika. Nie można wykonać operacji."
            }
        return func(user_id, *args, **kwargs)
    return wrapper

# Funkcje pomocnicze dla funkcji wywoływanych przez model
@with_error_handling
@requires_user_id
def call_analyze_hp_portfolio(user_id, microservice_token=None, **kwargs):
    """Wrapper dla funkcji analyze_hp_portfolio"""
    logger.info(f"Wywołanie funkcji analyze_hp_portfolio dla użytkownika {user_id}")
    return analyze_hp_portfolio(user_id)

@with_error_handling
@requires_user_id
def call_analyze_capital_allocation(user_id, microservice_token=None, **kwargs):
    """Wrapper dla funkcji analyze_capital_allocation"""
    if not microservice_token:
        # Pobierz token mikrousługi jeśli nie został przekazany
        from .services import get_microservice_token
        microservice_token = get_microservice_token()
        
    logger.info(f"Wywołanie funkcji analyze_capital_allocation dla użytkownika {user_id}")
    return analyze_capital_allocation(user_id, microservice_token)

@with_error_handling
@requires_user_id
def call_analyze_portfolio(user_id, microservice_token=None, **kwargs):
    """Wrapper dla funkcji analyze_portfolio"""
    if not microservice_token:
        # Pobierz token mikrousługi jeśli nie został przekazany
        from .services import get_microservice_token
        microservice_token = get_microservice_token()
        
    logger.info(f"Wywołanie funkcji analyze_portfolio dla użytkownika {user_id}")
    return analyze_portfolio(user_id=user_id, microservice_token=microservice_token)

@with_error_handling
@requires_user_id
def call_analyze_bots(user_id, microservice_token=None, **kwargs):
    """Wrapper dla funkcji analyze_portfolio (analiza botów)"""
    # Funkcjonalnie to samo co analyze_portfolio, ale z inną nazwą dla lepszej UX
    if not microservice_token:
        # Pobierz token mikrousługi jeśli nie został przekazany
        from .services import get_microservice_token
        microservice_token = get_microservice_token()
        
    logger.info(f"Wywołanie funkcji analyze_bots dla użytkownika {user_id}")
    return analyze_portfolio(user_id=user_id, microservice_token=microservice_token)

@with_error_handling
@requires_user_id
def call_execute_trade(user_id, trading_data=None, microservice_token=None, action=None, **kwargs):
    """Wrapper dla funkcji execute_trade"""
    if trading_data is None:
        trading_data = {}  # Ustaw domyślną pustą wartość
    
    if not trading_data:
        return {"success": False, "message": "Brak danych transakcji"}
    
    logger.info(f"Wywołanie funkcji execute_trade dla użytkownika {user_id}")
    return execute_trade(user_id, trading_data)

@with_error_handling
@requires_user_id
def call_execute_stop_limit(user_id, order_data=None, microservice_token=None, **kwargs):
    """Wrapper dla funkcji execute_stop_limit_order"""
    if order_data is None:
        order_data = {}  # Ustaw domyślną pustą wartość
        
    if not order_data:
        return {"success": False, "message": "Brak danych zlecenia stop-limit"}
    
    logger.info(f"Wywołanie funkcji execute_stop_limit_order dla użytkownika {user_id}")
    return execute_stop_limit_order(user_id, order_data)

@with_error_handling
@requires_user_id
def call_generate_bot_chart(user_id, microservice_token=None, bot_id=None, period_days=365, use_chartjs=True, **kwargs):
    """Generuje wykres dla bota o podanym ID"""
    logger.info(f"Wywołanie funkcji generate_bot_chart dla użytkownika {user_id}, bot {bot_id}, use_chartjs={use_chartjs}")
    
    if not microservice_token:
        # Pobierz token mikrousługi jeśli nie został przekazany
        from .services import get_microservice_token
        microservice_token = get_microservice_token()
    
    # Sprawdź czy mamy bot_id
    if bot_id is None:
        return {
            "success": False,
            "message": "Nie podano ID bota do wygenerowania wykresu."
        }
        
    # Konwertuj bot_id na int, jeśli jest to string
    if bot_id and isinstance(bot_id, str) and bot_id.isdigit():
        bot_id = int(bot_id)

    # Sprawdź czy bot istnieje
    bot_exists, bot_name, bot_data = check_bot_existence(bot_id, microservice_token)
    
    # Pobierz mapowanie ID lokalnego bota na microservice_bot_id
    microservice_bot_id, mapped_bot_name = get_bot_microservice_id(bot_id, user_id)
    if mapped_bot_name != f"Bot {bot_id}":
        bot_name = mapped_bot_name
    
    # Pobierz dane o zyskach
    profit_data = get_bot_profit_data(user_id, microservice_token, bot_id=bot_id, period_days=period_days)
    
    # Przygotuj informacje o bocie
    bot_info = {
        "id": bot_id,
        "name": bot_name,
        "exists": bot_exists
    }
    
    # Analizuj dane bota
    detailed_info = None
    if profit_data and profit_data.get("data"):
        detailed_info = analyze_bot_data(profit_data, bot_id, microservice_bot_id, bot_name)
    
    # Generuj wykres - wybierz metodę w zależności od parametru use_chartjs
    chart_is_html = False
    try:
        if use_chartjs:
            # Użyj nowej metody z Chart.js (zwraca HTML/JS)
            logger.info(f"Generowanie wykresu Chart.js dla bota {bot_id} ({bot_name})")
            chart_content = generate_bot_chartjs(profit_data, bot_id, bot_name)
            chart_is_html = True
            chart_image = True
            chart_image_base64 = None
            logger.info(f"Wygenerowano wykres Chart.js dla bota {bot_id}")
        else:
            # Użyj starej metody z matplotlib (zwraca base64 image)
            logger.info(f"Generowanie obrazu wykresu dla bota {bot_id} ({bot_name})")
            chart_image_base64 = generate_bot_profit_chart(profit_data, bot_id, bot_name)
            chart_image = True if chart_image_base64 else False
            chart_content = chart_image_base64
            logger.info(f"Wygenerowano obraz wykresu dla bota {bot_id} - sukces: {chart_image}")
    except Exception as e:
        logger.error(f"Błąd podczas generowania wykresu: {str(e)}")
        chart_image = False
        chart_image_base64 = None
        chart_content = None
        chart_is_html = False
    
    return {
        "success": True,
        "bot_info": bot_info,
        "detailed_info": detailed_info,
        "chart_image": chart_image,
        "chart_image_base64": chart_image_base64 if not chart_is_html else None,
        "chart_html": chart_content if chart_is_html else None,
        "chart_is_html": chart_is_html,
        "profit_data": profit_data.get("summary") if profit_data else None
    }

@with_error_handling
@requires_user_id
def call_generate_chart(user_id, microservice_token=None, period_days=365, strategy_filter=None, title=None, use_chartjs=True, **kwargs):
    """Generuje wykres zysków dla wszystkich botów użytkownika"""
    logger.info(f"Wywołanie funkcji generate_chart dla użytkownika {user_id}, use_chartjs={use_chartjs}")
    
    if not microservice_token:
        # Pobierz token mikrousługi jeśli nie został przekazany
        from .services import get_microservice_token
        microservice_token = get_microservice_token()
    
    # Pobierz dane o zyskach
    profit_data = get_bot_profit_data(user_id, microservice_token, strategy_filter=strategy_filter, period_days=period_days)
    
    # Sprawdź czy mamy wyniki
    has_data = profit_data and "data" in profit_data and len(profit_data["data"]) > 0
    
    # Analizuj dane portfolio
    portfolio_analysis = None
    if has_data:
        portfolio_analysis = analyze_portfolio(profit_data)
    
    # Ustal tytuł wykresu
    chart_title = title or (f"Zyski dla strategii {strategy_filter}" if strategy_filter else "Zyski wszystkich botów")
    
    # Generuj wykres - wybierz metodę w zależności od parametru use_chartjs
    chart_is_html = False
    try:
        if use_chartjs:
            # Użyj nowej metody z Chart.js (zwraca HTML/JS)
            logger.info(f"Generowanie wykresu Chart.js dla wszystkich botów")
            chart_content = generate_profit_chartjs(profit_data, strategy_filter, title=chart_title)
            chart_is_html = True
            chart_image = True
            chart_image_base64 = None
            logger.info(f"Wygenerowano wykres Chart.js dla wszystkich botów")
        else:
            # Stara metoda z matplotlib
            logger.info(f"Generowanie obrazu wykresu dla wszystkich botów")
            
            if not has_data:
                logger.info("Brak danych o zyskach, generuję przykładowy wykres")
                chart_image_base64 = example_chart()
            else:
                # Przygotuj dane dla wykresu
                dates = []
                profits = []
                
                # Grupowanie zysków po datach dla wszystkich botów
                profits_by_date = {}
                
                for point in profit_data["data"]:
                    date_str = point.get("date")
                    if date_str:
                        profit = point.get("profit", 0)
                        if date_str in profits_by_date:
                            profits_by_date[date_str] += profit
                        else:
                            profits_by_date[date_str] = profit
                
                # Sortowanie dat
                sorted_dates = sorted(profits_by_date.keys())
                
                for date_str in sorted_dates:
                    try:
                        from datetime import datetime
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        dates.append(date)
                        profits.append(profits_by_date[date_str])
                    except:
                        logger.warning(f"Niepoprawny format daty: {date_str}")
                
                if len(dates) > 0:
                    chart_image_base64 = generate_minimal_chart(
                        dates, 
                        profits, 
                        chart_title
                    )
                else:
                    logger.info("Brak dat po przetworzeniu danych, generuję przykładowy wykres")
                    chart_image_base64 = example_chart()
            
            chart_image = True if chart_image_base64 else False
            chart_content = chart_image_base64
            logger.info(f"Wygenerowano obraz wykresu dla wszystkich botów - sukces: {chart_image}")
    
    except Exception as e:
        logger.error(f"Błąd podczas generowania wykresu: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        chart_image = False
        chart_content = None
        chart_image_base64 = None
        chart_is_html = False
    
    return {
        "success": True,
        "chart_image": chart_image,
        "chart_image_base64": chart_image_base64 if not chart_is_html else None,
        "chart_html": chart_content if chart_is_html else None, 
        "chart_is_html": chart_is_html,
        "profit_data": profit_data.get("summary") if profit_data else None,
        "portfolio_analysis": portfolio_analysis
    }

def analyze_capital_allocation_function(user_id, microservice_token):
    """
    Funkcja do analizy alokacji kapitału między botami 51015rei, 51015 i portfelem HP.
    
    Args:
        user_id: ID użytkownika
        microservice_token: Token do mikrousług
        
    Returns:
        dict: Dane o alokacji kapitału w formacie:
            {
                'response': str, # Sformatowana odpowiedź dla użytkownika
                'data': dict # Dane o alokacji kapitału
            }
    """
    try:
        # Pobierz dane o alokacji kapitału
        allocation_data = analyze_capital_allocation(user_id, microservice_token)
        
        if not allocation_data.get('success', False):
            return {
                'response': f"Przepraszam, nie udało się przeanalizować alokacji kapitału: {allocation_data.get('message', 'Nieznany błąd')}",
                'data': None
            }
        
        # Przygotuj sformatowaną odpowiedź
        total_capital = allocation_data.get('total_capital', 0)
        
        # Dane o botach 51015rei
        bots_rei = allocation_data.get('summary', {}).get('bots_rei', {})
        bots_rei_value = bots_rei.get('value', 0)
        bots_rei_percentage = bots_rei.get('percentage', 0)
        bots_rei_count = bots_rei.get('count', 0)
        
        # Dane o botach 51015
        bots_no_rei = allocation_data.get('summary', {}).get('bots_no_rei', {})
        bots_no_rei_value = bots_no_rei.get('value', 0)
        bots_no_rei_percentage = bots_no_rei.get('percentage', 0)
        bots_no_rei_count = bots_no_rei.get('count', 0)
        
        # Dane o portfelu HP
        hp_portfolio = allocation_data.get('summary', {}).get('hp_portfolio', {})
        hp_value = hp_portfolio.get('value', 0)
        hp_percentage = hp_portfolio.get('percentage', 0)
        
        # Dane o BTC w portfelu HP
        btc_value = hp_portfolio.get('btc_value', 0)
        btc_percentage_in_hp = hp_portfolio.get('btc_percentage_in_hp', 0)
        btc_percentage_total = hp_portfolio.get('btc_percentage_total', 0)
        
        # Przygotuj odpowiedź
        response = f"""# Analiza Alokacji Kapitału

Twój portfel jest prowadzony w stablecoinach, gdzie wszystkie wartości są podane w USD.

## Łączny kapitał: {total_capital:.2f} USD

## Struktura alokacji kapitału:

1. **Boty 5-10-15rei (z reinwestycją)**: {bots_rei_percentage:.2f}% ({bots_rei_value:.2f} USD)
   - Liczba botów: {bots_rei_count}

2. **Boty 5-10-15 (bez reinwestycji)**: {bots_no_rei_percentage:.2f}% ({bots_no_rei_value:.2f} USD)
   - Liczba botów: {bots_no_rei_count}

3. **Portfel HP**: {hp_percentage:.2f}% ({hp_value:.2f} USD)
   - BTC w portfelu HP: {btc_percentage_in_hp:.2f}% portfela HP
   - BTC jako % całkowitego kapitału: {btc_percentage_total:.2f}%

## Rekomendacje:

- Utrzymuj zdywersyfikowaną alokację kapitału między botami a portfelem HP
- Monitoruj wyniki poszczególnych strategii i dostosowuj alokację w zależności od ich skuteczności
- Rozważ zwiększenie udziału BTC dla większej stabilności portfela
"""
        
        return {
            'response': response,
            'data': allocation_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas analizy alokacji kapitału: {str(e)}")
        return {
            'response': f"Przepraszam, wystąpił błąd podczas analizy alokacji kapitału: {str(e)}",
            'data': None
        }

@with_error_handling
def call_search_knowledge_base(user_id=None, query=None, top_k=3, threshold=0.6, **kwargs):
    """Funkcja do przeszukiwania bazy wiedzy za pomocą zapytania semantycznego"""
    logger.info(f"Wywołanie funkcji search_knowledge_base dla zapytania: {query}")
    
    if not query:
        return {
            "success": False,
            "message": "Brak zapytania wyszukiwania"
        }
    
    if not has_search_utils:
        return {
            "success": False,
            "message": "Funkcja wyszukiwania w bazie wiedzy jest niedostępna"
        }
    
    try:
        # Wykonaj wyszukiwanie semantyczne
        results = search_knowledge_base(query, top_k=top_k, threshold=threshold)
        
        if not results:
            return {
                "success": True,
                "found": False,
                "message": "Nie znaleziono pasujących dokumentów w bazie wiedzy",
                "results": []
            }
        
        # Formatuj wyniki w bardziej czytelny sposób
        formatted_results = []
        for idx, result in enumerate(results):
            content = result.get('text', '')
            metadata = result.get('metadata', {})
            
            formatted_result = {
                "id": idx + 1,
                "main_topic": metadata.get('main_topic', 'Brak tematu'),
                "subtopic": metadata.get('subtopic', ''),
                "source": metadata.get('source', ''),
                "similarity": result.get('similarity', 0),
                "content": content[:500] + ("..." if len(content) > 500 else "")  # Skróć zawartość dla przejrzystości
            }
            formatted_results.append(formatted_result)
        
        return {
            "success": True,
            "found": True,
            "count": len(results),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas wyszukiwania w bazie wiedzy: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Wystąpił błąd podczas przeszukiwania bazy wiedzy: {str(e)}"
        }

@with_error_handling
@requires_user_id
def format_hp_position(user_id, ticker=None, category=None, **kwargs):
    """
    Formatuje informacje o pozycji HP, włączając pole notes.
    
    Args:
        user_id: ID użytkownika
        ticker: Symbol pozycji (np. 'BTC')
        category: Nazwa kategorii pozycji (opcjonalnie)
        
    Returns:
        Sformatowane dane o pozycji lub pozycjach
    """
    try:
        from .data_utils import get_hp_positions
        
        # Pobierz dane pozycji HP
        hp_data = get_hp_positions(user_id)
        
        if not hp_data or not hp_data.get('categories'):
            return {
                'success': False,
                'message': 'Nie znaleziono pozycji w portfelu HP'
            }
            
        # Przygotuj odpowiedź
        positions_info = []
        
        # Przeglądaj kategorie i szukaj odpowiednich pozycji
        for cat in hp_data.get('categories', []):
            category_name = cat.get('name', '')
            
            # Jeśli podano kategorię i nie pasuje, pomiń
            if category and category.lower() not in category_name.lower():
                continue
                
            # Przeglądaj pozycje w kategorii
            for position in cat.get('positions', []):
                position_ticker = position.get('ticker', '').upper()
                
                # Jeśli podano ticker i nie pasuje, pomiń
                if ticker and ticker.upper() not in position_ticker:
                    continue
                    
                # Formatuj dane pozycji
                position_data = {
                    'ticker': position_ticker,
                    'category': category_name,
                    'quantity': float(position.get('quantity', 0)),
                    'entry_price': float(position.get('entry_price', 0)),
                    'current_price': float(position.get('current_price', 0)),
                    'position_value': float(position.get('position_size', 0)) + float(position.get('profit_loss', 0)),
                    'profit_loss': float(position.get('profit_loss', 0)),
                    'profit_loss_percent': float(position.get('profit_loss_percent', 0)),
                    'notes': position.get('notes', '')
                }
                
                positions_info.append(position_data)
        
        # Jeśli nie znaleziono żadnych pozycji, zwróć informację
        if not positions_info:
            if ticker:
                return {
                    'success': False,
                    'message': f'Nie znaleziono pozycji {ticker} w portfelu HP'
                }
            else:
                return {
                    'success': False,
                    'message': 'Nie znaleziono pozycji spełniających kryteria'
                }
        
        # Jeśli znaleziono pozycje, zwróć je
        return {
            'success': True,
            'positions': positions_info,
            'count': len(positions_info)
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas formatowania pozycji HP: {e}")
        return {
            'success': False,
            'message': f'Wystąpił błąd podczas pobierania danych pozycji: {e}'
        }

@with_error_handling
def parse_alert_command(user_message, openai_client=None):
    """
    Parsuje komendę alertu używając OpenAI, aby wyodrębnić szczegóły alertu.
    
    Args:
        user_message: Wiadomość od użytkownika zawierająca komendę alertu.
        openai_client: Opcjonalny klient OpenAI.
        
    Returns:
        dict: Słownik z danymi alertu lub None jeśli nie udało się sparsować.
    """
    try:
        # Jeśli nie podano klienta OpenAI, stwórz nowy
        if not openai_client:
            openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        logger.info(f"Parsowanie komendy alertu: {user_message}")
        
        # Sprawdź, czy dotyczy portfela GT (akcje) czy HP (kryptowaluty)
        is_gt_portfolio = False
        gt_keywords = ["gt", "akcje", "stock", "tsla", "aapl", "msft", "portfel gt", "portfelu gt"]
        
        for keyword in gt_keywords:
            if keyword.lower() in user_message.lower():
                is_gt_portfolio = True
                break
        
        # Dostosuj prompt systemowy w zależności od typu portfela
        if is_gt_portfolio:
            system_prompt = """
            Jesteś ekspertem w przetwarzaniu komend alertów cenowych dla akcji w portfelu GT. Twoim zadaniem jest rozpoznanie 
            akcji/pozycji, typu alertu i wartości progowej z tekstu użytkownika.
            
            Typy alertów:
            - PRICE_ABOVE: cena powyżej określonej wartości (np. "gdy cena wzrośnie powyżej 100 USD")
            - PRICE_BELOW: cena poniżej określonej wartości (np. "gdy cena spadnie poniżej 90 USD")
            - PCT_INCREASE: procentowy wzrost o określoną wartość (np. "gdy cena wzrośnie o 10%")
            - PCT_DECREASE: procentowy spadek o określoną wartość (np. "gdy cena spadnie o 5%")
            
            Zwróć dane w formacie JSON zgodnie z poniższym schematem:
            {
                "ticker": "SYMBOL" (np. AAPL, MSFT, obowiązkowe),
                "alert_type": "TYP_ALERTU" (jeden z: PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE, obowiązkowe),
                "threshold_value": WARTOŚĆ (liczba, obowiązkowe),
                "position_identifier": null (nie używane dla portfela GT),
                "category": "nazwa kategorii, jeśli podana" (opcjonalne),
                "notes": "dodatkowe uwagi do alertu" (opcjonalne),
                "is_gt_portfolio": true (obowiązkowe)
            }
            
            Przykłady dopasowań:
            - "Ustaw alert dla TSLA w portfelu GT gdy cena spadnie poniżej 250 USD" -> {"ticker": "TSLA", "alert_type": "PRICE_BELOW", "threshold_value": 250, "is_gt_portfolio": true}
            - "Daj znać jak Apple w GT wzrośnie o 5%" -> {"ticker": "AAPL", "alert_type": "PCT_INCREASE", "threshold_value": 5, "is_gt_portfolio": true}
            - "Alert AMD kategoria tech -10%" -> {"ticker": "AMD", "alert_type": "PCT_DECREASE", "threshold_value": 10, "category": "tech", "is_gt_portfolio": true}
            
            Jeśli procent jest podany jako liczba ujemna (np. -5%), zawsze interpretuj to jako PCT_DECREASE z wartością bezwzględną.
            Jeśli w wiadomości pojawi się informacja o kategorii, dodaj ją do pola category.
            """
        else:
            system_prompt = """
            Jesteś ekspertem w przetwarzaniu komend alertów cenowych dla kryptowalut. Twoim zadaniem jest rozpoznanie 
            kryptowaluty/pozycji, typu alertu i wartości progowej z tekstu użytkownika.
            
            Typy alertów:
            - PRICE_ABOVE: cena powyżej określonej wartości (np. "gdy cena wzrośnie powyżej 100 USD")
            - PRICE_BELOW: cena poniżej określonej wartości (np. "gdy cena spadnie poniżej 90 USD")
            - PCT_INCREASE: procentowy wzrost o określoną wartość (np. "gdy cena wzrośnie o 10%")
            - PCT_DECREASE: procentowy spadek o określoną wartość (np. "gdy cena spadnie o 5%")
            
            Zwróć dane w formacie JSON zgodnie z poniższym schematem:
            {
                "ticker": "SYMBOL" (np. BTC, ETH, obowiązkowe),
                "alert_type": "TYP_ALERTU" (jeden z: PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE, obowiązkowe),
                "threshold_value": WARTOŚĆ (liczba, obowiązkowe),
                "position_identifier": "identyfikator pozycji, jeśli podany" (np. "HP1", "HP2", opcjonalne),
                "notes": "dodatkowe uwagi do alertu" (opcjonalne),
                "is_gt_portfolio": false (obowiązkowe)
            }
            
            Przykłady dopasowań:
            - "Ustaw alert dla BTC gdy cena spadnie poniżej 70000 USD" -> {"ticker": "BTC", "alert_type": "PRICE_BELOW", "threshold_value": 70000, "is_gt_portfolio": false}
            - "Daj znać jak Ethereum HP1 wzrośnie o 5%" -> {"ticker": "ETH", "alert_type": "PCT_INCREASE", "threshold_value": 5, "position_identifier": "HP1", "is_gt_portfolio": false}
            - "Alert SOL HP2 -10%" -> {"ticker": "SOL", "alert_type": "PCT_DECREASE", "threshold_value": 10, "position_identifier": "HP2", "is_gt_portfolio": false}
            
            Jeśli procent jest podany jako liczba ujemna (np. -5%), zawsze interpretuj to jako PCT_DECREASE z wartością bezwzględną.
            """
            
        # Wywołaj API OpenAI z odpowiednim promptem
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        alert_data = json.loads(response.choices[0].message.content)
        logger.info(f"Rozpoznane dane alertu: {json.dumps(alert_data, ensure_ascii=False, cls=DecimalJSONEncoder)}")
        
        # Wyodrębnij podstawowe dane do logowania
        ticker = alert_data.get('ticker', '').upper() if alert_data.get('ticker') else None
        alert_type = alert_data.get('alert_type')
        threshold_value = alert_data.get('threshold_value')
        is_gt_portfolio = alert_data.get('is_gt_portfolio', False)
        
        logger.info(f"Przygotowanie do utworzenia alertu - ticker: {ticker}, typ: {alert_type}, wartość: {threshold_value}, portfel GT: {is_gt_portfolio}")
        
        return alert_data
    except Exception as e:
        logger.error(f"Błąd podczas parsowania komendy alertu: {str(e)}")
        return None

@with_error_handling
@requires_user_id
def create_price_alert(user_id, ticker=None, position_identifier=None, alert_type=None, threshold_value=None, notes=None, **kwargs):
    """
    Tworzy alert cenowy dla pozycji w portfelu HP.
    
    Args:
        user_id: ID użytkownika
        ticker: Symbol kryptowaluty (np. "BTC")
        position_identifier: Identyfikator pozycji (np. "HP2" w "BTC HP2")
        alert_type: Typ alertu (PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE)
        threshold_value: Wartość progowa alertu
        notes: Dodatkowe notatki dla alertu
        
    Returns:
        Wynik operacji utworzenia alertu
    """
    try:
        from django.contrib.auth.models import User
        from hpcrypto.models import Position, PriceAlert
        from decimal import Decimal
        
        user = User.objects.get(id=user_id)
        
        # Sprawdź, czy jest to alert dla portfela GT (akcje)
        is_gt_portfolio = kwargs.get('is_gt_portfolio', False)
        if is_gt_portfolio:
            # Przekieruj do funkcji add_price_alert dla portfela GT
            logger.info(f"Wykryto alert dla portfela GT (ticker: {ticker}), przekierowuję do add_price_alert")
            return add_price_alert(
                user_id=user_id,
                ticker=ticker,
                position_id=None,  # Pozycja zostanie znaleziona po tickerze
                alert_type=alert_type,
                threshold_value=threshold_value,
                notes=notes
            )
        
        # Znajdź odpowiednią pozycję
        position = None
        
        # Próba znalezienia pozycji na podstawie identyfikatora i/lub tickera
        if position_identifier and ticker:
            # Szukaj pozycji zawierających zarówno ticker jak i identyfikator w notatkach
            positions = Position.objects.filter(
                user=user, 
                ticker__icontains=ticker,
                notes__icontains=position_identifier
            )
            if positions.exists():
                position = positions.first()
                print(f"[DEBUG] Znaleziono pozycję po identyfikatorze {position_identifier} i tickerze {ticker}")
        
        # Jeśli nie znaleziono, spróbuj po samym identyfikatorze
        if not position and position_identifier:
            positions = Position.objects.filter(
                user=user,
                notes__icontains=position_identifier
            )
            if positions.exists():
                position = positions.first()
                print(f"[DEBUG] Znaleziono pozycję po identyfikatorze {position_identifier}")
        
        # Jeśli nadal nie znaleziono, spróbuj po samym tickerze
        if not position and ticker:
            positions = Position.objects.filter(
                user=user,
                ticker__icontains=ticker
            )
            if positions.exists():
                position = positions.first()
                print(f"[DEBUG] Znaleziono pozycję po tickerze {ticker}")
        
        if not position:
            return {
                'success': False,
                'message': f'Nie znaleziono pozycji dla tickera {ticker} i identyfikatora {position_identifier}'
            }
        
        # Sprawdź poprawność typu alertu
        valid_alert_types = dict(PriceAlert.ALERT_TYPES)
        if alert_type not in valid_alert_types:
            return {
                'success': False,
                'message': f'Niepoprawny typ alertu. Dostępne typy: {", ".join(valid_alert_types.keys())}'
            }
        
        # Stwórz nowy alert
        new_alert = PriceAlert(
            position=position,
            alert_type=alert_type,
            threshold_value=Decimal(str(threshold_value)),
            notes=notes or '',
            is_active=True
        )
        new_alert.save()
        
        # Przygotuj czytelny opis typu alertu
        alert_type_display = dict(PriceAlert.ALERT_TYPES).get(alert_type)
        
        return {
            'success': True,
            'message': f'Utworzono alert typu {alert_type_display} dla {position.ticker} z progiem {threshold_value}',
            'alert': {
                'id': new_alert.id,
                'ticker': position.ticker,
                'alert_type': alert_type,
                'alert_type_display': alert_type_display,
                'threshold_value': str(threshold_value),
                'notes': notes or ''
            }
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia alertu: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Wystąpił błąd podczas tworzenia alertu: {str(e)}'
        }

# Dodanie nowych funkcji dla portfela GT
@with_error_handling
@requires_user_id
def call_get_gt_portfolio(user_id, **kwargs):
    """
    Wrapper dla funkcji get_gt_portfolio
    """
    logger.info(f"Wywołanie funkcji call_get_gt_portfolio dla user_id={user_id}")
    return get_gt_portfolio(user_id)

@with_error_handling
@requires_user_id
def call_get_gt_categories(user_id, **kwargs):
    """
    Wrapper dla funkcji get_gt_categories
    """
    logger.info(f"Wywołanie funkcji call_get_gt_categories dla user_id={user_id}")
    return get_gt_categories(user_id)

@with_error_handling
@requires_user_id
def call_add_stock_position(user_id, ticker=None, quantity=None, category_name="Default", notes=None, **kwargs):
    """
    Wrapper dla funkcji add_stock_position
    """
    logger.info(f"Wywołanie funkcji call_add_stock_position dla user_id={user_id}, ticker={ticker}")
    
    if not ticker:
        return {
            "success": False,
            "message": "Brak tickera. Nie można dodać pozycji."
        }
    
    if not quantity:
        return {
            "success": False,
            "message": "Brak ilości. Nie można dodać pozycji."
        }
    
    try:
        # Konwersja quantity do float
        quantity = float(quantity)
    except ValueError:
        return {
            "success": False,
            "message": f"Nieprawidłowa wartość ilości: {quantity}. Podaj liczbę."
        }
    
    return add_stock_position(
        user_id=user_id,
        ticker=ticker,
        quantity=quantity,
        category_name=category_name,
        notes=notes
    )

@with_error_handling
@requires_user_id
def call_add_price_alert(user_id, ticker=None, position_id=None, alert_type="PRICE_BELOW", 
                   threshold_value=None, notes=None, **kwargs):
    """
    Wrapper dla funkcji add_price_alert
    """
    logger.info(f"Wywołanie funkcji call_add_price_alert dla user_id={user_id}, ticker={ticker}, position_id={position_id}")
    
    if not ticker and not position_id:
        return {
            "success": False,
            "message": "Brak tickera lub ID pozycji. Nie można dodać alertu."
        }
    
    if not threshold_value:
        return {
            "success": False,
            "message": "Brak wartości progowej. Nie można dodać alertu."
        }
    
    try:
        # Konwersja threshold_value do float
        threshold_value = float(threshold_value)
    except ValueError:
        return {
            "success": False,
            "message": f"Nieprawidłowa wartość progowa: {threshold_value}. Podaj liczbę."
        }
    
    return add_price_alert(
        user_id=user_id,
        ticker=ticker,
        position_id=position_id,
        alert_type=alert_type,
        threshold_value=threshold_value,
        notes=notes
    )

@with_error_handling
@requires_user_id
def call_get_position_details(user_id, ticker=None, position_id=None, **kwargs):
    """
    Wrapper dla funkcji get_position_details
    """
    logger.info(f"Wywołanie funkcji call_get_position_details dla user_id={user_id}, ticker={ticker}, position_id={position_id}")
    
    if not ticker and not position_id:
        return {
            "success": False,
            "message": "Brak tickera lub ID pozycji. Nie można pobrać szczegółów."
        }
    
    return get_position_details(
        user_id=user_id,
        ticker=ticker,
        position_id=position_id
    )

# Definicje dostępnych funkcji dla modelu
AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_hp_portfolio",
            "description": "Analizuje strukturę portfela HP Crypto użytkownika, pokazując alokację kapitału pomiędzy różne aktywa oraz oceniając koncentrację BTC.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_capital_allocation",
            "description": "Analizuje całościową alokację kapitału użytkownika pomiędzy boty 5-10-15, boty 5-10-15rei i portfel HP.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_portfolio",
            "description": "Analizuje portfel botów użytkownika, pobierając informacje o botach z i bez reinwestycji.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_bots",
            "description": "Analizuje boty użytkownika, w tym ich strategie, kapitał i wydajność. Używaj tej funkcji gdy użytkownik pyta o analizę botów, statystyki botów lub prosi o przeanalizowanie botów.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_trade",
            "description": "Wykonuje transakcję handlową zgodnie z instrukcjami użytkownika.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trading_data": {
                        "type": "object",
                        "description": "Dane transakcji zawierające typ (buy/sell), ticker, ilość, cenę itp."
                    }
                },
                "required": ["trading_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_stop_limit",
            "description": "Wykonuje zlecenie stop-limit zgodnie z instrukcjami użytkownika. Używaj tej funkcji gdy użytkownik chce złożyć zlecenie stop-limit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_data": {
                        "type": "object",
                        "description": "Dane zlecenia zawierające ticker, ilość, trigger price, limit price itp."
                    }
                },
                "required": ["order_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_bot_chart",
            "description": "Generuje wykres dla wybranego bota. Używaj tej funkcji gdy użytkownik prosi o wykres konkretnego bota.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bot_id": {
                        "type": "string",
                        "description": "ID bota, dla którego ma być wygenerowany wykres"
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Liczba dni, za które mają być pokazane dane (domyślnie 365)"
                    },
                    "use_chartjs": {
                        "type": "boolean",
                        "description": "Czy użyć Chart.js do generowania interaktywnego wykresu (true) zamiast statycznego obrazu (false). Domyślnie true."
                    }
                },
                "required": ["bot_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart",
            "description": "Generuje wykres zysków dla wszystkich botów użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_days": {
                        "type": "integer",
                        "description": "Liczba dni, za które mają być pokazane dane (domyślnie 365)"
                    },
                    "strategy_filter": {
                        "type": "string",
                        "description": "Filtr strategii, które mają być uwzględnione w wykresie"
                    },
                    "title": {
                        "type": "string",
                        "description": "Tytuł wykresu"
                    },
                    "use_chartjs": {
                        "type": "boolean",
                        "description": "Czy użyć Chart.js do generowania interaktywnego wykresu (true) zamiast statycznego obrazu (false). Domyślnie true."
                    }
                },
                "required": ["period_days"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Przeszukuje bazę wiedzy za pomocą zapytania semantycznego.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Zapytanie do wyszukania"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maksymalna liczba wyników do zwrócenia"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Próg podobieństwa do zaakceptowania wyniku"
                    }
                },
                "required": ["query", "top_k", "threshold"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_hp_position",
            "description": "Pobiera i formatuje informacje o pozycjach w portfelu HP, włączając pole notes. Używaj tej funkcji, gdy użytkownik pyta o swoje pozycje w portfelu HP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Symbol kryptowaluty (np. 'BTC', 'ETH')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Nazwa kategorii pozycji (np. 'BTC HP')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_price_alert",
            "description": "Tworzy alert cenowy dla pozycji w portfelu HP. Używaj tej funkcji, gdy użytkownik chce utworzyć alert na konkretną cenę lub procentową zmianę.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Symbol kryptowaluty (np. 'BTC', 'ETH')"
                    },
                    "position_identifier": {
                        "type": "string",
                        "description": "Identyfikator pozycji (np. 'HP2' w 'BTC HP2')"
                    },
                    "alert_type": {
                        "type": "string",
                        "description": "Typ alertu (PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE)",
                        "enum": ["PRICE_ABOVE", "PRICE_BELOW", "PCT_INCREASE", "PCT_DECREASE"]
                    },
                    "threshold_value": {
                        "type": "number",
                        "description": "Wartość progowa dla alertu (cena lub procent)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Dodatkowe notatki dla alertu"
                    }
                },
                "required": ["ticker", "alert_type", "threshold_value"]
            }
        }
    },
    # Nowe funkcje do zarządzania portfelem GT
    {
        "type": "function",
        "function": {
            "name": "get_gt_portfolio",
            "description": "Pobiera wszystkie kategorie i pozycje z portfela GT użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID użytkownika"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gt_categories",
            "description": "Pobiera wszystkie kategorie z portfela GT użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID użytkownika"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_stock_position",
            "description": "Dodaje nową pozycję akcji do portfela GT",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID użytkownika"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Symbol akcji (np. AAPL, MSFT)"
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Ilość akcji"
                    },
                    "category_name": {
                        "type": "string",
                        "description": "Nazwa kategorii (zostanie utworzona, jeśli nie istnieje)",
                        "default": "Default"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notatki do pozycji"
                    }
                },
                "required": ["user_id", "ticker", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gt_add_price_alert",
            "description": "Dodaje alert cenowy do pozycji akcji",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID użytkownika"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Symbol akcji, do której dodać alert"
                    },
                    "position_id": {
                        "type": "integer",
                        "description": "ID pozycji, do której dodać alert (alternatywnie do ticker)"
                    },
                    "alert_type": {
                        "type": "string",
                        "description": "Typ alertu (PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE)",
                        "enum": ["PRICE_ABOVE", "PRICE_BELOW", "PCT_INCREASE", "PCT_DECREASE", "ABOVE", "BELOW", "INCREASE", "DECREASE", "UP", "DOWN"],
                        "default": "PRICE_BELOW"
                    },
                    "threshold_value": {
                        "type": "number",
                        "description": "Wartość progowa alertu"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notatki do alertu"
                    }
                },
                "required": ["user_id", "threshold_value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_position_details",
            "description": "Pobiera szczegółowe informacje o pozycji akcji",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID użytkownika"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Symbol akcji"
                    },
                    "position_id": {
                        "type": "integer",
                        "description": "ID pozycji (alternatywnie do ticker)"
                    }
                },
                "required": ["user_id"]
            }
        }
    }
]

# Mapowanie nazw funkcji do ich implementacji
FUNCTION_MAP = {
    "analyze_hp_portfolio": call_analyze_hp_portfolio,
    "analyze_capital_allocation": call_analyze_capital_allocation,
    "analyze_portfolio": call_analyze_portfolio,
    "analyze_bots": call_analyze_bots,
    "execute_trade": call_execute_trade,
    "execute_stop_limit": call_execute_stop_limit,
    "generate_bot_chart": call_generate_bot_chart,
    "generate_chart": call_generate_chart,
    "search_knowledge_base": call_search_knowledge_base,
    "format_hp_position": format_hp_position,
    "create_price_alert": create_price_alert,
    # Nowe funkcje do zarządzania portfelem GT
    "get_gt_portfolio": call_get_gt_portfolio,
    "get_gt_categories": call_get_gt_categories,
    "add_stock_position": call_add_stock_position,
    "gt_add_price_alert": call_add_price_alert,
    "get_position_details": call_get_position_details,
}

def process_function_calling(user_message, conversation_history, user_id=None, microservice_token=None):
    """
    Główna funkcja do obsługi function calling dla AI.
    
    Args:
        user_message: Wiadomość od użytkownika
        conversation_history: Historia konwersacji
        user_id: ID użytkownika
        microservice_token: Token mikrousługi
        
    Returns:
        Odpowiedź od AI wraz z informacją, czy wykorzystano function calling
    """
    try:
        # Sprawdź, czy mamy dostęp do bazy wektorowej
        knowledge_base_context = None
        if has_search_utils:
            try:
                # Spróbuj wzbogacić kontekst wyszukiwaniem semantycznym
                logger.info(f"Wyszukiwanie semantyczne dla zapytania: {user_message[:50]}...")
                search_results = search_knowledge_base(user_message, top_k=3, threshold=0.6)
                
                if search_results:
                    # Utwórz kontekst z wyników wyszukiwania
                    knowledge_base_context = "Kontekst z bazy wiedzy:\n\n"
                    for idx, result in enumerate(search_results):
                        content = result.get('text', '')
                        metadata = result.get('metadata', {})
                        topic = metadata.get('main_topic', 'Brak tematu')
                        subtopic = metadata.get('subtopic', '')
                        
                        knowledge_base_context += f"### Dokument {idx+1}: {topic}\n"
                        if subtopic:
                            knowledge_base_context += f"Podtemat: {subtopic}\n"
                        knowledge_base_context += f"{content}\n\n"
                    
                    logger.info(f"Znaleziono {len(search_results)} pasujących dokumentów w bazie wektorowej")
            except Exception as e:
                logger.error(f"Błąd podczas wyszukiwania semantycznego: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Wzbogać wiadomość kontekstem, jeśli jest dostępny
        if knowledge_base_context:
            user_message_with_context = f"{knowledge_base_context}\n\nPytanie użytkownika: {user_message}"
        else:
            user_message_with_context = user_message
            
        # Inicjalizacja klienta OpenAI
        openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Przygotuj konwersację
        messages = []
        
        # Dodaj systemowy prompt, który wyjaśnia zadanie i dostępne narzędzia
        system_message = """Jesteś asystentem tradingowym specjalizującym się w analizie portfela, kryptowalutach i botach tradingowych.
        
Twoja rola obejmuje:
1. Analizę portfela kryptowalutowego użytkownika
2. Pomoc w zrozumieniu działania botów tradingowych
3. Wykonywanie operacji handlowych na prośbę użytkownika
4. Generowanie wykresów przedstawiających zyski
5. Udzielanie odpowiedzi na pytania związane z tradingiem i kryptowalutami

Masz dostęp do bazy wiedzy z informacjami o tradingu, kryptowalutach i analizie technicznej. Używaj tych informacji, gdy to możliwe.

Dostępne są dla Ciebie funkcje umożliwiające wykonywanie różnych operacji. Korzystaj z nich, gdy będzie to pomocne w odpowiedzi na pytania użytkownika."""
        
        # Dodaj identyfikator użytkownika do kontekstu systemowego
        if user_id:
            messages.append({"role": "system", "content": f"Identyfikator użytkownika (user_id): {user_id}"})
        
        # Dodaj wiadomości do konwersacji
        messages.append({"role": "system", "content": system_message})
        
        # Dodaj historię konwersacji, jeśli jest dostępna
        if conversation_history and isinstance(conversation_history, list):
            # Dodaj maksymalnie 10 ostatnich wiadomości z historii, aby zmieścić się w kontekście
            for message in conversation_history[-10:]:
                if isinstance(message, dict) and "role" in message and "content" in message:
                    messages.append(message)
            logger.info(f"Dodano {len(conversation_history[-10:])} wiadomości z historii konwersacji")
        
        # Dodaj aktualną wiadomość użytkownika
        messages.append({"role": "user", "content": user_message_with_context})
        
        # Wywołaj model z definicjami funkcji
        logger.info(f"Wywołanie modelu dla wiadomości: {user_message[:50]}...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Możesz dostosować model
            messages=messages,
            tools=AVAILABLE_FUNCTIONS,
            tool_choice="auto",  # auto oznacza, że model sam zdecyduje czy używać narzędzi
            temperature=0.7
        )
        
        # Sprawdź, czy model chce wywołać funkcję
        message = response.choices[0].message
        
        # Sprawdź, czy function_call jest obecny w odpowiedzi
        tool_calls = message.tool_calls
        
        # Jeśli model nie chce wywołać funkcji, zwróć normalną odpowiedź
        if not tool_calls:
            logger.info("Model nie wywołał żadnej funkcji")
            return {
                "response": message.content,
                "function_called": False,
                "chart_image": None
            }
        
        # Model chce wywołać funkcję
        logger.info(f"Model wywołał narzędzie: {tool_calls[0].function.name}")
        
        # Przygotuj wiadomości dla kolejnego wywołania, dodając wyniki wywołania funkcji
        messages.append(message)  # Dodaj wiadomość od asystenta z wywołaniem funkcji
        
        # Dla każdego wywołania funkcji, wykonaj funkcję i dodaj wynik
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.error(f"Błąd dekodowania argumentów JSON dla {function_name}: {tool_call.function.arguments}")
                function_args = {}
            
            # Dodaj user_id do argumentów, jeśli nie został podany
            if "user_id" not in function_args and user_id is not None:
                function_args["user_id"] = user_id
            
            # Dodaj token mikrousługi, jeśli funkcja go wymaga
            if "microservice_token" in function_args and microservice_token:
                function_args["microservice_token"] = microservice_token
            
            # Wywołaj odpowiednią funkcję
            logger.info(f"Wywołanie funkcji: {function_name} z argumentami: {json.dumps(function_args, cls=DecimalJSONEncoder, default=str)}")
            
            # Pobierz i wywołaj funkcję
            function_to_call = FUNCTION_MAP.get(function_name)
            if function_to_call:
                try:
                    function_response = function_to_call(**function_args)
                    
                    # Logowanie wyniku
                    if isinstance(function_response, dict):
                        success = function_response.get('success', False)
                        logger.info(f"Wynik funkcji {function_name}: success={success}")
                    else:
                        logger.info(f"Wynik funkcji {function_name} nie jest słownikiem: {type(function_response)}")
                        # Konwertuj na słownik, jeśli to nie jest słownik
                        if function_response is None:
                            function_response = {"success": False, "message": "Funkcja zwróciła None"}
                        else:
                            try:
                                function_response = {"success": True, "result": str(function_response)}
                            except Exception as e:
                                function_response = {"success": False, "message": f"Błąd konwersji wyniku: {str(e)}"}
                except Exception as e:
                    logger.error(f"Błąd wykonania funkcji {function_name}: {str(e)}")
                    function_response = {"success": False, "message": f"Błąd wykonania funkcji: {str(e)}"}
                
                # Dodaj wynik wywołania funkcji jako wiadomość
                try:
                    content_json = json.dumps(function_response, ensure_ascii=False, cls=DecimalJSONEncoder)
                except Exception as e:
                    logger.error(f"Błąd serializacji wyniku funkcji {function_name}: {str(e)}")
                    content_json = json.dumps({"success": False, "message": "Błąd serializacji wyniku"}, ensure_ascii=False)
                
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": content_json
                    }
                )
            else:
                # Funkcja nie została znaleziona
                logger.error(f"Funkcja {function_name} nie została znaleziona w FUNCTION_MAP")
                function_response = {
                    "success": False, 
                    "message": f"Funkcja {function_name} nie jest dostępna"
                }
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response, ensure_ascii=False, cls=DecimalJSONEncoder)
                    }
                )
        
        # Po wywołaniu wszystkich funkcji, wywołaj model ponownie aby otrzymać końcową odpowiedź
        logger.info("Wywołanie modelu ponownie, aby otrzymać końcową odpowiedź")
        second_response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Możesz dostosować model
            messages=messages,
            temperature=0.7
        )
        
        # Pobierz końcową odpowiedź
        final_response = second_response.choices[0].message.content
        
        # Sprawdź, czy odpowiedź zawiera obrazek wykresu
        chart_image = None
        chart_image_base64 = None
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if function_name in ["generate_bot_chart", "generate_chart"]:
                # Szukamy wiadomości zawierających wyniki wywołania funkcji
                for msg in messages:
                    # Sprawdź, czy to wiadomość od narzędzia (tool) i ma odpowiednie atrybuty
                    if isinstance(msg, dict):
                        if msg.get("role") == "tool" and msg.get("name") == function_name:
                            try:
                                function_result = json.loads(msg.get("content", "{}"))
                                if function_result.get("success") and function_result.get("chart_image"):
                                    chart_image = True
                                    # Pobierz rzeczywiste dane obrazu, jeśli są dostępne
                                    if "chart_image_base64" in function_result:
                                        chart_image_base64 = function_result.get("chart_image_base64")
                                        logger.info(f"Znaleziono dane obrazu wykresu w wyniku funkcji {function_name}")
                                    logger.info(f"Znaleziono obrazek wykresu w wyniku funkcji {function_name}")
                                    break
                            except json.JSONDecodeError:
                                logger.error(f"Błąd dekodowania JSON z wyniku funkcji {function_name}")
                    # Obsługa obiektu ChatCompletionMessage
                    elif hasattr(msg, "role") and hasattr(msg, "name") and hasattr(msg, "content"):
                        if msg.role == "tool" and msg.name == function_name:
                            try:
                                function_result = json.loads(msg.content)
                                if function_result.get("success") and function_result.get("chart_image"):
                                    chart_image = True
                                    # Pobierz rzeczywiste dane obrazu, jeśli są dostępne
                                    if "chart_image_base64" in function_result:
                                        chart_image_base64 = function_result.get("chart_image_base64")
                                        logger.info(f"Znaleziono dane obrazu wykresu w wyniku funkcji {function_name}")
                                    logger.info(f"Znaleziono obrazek wykresu w wyniku funkcji {function_name}")
                                    break
                            except json.JSONDecodeError:
                                logger.error(f"Błąd dekodowania JSON z wyniku funkcji {function_name}")
                if chart_image:
                    break
        
        # Zwróć odpowiedź z informacją o wywołanej funkcji i obrazku
        result = {
            "response": final_response,
            "function_called": True,
            "chart_image": chart_image
        }
        
        # Dodaj dane obrazu, jeśli są dostępne
        if chart_image_base64:
            result["chart_image_base64"] = chart_image_base64
            
        return result
    
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania function calling: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # W przypadku błędu, zwróć informację o nim
        return {
            "response": f"Przepraszam, wystąpił błąd podczas przetwarzania twojego zapytania: {str(e)}",
            "function_called": False,
            "chart_image": None
        } 