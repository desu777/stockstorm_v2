"""
Moduł analizy portfela HP Crypto.

Ten moduł zawiera funkcje do analizy struktury portfela HP Crypto, w tym:
- Analizę alokacji kapitału między różne aktywa
- Wykrywanie nadmiernej koncentracji w jednym aktywie
- Rekomendacje dotyczące dywersyfikacji
- Analizę ryzyka portfela
"""

import logging
from decimal import Decimal
from collections import defaultdict
import json

# Konfiguracja loggera
logger = logging.getLogger(__name__)

def analyze_hp_portfolio(user_id):
    """
    Główna funkcja do kompleksowej analizy portfela HP Crypto.
    
    Args:
        user_id: ID użytkownika
        
    Returns:
        dict: Kompleksowa analiza portfela zawierająca:
            - Alokację kapitału między kryptowaluty
            - Koncentrację kapitału i ostrzeżenia
            - Ocenę dywersyfikacji
            - Rekomendacje
    """
    try:
        # Import funkcji get_hp_positions z modułu data_utils
        from ai_agent.data_utils import get_hp_positions
        
        # Pobierz podstawowe dane o portfelu
        portfolio_data = get_hp_positions(user_id)
        
        if not portfolio_data:
            logger.error(f"Nie udało się pobrać danych portfela dla użytkownika {user_id}")
            return {
                'success': False,
                'message': 'Nie udało się pobrać danych portfela'
            }
            
        # Analizuj strukturę portfela
        portfolio_structure = analyze_portfolio_structure(portfolio_data)
        
        # Analizuj koncentrację kapitału
        concentration_analysis = analyze_capital_concentration(portfolio_structure)
        
        # Przygotuj rekomendacje
        recommendations = generate_portfolio_recommendations(portfolio_structure, concentration_analysis)
        
        # Zwróć pełną analizę
        return {
            'success': True,
            'portfolio_data': portfolio_data,
            'portfolio_structure': portfolio_structure,
            'concentration_analysis': concentration_analysis,
            'recommendations': recommendations
        }
        
    except Exception as e:
        logger.error(f"Błąd podczas analizy portfela HP: {str(e)}")
        return {
            'success': False,
            'message': f'Wystąpił błąd podczas analizy: {str(e)}'
        }

def analyze_portfolio_structure(portfolio_data):
    """
    Analizuje strukturę portfela HP Crypto, wyliczając alokację kapitału między kryptowaluty.
    
    Args:
        portfolio_data: Dane portfela z funkcji get_hp_positions
        
    Returns:
        dict: Analiza struktury portfela zawierająca:
            - Alokację procentową między aktywa
            - Skupienie według głównych kryptowalut 
            - Rozkład między kategorie
    """
    # Inicjalizuj strukturę wyniku
    structure = {
        'total_value': float(portfolio_data.get('current_value', 0)),
        'assets': {},
        'categories': {},
        'assets_by_value': [],
        'biggest_positions': []
    }
    
    # Tymczasowe zmienne do agregacji
    assets_totals = defaultdict(float)
    categories_totals = defaultdict(float)
    all_positions = []
    
    # Wyodrębnij dane o pozycjach z wszystkich kategorii
    for category in portfolio_data.get('categories', []):
        category_name = category.get('name', 'Nieznana')
        category_value = float(category.get('total_value', 0))
        
        # Dodaj dane kategorii
        structure['categories'][category_name] = {
            'value': category_value,
            'percentage': 0  # uzupełnione później
        }
        
        # Agreguj wartości pozycji według aktywów
        for position in category.get('positions', []):
            ticker = position.get('ticker', '').split('USDT')[0].split('USDC')[0]  # Wyodrębnij symbol bez sufiksu waluty
            position_value = float(position.get('position_size', 0)) + float(position.get('profit_loss', 0))
            
            # Agreguj według aktywa
            assets_totals[ticker] += position_value
            
            # Zbieraj wszystkie pozycje do listy
            all_positions.append({
                'ticker': ticker,
                'category': category_name,
                'value': position_value,
                'quantity': float(position.get('quantity', 0)),
                'entry_price': float(position.get('entry_price', 0)),
                'current_price': float(position.get('current_price', 0))
            })
    
    # Oblicz procenty dla kategorii
    if structure['total_value'] > 0:
        for category_name, category_data in structure['categories'].items():
            category_data['percentage'] = (category_data['value'] / structure['total_value']) * 100
    
    # Oblicz procenty dla aktywów
    for ticker, value in assets_totals.items():
        percentage = (value / structure['total_value']) * 100 if structure['total_value'] > 0 else 0
        structure['assets'][ticker] = {
            'value': value,
            'percentage': percentage
        }
        structure['assets_by_value'].append({
            'ticker': ticker,
            'value': value,
            'percentage': percentage
        })
    
    # Sortuj aktywa według wartości
    structure['assets_by_value'] = sorted(structure['assets_by_value'], key=lambda x: x['value'], reverse=True)
    
    # Sortuj pozycje według wartości i wybierz 5 największych
    all_positions_sorted = sorted(all_positions, key=lambda x: x['value'], reverse=True)
    structure['biggest_positions'] = all_positions_sorted[:5]
    
    return structure

