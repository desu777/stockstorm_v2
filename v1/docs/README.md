# 📊 StockStorm - Platforma Trading z AI

StockStorm to zaawansowana platforma handlowa z integracją sztucznej inteligencji, stworzona do zarządzania inwestycjami kryptowalutowymi. System oferuje możliwość zarządzania portfelem, automatyzację handlu z wykorzystaniem zleceń limit-stop oraz asystenta AI do analizy rynku i pomocy w podejmowaniu decyzji inwestycyjnych.

![StockStorm Platform](../media/stockstorm_logo.png)

## 🚀 Funkcjonalności

### 📈 HP Crypto - Zarządzanie Portfelem
- **Śledzenie pozycji**: monitorowanie aktywnych i zamkniętych pozycji
- **Kategorie portfela**: organizacja inwestycji w grupy (np. HP1, HP2)
- **Aktualizacje cen**: automatyczne aktualizacje cen z API Binance
- **Metryki wydajności**: śledzenie zysków/strat, wartości portfela i innych wskaźników
- **Alerty cenowe**: powiadomienia o zmianach cen i osiągnięciu progów

### 🤖 Zlecenia Stop-Limit
- **Składanie zleceń**: tworzenie zleceń stop-limit buy/sell z określonymi parametrami
- **Monitorowanie zleceń**: śledzenie statusu wszystkich oczekujących zleceń
- **Automatyczne wykonanie**: zlecenia są monitorowane i wykonywane przez zadania Celery
- **Integracja z Binance**: możliwość wykonania zleceń za pośrednictwem API Binance

### 🧠 AI Agent
- **Czat asystujący**: asystent AI do analizy rynku i wsparcia w podejmowaniu decyzji
- **Przetwarzanie języka naturalnego**: możliwość wydawania poleceń w języku naturalnym
- **Analizy techniczne**: generowanie analiz technicznych i wykresów
- **Wykonywanie operacji**: implementacja zleceń i zarządzanie portfelem poprzez polecenia tekstowe

### 📱 BNB Grid Trading Bots (Mikrousługi)
- **Automatyczny grid trading**: tworzenie i zarządzanie botami handlowymi wykorzystującymi strategię grid
- **Wielopoziomowe zlecenia**: automatyczne kupno i sprzedaż na wielu poziomach cenowych
- **Niezależne mikrousługi**: oddzielne serwery bnbbot1 i bnbbot2 dla różnych strategii i użytkowników
- **Zarządzanie kapitałem**: dynamiczna alokacja środków i reinwestycja zysków

## 🏗️ Architektura Systemu

### Struktura Projektu
```
stockstorm/
├── v1/                      # Główna aplikacja StockStorm
│   ├── ai_agent/            # Asystent AI
│   ├── hpcrypto/            # Zarządzanie portfelem
│   ├── home/                # Strona główna i uwierzytelnianie
│   └── stockstorm_project/  # Konfiguracja projektu
├── bnbbot1/                 # Mikrousługa tradingowa (Grid Bot 1)
│   ├── bnbbot1/             # Konfiguracja projektu
│   └── bnbgrid/             # Implementacja grid tradingu
│       ├── models.py        # Modele danych (BnbBot, BnbTrade)
│       ├── bnb_manager.py   # Zarządzanie botami i integracja z Binance
│       ├── bnb_logic.py     # Logika strategii grid trading
│       └── views.py         # API endpoints
├── bnbbot2/                 # Mikrousługa tradingowa (Grid Bot 2)
│   ├── bnbbot2/             # Konfiguracja projektu
│   └── bnbgrid/             # Implementacja ulepszonej wersji grid tradingu
│       ├── models.py        # Modele danych
│       ├── bnb_manager.py   # Zarządzanie botami
│       └── views.py         # API endpoints
```

### Komponenty Techniczne
- **Framework**: Django 5.1
- **Baza danych**: SQLite (development) / PostgreSQL (produkcja)
- **Kolejkowanie zadań**: Celery z Redis jako brokerem
- **Front-end**: HTML, CSS, JavaScript, Alpine.js
- **API**: Integracja z Binance API
- **Powiadomienia**: Telegram Bot API
- **Mikrousługi**: Niezależne serwery Django z własną bazą danych

## 📋 Modele Danych

### HPCategory
- Grupy kategorii inwestycji (np. HP1, HP2)
- Relacja jeden-do-wielu z pozycjami

