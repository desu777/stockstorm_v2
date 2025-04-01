import re

def check_if_chart_needed(user_message):
    """Sprawdza, czy użytkownik prosi o wykres."""
    indicators = ["wykres", "chart", "pokaż zyski", "pokaż profity", "wykreślić", "wizualizacja",
                  "zobrazować", "trend", "wykresy", "narysuj", "narysować", "analiza zysków"]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():
            return True
    return False

def check_if_portfolio_analysis_needed(user_message):
    """Sprawdza, czy użytkownik prosi o analizę portfela."""
    indicators = ["analiza portfela", "pokaż portfel", "struktura portfela", "skład portfela", "boty w portfelu"]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():  
            return True
    return False

def check_if_hp_analysis_needed(user_message):
    """Sprawdza, czy użytkownik prosi o analizę HP."""
    indicators = ["analiza hp", "pokaż hp", "hardpool", "hard pool", "hard-pool", "hpool", "h-pool"]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():
            return True
    return False

def check_if_hp_portfolio_allocation_needed(user_message):
    """Sprawdza, czy użytkownik prosi o analizę alokacji kapitału w portfelu HP."""
    indicators = [
        "alokacja kapitału", "struktura portfela", "rozkład kapitału", "podział portfela", 
        "koncentracja kapitału", "ile btc w portfelu", "ile eth w portfelu", "procent btc", 
        "struktura hp", "skład portfela", "skład hp", "przeanalizuj portfel hp", 
        "jak wygląda mój portfel", "analiza struktury portfela",
        # Dodaję dokładne frazy użytkownika
        "przeanalizujesz mój portfel hp", "przeanalizujesz mi portfel hp",
        "przeanalizuj mój portfel hp", "przeanalizuj mi portfel hp",
        "analizuj portfel hp", "analizuj mój portfel"
    ]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():
            return True
    return False

def check_if_bot_analysis_needed(user_message):
    """Sprawdza, czy użytkownik prosi o analizę botów."""
    indicators = [
        "przeanalizuj moje boty", "przeanalizuj boty", "analiza botów", 
        "pokaż boty", "moje boty", "lista botów", "analiza moich botów",
        "sprawdź boty"
    ]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():
            return True
    return False

def check_if_capital_allocation_analysis_needed(user_message):
    """Sprawdza, czy użytkownik prosi o analizę alokacji kapitału pomiędzy różnymi instrumentami."""
    indicators = [
        "przeanalizuj alokacje kapitału", "przeanalizuj alokację kapitału", 
        "analiza alokacji kapitału", "podział kapitału", "alokacja kapitału",
        "rozkład kapitału", "ile % kapitału", "procent kapitału",
        "ile procent kapitału", "jak podzielony jest kapitał"
    ]
    
    for indicator in indicators:
        if indicator.lower() in user_message.lower():
            return True
    return False

