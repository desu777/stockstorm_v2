import os
import json
import logging
import openai
import re
from django.conf import settings
import requests
from typing import List, Dict, Any, Optional
import time
from decimal import Decimal

# Klasa do serializacji obiektów Decimal do JSON
class DecimalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalJSONEncoder, self).default(obj)

# Dodajmy bibliotekę do konwersji Markdown na HTML
try:
    import markdown
    has_markdown = True
except ImportError:
    has_markdown = False
    logger = logging.getLogger(__name__)
    logger.warning("Nie można zaimportować modułu markdown. Formatowanie będzie ograniczone.")

# Importy z istniejących plików
from .chart_utils import generate_test_chart, generate_example_chart_for_bot, generate_profit_chart
from .data_utils import get_bot_profit_data, analyze_portfolio, get_hp_positions

# Importy z nowych modułów
from .intent_detection import (
    check_if_chart_needed, 
    check_if_portfolio_analysis_needed,
    check_if_hp_analysis_needed,
    check_if_hp_portfolio_allocation_needed,
    check_trading_command,
    check_bot_chart_request,
    check_if_capital_allocation_analysis_needed,
    check_if_bot_analysis_needed,
    check_alert_command
)
from .trading import parse_trading_command, execute_trade
from .conversation import prepare_conversation_for_ai, get_ai_response
from .bot_analysis import analyze_bot_data, check_bot_existence, get_bot_microservice_id
from .hp_analysis import analyze_hp_portfolio

# Import nowego modułu function calling
from .function_calling import process_function_calling, parse_alert_command, create_price_alert

# Bezpieczny import funkcji z search_utils
try:
    from .search_utils import get_embedding, search_knowledge_base
    has_search_utils = True
    logger.info("Pomyślnie zaimportowano moduły search_utils")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Nie można zaimportować modułów search_utils. Funkcjonalność wyszukiwania będzie ograniczona.")
    has_search_utils = False
    
    # Deklarujemy puste funkcje w przypadku braku modułu
    def get_embedding(text, **kwargs):
        return None
        
    def search_knowledge_base(query, **kwargs):
        return []

logger = logging.getLogger(__name__)

try:
    # Konfiguracja klienta OpenAI
    openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    logger.info("Pomyślnie zainicjalizowano klienta OpenAI")
except Exception as e:
    logger.error(f"Błąd podczas inicjalizacji klienta OpenAI: {e}")

def init_openai_client():
    """Inicjalizuje i zwraca klienta OpenAI API."""
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)

def get_microservice_token(user_id=None):
    """Pobiera token mikrousługi dla użytkownika."""
    if not user_id:
        return None
        
    try:
        from home.utils import get_token
        token = get_token(user_id)
        logger.info(f"Pobrano token mikrousługi dla user_id={user_id}")
        return token
    except Exception as e:
        logger.error(f"Błąd podczas pobierania tokenu mikrousługi: {e}")
        return None

def convert_markdown_to_html(text):
    """Konwertuje tekst Markdown na HTML."""
    if has_markdown:
        # Używamy biblioteki markdown do konwersji
        html = markdown.markdown(text)
        return html
    else:
        # Prosta konwersja bez biblioteki
        text = text.replace('\n\n', '<br/><br/>')
        text = text.replace('\n', '<br/>')
        
        # Nagłówki
        text = re.sub(r'# (.*?)(?:<br/>|$)', r'<h1>\1</h1>', text)
        text = re.sub(r'## (.*?)(?:<br/>|$)', r'<h2>\1</h2>', text)
        text = re.sub(r'### (.*?)(?:<br/>|$)', r'<h3>\1</h3>', text)
        
        # Pogrubienie
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Listy
        text = re.sub(r'- (.*?)(?:<br/>|$)', r'<li>\1</li>', text)
        
        return text

