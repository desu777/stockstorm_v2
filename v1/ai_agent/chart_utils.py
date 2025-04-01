import matplotlib
matplotlib.use('Agg')  # Ustawienie backendu przed importem pyplot
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import base64
import random
import re
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from django.utils import timezone  # Dodaję import timezone z Django

logger = logging.getLogger(__name__)

def generate_test_chart():
    """
    Generuje prosty testowy wykres dla sprawdzenia czy matplotlib działa poprawnie.
    """
    try:
        # Generuj proste dane testowe
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        # Utwórz prosty wykres
        plt.figure(figsize=(10, 6))
        plt.plot(x, y)
        plt.title('Wykres testowy')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.grid(True)
        
        # Zapisz do bufora i zakoduj do base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        print(f"[DEBUG] Wygenerowano testowy wykres o rozmiarze {len(image_base64)} znaków")
        return image_base64
    
    except Exception as e:
        print(f"[DEBUG ERROR] Błąd podczas generowania testowego wykresu: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_example_chart_for_bot(bot_id, bot_name, period_days=365):
    """
    Generuje przykładowy wykres dla konkretnego bota, gdy brak jest rzeczywistych danych.
    
    Args:
        bot_id: ID bota
        bot_name: Nazwa bota (jeśli znana)
        period_days: Okres w dniach
        
    Returns:
        Zakodowany obraz w formacie base64 lub None w przypadku błędu
    """
    try:
        print(f"[DEBUG] Generowanie przykładowego wykresu dla bota {bot_id} ({bot_name})")
        
        # Przygotuj dane
        today = timezone.now()  # Używam timezone.now() zamiast datetime.now()
        dates = []
        profits = []
        
        # Generuj daty (ostatnie 6 miesięcy zamiast 12 dla mniejszej liczby punktów)
        for i in range(6):
            date = today - timedelta(days=(5-i)*30)
            dates.append(date)
        
        # Generuj przykładowe zyski z losowym trendem
        current_profit = 0
        for i in range(6):
            # Losowy ruch zysku w górę lub w dół
            move = (random.random() - 0.45) * 0.01  # Niewielkie wahania 
            current_profit += move
            profits.append(current_profit)
        
        print(f"[DEBUG] Wygenerowano {len(dates)} punktów danych do przykładowego wykresu")
        
        # Utwórz wykres z odpowiednim tłem - mniejsze rozmiary i DPI dla optymalizacji
        plt.figure(figsize=(8, 5), facecolor='#15151f', dpi=80)
        plt.clf()  # Upewnij się, że figura jest czysta
        
        # Konfiguracja subplota
        ax = plt.subplot(111)
        ax.set_facecolor('#1a1a27')
        
        # Wykreśl dane
        plt.plot(dates, profits, marker='o', linestyle='-', color='#7209b7', linewidth=2, markersize=5)
        
        # Formatowanie - mniejsze rozmiary fontów dla optymalizacji
        plt.title(f"Przykładowy wykres zysków dla bota {bot_name} (ID: {bot_id})", fontsize=14, color='white', pad=15)
        plt.xlabel('Data', fontsize=10, color='white', labelpad=8)
        plt.ylabel('Zysk (USDT)', fontsize=10, color='white', labelpad=8)
        
        # Linie siatki
        plt.grid(True, linestyle='--', linewidth=0.5, color='#444444', alpha=0.3)
        
        # Formatowanie osi
        plt.tick_params(axis='both', colors='white', labelsize=9)
        
        # Formatowanie dat na osi X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45)
        
        # Formatowanie krawędzi wykresu
        for spine in ax.spines.values():
            spine.set_color('#444444')
            
        # Notatka na wykresie o przykładowych danych
        plt.figtext(0.5, 0.01, "Uwaga: Wykres zawiera przykładowe dane", 
                  ha='center', color='#ff9999', fontsize=8)
            
        # Dopasowanie wykresu
        plt.tight_layout()
        
        # Zapisz wykres do bufora w pamięci z optymalizacją
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight', transparent=False)
        buffer.seek(0)
        
        # Koduj do base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        print(f"[DEBUG] Wygenerowano przykładowy wykres o rozmiarze {len(image_base64)} znaków base64")
        plt.close()  # Zamknij figurę, aby zwolnić pamięć
        
        return image_base64
        
    except Exception as e:
        print(f"[DEBUG ERROR] Wyjątek podczas generowania przykładowego wykresu dla bota {bot_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # W przypadku awarii, spróbuj wygenerować jeszcze prostszy wykres
        try:
            print(f"[DEBUG] Próba wygenerowania prostego wykresu awaryjnego")
            plt.figure(figsize=(8, 5), facecolor='#15151f', dpi=80)
            plt.clf()
            ax = plt.subplot(111)
            ax.set_facecolor('#1a1a27')
            
            # Bardzo proste dane - tylko dwa punkty
            simple_dates = [timezone.now() - timedelta(days=30), timezone.now()]
            simple_profits = [0, 0.01]  # Minimalny zysk
            
            plt.plot(simple_dates, simple_profits, marker='o', linestyle='-', color='#7209b7', linewidth=2, markersize=5)
            plt.title(f"Wykres awaryjny dla bota {bot_name} (ID: {bot_id})", fontsize=14, color='white', pad=15)
            plt.xlabel('Data', fontsize=10, color='white', labelpad=8)
            plt.ylabel('Zysk (USDT)', fontsize=10, color='white', labelpad=8)
            plt.grid(True, linestyle='--', linewidth=0.5, color='#444444', alpha=0.3)
            plt.tick_params(axis='both', colors='white', labelsize=9)
            
            # Formatowanie dat na osi X
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            plt.xticks(rotation=45)
            
            # Notatka
            plt.figtext(0.5, 0.01, "Dane niedostępne - wykres awaryjny", ha='center', color='#ff9999', fontsize=8)
            
            plt.tight_layout()
            
            # Zapisz wykres do bufora w pamięci z optymalizacją
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight', transparent=False)
            buffer.seek(0)
            
            # Koduj do base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            print(f"[DEBUG] Wygenerowano awaryjny wykres o rozmiarze {len(image_base64)} znaków base64")
            return image_base64
            
        except Exception as fallback_error:
            print(f"[DEBUG ERROR] Nawet awaryjny wykres nie mógł zostać wygenerowany: {fallback_error}")
            return None

def generate_profit_chart(data, period_days=365, strategy_filter=None, title=None):
    """
    Generuje wykres zysków na podstawie dostarczonych danych.
    """
    try:
        if not data or not data.get("data"):
            print("[DEBUG] Brak danych do wygenerowania wykresu")
            return generate_example_chart_for_bot("unknown", "Brak danych", period_days)
            
        # Ekstrakcja ID bota z tytułu (jeśli jest)
        bot_id = None
        if title:
            match = re.search(r'ID:\s*(\d+)', title)
            if match:
                bot_id = match.group(1)
                print(f"[DEBUG] Wykryto ID bota z tytułu: {bot_id}")
        
        # Ustal tytuł wykresu
        if title:
            chart_title = title
        elif strategy_filter == 'rei':
            chart_title = "Zyski strategii 5-10-15rei (z reinwestycją)"
        elif strategy_filter == 'no_rei':
            chart_title = "Zyski strategii 5-10-15 (bez reinwestycji)"
        else:
            chart_title = "Zyski wszystkich botów"
        
        # Konwertuj dane do odpowiedniego formatu
        raw_data = data["data"]
        print(f"[DEBUG] Przygotowuję dane do wykresu, {len(raw_data)} punktów")
        
        # Upewnij się, że cutoff_date jest datą bez informacji o strefie czasowej (naive datetime)
        # aby uniknąć problemu porównywania offset-naive i offset-aware datetimes
        cutoff_date = timezone.now().replace(tzinfo=None) - timedelta(days=period_days)
        print(f"[DEBUG] Data graniczna: {cutoff_date} (typ: {type(cutoff_date)})")
        
        # Filtruj dane do zakresu czasowego z konwersją do tego samego formatu dat
        filtered_data = []
        for item in raw_data:
            try:
                # Parsuj datę z tekstu i zapewnij, że jest w formacie naive datetime
                item_date_str = item.get("date", "2020-01-01")
                item_date = datetime.strptime(item_date_str, "%Y-%m-%d").replace(tzinfo=None)
                
                # Porównuj tylko daty bez informacji o strefie czasowej
                if item_date >= cutoff_date:
                    filtered_data.append(item)
            except Exception as e:
                print(f"[DEBUG] Błąd podczas parsowania daty {item.get('date')}: {e}")
                continue
        
        print(f"[DEBUG] Filtrowanie: pozostało {len(filtered_data)} punktów po filtracji daty")
        
        # Filtrowanie danych dla konkretnego bota
        if bot_id:
            print(f"[DEBUG] Filtrowanie dla konkretnego bota: ID={bot_id}")
            
            # Najpierw sprawdź, czy mamy dokładne dopasowanie dla bot_id
            exact_match = [item for item in filtered_data if str(item.get("bot_id")) == str(bot_id)]
            
            if exact_match:
                filtered_data = exact_match
                print(f"[DEBUG] Filtrowanie: znaleziono {len(filtered_data)} punktów dla bot_id={bot_id}")
            else:
                # Następnie sprawdź, czy mamy dopasowanie dla microservice_bot_id
                microservice_match = [item for item in filtered_data if str(item.get("microservice_bot_id", "")) == str(bot_id)]
                if microservice_match:
                    filtered_data = microservice_match
                    print(f"[DEBUG] Filtrowanie: znaleziono {len(filtered_data)} punktów dla microservice_bot_id={bot_id}")
                else:
                    # Na koniec sprawdź, czy mamy dopasowanie dla local_bot_id
                    local_match = [item for item in filtered_data if str(item.get("local_bot_id", "")) == str(bot_id)]
                    if local_match:
                        filtered_data = local_match
                        print(f"[DEBUG] Filtrowanie: znaleziono {len(filtered_data)} punktów dla local_bot_id={bot_id}")
                    else:
                        # Ostatnia szansa - sprawdź, czy bot_id jest częścią oryginalnego ID bota
                        # To dla przypadków, gdy mapowanie jest niepełne
                        print(f"[DEBUG] Filtrowanie: nie znaleziono bezpośrednich dopasowań dla bota {bot_id}, szukam w danych oryginalnych")
                        
                        # Sprawdź, czy bot_id jest częścią oryginalnych danych
                        if data.get("summary") and data["summary"].get("original_bot_id"):
                            original_id = str(data["summary"]["original_bot_id"])
                            if original_id == str(bot_id):
                                print(f"[DEBUG] Filtrowanie: bot_id={bot_id} pasuje do original_bot_id w summary")
                                
                                # Jeśli mamy microservice_bot_id w summary, użyj go do filtrowania
                                if data["summary"].get("microservice_bot_id"):
                                    ms_id = str(data["summary"]["microservice_bot_id"])
                                    ms_match = [item for item in filtered_data if str(item.get("bot_id")) == ms_id]
                                    if ms_match:
                                        filtered_data = ms_match
                                        print(f"[DEBUG] Filtrowanie: znaleziono {len(filtered_data)} punktów dla summary.microservice_bot_id={ms_id}")
                                    else:
                                        print(f"[DEBUG] Filtrowanie: nie znaleziono danych dla bota {bot_id}")
                                else:
                                    print(f"[DEBUG] Filtrowanie: brak microservice_bot_id w summary")
                            else:
                                print(f"[DEBUG] Filtrowanie: bot_id={bot_id} nie pasuje do original_bot_id={original_id}")
                        else:
                            print(f"[DEBUG] Filtrowanie: brak original_bot_id w summary")
            
            if not filtered_data:
                print(f"[DEBUG] Filtrowanie: nie znaleziono żadnych danych dla bota {bot_id} po próbach wszystkich metod filtrowania")
        
        # Filtrowanie dla konkretnej strategii, jeśli podano
        if strategy_filter:
            if strategy_filter == 'rei':
                filtered_data = [item for item in filtered_data if 'rei' in item.get("bot_name", "").lower()]
                print(f"[DEBUG] Filtrowanie: pozostało {len(filtered_data)} punktów dla strategii REI")
            elif strategy_filter == 'no_rei':
                filtered_data = [item for item in filtered_data if 'rei' not in item.get("bot_name", "").lower()]
                print(f"[DEBUG] Filtrowanie: pozostało {len(filtered_data)} punktów dla strategii NO-REI")
        
        # Sprawdź, czy po filtrowaniu mamy jakiekolwiek dane
        if not filtered_data:
            print("[DEBUG] Brak danych po filtrowaniu")
            return generate_example_chart_for_bot(bot_id or "unknown", title or "Bot", period_days)
        
        # Przygotuj dane do wykresu
        dates = []
        profits = []
        bots = {}
        
        for item in filtered_data:
            try:
                # Parsuj datę z obsługą błędów
                date = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=None)
                profit = item["profit"]
                bot_id = item.get("bot_id", "unknown")
                bot_name = item.get("bot_name", "Bot")
                
                dates.append(date)
                profits.append(profit)
                
                # Grupuj dane według botów
                if bot_id not in bots:
                    bots[bot_id] = {
                        "name": bot_name,
                        "dates": [date],
                        "profits": [profit]
                    }
                else:
                    bots[bot_id]["dates"].append(date)
                    bots[bot_id]["profits"].append(profit)
            except Exception as e:
                print(f"[DEBUG] Błąd podczas przetwarzania elementu danych: {e}, Element: {item}")
                continue
        
        # Sprawdź czy mamy wystarczająco danych do wykresu
        total_points = len(dates)
        if total_points == 0:
            print("[DEBUG] Brak punktów danych po filtrowaniu")
            return generate_example_chart_for_bot(bot_id or "unknown", title or "Bot", period_days)
            
        print(f"[DEBUG] Przygotowano {total_points} punktów danych do wykresu")
        
        # Gdy mamy tylko jeden punkt danych, dodaj dodatkowy punkt dla lepszej wizualizacji
        if total_points == 1:
            print(f"[DEBUG] Wykryto tylko jeden punkt danych ({dates[0]}, {profits[0]}). Dodaję dodatkowy punkt dla lepszej wizualizacji")
            # Dodaj punkt dzień wcześniej z wartością 0 dla lepszej wizualizacji
            dates.insert(0, dates[0] - timedelta(days=1))
            profits.insert(0, 0)
            
            # Zaktualizuj również dane dla botów
            for bot_id, bot_data in bots.items():
                if len(bot_data["dates"]) == 1:
                    bot_data["dates"].insert(0, bot_data["dates"][0] - timedelta(days=1))
                    bot_data["profits"].insert(0, 0)
                    print(f"[DEBUG] Dodano punkt dla bota {bot_id}: ({bot_data['dates'][0]}, {bot_data['profits'][0]})")
        
        # Inicjalizuj zmienną przed jej użyciem
        total_profits_by_date = {}
        
        # Sumuj zyski dla wszystkich botów na każdy dzień - tylko jeśli mamy wiele botów
        if len(bots) > 1:
            print(f"[DEBUG] Sumowanie zysków dla {len(bots)} botów")
            all_dates = set()
            for bot_id, bot_data in bots.items():
                all_dates.update(bot_data["dates"])
            
            # Sortuj daty
            all_dates = sorted(list(all_dates))
            
            # Przygotuj zsumowane dane 
            for date in all_dates:
                total_profit = 0
                for bot_id, bot_data in bots.items():
                    # Znajdź najbliższą datę w danych bota
                    for i, bot_date in enumerate(bot_data["dates"]):
                        if bot_date == date:
                            total_profit += bot_data["profits"][i]
                            break
                total_profits_by_date[date] = total_profit
        
        # Kompletnie nowe podejście do generowania wykresu - optymalizacja dla mniejszego rozmiaru
        plt.figure(figsize=(8, 5), facecolor='#15151f', dpi=80)  # Zmniejszona wielkość i DPI
        plt.clf()  # Wyczyść figurę na wszelki wypadek
        
        # Konfiguracja subplota 
        ax = plt.subplot(111)
        ax.set_facecolor('#1a1a27')
        
        # Wybierz kolor w zależności od strategii
        if strategy_filter == 'rei':
            line_color = '#7209b7'  # Fioletowy dla strategii z reinwestycją
        elif strategy_filter == 'no_rei':
            line_color = '#4361ee'  # Niebieski dla strategii bez reinwestycji
        else:
            line_color = '#8a2be2'  # Domyślny fiolet
        
        # Rysuj wykres z punktami - użyj danych zsumowanych jeśli są dostępne
        if total_profits_by_date and len(total_profits_by_date) > 0:
            chart_dates = sorted(total_profits_by_date.keys())
            chart_profits = [total_profits_by_date[date] for date in chart_dates]
            plt.plot(chart_dates, chart_profits, marker='o', linestyle='-', color=line_color, linewidth=2, markersize=5)
            print(f"[DEBUG] Narysowano wykres z {len(chart_dates)} punktami zsumowanymi")
        else:
            # Użyj oryginalnych danych jeśli zsumowane nie są dostępne
            plt.plot(dates, profits, marker='o', linestyle='-', color=line_color, linewidth=2, markersize=5)
            print(f"[DEBUG] Narysowano wykres z {len(dates)} punktami oryginalnymi")
        
        # Formatowanie
        plt.title(chart_title, fontsize=14, color='white', pad=15)
        plt.xlabel('Data', fontsize=10, color='white', labelpad=8)
        plt.ylabel('Zysk (USDT)', fontsize=10, color='white', labelpad=8)
        
        # Linie siatki
        plt.grid(True, linestyle='--', linewidth=0.5, color='#444444', alpha=0.3)
        
        # Formatowanie osi
        plt.tick_params(axis='both', colors='white', labelsize=9)
        
        # Formatowanie dat na osi X - pokazuj nazwy miesięcy
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))  # Format miesiąc rok
        ax.xaxis.set_major_locator(mdates.MonthLocator())  # Pokaż znaczniki co miesiąc
        plt.xticks(rotation=45)  # Obróć etykiety, aby się nie nakładały
        
        # Formatowanie krawędzi wykresu
        for spine in ax.spines.values():
            spine.set_color('#444444')
            
        # Dopasowanie wykresu
        plt.tight_layout()
        
        # Zapisz wykres do bufora w pamięci z większą kompresją
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight', transparent=False)
        buffer.seek(0)
        plt.close()  # Zamknij figurę, aby zwolnić pamięć
        
        # Koduj do base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        print(f"[DEBUG] Wygenerowano wykres o rozmiarze {len(image_base64)} znaków base64")
        
        return image_base64
        
    except Exception as e:
        print(f"[DEBUG ERROR] Wyjątek podczas generowania wykresu: {e}")
        import traceback
        traceback.print_exc()
        return generate_example_chart_for_bot(bot_id or "unknown", title or "Bot", period_days) 