def check_trading_command(message):
    """
    Sprawdza, czy wiadomość użytkownika zawiera komendę handlową.
    
    Args:
        message: Wiadomość od użytkownika.
        
    Returns:
        bool: True, jeśli wykryto komendę handlową, False w przeciwnym razie.
    """
    # Normalizacja wiadomości
    message_lower = message.lower()
    
    # Najpierw wyklucz komendy alertu, zwłaszcza dla akcji (portfel GT)
    # WAŻNE: Słowa kluczowe związane z alertami i portfelem GT
    alert_keywords = ["alert", "powiadomienie", "powiadom", "notyfikacja", "notyfikuj"]
    gt_keywords = ["gt", "akcje", "akcji", "stock", "tsla", "aapl", "msft", "portfel gt", "portfelu gt"]
    
    # Jeśli wiadomość zawiera słowo "alert" plus którekolwiek ze słów kluczowych dla portfela GT,
    # nie klasyfikuj jako komendy handlowej
    for alert_word in alert_keywords:
        if alert_word in message_lower:
            for gt_word in gt_keywords:
                if gt_word in message_lower:
                    print(f"[DEBUG] Wykryto komendę alertu dla portfela GT, nie klasyfikuję jako komendy handlowej: {message}")
                    return False
    
    # Następnie sprawdź, czy to nie jest komenda alertu - jeśli tak, to nie klasyfikuj jako komendy handlowej
    if check_alert_command(message):
        print(f"[DEBUG] Wykryto komendę alertu, nie klasyfikuję jako komendy handlowej: {message}")
        return False
    
    # Wzorce dla kupna
    buy_patterns = [
        r'kup[ić]?\s+(\w+)', 
        r'zaku[pić]?\s+(\w+)',
        r'kupuj[ę]?\s+(\w+)',
        r'kupno\s+(\w+)',
        r'do[łć]aduj\s+(\w+)',
        r'nabywam\s+(\w+)',
        r'(chcę|chciałbym)\s+kupić\s+(\w+)',
        r'(chcę|chciałbym)\s+zakupić\s+(\w+)',
        r'zainwestuj\s+w\s+(\w+)',
        r'kup[ię]\s+za\s+(\d+)',
        r'(\w+)\s+kup\s+za\s+(\d+)',
        r'kupno\s+za\s+(\d+)',
        r'wejd(ę|ź)\s+w\s+(\w+)',
        r'wejście\s+w\s+(\w+)',
        r'wejdźmy\s+w\s+(\w+)',
        r'dokup\s+(\w+)',
        r'dobierz\s+(\w+)',
    ]
    
    # Wzorce dla sprzedaży
    sell_patterns = [
        r'sprzeda[jć]\s+(\w+)',
        r'sprzedaż\s+(\w+)',
        r'sprzedam\s+(\w+)',
        r'(chcę|chciałbym)\s+sprzedać\s+(\w+)',
        r'wyjdź\s+z\s+(\w+)',
        r'wyjście\s+z\s+(\w+)',
        r'wyjdźmy\s+z\s+(\w+)',
        r'zam(knij|knięcie)\s+pozycj[ęi]?\s+(\w+)',
        r'likwidacja\s+pozycji\s+(\w+)',
        r'zlikwiduj\s+pozycj[ęi]?\s+(\w+)',
        r'pozbądź\s+się\s+(\w+)',
        r'sell\s+(\w+)',
    ]
    
    # Wzorce dla sprzedaży z identyfikatorem pozycji (np. BTC HP2)
    position_sell_patterns = [
        r'sprzeda[jć]\s+(\w+\s*\w+\d+)',
        r'sprze[dć]aję?\s+(\w+\s*\w+\d+)',
        r'wypłata\s+z\s+(\w+\s*\w+\d+)',
        r'zamknij\s+(\w+\s*\w+\d+)',
        r'zamkni[ęe]cie\s+(\w+\s*\w+\d+)',
        # Obsługa wzorców typu "sprzedaj HP1", "sprzedaję HP2 z BTC HP", itp.
        r'sprzeda[jć]\s+(\w+\d+)',
        r'sprze[dć]aję?\s+(\w+\d+)',
        r'sprzeda[jć]\s+pozycj[eę]?\s+(\w+\d+)',
    ]
    
    # Wzorce dla stop-limit buy
    stop_limit_buy_patterns = [
        r'(zlecenie|ustaw|ustal)\s+(stop[- ]?limit|limit[- ]?stop)\s+buy\s+(\w+)',
        r'(zlecenie|ustaw|ustal)\s+(stop[- ]?limit|limit[- ]?stop)\s+kupn[aoy]\s+(\w+)',
        r'(zlecenie|ustaw|ustal)\s+kupn[aoy]\s+(stop[- ]?limit|limit[- ]?stop)\s+(\w+)',
    ]
    
    # Wzorce dla stop-limit sell
    stop_limit_sell_patterns = [
        r'(zlecenie|ustaw|ustal)\s+(stop[- ]?limit|limit[- ]?stop)\s+sell\s+(\w+)',
        r'(zlecenie|ustaw|ustal)\s+(stop[- ]?limit|limit[- ]?stop)\s+sprzeda[zż][yżai]\s+(\w+)',
        r'(zlecenie|ustaw|ustal)\s+sprzeda[zż][yżai]\s+(stop[- ]?limit|limit[- ]?stop)\s+(\w+)',
    ]
    
    # Sprawdź wzorce kupna
    for pattern in buy_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę kupna: {message}")
            return True
    
    # Sprawdź wzorce sprzedaży
    for pattern in sell_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę sprzedaży: {message}")
            return True
            
    # Sprawdź wzorce sprzedaży z identyfikatorem pozycji
    for pattern in position_sell_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę sprzedaży z identyfikatorem pozycji: {message}")
            return True
    
    # Sprawdź wzorce stop-limit buy
    for pattern in stop_limit_buy_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę stop-limit buy: {message}")
            return True
    
    # Sprawdź wzorce stop-limit sell
    for pattern in stop_limit_sell_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę stop-limit sell: {message}")
            return True
    
    # Specjalne przypadki
    # Płatność/wpłata w krypto
    if re.search(r'(płat|wpłat)[aąyę]\s+w\s+(\w+)', message_lower):
        print(f"[DEBUG] Wykryto komendę płatności w krypto: {message}")
        return True
    
    # Specjalne frazy z walutą
    for crypto in ['btc', 'eth', 'usdt', 'usdc', 'bnb']:
        # Wzorzec: "za X USDT" - sugeruje kupno lub sprzedaż
        if re.search(rf'za\s+\d+(\.\d+)?\s+{crypto}', message_lower) or re.search(rf'za\s+\d+(\.\d+)?\s+{crypto.upper()}', message):
            print(f"[DEBUG] Wykryto komendę z kwotą w {crypto}: {message}")
            return True
            
        # Wzorzec: "X USDT" na początku zdania - sugeruje kwotę    
        if re.search(rf'^\s*\d+(\.\d+)?\s+{crypto}', message_lower) or re.search(rf'^\s*\d+(\.\d+)?\s+{crypto.upper()}', message):
            print(f"[DEBUG] Wykryto komendę z kwotą w {crypto} na początku: {message}")
            return True
    
    # Dodatkowe wzorce dla formatu "kup mi btc za 100 usdt"
    if re.search(r'kup\s+mi\s+\w+\s+za\s+\d+(\.\d+)?\s+\w+', message_lower):
        print(f"[DEBUG] Wykryto komendę kupna z kwotą: {message}")
        return True
        
    if re.search(r'sprzeda[jć]\s+mi\s+\w+\s+za\s+\d+(\.\d+)?\s+\w+', message_lower):
        print(f"[DEBUG] Wykryto komendę sprzedaży z kwotą: {message}")
        return True
            
    # Sprawdź dodatkowe wzorce bezpośredniego odniesienia do pozycji
    # WAŻNE: Nie wykrywaj jako komendy handlowej, jeśli wiadomość zawiera słowo "alert"
    if not "alert" in message_lower and re.search(r'(hp|pozycj[aą])\s*\d+', message_lower):
        print(f"[DEBUG] Wykryto odniesienie do pozycji HP: {message}")
        return True
    
    return False

