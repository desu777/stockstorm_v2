"""
Test script for Yahoo Finance API integration within Django project
"""
import os
import sys
import django
import json
import time
import logging
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stockstorm.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Now import from Django project
from v1.gt.utils import (
    get_stock_price,
    get_stock_price_advanced,
    get_bulk_stock_prices
)

def test_get_price(ticker):
    """Test getting a single price"""
    print(f"\n=== Testing price retrieval for {ticker} ===")
    price = get_stock_price(ticker)
    if price is not None:
        print(f"SUCCESS: Price for {ticker} = {price}")
    else:
        print(f"ERROR: Could not retrieve price for {ticker}")
    return price

def test_get_price_data(ticker):
    """Test getting detailed price data"""
    print(f"\n=== Testing detailed price data for {ticker} ===")
    data = get_stock_price_advanced(ticker)
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
    results = get_bulk_stock_prices(tickers)
    
    for ticker, price in results.items():
        if price is not None:
            print(f"SUCCESS: {ticker} = {price}")
        else:
            print(f"ERROR: Could not retrieve price for {ticker}")
    
    return results

def test_caching():
    """Test that caching works correctly"""
    print("\n=== Testing caching mechanism ===")
    ticker = "AAPL"
    
    # First request should hit the API
    start_time = time.time()
    price1 = get_stock_price(ticker)
    first_request_time = time.time() - start_time
    print(f"First request time: {first_request_time:.4f}s, price: {price1}")
    
    # Second request should be cached (much faster)
    start_time = time.time()
    price2 = get_stock_price(ticker)
    second_request_time = time.time() - start_time
    print(f"Second request time: {second_request_time:.4f}s, price: {price2}")
    
    # Check if second request was faster (cached)
    if second_request_time < first_request_time:
        print(f"SUCCESS: Caching works! Second request was {first_request_time/second_request_time:.1f}x faster")
    else:
        print("ERROR: Caching may not be working properly")
    
    return {
        "first_request_time": first_request_time,
        "second_request_time": second_request_time,
        "speedup": first_request_time / second_request_time if second_request_time > 0 else 0
    }

def test_error_handling(invalid_ticker):
    """Test error handling for invalid ticker"""
    print(f"\n=== Testing error handling with invalid ticker: {invalid_ticker} ===")
    data = get_stock_price_advanced(invalid_ticker)
    
    if data is None:
        print(f"SUCCESS: Properly returned None for invalid ticker: {invalid_ticker}")
    elif 'error' in data:
        print(f"SUCCESS: Properly returned error for invalid ticker: {invalid_ticker}")
        print(f"Error message: {data['error']}")
    else:
        print(f"WARNING: Did not handle invalid ticker as expected: {invalid_ticker}")
        print(f"Returned: {data}")
    
    return data

if __name__ == "__main__":
    # Test single ticker price
    test_get_price('AAPL')
    
    # Test detailed data
    test_get_price_data('MSFT')
    
    # Test multiple tickers
    test_multiple_tickers(['NVDA', 'TSLA', 'AMZN', 'GOOG'])
    
    # Test some other market tickers
    test_multiple_tickers(['GC=F', 'BTC-USD', 'EURUSD=X'])
    
    # Test caching
    test_caching()
    
    # Test error handling
    test_error_handling('INVALID-TICKER-SYMBOL')
    
    print("\nAll tests completed!")