def analyze_capital_concentration(portfolio_structure):
    """
    Analizuje koncentrację kapitału w portfelu i wykrywa potencjalne ryzyka.
    Stawia silny nacisk na dominację BTC w portfelu (min. 70%).
    
    Args:
        portfolio_structure: Struktura portfela z funkcji analyze_portfolio_structure
        
    Returns:
        dict: Analiza koncentracji kapitału
    """
    concentration = {
        'high_concentration': False,
        'warnings': [],
        'concentration_level': 'Niski',
        'largest_asset': None,
        'top_3_assets_percentage': 0,
        'btc_dominance': False,
        'btc_percentage': 0
    }
    
    # Sprawdź czy istnieje koncentracja w jednym aktywie
    assets_by_value = portfolio_structure.get('assets_by_value', [])
    
    if not assets_by_value:
        return concentration
    
    # Sprawdź największe aktywo
    largest_asset = assets_by_value[0]
    concentration['largest_asset'] = largest_asset
    
    # Sprawdź czy BTC istnieje w portfelu i jaki ma udział
    btc_asset = None
    for asset in assets_by_value:
        if asset['ticker'] == 'BTC':
            btc_asset = asset
            concentration['btc_percentage'] = asset['percentage']
            break
    
    # Sprawdź dominację BTC (czy stanowi co najmniej 70% portfela)
    if btc_asset and btc_asset['percentage'] >= 70:
        concentration['btc_dominance'] = True
        concentration['concentration_level'] = 'Optymalny'
        concentration['warnings'].append(
            f"BTC stanowi {btc_asset['percentage']:.1f}% portfela - to dobra koncentracja, zapewniająca stabilność portfela."
        )
    # Jeśli BTC jest w portfelu, ale poniżej 70%
    elif btc_asset:
        concentration['btc_dominance'] = False
        concentration['concentration_level'] = 'Ryzykowny'
        concentration['warnings'].append(
            f"BTC stanowi tylko {btc_asset['percentage']:.1f}% portfela - to zbyt mało. "
            f"Zalecane jest zwiększenie udziału BTC do minimum 70% portfela, ponieważ pozostałe aktywa "
            f"są znacznie bardziej ryzykowne i zmienne."
        )
    # Jeśli nie ma BTC w portfelu
    else:
        concentration['btc_dominance'] = False
        concentration['concentration_level'] = 'Krytycznie ryzykowny'
        concentration['warnings'].append(
            f"W portfelu nie znajduje się BTC, co oznacza bardzo wysokie ryzyko. "
            f"Bitcoin powinien stanowić minimum 70% całego portfela kryptowalut, aby zapewnić stabilność."
        )
    
    # Sprawdź czy największe aktywo inne niż BTC nie stanowi zbyt dużej części portfela
    if largest_asset['ticker'] != 'BTC' and largest_asset['percentage'] >= 40:
        concentration['high_concentration'] = True
        concentration['warnings'].append(
            f"{largest_asset['ticker']} stanowi {largest_asset['percentage']:.1f}% portfela, "
            f"co jest niebezpieczną koncentracją w aktywie o wysokim ryzyku. "
            f"Rozważ przeniesienie części kapitału z {largest_asset['ticker']} do BTC."
        )
    
    # Oblicz procent top 3 aktywów
    top_3_assets = assets_by_value[:3] if len(assets_by_value) >= 3 else assets_by_value
    top_3_percentage = sum(asset['percentage'] for asset in top_3_assets)
    concentration['top_3_assets_percentage'] = top_3_percentage
    
    # Jeśli w topowych aktywach nie ma BTC, zaznacz to jako problem
    top_3_tickers = [asset['ticker'] for asset in top_3_assets]
    if 'BTC' not in top_3_tickers:
        concentration['warnings'].append(
            f"BTC nie znajduje się w top 3 aktywach portfela ({', '.join(top_3_tickers)}), "
            f"co stanowi poważny problem dla stabilności i bezpieczeństwa inwestycji."
        )
    
    return concentration