def format_ai_response(response_text, user_message):
    """
    Formatuje odpowiedź AI dla lepszej czytelności, szczególnie dla analiz portfela i botów.
    
    Args:
        response_text: Tekst odpowiedzi od AI
        user_message: Oryginalne zapytanie użytkownika
        
    Returns:
        Sformatowany tekst odpowiedzi
    """
    # Sprawdź czy wiadomość dotyczy analizy portfela lub botów
    is_portfolio_analysis = check_if_portfolio_analysis_needed(user_message) or check_if_hp_portfolio_allocation_needed(user_message)
    is_bot_analysis = check_if_bot_analysis_needed(user_message)
    is_capital_allocation = check_if_capital_allocation_analysis_needed(user_message)
    
    # Jeśli to nie jest analiza, zwróć oryginalną odpowiedź
    if not (is_portfolio_analysis or is_bot_analysis or is_capital_allocation):
        return response_text
    
    # Konwertuj PLN na USD, jeśli występuje w tekście
    response_text = response_text.replace("PLN", "USD")
    
    # Podziel odpowiedź na sekcje
    sections = re.split(r'(#+\s*[^#\n]+|###\s*[^#\n]+)', response_text)
    
    # Jeśli nie ma sekcji, spróbuj podzielić po punktach
    if len(sections) <= 1:
        sections = re.split(r'(\d+\.\s*[^\d\n]+)', response_text)
    
    # Jeśli nadal nie ma podziału, spróbuj znaleźć kategorie
    if len(sections) <= 1:
        sections = re.split(r'(\*\*[^*\n]+\*\*:)', response_text)
    
    # Jeśli nie udało się podzielić na sekcje, sformatuj podstawowo
    if len(sections) <= 1:
        # Podstawowe formatowanie
        formatted_text = ""
        
        if is_portfolio_analysis:
            formatted_text = "# Analiza Portfela\n\n"
            # Dodaj informację o stable coinach
            formatted_text += "Twój portfel jest prowadzony w stablecoinach, gdzie wszystkie wartości są podane w USD.\n\n"
        elif is_bot_analysis:
            formatted_text = "# Analiza Botów\n\n"
        elif is_capital_allocation:
            formatted_text = "# Analiza Alokacji Kapitału\n\n"
            # Dodaj informację o stable coinach
            formatted_text += "Twój portfel jest prowadzony w stablecoinach, gdzie wszystkie wartości są podane w USD.\n\n"
        
        formatted_text += response_text
            
        # Wyróżnij wartości liczbowe i procenty
        formatted_text = re.sub(r'(\d+(\.\d+)?%)', r'**\1**', formatted_text)
        formatted_text = re.sub(r'(\d+(\.\d+)?\s*USD)', r'**\1**', formatted_text)
        
        # Konwertuj Markdown na HTML
        return convert_markdown_to_html(formatted_text)
    
    # Złóż sekcje z powrotem z lepszym formatowaniem
    formatted_text = ""
    current_section_title = ""
    
    # Dodaj ogólny nagłówek i informację o stable coinach
    if is_portfolio_analysis:
        formatted_text = "# Analiza Portfela\n\n"
        formatted_text += "Twój portfel jest prowadzony w stablecoinach, gdzie wszystkie wartości są podane w USD.\n\n"
    elif is_bot_analysis:
        formatted_text = "# Analiza Botów\n\n"
    elif is_capital_allocation:
        formatted_text = "# Analiza Alokacji Kapitału\n\n"
        formatted_text += "Twój portfel jest prowadzony w stablecoinach, gdzie wszystkie wartości są podane w USD.\n\n"
    
    # Przetwórz każdą sekcję
    for i, section in enumerate(sections):
        if i % 2 == 0:  # To jest treść sekcji
            if section.strip():  # Jeśli treść nie jest pusta
                # Dodaj treść sekcji z lepszym formatowaniem
                content = section.strip()
                
                # Wyróżnij wartości liczbowe i procenty
                content = re.sub(r'(\d+(\.\d+)?%)', r'**\1**', content)
                content = re.sub(r'(\d+(\.\d+)?\s*USD)', r'**\1**', content)
                
                # Przekształć listy punktowane
                content = re.sub(r'- ([^\n]+)', r'- \1', content)
                
                formatted_text += content + "\n\n"
        else:  # To jest nagłówek sekcji
            # Sprawdź, czy to nagłówek czy tylko wyróżniony tekst
            if section.strip().startswith('#'):
                # Nagłówek sekcji - dodaj jako nagłówek
                current_section_title = section.strip()
                formatted_text += current_section_title + "\n\n"
            else:
                # Wyróżniony tekst - traktuj jako podtytuł
                subtitle = section.strip()
                # Usuń gwiazdki z podtytułu jeśli są
                subtitle = re.sub(r'\*\*', '', subtitle)
                formatted_text += "## " + subtitle + "\n\n"
    
    # Konwertuj Markdown na HTML
    return convert_markdown_to_html(formatted_text)

