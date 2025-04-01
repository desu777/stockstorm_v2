"""
AI Agent - Inteligentny asystent wspomagający handel kryptowalutami i zarządzanie botami.

Ten moduł zawiera:
- Interfejs dla modeli językowych AI (OpenAI API)
- Narzędzia do analizy danych i generowania wykresów
- Interfejs do obsługi transakcji handlowych
- Narzędzia do wykrywania intencji użytkownika
- Funkcje do analizy portfela HP i alokacji kapitału
- Mechanizm function calling dla modeli LLM
"""

# Plik inicjalizacyjny pakietu v1/ai_agent
# Służy do umożliwienia importowania modułów z tego katalogu

# Definiujemy listę dostępnych funkcji, ale nie importujemy ich bezpośrednio
# To zapobiegnie wczesnemu ładowaniu modułów, które wymagają zainicjalizowanych aplikacji Django
__all__ = [
    'chat_with_ai',
    'generate_test_chart', 
    'generate_profit_chart', 
    'generate_example_chart_for_bot',
    'get_bot_profit_data', 
    'analyze_portfolio', 
    'get_hp_positions',
    'get_embedding', 
    'search_knowledge_base',
    'analyze_hp_portfolio',
    'analyze_capital_allocation',
    'process_function_calling',
    'call_search_knowledge_base'
]

# Nie importujemy modułów tutaj - będą importowane dopiero wtedy, gdy zostaną użyte

# Importy głównych funkcji z modułów
from .services import chat_with_ai
from .intent_detection import (
    check_if_chart_needed, 
    check_if_portfolio_analysis_needed,
    check_if_hp_analysis_needed,
    check_if_hp_portfolio_allocation_needed,
    check_trading_command,
    check_bot_chart_request,
    check_if_bot_analysis_needed,
    check_if_capital_allocation_analysis_needed
)
from .trading import parse_trading_command, execute_trade, execute_stop_limit_order
from .conversation import prepare_conversation_for_ai, get_ai_response
from .bot_analysis import analyze_bot_data, check_bot_existence, get_bot_microservice_id
from .chart_utils import generate_profit_chart, generate_example_chart_for_bot
from .data_utils import get_bot_profit_data, analyze_portfolio, get_hp_positions
from .hp_analysis import analyze_hp_portfolio
from .capital_analysis import analyze_capital_allocation
from .function_calling import process_function_calling, call_search_knowledge_base
from .search_utils import get_embedding, search_knowledge_base

# Wersja
__version__ = "1.2.0"
