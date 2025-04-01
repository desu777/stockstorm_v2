"""
Moduł gt_portfolio_management.py do zarządzania portfelem GT przez AI agenta.

Funkcje:
- Wyświetlanie pozycji i kategorii z portfela GT
- Dodawanie nowych pozycji do portfela GT
- Tworzenie alertów cenowych dla pozycji w portfelu GT
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# Import własnego enkodera JSON dla obsługi obiektów Decimal
try:
    from .services import DecimalJSONEncoder
    import json
except ImportError:
    # Definiujemy własną klasę w przypadku importu cyklicznego
    import json
    class DecimalJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return super(DecimalJSONEncoder, self).default(obj)

# Importy modeli zostały usunięte z tego miejsca i przeniesione do funkcji

logger = logging.getLogger(__name__)

def get_gt_portfolio(user_id):
    """
    Pobiera wszystkie kategorie i pozycje z portfela GT użytkownika.
    
    Args:
        user_id (int): ID użytkownika
        
    Returns:
        dict: Dane o portfelu GT w formacie:
        {
            'success': bool,
            'message': str,
            'portfolio': {
                'categories': [
                    {
                        'id': int,
                        'name': str,
                        'positions': [
                            {
                                'id': int,
                                'ticker': str,
                                'quantity': Decimal,
                                'entry_price': Decimal,
                                'current_price': Decimal,
                                'profit_loss_percent': Decimal,
                                'profit_loss_dollar': Decimal,
                                'notes': str,
                                'alerts': [
                                    {
                                        'id': int,
                                        'alert_type': str,
                                        'threshold_value': Decimal,
                                        'status': str,
                                        'is_active': bool,
                                        'triggered': bool,
                                        'notes': str
                                    }
                                ]
                            }
                        ]
                    }
                ],
                'summary': {
                    'total_positions': int,
                    'total_categories': int,
                    'total_value': Decimal,
                    'total_profit_loss': Decimal,
                    'profit_loss_percent': Decimal
                }
            }
        }
    """
    try:
        # Importy modeli wewnątrz funkcji
        from django.contrib.auth.models import User
        from gt.models import GTCategory, StockPosition, StockPriceAlert
        
        # Pobierz użytkownika
        user = User.objects.get(id=user_id)
        
        # Pobierz wszystkie kategorie użytkownika
        categories = GTCategory.objects.filter(user=user).prefetch_related('positions', 'positions__alerts')
        
        if not categories.exists():
            return {
                'success': True,
                'message': 'Nie znaleziono kategorii w portfelu GT.',
                'portfolio': {
                    'categories': [],
                    'summary': {
                        'total_positions': 0,
                        'total_categories': 0,
                        'total_value': Decimal('0'),
                        'total_profit_loss': Decimal('0'),
                        'profit_loss_percent': Decimal('0')
                    }
                }
            }
        
        # Przygotuj strukturę danych
        portfolio_data = {
            'categories': [],
            'summary': {
                'total_positions': 0,
                'total_categories': 0,
                'total_value': Decimal('0'),
                'total_profit_loss': Decimal('0')
            }
        }
        
        # Pobierz dane dla każdej kategorii
        for category in categories:
            category_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'positions': []
            }
            
            # Pobierz pozycje w kategorii
            positions = StockPosition.objects.filter(category=category, exit_date__isnull=True)
            
            for position in positions:
                # Dane alertów dla pozycji
                alerts_data = []
                for alert in position.alerts.all():
                    alerts_data.append({
                        'id': alert.id,
                        'alert_type': alert.alert_type,
                        'threshold_value': alert.threshold_value,
                        'status': alert.status,
                        'is_active': alert.is_active,
                        'triggered': alert.triggered,
                        'notes': alert.notes
                    })
                
                # Dane pozycji
                position_data = {
                    'id': position.id,
                    'ticker': position.ticker,
                    'quantity': position.quantity,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'profit_loss_percent': position.profit_loss_percent,
                    'profit_loss_dollar': position.profit_loss_dollar,
                    'notes': position.notes,
                    'alerts': alerts_data
                }
                
                category_data['positions'].append(position_data)
                
                # Aktualizuj podsumowanie
                portfolio_data['summary']['total_positions'] += 1
                
                if position.current_price:
                    position_value = position.quantity * position.current_price
                    portfolio_data['summary']['total_value'] += position_value
                    
                    if position.profit_loss_dollar:
                        portfolio_data['summary']['total_profit_loss'] += position.profit_loss_dollar
            
            # Dodaj kategorię do portfolio tylko jeśli ma pozycje
            if category_data['positions']:
                portfolio_data['categories'].append(category_data)
                portfolio_data['summary']['total_categories'] += 1
        
        # Oblicz procentowy zysk/stratę portfela
        if portfolio_data['summary']['total_value'] > 0:
            initial_value = portfolio_data['summary']['total_value'] - portfolio_data['summary']['total_profit_loss']
            if initial_value > 0:
                portfolio_data['summary']['profit_loss_percent'] = (
                    portfolio_data['summary']['total_profit_loss'] / initial_value
                ) * 100
            else:
                portfolio_data['summary']['profit_loss_percent'] = Decimal('0')
        else:
            portfolio_data['summary']['profit_loss_percent'] = Decimal('0')
        
        return {
            'success': True,
            'message': 'Dane portfela GT pobrane pomyślnie.',
            'portfolio': portfolio_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania portfela GT: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas pobierania portfela GT: {str(e)}"
        }

def get_gt_categories(user_id):
    """
    Pobiera wszystkie kategorie z portfela GT użytkownika.
    
    Args:
        user_id (int): ID użytkownika
        
    Returns:
        dict: Dane o kategoriach w formacie:
        {
            'success': bool,
            'message': str,
            'categories': [
                {
                    'id': int,
                    'name': str,
                    'description': str,
                    'position_count': int
                }
            ]
        }
    """
    try:
        # Importy modeli wewnątrz funkcji
        from django.contrib.auth.models import User
        from gt.models import GTCategory, StockPosition
        
        # Pobierz użytkownika
        user = User.objects.get(id=user_id)
        
        # Pobierz wszystkie kategorie użytkownika
        categories = GTCategory.objects.filter(user=user)
        
        if not categories.exists():
            return {
                'success': True,
                'message': 'Nie znaleziono kategorii w portfelu GT.',
                'categories': []
            }
        
        # Przygotuj dane kategorii
        categories_data = []
        for category in categories:
            # Zlicz aktywne pozycje w kategorii
            position_count = StockPosition.objects.filter(
                category=category, 
                exit_date__isnull=True
            ).count()
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'position_count': position_count
            })
        
        return {
            'success': True,
            'message': 'Dane kategorii pobrane pomyślnie.',
            'categories': categories_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania kategorii GT: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas pobierania kategorii GT: {str(e)}"
        }

def find_or_create_category(user_id, category_name):
    """
    Znajduje lub tworzy kategorię o podanej nazwie dla użytkownika.
    
    Args:
        user_id (int): ID użytkownika
        category_name (str): Nazwa kategorii
        
    Returns:
        tuple: (success, category_obj, message)
    """
    try:
        # Importy modeli wewnątrz funkcji
        from django.contrib.auth.models import User
        from gt.models import GTCategory
        
        user = User.objects.get(id=user_id)
        
        # Spróbuj znaleźć istniejącą kategorię
        try:
            category = GTCategory.objects.get(user=user, name=category_name)
            return True, category, f"Znaleziono istniejącą kategorię: {category_name}"
        except GTCategory.DoesNotExist:
            # Jeśli kategoria nie istnieje, utwórz nową
            category = GTCategory.objects.create(
                user=user,
                name=category_name,
                description=f"Kategoria {category_name} utworzona przez AI agenta"
            )
            return True, category, f"Utworzono nową kategorię: {category_name}"
    except Exception as e:
        return False, None, f"Błąd podczas tworzenia kategorii: {str(e)}"

@transaction.atomic
def add_stock_position(user_id, ticker, quantity, category_name="Default", notes=None):
    """
    Dodaje nową pozycję akcji do portfela GT.
    
    Args:
        user_id (int): ID użytkownika
        ticker (str): Symbol akcji (np. AAPL, MSFT)
        quantity (float): Ilość akcji
        category_name (str): Nazwa kategorii (zostanie utworzona, jeśli nie istnieje)
        notes (str, optional): Notatki do pozycji
        
    Returns:
        dict: Wynik operacji w formacie:
        {
            'success': bool,
            'message': str,
            'position': dict z danymi pozycji (opcjonalnie)
        }
    """
    try:
        # Importy modeli wewnątrz funkcji
        from gt.models import StockPosition
        from gt.utils import get_stock_price
        
        # Znajdź lub utwórz kategorię
        success, category, message = find_or_create_category(user_id, category_name)
        if not success:
            return {'success': False, 'message': message}
        
        # Pobierz aktualną cenę akcji
        current_price = get_stock_price(ticker)
        if current_price is None:
            return {
                'success': False,
                'message': f"Nie udało się pobrać ceny dla {ticker}. Sprawdź, czy symbol jest poprawny."
            }
        
        # Utwórz nową pozycję
        position = StockPosition.objects.create(
            user_id=user_id,
            category=category,
            ticker=ticker.upper(),
            quantity=Decimal(str(quantity)),
            entry_price=Decimal(str(current_price)),
            current_price=Decimal(str(current_price)),
            last_price_update=timezone.now(),
            notes=notes
        )
        
        # Przygotuj dane odpowiedzi
        position_data = {
            'id': position.id,
            'ticker': position.ticker,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'category': category.name,
            'notes': position.notes,
            'created_at': position.created_at.isoformat() if position.created_at else None
        }
        
        return {
            'success': True,
            'message': f"Pozycja {position.ticker} dodana pomyślnie do kategorii {category.name}.",
            'position': position_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas dodawania pozycji: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas dodawania pozycji: {str(e)}"
        }

@transaction.atomic
def add_price_alert(user_id, ticker=None, position_id=None, alert_type=None, threshold_value=None, notes=None):
    """
    Dodaje alert cenowy do pozycji w portfelu GT.
    
    Args:
        user_id: ID użytkownika
        ticker: Symbol akcji (np. "AAPL")
        position_id: ID pozycji (opcjonalne, jeśli podano ticker)
        alert_type: Typ alertu (PRICE_ABOVE, PRICE_BELOW, PCT_INCREASE, PCT_DECREASE)
        threshold_value: Wartość progowa alertu
        notes: Dodatkowe notatki dla alertu
        
    Returns:
        Słownik z wynikiem operacji
    """
    from django.contrib.auth.models import User
    from gt.models import StockPosition, StockPriceAlert
    from decimal import Decimal
    
    logger.info(f"Dodawanie alertu cenowego dla ticker={ticker}, position_id={position_id}, typ={alert_type}, wartość={threshold_value}")
    
    # Walidacja typu alertu
    VALID_ALERT_TYPES = ['PRICE_ABOVE', 'PRICE_BELOW', 'PCT_INCREASE', 'PCT_DECREASE']
    if alert_type not in VALID_ALERT_TYPES:
        return {
            'success': False, 
            'message': f"Nieprawidłowy typ alertu: {alert_type}. Dozwolone typy: {', '.join(VALID_ALERT_TYPES)}"
        }
    
    try:
        user = User.objects.get(id=user_id)
        
        # Znajdź pozycję
        position = None
        
        if position_id:
            # Jeśli podano ID pozycji, znajdź po ID
            try:
                position = StockPosition.objects.get(id=position_id, user=user)
            except StockPosition.DoesNotExist:
                return {'success': False, 'message': f"Nie znaleziono pozycji o ID {position_id}"}
                
        elif ticker:
            # Znajdź aktywną pozycję dla danego tickera
            try:
                # Używamy created_at zamiast entry_date (które nie jest dostępne w modelu)
                logger.info(f"Szukam pozycji dla użytkownika {user.id}, ticker={ticker}")
                positions = StockPosition.objects.filter(
                    user=user, 
                    ticker__iexact=ticker,  # Ignorowanie wielkości liter
                    exit_date__isnull=True
                )
                
                # Wyświetl znalezione pozycje dla celów debugowania
                positions_list = list(positions.values('id', 'ticker', 'quantity'))
                logger.info(f"Znalezione pozycje: {positions_list}")
                
                position = positions.order_by('-created_at').first()
                
                if not position:
                    # Sprawdźmy także zamknięte pozycje, jeśli nie znaleziono otwartych
                    all_positions = StockPosition.objects.filter(
                        user=user, 
                        ticker__iexact=ticker
                    )
                    all_positions_list = list(all_positions.values('id', 'ticker', 'quantity', 'exit_date'))
                    logger.info(f"Wszystkie pozycje (włączając zamknięte): {all_positions_list}")
                    
                    # Jeśli brak pozycji, oferujemy możliwość utworzenia nowej
                    if not all_positions.exists():
                        return {
                            'success': False, 
                            'message': f"Nie znaleziono pozycji dla tickera {ticker}. Użyj funkcji 'add_stock_position' aby najpierw dodać pozycję."
                        }
                    else:
                        return {
                            'success': False, 
                            'message': f"Nie znaleziono aktywnej pozycji dla tickera {ticker}. Znaleziono {len(all_positions_list)} zamkniętych pozycji."
                        }
                
            except Exception as e:
                logger.error(f"Błąd podczas wyszukiwania pozycji: {str(e)}")
                return {'success': False, 'message': f"Błąd podczas wyszukiwania pozycji: {str(e)}"}
        else:
            return {'success': False, 'message': "Nie podano ID pozycji ani tickera. Nie można dodać alertu."}
        
        if not position:
            return {'success': False, 'message': f"Nie znaleziono pozycji dla tickera {ticker} i identyfikatora {position_id}"}
        
        # Konwertuj threshold_value na Decimal
        try:
            threshold_value = Decimal(str(threshold_value))
        except:
            return {
                'success': False,
                'message': f"Nieprawidłowa wartość progowa: {threshold_value}"
            }
        
        # Utwórz alert
        alert = StockPriceAlert.objects.create(
            position=position,
            alert_type=alert_type,
            threshold_value=threshold_value,
            notes=notes,
            is_active=True
        )
        
        # Przygotuj dane odpowiedzi
        alert_data = {
            'id': alert.id,
            'position_ticker': position.ticker,
            'alert_type': alert.alert_type,
            'threshold_value': alert.threshold_value,
            'notes': alert.notes,
            'is_active': alert.is_active,
            'created_at': alert.created_at.isoformat() if alert.created_at else None
        }
        
        return {
            'success': True,
            'message': f"Alert {alert.get_alert_type_display()} przy {alert.threshold_value} dodany pomyślnie do pozycji {position.ticker}.",
            'alert': alert_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas dodawania alertu: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas dodawania alertu: {str(e)}"
        }

def get_position_details(user_id, ticker=None, position_id=None):
    """
    Pobiera szczegółowe informacje o pozycji akcji.
    
    Args:
        user_id (int): ID użytkownika
        ticker (str, optional): Symbol akcji
        position_id (int, optional): ID pozycji (alternatywnie do ticker)
        
    Returns:
        dict: Szczegółowe dane pozycji w formacie:
        {
            'success': bool,
            'message': str,
            'position': dict z danymi pozycji (opcjonalnie)
        }
    """
    try:
        # Importy modeli wewnątrz funkcji
        from django.contrib.auth.models import User
        from gt.models import StockPosition, StockPriceAlert
        from gt.utils import get_stock_price_advanced
        
        # Pobierz użytkownika
        user = User.objects.get(id=user_id)
        
        # Znajdź pozycję
        if position_id:
            try:
                position = StockPosition.objects.get(id=position_id, user=user)
            except StockPosition.DoesNotExist:
                return {
                    'success': False,
                    'message': f"Nie znaleziono pozycji o ID {position_id} dla użytkownika."
                }
        elif ticker:
            # Znajdź aktywną pozycję dla danego tickera
            try:
                # Używamy created_at zamiast entry_date (które nie jest dostępne w modelu)
                logger.info(f"Szukam pozycji dla użytkownika {user.id}, ticker={ticker}")
                positions = StockPosition.objects.filter(
                    user=user, 
                    ticker=ticker.upper(),
                    exit_date__isnull=True
                )
                
                # Wyświetl znalezione pozycje dla celów debugowania
                positions_list = list(positions.values('id', 'ticker', 'quantity'))
                logger.info(f"Znalezione pozycje: {positions_list}")
                
                position = positions.order_by('-created_at').first()
                
                if not position:
                    return {
                        'success': False,
                        'message': f"Nie znaleziono aktywnej pozycji dla {ticker}."
                    }
            except StockPosition.DoesNotExist:
                return {
                    'success': False,
                    'message': f"Nie znaleziono aktywnej pozycji dla {ticker}."
                }
        else:
            return {
                'success': False,
                'message': "Należy podać ticker lub ID pozycji."
            }
        
        # Pobierz aktualne dane rynkowe
        try:
            market_data = get_stock_price_advanced(position.ticker)
            if market_data:
                current_price = Decimal(str(market_data['price']))
                
                # Aktualizuj cenę w bazie danych
                position.current_price = current_price
                position.last_price_update = timezone.now()
                position.save(update_fields=['current_price', 'last_price_update'])
            else:
                # Użyj zapisanej ceny, jeśli nie udało się pobrać aktualnej
                current_price = position.current_price
                market_data = {
                    'price': float(current_price) if current_price else None,
                    'change': None,
                    'change_percent': None,
                    'volume': None,
                    'prev_close': None
                }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych: {str(e)}")
            current_price = position.current_price
            market_data = {
                'price': float(current_price) if current_price else None,
                'change': None,
                'change_percent': None,
                'volume': None,
                'prev_close': None
            }
        
        # Pobierz alerty
        alerts = StockPriceAlert.objects.filter(position=position)
        alerts_data = []
        
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'alert_type_display': alert.get_alert_type_display(),
                'threshold_value': alert.threshold_value,
                'status': alert.status,
                'is_active': alert.is_active,
                'triggered': alert.triggered,
                'notes': alert.notes,
                'created_at': alert.created_at.isoformat() if alert.created_at else None
            })
        
        # Przygotuj dane pozycji
        position_data = {
            'id': position.id,
            'ticker': position.ticker,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'profit_loss_percent': position.profit_loss_percent,
            'profit_loss_dollar': position.profit_loss_dollar,
            'notes': position.notes,
            'category': {
                'id': position.category.id,
                'name': position.category.name
            },
            'market_data': market_data,
            'alerts': alerts_data,
            'created_at': position.created_at.isoformat() if position.created_at else None,
            'updated_at': position.updated_at.isoformat() if position.updated_at else None
        }
        
        return {
            'success': True,
            'message': f"Dane pozycji {position.ticker} pobrane pomyślnie.",
            'position': position_data
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas pobierania danych pozycji: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas pobierania danych pozycji: {str(e)}"
        }

def create_test_portfolio(user_id):
    """
    Tworzy przykładowy portfel GT z popularnymi akcjami dla testów.
    Uwaga: Wykorzystywać tylko do testów i demonstracji.
    
    Args:
        user_id (int): ID użytkownika
        
    Returns:
        dict: Wynik operacji w formacie:
        {
            'success': bool,
            'message': str
        }
    """
    try:
        # Sprawdź, czy użytkownik już ma jakieś pozycje
        from django.contrib.auth.models import User
        from gt.models import GTCategory, StockPosition
        
        user = User.objects.get(id=user_id)
        existing_positions = StockPosition.objects.filter(user=user, exit_date__isnull=True)
        
        if existing_positions.exists():
            return {
                'success': True,
                'message': f'Portfel GT już istnieje i zawiera {existing_positions.count()} aktywnych pozycji.'
            }
        
        # Zdefiniuj kategorie i przykładowe akcje do utworzenia
        test_data = [
            {
                'category': 'Technologia',
                'positions': [
                    {'ticker': 'TSLA', 'quantity': 1, 'entry_price': 845.00, 'current_price': 875.50, 'notes': 'Tesla Inc. - akcje kupione 15 kwietnia'}
                ]
            },
            {
                'category': 'Spożywcze',
                'positions': [
                    {'ticker': 'KO', 'quantity': 10, 'entry_price': 65.75, 'current_price': 68.25, 'notes': 'Coca-Cola Company - długoterminowa inwestycja'}
                ]
            }
        ]
        
        # Utwórz kategorie i pozycje
        for category_data in test_data:
            # Znajdź lub utwórz kategorię
            success, category, message = find_or_create_category(user_id, category_data['category'])
            
            if not success or not category:
                logger.warning(f"Nie udało się utworzyć kategorii {category_data['category']}: {message}")
                continue
            
            # Dodaj pozycje do kategorii
            for position_data in category_data['positions']:
                # Tworzenie pozycji
                position = StockPosition(
                    user=user,
                    category=category,
                    ticker=position_data['ticker'],
                    quantity=Decimal(str(position_data['quantity'])),
                    entry_price=Decimal(str(position_data['entry_price'])),
                    current_price=Decimal(str(position_data['current_price'])),
                    notes=position_data['notes'],
                    entry_date=timezone.now()
                )
                position.save()
                
                # Oblicz zysk/stratę
                position.profit_loss_dollar = (position.current_price - position.entry_price) * position.quantity
                position.profit_loss_percent = (position.current_price / position.entry_price - 1) * 100
                position.save()
                
                logger.info(f"Utworzono pozycję {position.ticker} w kategorii {category.name}")
        
        return {
            'success': True,
            'message': 'Utworzono przykładowy portfel GT z testowymi pozycjami.'
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia przykładowego portfela: {str(e)}")
        return {
            'success': False,
            'message': f"Błąd podczas tworzenia przykładowego portfela: {str(e)}"
        }