def chat_with_ai(user_message, conversation_history=None, knowledge_base_context=None, user_id=None, use_function_calling=None):
    """
    Główna funkcja do interakcji z AI.
    
    Args:
        user_message: Wiadomość od użytkownika
        conversation_history: Historia konwersacji (opcjonalnie)
        knowledge_base_context: Kontekst z bazy wiedzy (opcjonalnie)
        user_id: ID użytkownika (opcjonalnie)
        use_function_calling: Czy używać funkcji function calling (opcjonalnie)
        
    Returns:
        Odpowiedź od AI
    """
    # Rozpocznij pomiar czasu
    start_time = time.time()
    
    try:
        # Logowanie wartości settings.USE_FUNCTION_CALLING i przekazanego parametru use_function_calling
        logger.info(f"settings.USE_FUNCTION_CALLING = {getattr(settings, 'USE_FUNCTION_CALLING', None)}")
        logger.info(f"use_function_calling (parametr) = {use_function_calling}")
        
        # Użyj wartości z parametru, jeśli została podana, w przeciwnym razie użyj wartości z settings
        if use_function_calling is None:
            use_function_calling = getattr(settings, 'USE_FUNCTION_CALLING', True)
            logger.info(f"use_function_calling (używane) = {use_function_calling}")
            
        # Wymuszamy włączenie function calling
        use_function_calling = True
        if not use_function_calling:
            logger.info("Function calling jest wyłączone w ustawieniach - ale wymuszamy jego działanie")
        
        # Wyszukaj kontekst z bazy wektorowej, jeśli dostępna
        if has_search_utils and not knowledge_base_context:
            try:
                logger.info(f"Wyszukiwanie w bazie wektorowej dla zapytania: {user_message[:50]}...")
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
                logger.error(f"Błąd podczas wyszukiwania w bazie wektorowej: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Dodaj kontekst z bazy wiedzy, jeśli istnieje
        full_message = user_message
        if knowledge_base_context:
            logger.info(f"Dodawanie kontekstu z bazy wiedzy: {len(knowledge_base_context)} znaków")
            full_message = f"{knowledge_base_context}\n\nPytanie: {user_message}"
        
        # Inicjalizacja klienta OpenAI
        try:
            openai_client = init_openai_client()
        except Exception as e:
            logger.error(f"Błąd inicjalizacji klienta OpenAI: {e}")
            return {"response": "Wystąpił problem z połączeniem z usługą AI. Spróbuj ponownie później."}
            
        # Pobierz token mikrousługi, jeśli user_id jest dostępne
        microservice_token = None
        if user_id:
            try:
                microservice_token = get_microservice_token(user_id)
            except Exception as e:
                logger.warning(f"Nie udało się pobrać tokenu mikrousługi: {e}")
        
        # Sprawdź najpierw, czy wiadomość zawiera komendę alertu (priorytet nad komendami handlowymi)
        from .intent_detection import check_alert_command
        is_alert_command = check_alert_command(user_message)
        
        if is_alert_command:
            logger.info(f"Wykryto komendę alertu: {user_message}")
            
            # Parsuj komendę alertu za pomocą modelu
            alert_data = parse_alert_command(user_message, openai_client)
            
            if alert_data:
                logger.info(f"Sparsowane dane alertu: {alert_data}")
                # Wykonaj utworzenie alertu
                alert_result = create_price_alert(
                    user_id=user_id,
                    ticker=alert_data.get('ticker'),
                    position_identifier=alert_data.get('position_identifier'),
                    alert_type=alert_data.get('alert_type'),
                    threshold_value=alert_data.get('threshold_value'),
                    notes=alert_data.get('notes')
                )
                
                # Sformułuj odpowiedź na podstawie wyniku
                if alert_result.get('success'):
                    return {"response": f"Alert utworzony pomyślnie: {alert_result.get('message', '')}"}
                else:
                    return {"response": f"Nie udało się utworzyć alertu: {alert_result.get('message', 'Sprawdź dane alertu.')}"}
        
        # Sprawdź, czy to zapytanie o portfel GT
        def check_gt_portfolio_query(message):
            """Sprawdza, czy wiadomość zawiera zapytanie o portfel GT"""
            message = message.lower()
            gt_keywords = ['portfel gt', 'portfela gt', 'portfelu gt', 'gt portfolio', 'mój portfel', 'moje akcje']
            return any(keyword in message for keyword in gt_keywords)
            
        is_gt_portfolio_query = check_gt_portfolio_query(user_message)
        
        if is_gt_portfolio_query and user_id:
            logger.info(f"Wykryto zapytanie o portfel GT: {user_message}")
            try:
                # Import bezpośrednio funkcji do portfela GT
                from .gt_portfolio_management import get_gt_portfolio, create_test_portfolio
                
                # Pobierz dane portfela GT
                gt_portfolio_data = get_gt_portfolio(user_id)
                
                if gt_portfolio_data.get('success'):
                    # Sprawdź, czy portfolio ma jakiekolwiek pozycje
                    portfolio = gt_portfolio_data.get('portfolio', {})
                    has_positions = (
                        portfolio.get('summary', {}).get('total_positions', 0) > 0
                        if portfolio else False
                    )
                    
                    if not has_positions:
                        # Użytkownik nie ma pozycji - utwórz przykładowy portfel
                        logger.info("Użytkownik nie ma pozycji w portfelu GT - tworzę przykładowy portfel")
                        create_result = create_test_portfolio(user_id)
                        
                        if create_result.get('success'):
                            logger.info("Pomyślnie utworzono przykładowy portfel GT")
                            # Ponownie pobierz dane portfela po utworzeniu przykładowych pozycji
                            gt_portfolio_data = get_gt_portfolio(user_id)
                        else:
                            logger.warning(f"Nie udało się utworzyć przykładowego portfela: {create_result.get('message')}")
                    
                    # Gdy dane zostały pobrane pomyślnie, możemy przekazać je do modelu
                    logger.info("Pobrano dane portfela GT pomyślnie")
                    
                    # Dodaj instrukcje dla modelu o portfelu GT
                    gt_portfolio_context = (
                        f"Odpowiadając na pytanie o portfel GT, weź pod uwagę poniższe dane: "
                        f"{json.dumps(gt_portfolio_data, ensure_ascii=False, cls=DecimalJSONEncoder)}"
                    )
                    
                    # Dodaj kontekst do wiadomości użytkownika
                    full_message = f"{gt_portfolio_context}\n\nPytanie użytkownika: {user_message}"
                    
                    # Używamy normalnej ścieżki function_calling ale z dodatkowym kontekstem
                else:
                    logger.warning(f"Nie udało się pobrać danych portfela GT: {gt_portfolio_data.get('message')}")
                    # W razie problemów z danymi kontynuujemy normalną ścieżkę
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania zapytania o portfel GT: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Jeśli to nie komenda alertu, sprawdź czy to komenda handlowa
        from .intent_detection import check_trading_command
        is_trading_command = check_trading_command(user_message)
        
        if is_trading_command:
            logger.info(f"Wykryto komendę handlową: {user_message}")
            from .trading import parse_trading_command, execute_trade
            
            # Parsuj komendę za pomocą modelu
            trading_data = parse_trading_command(user_message, openai_client)
            
            if trading_data:
                # Wykonaj transakcję
                trade_result = execute_trade(user_id, trading_data)
                
                # Sformułuj odpowiedź na podstawie wyniku
                if trade_result.get('success'):
                    return {"response": f"Transakcja wykonana pomyślnie: {trade_result.get('message', '')}"}
                else:
                    return {"response": f"Nie udało się wykonać transakcji: {trade_result.get('message', 'Sprawdź dane transakcji.')}"}
        
        if use_function_calling:
            # Użyj trybu function calling
            try:
                from .function_calling import process_function_calling
                logger.info("Używam trybu funkcyjnego (function calling)")
                
                # Dodaj dodatkowe instrukcje systemowe dotyczące portfela GT
                gt_portfolio_instructions = """
                System obsługuje portfel GT, który zawiera pozycje akcji, kategorie i alerty cenowe. Aby zarządzać portfelem GT:
                1. Gdy użytkownik pyta o swój portfel GT, użyj funkcji get_gt_portfolio(user_id).
                2. Gdy użytkownik chce dodać pozycję, użyj funkcji add_stock_position(user_id, ticker, quantity, category_name, notes).
                3. Gdy użytkownik chce ustawić alert cenowy, użyj funkcji gt_add_price_alert(user_id, ticker, alert_type, threshold_value, notes).
                """
                
                # Sprawdź czy mamy dodatkowy kontekst GT i zaktualizuj wiadomość użytkownika
                if 'Odpowiadając na pytanie o portfel GT' in full_message:
                    logger.info("Wykryto dodatkowy kontekst GT w wiadomości użytkownika")
                    # Gdy już mamy kontekst GT, używamy full_message
                else:
                    # Dodaj instrukcje GT do pełnej wiadomości
                    full_message = f"{gt_portfolio_instructions}\n\n{full_message}"
                
                # Wywołaj funkcję z dodatkowym kontekstem
                result = process_function_calling(
                    user_message=full_message, 
                    conversation_history=conversation_history,
                    user_id=user_id,
                    microservice_token=microservice_token
                )
                
                # Zastosuj automatyczne formatowanie odpowiedzi AI
                if result and 'response' in result:
                    result['response'] = format_ai_response(result['response'], user_message)
                
                # Zbierz wynik
                # Wyniki oczekujemy jako słownika, ale obsłużmy wszystkie możliwe przypadki
                if isinstance(result, dict):
                    # Już mamy słownik, wszystko ok
                    pass
                elif isinstance(result, str):
                    # Mamy string, opakuj w słownik
                    result = {"response": result}
                elif result is None:
                    # Brak wyniku, utwórz domyślny
                    result = {"response": "Przepraszam, nie udało się przetworzyć Twojego zapytania."}
                else:
                    # Cokolwiek innego, spróbuj skonwertować na string
                    try:
                        result = {"response": str(result)}
                    except:
                        result = {"response": "Przepraszam, wystąpił nieznany błąd."}
                
                # Zastosuj automatyczne formatowanie odpowiedzi AI
                if result and 'response' in result:
                    result['response'] = format_ai_response(result['response'], user_message)
                
                # Przygotuj wartości zwracane
                response = result.get('response', '')
                chart_image = None
                
                # Sprawdź, czy mamy dane obrazu w wyniku
                if result.get('chart_image'):
                    logger.info("Wykryto obrazek wykresu w wyniku")
                    
                    # Sprawdź, czy mamy faktyczne dane obrazu base64, czy tylko flagę
                    if result.get('chart_image_base64'):
                        chart_image = result.get('chart_image_base64')
                        logger.info(f"Pobrano dane obrazu wykresu o rozmiarze {len(chart_image)} znaków base64")
                    else:
                        logger.warning("Wykryto flagę chart_image, ale brak danych base64 obrazu")
                
                # Ekstrakcja tytułu konwersacji na podstawie pierwszej linii odpowiedzi
                title = None
                first_line = response.split('\n')[0] if response else ""
                if first_line and len(first_line) > 3:
                    # Usuń znaki markdownu z początku linii
                    if first_line.startswith('# '):
                        first_line = first_line[2:]
                    if len(first_line) <= 50:
                        title = first_line  # Używaj pierwszej linii jako tytuł
                    else:
                        title = first_line[:47] + "..."  # Skróć tytuł, jeśli jest zbyt długi
                
                # Zapisz czas generowania odpowiedzi
                end_time = time.time()
                elapsed_time = round(end_time - start_time, 2)
                logger.info(f"Wygenerowano odpowiedź w {elapsed_time}s")
                
                # Zwróć wynik
                return {
                    "response": response,
                    "chart_image": chart_image,
                    "title": title
                }
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania function calling: {str(e)}")
                logger.info("Przełączanie na tryb tradycyjny po błędzie w function calling")
                # Jeśli wystąpi błąd, przełącz się na tryb tradycyjny
        
        # Tryb tradycyjny (bez function calling)
        logger.info("Używam trybu tradycyjnego (bez function calling)")
        from .conversation import get_ai_response
        
        # Przygotuj wiadomości dla modelu, włączając historię konwersacji
        prepared_messages = []
        
        # Dodaj systemowy prompt
        system_message = """Jesteś asystentem tradingowym specjalizującym się w analizie portfela, kryptowalutach i botach tradingowych.
        
Twoja rola obejmuje:
1. Analizę portfela kryptowalutowego użytkownika
2. Pomoc w zrozumieniu działania botów tradingowych
3. Udzielanie odpowiedzi na pytania związane z tradingiem i kryptowalutami

Odpowiadaj w sposób zwięzły, ale informatywny."""

        prepared_messages.append({"role": "system", "content": system_message})
        
        # Dodaj historię konwersacji, jeśli jest dostępna
        if conversation_history and isinstance(conversation_history, list):
            # Dodaj maksymalnie 10 ostatnich wiadomości z historii, aby zmieścić się w kontekście
            for message in conversation_history[-10:]:
                if isinstance(message, dict) and "role" in message and "content" in message:
                    prepared_messages.append(message)
            logger.info(f"Dodano {len(conversation_history[-10:])} wiadomości z historii konwersacji")
        
        # Dodaj aktualną wiadomość użytkownika
        prepared_messages.append({"role": "user", "content": full_message})
        
        # Wywołaj model poprzez get_ai_response
        ai_response = get_ai_response(prepared_messages, openai_client)
        result = {"response": ai_response.get("response", "Brak odpowiedzi od AI.")}
        
        # Zastosuj automatyczne formatowanie odpowiedzi AI
        if result and 'response' in result:
            result['response'] = format_ai_response(result['response'], user_message)
        
        # Zbierz wynik
        # Wyniki oczekujemy jako słownika, ale obsłużmy wszystkie możliwe przypadki
        if isinstance(result, dict):
            # Już mamy słownik, wszystko ok
            pass
        elif isinstance(result, str):
            # Mamy string, opakuj w słownik
            result = {"response": result}
        elif result is None:
            # Brak wyniku, utwórz domyślny
            result = {"response": "Przepraszam, nie udało się przetworzyć Twojego zapytania."}
        else:
            # Cokolwiek innego, spróbuj skonwertować na string
            try:
                result = {"response": str(result)}
            except:
                result = {"response": "Przepraszam, wystąpił nieznany błąd."}
                
        # Zastosuj automatyczne formatowanie odpowiedzi AI
        if result and 'response' in result:
            result['response'] = format_ai_response(result['response'], user_message)
                
        # Przygotuj wartości zwracane
        response = result.get('response', '')
        chart_image = None
        
        # Sprawdź, czy mamy dane obrazu w wyniku
        if result.get('chart_image'):
            logger.info("Wykryto obrazek wykresu w wyniku")
            
            # Sprawdź, czy mamy faktyczne dane obrazu base64, czy tylko flagę
            if result.get('chart_image_base64'):
                chart_image = result.get('chart_image_base64')
                logger.info(f"Pobrano dane obrazu wykresu o rozmiarze {len(chart_image)} znaków base64")
            else:
                logger.warning("Wykryto flagę chart_image, ale brak danych base64 obrazu")
                
        # Ekstrakcja tytułu konwersacji na podstawie pierwszej linii odpowiedzi
        title = None
        first_line = response.split('\n')[0] if response else ""
        if first_line and len(first_line) > 3:
            # Usuń znaki markdownu z początku linii
            if first_line.startswith('# '):
                first_line = first_line[2:]
            if len(first_line) <= 50:
                title = first_line  # Używaj pierwszej linii jako tytuł
            else:
                title = first_line[:47] + "..."  # Skróć tytuł, jeśli jest zbyt długi
                
        # Zapisz czas generowania odpowiedzi
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)
        logger.info(f"Wygenerowano odpowiedź w {elapsed_time}s")
                
        # Zwróć wynik
        return {
            "response": response,
            "chart_image": chart_image,
            "title": title
        }
            
    except Exception as e:
        logger.exception(f"Błąd w chat_with_ai: {str(e)}")
        return {"response": "Przepraszam, wystąpił błąd podczas przetwarzania Twojego zapytania. Spróbuj ponownie później."} 