def generate_simple_chart(dates, values, title="Chart", x_label="Date", y_label="Value", figsize=(6, 3), dpi=72):
    """
    Generuje prosty wykres liniowy na podstawie dostarczonych dat i wartości.
    Mocno zoptymalizowana wersja z minimalnymi elementami dla szybszego generowania.
    
    Args:
        dates: lista dat (w formacie str lub datetime)
        values: lista wartości liczbowych
        title: tytuł wykresu
        x_label: etykieta osi X
        y_label: etykieta osi Y
        figsize: rozmiar wykresu (szerokość, wysokość) w calach
        dpi: rozdzielczość wykresu (dots per inch)
        
    Returns:
        String base64 z zakodowanym obrazem wykresu lub None w przypadku błędu
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from io import BytesIO
        import base64
        from datetime import datetime
        import numpy as np
        
        # Konwersja dat na obiekty datetime jeśli są stringami
        if dates and isinstance(dates[0], str):
            try:
                dates = [datetime.strptime(date, "%Y-%m-%d") for date in dates]
            except:
                try:
                    dates = [datetime.strptime(date, "%Y-%m-%d %H:%M:%S") for date in dates]
                except:
                    pass
                    
        # Jeśli mamy tylko jeden punkt danych, dodajemy drugi punkt dla lepszej wizualizacji
        if len(dates) == 1:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Wykryto tylko jeden punkt danych w generate_simple_chart. Dodanie pomocniczego punktu")
            from datetime import timedelta
            # Dodaj punkt dzień wcześniej
            dates.insert(0, dates[0] - timedelta(days=1))
            values.insert(0, 0)  # Rozpocznij od 0
                    
        # Próbkowanie danych jeśli jest ich zbyt dużo (powyżej 30 punktów)
        if len(dates) > 30:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Próbkowanie danych z {len(dates)} do 30 punktów")
            
            # Wybierz równomiernie rozłożone punkty
            indices = np.linspace(0, len(dates) - 1, 30).astype(int)
            dates = [dates[i] for i in indices]
            values = [values[i] for i in indices]
        
        # Utworzenie wykresu z minimalnym stylem
        plt.figure(figsize=figsize, dpi=dpi)
        plt.rcParams['font.size'] = 8  # Mniejsza czcionka globalna
        
        # Prostszy wykres z cieńszą linią i bez markerów
        plt.plot(dates, values, linestyle='-', color='#1f77b4', linewidth=1.5)
        
        # Dodanie tytułu i etykiet z mniejszymi fontami
        plt.title(title, fontsize=10)
        plt.xlabel(x_label, fontsize=8)
        plt.ylabel(y_label, fontsize=8)
        
        # Formatowanie osi X (daty) - minimalne
        date_format = '%m/%d' if len(dates) <= 10 else '%m/%y'
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        plt.xticks(rotation=45, fontsize=7)
        plt.yticks(fontsize=7)
        
        # Lżejsza siatka
        plt.grid(True, linestyle=':', alpha=0.3)
        
        # Dopasowanie układu z minimalnymi marginesami
        plt.tight_layout(pad=0.5)
        
        # Zapisanie wykresu do bufora pamięci jako JPEG (bez argumentu quality)
        buffer = BytesIO()
        plt.savefig(buffer, format='jpeg', dpi=dpi, bbox_inches='tight')
        plt.close()
        
        # Konwersja do base64
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Log wielkości obrazu
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Wygenerowano wykres o rozmiarze {len(image_base64)} znaków base64")
        
        return image_base64
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Błąd podczas generowania prostego wykresu: {str(e)}")
        return None

def example_chart():
    """Generuje przykładowy wykres do testów - zoptymalizowana wersja"""
    import datetime
    
    # Przykładowe dane - mniej punktów
    today = datetime.datetime.now()
    dates = [today - datetime.timedelta(days=x*10) for x in range(6, 0, -1)]
    values = [10, 15, 20, 18, 25, 30]
    
    return generate_simple_chart(
        dates, 
        values, 
        title="Przykładowy wykres", 
        x_label="Data", 
        y_label="Wartość"
    )

def generate_bot_profit_chart(profit_data, bot_id, bot_name):
    """
    Generuje wykres zysków dla konkretnego bota na podstawie jego danych.
    
    Args:
        profit_data: dane o zyskach bota (format z API mikrousługi)
        bot_id: ID bota
        bot_name: nazwa bota
        
    Returns:
        String base64 z zakodowanym obrazem wykresu lub None w przypadku błędu
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Sprawdzenie czy mamy dane
    if not profit_data or not profit_data.get("data"):
        logger.debug(f"Brak danych o zyskach dla bota {bot_id}, generuję minimalny przykładowy wykres")
        from datetime import datetime, timedelta
        # Generuj bardzo proste dane przykładowe
        dates = [datetime.now() - timedelta(days=30), datetime.now()]
        values = [0, 0.01]
        return generate_minimal_chart(dates, values, f"Przykładowy wykres - Bot {bot_id}")
    
    data_points = profit_data.get("data", [])
    logger.debug(f"Przygotowanie {len(data_points)} punktów danych do wykresu dla bota {bot_id}")
    
    if not data_points:
        logger.debug(f"Brak punktów danych dla bota {bot_id}, generuję minimalny przykładowy wykres")
        from datetime import datetime, timedelta
        dates = [datetime.now() - timedelta(days=30), datetime.now()]
        values = [0, 0.01]
        return generate_minimal_chart(dates, values, f"Przykładowy wykres - Bot {bot_id}")
    
    try:
        # Przygotowanie danych
        dates = []
        profits = []
        
        # Filtrowanie danych tylko dla tego bota
        for point in data_points:
            point_bot_id = str(point.get("bot_id", "")) or str(point.get("local_bot_id", "")) or str(point.get("microservice_bot_id", ""))
            
            # Jeśli dane punktu pasują do wybranego bota, dodaj je
            if point_bot_id == str(bot_id):
                date_str = point.get("date")
                profit = point.get("profit", 0)
                
                if date_str:
                    from datetime import datetime
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        dates.append(date)
                        profits.append(profit)
                    except:
                        logger.warning(f"Niepoprawny format daty: {date_str}")
        
        # Sprawdź czy mamy wystarczająco danych po filtrowaniu dla tego bota
        if len(dates) < 1:
            logger.debug(f"Za mało punktów danych dla bota {bot_id} po filtrowaniu, generuję minimalny przykładowy wykres")
            from datetime import datetime, timedelta
            dates = [datetime.now() - timedelta(days=30), datetime.now()]
            values = [0, 0.01]
            return generate_minimal_chart(dates, values, f"Brak danych - Bot {bot_id}")
        
        # Generuj wykres - użyj ultra-lekkiego wykresu dla maksymalnej wydajności
        title = f"Zyski: {bot_name}"
        
        return generate_minimal_chart(dates, profits, title)
    
    except Exception as e:
        logger.error(f"Błąd podczas generowania wykresu zysków dla bota {bot_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # W przypadku błędu generujemy minimalny przykładowy wykres
        try:
            from datetime import datetime, timedelta
            dates = [datetime.now() - timedelta(days=30), datetime.now()]
            values = [0, 0.01]
            return generate_minimal_chart(dates, values, f"Wykres awaryjny - Bot {bot_id}")
        except:
            return None

def generate_example_chart():
    """Generuje przykładowy wykres do wyświetlenia gdy nie ma danych"""
    import datetime
    import random
    
    # Przykładowe dane dla ostatnich 6 miesięcy
    today = datetime.datetime.now()
    dates = [today - datetime.timedelta(days=30*x) for x in range(6, 0, -1)]
    
    # Generujemy wartości pokazujące wzrost
    start_value = random.uniform(1000, 2000)
    values = [start_value]
    
    for i in range(1, 6):
        change = random.uniform(-0.05, 0.1)  # -5% do +10%
        values.append(values[-1] * (1 + change))
    
    return generate_simple_chart(
        dates, 
        values, 
        title="Przykładowy wykres zysków", 
        x_label="Data", 
        y_label="Zysk"
    )

def generate_minimal_chart(dates, values, title="Chart"):
    """
    Generuje absolutnie minimalny wykres liniowy.
    Funkcja zoptymalizowana pod kątem maksymalnej wydajności i minimalnego rozmiaru.
    Usuwa wszystkie zbędne elementy (etykiety, siatkę, legendę).
    
    Args:
        dates: lista dat
        values: lista wartości
        title: tytuł wykresu (opcjonalny)
        
    Returns:
        String base64 z zakodowanym obrazem wykresu
    """
    try:
        import matplotlib.pyplot as plt
        from io import BytesIO
        import base64
        import numpy as np
        from datetime import datetime
        import logging
        logger = logging.getLogger(__name__)
        
        # Konwersja dat do datetime jeśli to stringi
        if dates and isinstance(dates[0], str):
            try:
                dates = [datetime.strptime(date, "%Y-%m-%d") for date in dates]
            except:
                pass
        
        # Jeśli mamy tylko jeden punkt danych, dodajemy drugi punkt dla lepszej wizualizacji
        if len(dates) == 1:
            logger.debug(f"Wykryto tylko jeden punkt danych. Dodanie pomocniczego punktu")
            from datetime import timedelta
            # Dodaj punkt dzień wcześniej
            dates.insert(0, dates[0] - timedelta(days=1))
            values.insert(0, 0)  # Rozpocznij od 0
            
        # Próbkowanie do maksymalnie 15 punktów
        if len(dates) > 15:
            indices = np.linspace(0, len(dates) - 1, 15).astype(int)
            dates = [dates[i] for i in indices]
            values = [values[i] for i in indices]
        
        # Tworzenie maksymalnie uproszczonego wykresu
        plt.figure(figsize=(4, 2), dpi=60)
        
        # Wyłączenie wielu elementów dla zmniejszenia rozmiaru
        plt.box(False)  # Usunięcie ramki
        plt.xticks([])  # Usunięcie etykiet osi X
        plt.yticks([])  # Usunięcie etykiet osi Y
        
        # Prosty wykres liniowy bez dodatkowych elementów
        plt.plot(dates, values, linewidth=1, color='blue')
        
        # Tylko tytuł - opcjonalnie
        if title:
            plt.title(title, fontsize=8, pad=2)
        
        # Maksymalne zredukowanie marginesów
        plt.tight_layout(pad=0.1)
        
        # Zapisanie jako JPEG bez argumentu quality
        buffer = BytesIO()
        plt.savefig(buffer, format='jpeg', dpi=60, 
                   bbox_inches='tight', pad_inches=0.0)
        plt.close()
        
        # Konwersja do base64
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return image_base64
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Błąd podczas generowania minimalnego wykresu: {str(e)}")
        
        # W przypadku błędu zwracamy jeszcze prostszy wykres statyczny
        try:
            plt.figure(figsize=(3, 2), dpi=50)
            plt.box(False)
            plt.xticks([])
            plt.yticks([])
            plt.plot([0, 1], [0, 1], 'b-')
            if title:
                plt.title(title, fontsize=7)
            
            buffer = BytesIO()
            plt.savefig(buffer, format='jpeg', dpi=50)
            plt.close()
            
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except:
            return None

def generate_bot_chartjs(profit_data, bot_id, bot_name=None):
    """
    Generuje dane Chart.js dla wykresu zysków bota.
    
    Args:
        profit_data: dane o zyskach bota (format z API mikrousługi)
        bot_id: ID bota
        bot_name: nazwa bota (opcjonalna)
        
    Returns:
        Dict z danymi do renderowania wykresu Chart.js
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Sprawdzenie czy mamy dane
    if not profit_data or not profit_data.get("data"):
        logger.debug(f"Brak danych o zyskach dla bota {bot_id}, generuję przykładowy wykres")
        return example_chartjs()
    
    data_points = profit_data.get("data", [])
    logger.debug(f"Przygotowanie {len(data_points)} punktów danych do wykresu dla bota {bot_id}")
    
    if not data_points:
        logger.debug(f"Brak punktów danych dla bota {bot_id}, generuję przykładowy wykres")
        return example_chartjs()
    
    try:
        # Przygotowanie danych
        dates = []
        profits = []
        
        # Filtrowanie danych tylko dla tego bota
        for point in data_points:
            point_bot_id = str(point.get("bot_id", "")) or str(point.get("local_bot_id", "")) or str(point.get("microservice_bot_id", ""))
            
            # Jeśli dane punktu pasują do wybranego bota, dodaj je
            if point_bot_id == str(bot_id):
                date_str = point.get("date")
                profit = point.get("profit", 0)
                
                if date_str:
                    from datetime import datetime
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        dates.append(date)
                        profits.append(profit)
                    except:
                        logger.warning(f"Niepoprawny format daty: {date_str}")
        
        # Sprawdź czy mamy wystarczająco danych po filtrowaniu dla tego bota
        if len(dates) < 1:
            logger.debug(f"Za mało punktów danych dla bota {bot_id} po filtrowaniu, generuję przykładowy wykres")
            return example_chartjs()
        
        # Generuj wykres - przygotuj dane dla Chart.js
        title = f"Zyski: {bot_name or f'Bot {bot_id}'}"
        
        return generate_chartjs_code(dates, profits, title=title, y_label="Zysk")
    
    except Exception as e:
        logger.error(f"Błąd podczas generowania danych wykresu dla bota {bot_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # W przypadku błędu generujemy przykładowy wykres
        return example_chartjs()

def generate_profit_chartjs(profit_data, strategy_filter=None, title=None):
    """
    Generuje dane Chart.js dla wykresu ogólnych zysków wszystkich botów.
    
    Args:
        profit_data: dane o zyskach (format z API mikrousługi)
        strategy_filter: opcjonalny filtr dla strategii
        title: opcjonalny tytuł wykresu
        
    Returns:
        Dict z danymi do renderowania wykresu Chart.js
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if not profit_data or not profit_data.get("data"):
            logger.debug("Brak danych o zyskach, generuję przykładowy wykres")
            return example_chartjs()
            
        # Ustaw tytuł wykresu
        chart_title = title if title else "Zyski portfela"
        if strategy_filter:
            chart_title = f"{chart_title} - Strategia: {strategy_filter}"
            
        # Inicjalizujemy słownik do przechowywania sumy zysków wg dat
        total_profits_by_date = {}
        
        # Sumujemy zyski dla wszystkich botów dla każdej daty
        if profit_data.get("data"):
            for item in profit_data.get("data"):
                # Sprawdź filtr strategii jeśli podano
                if strategy_filter and item.get("strategy") != strategy_filter:
                    continue
                    
                date_str = item.get("date")
                profit = item.get("profit", 0)
                
                if date_str:
                    # Dodaj zysk do sumy dla danej daty
                    if date_str in total_profits_by_date:
                        total_profits_by_date[date_str] += profit
                    else:
                        total_profits_by_date[date_str] = profit
        
        # Jeśli nie znaleźliśmy żadnych danych pasujących do filtra
        if not total_profits_by_date:
            logger.debug(f"Brak danych o zyskach dla filtra strategii: {strategy_filter}, generuję przykładowy wykres")
            return example_chartjs()
            
        # Sortujemy daty
        sorted_dates = sorted(total_profits_by_date.keys())
        profits = [total_profits_by_date[date] for date in sorted_dates]
        
        # Generujemy dane dla Chart.js
        return generate_chartjs_code(sorted_dates, profits, title=chart_title, y_label="Zysk")
        
    except Exception as e:
        logger.error(f"Błąd podczas generowania danych wykresu zysków: {str(e)}")
        # W przypadku błędu generujemy przykładowy wykres
        return example_chartjs()

def example_chartjs():
    """
    Generuje przykładowe dane do wykresu Chart.js
    
    Returns:
        Dict z danymi do renderowania przykładowego wykresu Chart.js
    """
    dates = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]
    values = [10, 45, 30, 60, 25, 50]
    
    return generate_chartjs_code(dates, values, title="Przykładowy wykres zysków")

def generate_chartjs_code(dates, values, title='Wykres', x_label='Data', y_label='Wartość', color='#4361ee'):
    """
    Generuje dane do wykresu Chart.js
    
    Args:
        dates: lista dat (stringi lub obiekty datetime)
        values: lista wartości
        title: tytuł wykresu
        x_label: etykieta osi X
        y_label: etykieta osi Y
        color: kolor głównej linii wykresu
        
    Returns:
        Dict z danymi do renderowania wykresu Chart.js
    """
    # Formatowanie dat (jeśli są to obiekty datetime)
    formatted_dates = []
    for date in dates:
        if hasattr(date, 'strftime'):
            # To jest obiekt datetime
            formatted_dates.append(date.strftime('%Y-%m-%d'))
        else:
            # To jest już string
            formatted_dates.append(str(date))
    
    # Tworzenie danych do Chart.js
    return {
        'labels': formatted_dates,
        'datasets': [
            {
                'label': title,
                'data': values,
                'borderColor': color,
                'backgroundColor': f'{color}20', # Kolor z 12.5% przezroczystości
                'borderWidth': 2,
                'pointRadius': 3,
                'pointBackgroundColor': color,
                'tension': 0.1,
                'fill': True
            }
        ]
    } 