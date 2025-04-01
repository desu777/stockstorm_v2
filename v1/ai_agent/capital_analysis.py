"""
Moduł analizy alokacji kapitału w systemie StockStorm.

Ten moduł zawiera funkcje do analizy struktury alokacji kapitału pomiędzy:
- Boty 5-10-15rei (z reinwestycją)
- Boty 5-10-15 (bez reinwestycji)
- Portfel HP Crypto (w tym analizę zawartości BTC)
"""

import logging
from decimal import Decimal
import json
from django.conf import settings
import requests

# Konfiguracja loggera
logger = logging.getLogger(__name__)

def analyze_capital_allocation(user_id, microservice_token):
    """
    Analizuje alokację kapitału użytkownika pomiędzy różne instrumenty inwestycyjne.
    
    Args:
        user_id: ID użytkownika
        microservice_token: Token dostępu do mikrousług
        
    Returns:
        dict: Analiza alokacji kapitału zawierająca:
            - Łączną wartość kapitału
            - Alokację pomiędzy boty 5-10-15rei, 5-10-15 i portfel HP
            - Szczegółowe informacje o każdym instrumencie
    """
    try:
        # Import funkcji get_hp_positions z modułu data_utils
        from ai_agent.data_utils import get_hp_positions, analyze_portfolio
        from ai_agent.hp_analysis import analyze_hp_portfolio
        
        # Pobierz dane o portfelu HP
        hp_portfolio_data = get_hp_positions(user_id)
        hp_portfolio_value = float(hp_portfolio_data.get('current_value', 0)) if hp_portfolio_data else 0
        
        # Pobierz dane o botach
        bots_data = analyze_portfolio(user_id, microservice_token)
        
        # Pobierz szczegółową analizę portfela HP
        hp_analysis = analyze_hp_portfolio(user_id)
        hp_portfolio_structure = hp_analysis.get('portfolio_structure', {}) if hp_analysis and hp_analysis.get('success') else {}
        
        # Wyodrębnij wartości kapitału w botach
        bots_rei_value = 0  # Wartość botów 5-10-15rei (z reinwestycją)
        bots_no_rei_value = 0  # Wartość botów 5-10-15 (bez reinwestycji)
        
        bots_rei_count = 0
        bots_no_rei_count = 0
        
        # Przeanalizuj boty z podziałem na strategie
        bots_by_strategy = {}
        for bot_id, strategy in bots_data.get('strategies', {}).items():
            strategy_name = str(strategy).lower()
            if '5-10-15rei' in strategy_name or 'rei' in strategy_name:
                bots_rei_count += 1
                capital = float(bots_data.get('capitals', {}).get(bot_id, 0))
                bots_rei_value += capital
                
                if '5-10-15rei' not in bots_by_strategy:
                    bots_by_strategy['5-10-15rei'] = {
                        'count': 0,
                        'capital': 0,
                        'bots': []
                    }
                
                bots_by_strategy['5-10-15rei']['count'] += 1
                bots_by_strategy['5-10-15rei']['capital'] += capital
                bots_by_strategy['5-10-15rei']['bots'].append({
                    'id': bot_id,
                    'capital': capital,
                    'symbol': bots_data.get('symbols', {}).get(bot_id, "")
                })
            else:
                bots_no_rei_count += 1
                capital = float(bots_data.get('capitals', {}).get(bot_id, 0))
                bots_no_rei_value += capital
                
                if '5-10-15' not in bots_by_strategy:
                    bots_by_strategy['5-10-15'] = {
                        'count': 0,
                        'capital': 0,
                        'bots': []
                    }
                
                bots_by_strategy['5-10-15']['count'] += 1
                bots_by_strategy['5-10-15']['capital'] += capital
                bots_by_strategy['5-10-15']['bots'].append({
                    'id': bot_id,
                    'capital': capital,
                    'symbol': bots_data.get('symbols', {}).get(bot_id, "")
                })
        
        # Oblicz łączną wartość kapitału
        total_capital = bots_rei_value + bots_no_rei_value + hp_portfolio_value
        
        # Oblicz procenty alokacji
        bots_rei_percentage = (bots_rei_value / total_capital * 100) if total_capital > 0 else 0
        bots_no_rei_percentage = (bots_no_rei_value / total_capital * 100) if total_capital > 0 else 0
        hp_percentage = (hp_portfolio_value / total_capital * 100) if total_capital > 0 else 0
        
        # Przygotuj analizę BTC w portfelu HP
        btc_value = 0
        btc_percentage_in_hp = 0
        btc_percentage_total = 0
        
        # Znajdź BTC w strukturze portfela HP
        for asset in hp_portfolio_structure.get('assets_by_value', []):
            if asset.get('ticker') == 'BTC':
                btc_value = asset.get('value', 0)
                btc_percentage_in_hp = asset.get('percentage', 0)
                btc_percentage_total = (btc_value / total_capital * 100) if total_capital > 0 else 0
                break
        
        # Przygotuj wynik analizy
        allocation_analysis = {
            'success': True,
            'total_capital': total_capital,
            'summary': {
                'bots_rei': {
                    'value': bots_rei_value,
                    'percentage': bots_rei_percentage,
                    'count': bots_rei_count
                },
                'bots_no_rei': {
                    'value': bots_no_rei_value,
                    'percentage': bots_no_rei_percentage,
                    'count': bots_no_rei_count
                },
                'hp_portfolio': {
                    'value': hp_portfolio_value,
                    'percentage': hp_percentage,
                    'btc_value': btc_value,
                    'btc_percentage_in_hp': btc_percentage_in_hp,
                    'btc_percentage_total': btc_percentage_total
                }
            },
            'bots_by_strategy': bots_by_strategy,
            'hp_analysis': hp_analysis if hp_analysis and hp_analysis.get('success') else None
        }
        
        return allocation_analysis
    
    except Exception as e:
        logger.error(f"Błąd podczas analizy alokacji kapitału: {str(e)}")
        return {
            'success': False,
            'message': f'Wystąpił błąd podczas analizy alokacji kapitału: {str(e)}'
        } 