def check_alert_command(message):
    """
    Sprawdza, czy wiadomość użytkownika zawiera komendę utworzenia alertu cenowego.
    
    Args:
        message: Wiadomość od użytkownika.
        
    Returns:
        bool: True, jeśli wykryto komendę alertu, False w przeciwnym razie.
    """
    # Normalizacja wiadomości
    message_lower = message.lower()
    
    # Wzorce dla alertów cenowych
    alert_patterns = [
        r'(dodaj|utwórz|stwórz|ustaw|zrób)\s+alert',
        r'alert\s+(cenowy|na|dla)',
        r'(powiadom|informuj)\s+(mnie)?\s+(gdy|kiedy|jeśli|jeżeli)',
        r'(dodaj|utwórz|stwórz|ustaw)\s+powiadomienie',
        r'(ustaw|dodaj|stwórz)\s+alert\s+(dla|na)\s+(\w+)',
        r'(ustaw|dodaj|stwórz)\s+alert\s+(gdy|kiedy|jeśli|jeżeli)',
        r'(powiadom|informuj)\s+mnie\s+o\s+(zmianie|wzroście|spadku)',
        r'(chcę|potrzebuję)\s+(wiedzieć|być\s+powiadomionym)\s+gdy',
        r'(chcę|potrzebuję)\s+alert',
    ]
    
    # Frazy związane z cenami
    price_patterns = [
        r'(cena|wartość)\s+(wzrośnie|spadnie|przekroczy|osiągnie|dojdzie)',
        r'(wzrost|spadek|zmiana)\s+(ceny|wartości|kursu)',
        r'(osiągnie|przekroczy|spadnie\s+do|wzrośnie\s+do)\s+\d',
        r'(wzrośnie|spadnie|zmieni\s+się)\s+o\s+\d+\s*%',
    ]
    
    # Sprawdź wzorce alertów
    for pattern in alert_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę alertu: {message}")
            return True
    
    # Sprawdź kombinacje wzorców alertów i cen
    for a_pattern in alert_patterns:
        for p_pattern in price_patterns:
            if re.search(a_pattern, message_lower) and re.search(p_pattern, message_lower):
                print(f"[DEBUG] Wykryto komendę alertu z ceną: {message}")
                return True
    
    # Specjalne przypadki dla alertów na kryptowaluty
    for crypto in ['btc', 'eth', 'usdt', 'usdc', 'bnb']:
        if re.search(rf'alert\s+(na|dla)\s+{crypto}', message_lower):
            print(f"[DEBUG] Wykryto komendę alertu dla {crypto}: {message}")
            return True
        
        if re.search(rf'(dodaj|utwórz|stwórz|ustaw)\s+alert\s+.*{crypto}', message_lower):
            print(f"[DEBUG] Wykryto komendę alertu z {crypto}: {message}")
            return True
            
        # Wzorzec dla formatu "powiadom mnie gdy btc osiągnie 70000"
        if re.search(rf'(powiadom|informuj)\s+.*\s+{crypto}\s+.*\d', message_lower):
            print(f"[DEBUG] Wykryto komendę alertu z ceną dla {crypto}: {message}")
            return True
    
    # Wzorce dla HP pozycji z alertami
    hp_alert_patterns = [
        r'alert\s+.*\b(hp\d+|hp\s+\d+)\b',
        r'\b(hp\d+|hp\s+\d+)\b\s+.*alert',
        r'(dodaj|utwórz|stwórz|ustaw)\s+alert\s+.*\b(hp\d+|hp\s+\d+)\b',
    ]
    
    for pattern in hp_alert_patterns:
        if re.search(pattern, message_lower):
            print(f"[DEBUG] Wykryto komendę alertu dla pozycji HP: {message}")
            return True
    
    return False