def generate_portfolio_recommendations(portfolio_structure, concentration_analysis):
    """
    Generuje rekomendacje dotyczące zarządzania portfelem na podstawie analizy.
    Podkreśla konieczność posiadania co najmniej 70% BTC w portfelu.
    
    Args:
        portfolio_structure: Struktura portfela
        concentration_analysis: Analiza koncentracji
        
    Returns:
        list: Lista rekomendacji
    """
    recommendations = []
    
    # Rekomendacje dotyczące BTC
    btc_data = portfolio_structure.get('assets', {}).get('BTC')
    btc_percentage = concentration_analysis.get('btc_percentage', 0)
    
    # Jeśli BTC stanowi mniej niż 70% portfela, to główna rekomendacja
    if btc_percentage < 70:
        recommendations.append({
            'type': 'critical',
            'title': 'Zwiększ alokację BTC do minimum 70% portfela',
            'description': f"Bitcoin obecnie stanowi tylko {btc_percentage:.1f}% Twojego portfela. "
                           f"Zwiększ jego udział do minimum 70%, aby zapewnić stabilność i minimalizować ryzyko. "
                           f"Wszystkie altcoiny (aktywa poza BTC) należy traktować jako wysoce ryzykowne i nieprzewidywalne."
        })
    
    # Rekomendacje dotyczące zróżnicowania dla pozostałych 30%
    assets_count = len(portfolio_structure.get('assets', {}))
    if assets_count > 5 and btc_percentage >= 70:
        recommendations.append({
            'type': 'suggestion',
            'title': 'Ogranicz liczbę altcoinów w portfelu',
            'description': f"Posiadasz {assets_count} różnych kryptowalut w portfelu. "
                           f"Chociaż BTC stanowi odpowiednio dużą część portfela ({btc_percentage:.1f}%), "
                           f"rozważ ograniczenie liczby pozostałych aktywów do maksymalnie 3-4 najsilniejszych altcoinów."
        })
    
    # Rekomendacja dotycząca zbyt dużej ekspozycji na altcoiny
    if not btc_data:
        recommendations.append({
            'type': 'critical',
            'title': 'Dodaj BTC do portfela',
            'description': f"Twój portfel nie zawiera BTC, co jest krytycznym błędem w strategii inwestycyjnej. "
                           f"Bitcoin powinien być podstawowym aktywem w każdym portfelu kryptowalut, stanowiącym "
                           f"minimum 70% wartości portfela. Pozostałe aktywa bez BTC są zbyt ryzykowne."
        })
    
    # Jeśli portfel zawiera tylko BTC i stanowi >70%, to komplementujemy
    if assets_count == 1 and btc_data and btc_percentage == 100:
        recommendations.append({
            'type': 'positive',
            'title': 'Portfel w 100% składający się z BTC',
            'description': "Twój portfel w 100% składa się z Bitcoina, co jest optymalnym podejściem do minimalizacji ryzyka. "
                           "Utrzymuj tę strategię, szczególnie w niepewnych warunkach rynkowych."
        })
    elif btc_percentage >= 70:
        recommendations.append({
            'type': 'positive',
            'title': 'Odpowiednia dominacja BTC w portfelu',
            'description': f"Bitcoin stanowi {btc_percentage:.1f}% portfela, co jest dobrym poziomem. "
                           f"Utrzymuj dominację BTC na poziomie 70-90% dla optymalnego stosunku ryzyka do potencjału wzrostu."
        })
    
    # Jeśli dominuje inne aktywo niż BTC
    largest_asset = concentration_analysis.get('largest_asset')
    if largest_asset and largest_asset['ticker'] != 'BTC' and largest_asset['percentage'] > 30:
        recommendations.append({
            'type': 'warning',
            'title': f"Zbyt duża ekspozycja na {largest_asset['ticker']}",
            'description': f"{largest_asset['ticker']} stanowi {largest_asset['percentage']:.1f}% portfela, co jest zbyt dużą "
                           f"ekspozycją na pojedynczy altcoin. Ogranicz pozycję w {largest_asset['ticker']} i przenieś kapitał do BTC."
        })
    
    return recommendations 