### Position
- Poszczególne pozycje inwestycyjne
- Zawiera informacje o: symbolu, ilości, cenie wejścia/wyjścia, aktualnej cenie
- Obliczenia zysków/strat i pozycji

### PendingOrder
- Oczekujące zlecenia stop-limit
- Zawiera definicje zlecenia: typ, symbol, cena limitu, cena wyzwalacza
- Śledzi status zlecenia i jego wykonanie

### PriceAlert
- Alerty cenowe dla pozycji
- Definiuje progi alertów i warunki powiadomień

### BnbBot (mikrousługi)
- Konfiguracja botów grid tradingowych
- Definiuje parametry strategii: symbol, kapitał, poziomy cenowe, procent zysku
- Przechowuje dane do integracji z API Binance

### BnbTrade (mikrousługi)
- Transakcje zrealizowane przez boty grid trading
- Zawiera informacje o poziomie transakcji, stronie (buy/sell), ilości, cenie
- Śledzi zyski z zamkniętych transakcji

## 🔄 Procesy i Przepływy

### Proces Aktualizacji Cen
1. Wywołanie API update_prices
2. Pobranie aktualnych cen z Binance
3. Aktualizacja modeli pozycji
4. Sprawdzenie alertów cenowych
5. Powiadomienie użytkownika (Telegram)

### Proces Zleceń Stop-Limit
1. Użytkownik tworzy zlecenie poprzez asystenta AI
2. Zlecenie zapisywane jest w bazie danych
3. Zadanie Celery monitoruje cenę rynkową
4. Przy osiągnięciu ceny wyzwalacza, zlecenie jest wykonywane
5. Pozycja jest dodawana do portfela lub aktualizowana

### Proces Grid Tradingu (Mikrousługi)
1. Użytkownik tworzy bota z parametrami strategii (kapitał, poziomy, procent)
2. System automatycznie generuje siatkę poziomów cenowych
3. Bot monitoruje rynek i wykonuje transakcje według następujących zasad:
   - Kupuje na każdym poziomie gdy cena spada
   - Sprzedaje z określonym zyskiem procentowym gdy cena rośnie
4. Transakcje są zapisywane i widoczne w interfejsie
5. Zyski są reinwestowane lub akumulowane według preferencji

## 🔧 Konfiguracja i Uruchomienie

### Wymagania Systemowe
- Python 3.11+
- Django 5.1+
- Celery 5.3+
- Redis 7.0+

### Instalacja Głównej Aplikacji
```bash
# Klonowanie repozytorium
git clone https://github.com/desu777/stockstorm.git
cd stockstorm/v1

# Tworzenie wirtualnego środowiska
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalacja zależności
pip install -r requirements.txt

# Migracje bazy danych
python manage.py migrate

# Uruchomienie serwera
python manage.py runserver
```

### Uruchomienie Celery
```bash
# Terminal 1: Uruchomienie Celery worker
celery -A stockstorm_project worker -l info

# Terminal 2: Uruchomienie Celery beat
celery -A stockstorm_project beat -l info
```

### Uruchomienie Mikrousług
```bash
# Terminal 3: Uruchomienie bnbbot1
cd ../bnbbot1
python manage.py runserver 8001

# Terminal 4: Uruchomienie bnbbot2
cd ../bnbbot2
python manage.py runserver 8002
```

## 🌐 Integracja Mikrousług

Mikrousługi bnbbot1 i bnbbot2 komunikują się z główną aplikacją poprzez API. Główne punkty integracji:

1. **Uwierzytelnianie**: Współdzielone tokeny Auth między mikrousługami i główną aplikacją
2. **Synchronizacja danych**: Aktualizacja zysków i statusu botów w głównej aplikacji
3. **Zarządzanie kapitałem**: Sprawdzanie dostępnych środków z głównej aplikacji
4. **Powiadomienia**: Centralizacja powiadomień przez system głównej aplikacji

## 🔮 Dalszy Rozwój
- Integracja z większą liczbą giełd kryptowalut
- Zaawansowane strategie handlowe i botów
- Analizy predykcyjne z wykorzystaniem uczenia maszynowego
- Mobilna aplikacja
- Społecznościowe funkcje i dzielenie się strategiami
- Dodatkowe mikrousługi dla różnych strategii automatycznego tradingu

## 📝 Licencja
Copyright © 2025 StockStorm. Wszystkie prawa zastrzeżone. 