def check_bot_chart_request(user_message):
    """
    Sprawdza, czy użytkownik prosi o wykres dla konkretnego bota i zwraca ID bota.
    """
    # Wzorce do wykrywania ID bota
    patterns = [
        r'bot(?:a|u)?\s+(?:id)?\s*[:#=]?\s*(\d+)',  # bot 123, bota 123, botu 123, bot id 123, bot: 123
        r'(?:id|numer)\s+bot(?:a|u)?\s*[:#=]?\s*(\d+)',  # id bota 123, numer bota: 123
        r'przeanalizuj\s+bot(?:a|u)?\s+(?:id)?\s*[:#=]?\s*(\d+)',  # przeanalizuj bota 123, przeanalizuj bota id 123
        r'(?:bot|bota|botu)\s+(\d+)',  # bot 123, bota 123, botu 123
    ]
    
    # Szukaj dopasowań dla każdego wzorca
    for pattern in patterns:
        matches = re.findall(pattern, user_message.lower())
        if matches:
            print(f"[DEBUG] Znaleziono ID bota: {matches[0]} (wzorzec: {pattern})")
            return matches[0]
    
    # Brak dopasowania
    return None 

def check_bot_analysis_needed(message):
    """
    Sprawdza, czy wiadomość zawiera prośbę o analizę bota.
    """
    message_lower = message.lower()
    
    # Słowa kluczowe sugerujące analizę botów
    keywords = [
        'jak radzi sobie', 'pokaż statystyki', 'przeanalizuj bota', 'analiza bota',
        'jak działa bot', 'statystyki bota', 'wyniki bota', 'performance bota',
        'skuteczność bota', 'efektywność bota', 'jak pracuje bot', 'jak działa grid'
    ]
    
    # Słowa kluczowe związane z botami
    bot_keywords = [
        'bot', 'bota', 'botów', 'botach', 'botami', 'bocie',
        'bnbbot', 'bnbbota', 'bnbbot1', 'bnbbot2', 'grid', 'automat'
    ]
    
    # Sprawdź czy wiadomość zawiera kombinację keywordów i bot_keywords
    has_keywords = any(keyword in message_lower for keyword in keywords)
    has_bot_keywords = any(keyword in message_lower for keyword in bot_keywords)
    
    return has_keywords and has_bot_keywords

