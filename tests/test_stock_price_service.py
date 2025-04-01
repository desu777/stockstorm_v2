"""
Test script for the StockPriceService with fallback mechanisms
"""
import sys
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the StockPriceService class
sys.path.append('.')
from v1.gt.stock_price_service import StockPriceService

# Simple cache implementation for testing outside Django
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        if key in self.cache and self.cache[key]['expires'] > datetime.now().timestamp():
            return self.cache[key]['value']
        return None
    
    def set(self, key, value, timeout):
        self.cache[key] = {
            'value': value,
            'expires': datetime.now().timestamp() + timeout
        }

# Mock the Django cache for testing
import sys
import types
from unittest.mock import MagicMock

# Create a mock module
mock_cache = types.ModuleType('django.core.cache')
mock_cache.cache = SimpleCache()

# Add the mock module to sys.modules
sys.modules['django.core.cache'] = mock_cache

def test_get_price(ticker):
    """Test getting a single price"""
    print(f"\n=== Testing price retrieval for {ticker} ===")
    price = StockPriceService.get_price(ticker)
    if price is not None:
        print(f"SUCCESS: Price for {ticker} = {price}")
    else:
        print(f"ERROR: Could not retrieve price for {ticker}")
    return price

def test_get_price_data(ticker):
    """Test getting detailed price data"""
    print(f"\n=== Testing detailed price data for {ticker} ===")
    data = StockPriceService.get_price_data(ticker)
    if data and 'error' not in data:
        print(f"SUCCESS: Data for {ticker}:")
        print(json.dumps(data, indent=2))
    else:
        print(f"ERROR: Could not retrieve detailed data for {ticker}")
        if data and 'error' in data:
            print(f"Error message: {data['error']}")
    return data

def test_multiple_tickers(tickers):
    """Test getting prices for multiple tickers"""
    print(f"\n=== Testing multiple tickers {tickers} ===")
    results = {}
    for ticker in tickers:
        data = StockPriceService.get_price_data(ticker)
        if data and 'error' not in data:
            source = data.get('source', 'unknown')
            results[ticker] = {
                'price': data['price'],
                'change': data['change'],
                'change_percent': data['change_percent'],
                'source': source
            }
            print(f"SUCCESS: {ticker} = {data['price']} (from {source})")
        else:
            results[ticker] = {'error': 'Failed to retrieve data'}
            print(f"ERROR: Could not retrieve data for {ticker}")
    
    return results

if __name__ == "__main__":
    # Test single ticker price
    test_get_price('AAPL')
    
    # Test detailed data
    test_get_price_data('MSFT')
    
    # Test multiple tickers
    test_multiple_tickers(['NVDA', 'TSLA', 'AMZN', 'GOOG'])
    
    print("\nTests completed!")
