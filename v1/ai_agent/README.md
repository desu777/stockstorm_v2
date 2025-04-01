# AI Agent Module

Ten moduł zawiera implementację inteligentnego asystenta AI do obsługi zapytań użytkowników, analizy danych botów, generowania wykresów i obsługi transakcji.

## Struktura modułu

Moduł został podzielony na logiczne komponenty:

### Główne pliki

- `services.py` - główny plik koordynujący funkcjonalność asystenta
- `intent_detection.py` - wykrywanie intencji użytkownika
- `trading.py` - obsługa transakcji i zleceń giełdowych
- `conversation.py` - zarządzanie konwersacją z API OpenAI
- `bot_analysis.py` - analiza danych botów
- `chart_utils.py` - generowanie wykresów
- `data_utils.py` - pobieranie i przetwarzanie danych
- `search_utils.py` - przeszukiwanie bazy wiedzy
- `function_calling.py` - zarządzanie mechanizmem function calling
- `capital_analysis.py` - analiza alokacji kapitału
- `hp_analysis.py` - analiza portfela HP

## Funkcjonalność

### Function Calling

Agent wykorzystuje zaawansowany mechanizm "function calling" do bezpośredniej interakcji z funkcjami systemu:

```python
from ai_agent.function_calling import process_function_calling
```

Mechanizm umożliwia przekazanie do modelu AI informacji o dostępnych funkcjach, ich parametrach i przeznaczeniu. Dzięki temu model może "wywoływać" odpowiednie funkcje na podstawie intencji użytkownika. Dostępne funkcje:

1. `analyze_hp_portfolio` - analiza portfela HP (Hot Positions)
2. `analyze_capital_allocation` - analiza alokacji kapitału pomiędzy różnymi instrumentami
3. `analyze_portfolio` - analiza całego portfela użytkownika
4. `analyze_bots` - analiza botów tradingowych
5. `execute_trade` - wykonywanie transakcji handlowych
6. `execute_stop_limit` - ustawianie zleceń stop-limit
7. `generate_bot_chart` - generowanie wykresów dla konkretnych botów
8. `generate_profit_chart` - generowanie ogólnych wykresów zysków

### Automatyczne formatowanie odpowiedzi

Agent automatycznie formatuje odpowiedzi w stylu Markdown, z odpowiednim wyróżnieniem:

- Nagłówki różnych poziomów
- Pogrubiony tekst dla ważnych wartości
- Listy numerowane i punktowane 
- Specjalne formatowanie dla analiz portfela, botów i alokacji kapitału

Formatowanie jest obsługiwane zarówno po stronie backendu (Python) jak i frontendu (JavaScript).

### Intent Detection

Wykrywanie intencji użytkownika na podstawie przesłanej wiadomości:

```python
from ai_agent.intent_detection import (
    check_if_chart_needed,
    check_if_portfolio_analysis_needed,
    check_if_hp_analysis_needed,
    check_if_hp_portfolio_allocation_needed,
    check_if_capital_allocation_analysis_needed,
    check_if_bot_analysis_needed,
    check_trading_command,
    check_bot_chart_request
)
```

Agent potrafi rozpoznać następujące typy intencji:
- Prośby o wykresy
- Analizy portfela/botów
- Komendy handlowe (kupno/sprzedaż)
- Zlecenia stop-limit
- Analizy alokacji kapitału

### Trading

Moduł do obsługi transakcji handlowych:

```python
from ai_agent.trading import (
    parse_trading_command, 
    execute_trade,
    execute_stop_limit_order,
    parse_trading_command_to_dict
)
```

Obsługuje różne typy transakcji:
- Kupno/sprzedaż po cenie rynkowej
- Kupno/sprzedaż po cenie limitowej
- Zlecenia stop-limit
- Transakcje w portfelu HP

### Analiza Kapitału

Nowe funkcje analizy alokacji kapitału:

```python
from ai_agent.capital_analysis import analyze_capital_allocation
```

Dostarcza szczegółowej analizy podziału kapitału pomiędzy:
- Boty 5-10-15rei (z reinwestycją)
- Boty 5-10-15 (bez reinwestycji)
- Portfel HP (w tym udział BTC)

### Conversation

Moduł do obsługi konwersacji z API OpenAI:

```python
from ai_agent.conversation import prepare_conversation_for_ai, get_ai_response
```

### Bot Analysis

Moduł do analizy danych botów:

```python
from ai_agent.bot_analysis import (
    analyze_bot_data, 
    check_bot_existence, 
    get_bot_microservice_id
)
```

## Przykład użycia

```python
from ai_agent import chat_with_ai

# Wywołanie asystenta
response = chat_with_ai(
    user_message="Pokaż mi wykres zysków dla bota 42",
    user_id=123,
    microservice_token="token123"
)

# Wynik zawiera odpowiedź tekstową i opcjonalnie wykres
text_response = response["response"]
chart_image = response.get("chart_image")  # Może być None jeśli nie wygenerowano wykresu
```

### Przykłady zapytań

Agent obsługuje różnorodne typy zapytań, na przykład:

- "kup btc za 100 usdt" - wykonanie transakcji kupna
- "sprzedaj btc z hp1" - sprzedaż z określonego portfela
- "zlecenie stop limit na PORTAL za 100 usdt trigger 0.0902 cena 0.0901" - ustawienie zlecenia
- "przeanalizujesz mój portfel hp?" - analiza portfela
- "pokaż alokację kapitału" - analiza podziału kapitału

## Architektura

Moduł wykorzystuje wzorzec modułowy, gdzie każdy komponent jest odpowiedzialny za konkretną funkcjonalność:

1. `intent_detection.py` - wykrywa intencje użytkownika za pomocą analizy tekstu
2. `trading.py` - obsługuje transakcje handlowe, korzystając z API Binance
3. `conversation.py` - komunikuje się z API OpenAI do generowania odpowiedzi
4. `bot_analysis.py` - analizuje dane botów, generując statystyki
5. `function_calling.py` - zarządza komunikacją między modelem AI a funkcjami systemu
6. `services.py` - koordynuje działanie wszystkich powyższych modułów

## Korzyści modułowej architektury

1. **Większa modułowość** - każdy plik zajmuje się konkretnym aspektem funkcjonalności
2. **Łatwiejsze utrzymanie** - mniejsze pliki są bardziej czytelne i łatwiejsze w zarządzaniu
3. **Lepsza organizacja** - funkcje są zgrupowane logicznie, co ułatwia odnalezienie potrzebnej funkcjonalności
4. **Łatwiejsze testowanie** - można testować poszczególne komponenty niezależnie
5. **Prostsze rozszerzanie** - dodawanie nowych funkcji jest łatwiejsze dzięki jasno określonym granicom odpowiedzialności 

## Formatowanie tekstu

Agent automatycznie formatuje odpowiedzi, aby:

1. Nagłówki (h1, h2, h3) miały odpowiedni rozmiar i styl
2. Wartości liczbowe były pogrubione (np. **100.45 USD**)
3. Listy punktowane i numerowane były prawidłowo wyświetlane
4. Odpowiedzi były czytelne i estetyczne
5. Informacja o stablecoinach była zawsze uwzględniona

Formatowanie jest realizowane zarówno po stronie backendu w funkcji `format_ai_response` w pliku `services.py`, jak i po stronie frontendu za pomocą funkcji JavaScript `formatMarkdown` i `cleanMarkdownRemnants` w szablonie chat.html. 