def check_alert_command(message):
    """
    Sprawdza, czy wiadomość zawiera komendę utworzenia alertu cenowego
    """
    message_lower = message.lower()
    
    # Słowa kluczowe sugerujące tworzenie alertu
    alert_keywords = [
        'ustaw alert', 'stwórz alert', 'zrób alert', 'dodaj alert',
        'ustaw powiadomienie', 'stwórz powiadomienie', 'powiadom mnie',
        'daj znać gdy', 'alert cenowy', 'poinformuj mnie', 'gdy cena'
    ]
    
    # Sprawdź czy wiadomość zawiera słowa kluczowe alertu
    return any(keyword in message_lower for keyword in alert_keywords)

def check_gt_portfolio_query(message):
    """
    Sprawdza, czy wiadomość zawiera zapytanie o portfel GT
    """
    message_lower = message.lower()
    
    # Słowa kluczowe związane z portfelem GT
    gt_keywords = [
        'portfel gt', 'portfela gt', 'portfelu gt', 'gt portfolio', 
        'mój portfel', 'moje akcje', 'pokaż portfel', 'wyświetl portfel',
        'stan portfela', 'pozycje w portfelu', 'akcje w portfelu',
        'co mam w portfelu', 'jakie mam akcje', 'kategorie portfela'
    ]
    
    # Sprawdź czy wiadomość zawiera słowa kluczowe związane z portfelem GT
    return any(keyword in message_lower for keyword in gt_keywords)

def check_add_stock_position(message):
    """
    Sprawdza, czy wiadomość zawiera żądanie dodania pozycji akcji do portfela GT
    """
    message_lower = message.lower()
    
    # Słowa kluczowe związane z dodawaniem pozycji
    add_position_keywords = [
        'dodaj pozycję', 'dodaj akcje', 'kup akcje', 'dodaj do portfela',
        'nowa pozycja', 'dodaj ticker', 'dodaj spółkę', 'nowa inwestycja',
        'zainwestuj w', 'kup', 'dodaj'
    ]
    
    # Słowa kluczowe związane z tematem akcji/portfela
    stock_keywords = [
        'akcje', 'akcji', 'ticker', 'spółkę', 'spółki', 'portfel', 'portfela',
        'gt', 'pozycję', 'pozycji', 'tsla', 'tesla', 'apple', 'amazon'
    ]
    
    # Sprawdź czy wiadomość zawiera kombinację słów kluczowych
    has_add_keywords = any(keyword in message_lower for keyword in add_position_keywords)
    has_stock_keywords = any(keyword in message_lower for keyword in stock_keywords)
    
    return has_add_keywords and has_stock_keywords

def check_add_price_alert(message):
    """
    Sprawdza, czy wiadomość zawiera żądanie dodania alertu cenowego
    """
    message_lower = message.lower()
    
    # Słowa kluczowe związane z alertami cenowymi
    alert_keywords = [
        'dodaj alert', 'ustaw alert', 'nowy alert', 'alert cenowy', 
        'powiadom gdy', 'powiadomienie o cenie', 'monitoruj cenę',
        'gdy cena spadnie', 'gdy cena wzrośnie', 'alert spadkowy',
        'alert wzrostowy'
    ]
    
    return any(keyword in message_lower for keyword in alert_keywords)