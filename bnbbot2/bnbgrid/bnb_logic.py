# bnbgrid/bnb_logic.py
import threading
import time
from decimal import Decimal
from django.db import close_old_connections
from django.utils import timezone
from django.conf import settings

from .models import BnbBot
from .bnb_manager import get_binance_client, fetch_symbol_price, run_grid_bot

CHECK_INTERVAL = 5  # co ile sekund worker sprawdza boty?


def worker_loop():
    """
    Główna pętla worker-a.
    """
    while True:
        # Zamykanie połączeń DB przed/po pętli (zapobiega "MySQL has gone away" itp.)
        close_old_connections()

        # 1) Pobierz boty w statusie RUNNING
        running_bots = BnbBot.objects.filter(status="RUNNING")

        for bot in running_bots:
            try:
                # 2) Pobierz lv1 z levels_data
                levels_data = bot.get_levels_data()
                lv1_price = Decimal(str(levels_data.get("lv1", "0")))  # domyślnie 0, jeśli brak

                # 3) Pobierz aktualną cenę z Binance
                client = get_binance_client(bot)
                current_price = fetch_symbol_price(client, bot.symbol)

                # 4) Zmieniono logikę: zamiast kończyć gdy cena > lv1, kończymy dopiero gdy cena > lv1 * 1.1
                # Dodatkowo, zamiast bezpośrednio zmieniać status, przekazujemy flagę do run_grid_bot
                if current_price > lv1_price * Decimal("1.1"):
                    print(f"[worker] Bot {bot.id}: cena {current_price} przekroczyła 110% lv1={lv1_price}, zlecam zamknięcie pozycji i zakończenie.")
                    # Przekazujemy flagę close_and_finish=True aby najpierw zamknąć pozycje, potem zmienić status
                    run_grid_bot(bot.id, close_and_finish=True)
                else:
                    # W innym wypadku odpalamy standardową logikę grid-bota
                    run_grid_bot(bot.id)

            except Exception as e:
                # Obsługa wyjątków, żeby w razie błędu worker się nie zatrzymał
                print(f"[worker] Błąd przy obsłudze bota {bot.id}: {e}")

        # Odczekaj ustalony czas
        time.sleep(CHECK_INTERVAL)


def start_bnb_worker():
    """
    Uruchamia wątek worker-a w tle.
    """
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("[start_bnb_worker] Worker wystartował w tle.")





