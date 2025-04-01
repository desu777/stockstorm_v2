"""
Test script for Yahoo Finance API integration
"""
import json
import time
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simple cache implementation for testing
class SimpleCache:
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        if key in self.cache and self.cache[key]['expires'] > time.time():
            return self.cache[key]['value']
        return None
    
    def set(self, key, value, timeout):
        self.cache[key] = {
            'value': value,
            'expires': time.time() + timeout
        }

# Create global cache instance
cache = SimpleCache()

def get_yahoo_finance_price(ticker):
    """
    Get stock price from Yahoo Finance API
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        float: Current stock price or None if an error occurred
    """
    try:
        data = get_yahoo_finance_price_data(ticker)
        if data and 'price' in data:
            return data['price']
        return None
    except Exception as e:
        logger.error(f"Error getting Yahoo Finance price for {ticker}: {e}")
        return None

def get_yahoo_finance_price_data(ticker):
    """
    Get detailed stock data from Yahoo Finance
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        dict: Dictionary with stock data or None if an error occurred
    """
    try:
        # Yahoo Finance API URL
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        
        # Parameters including range and interval
        params = {
            "range": "1d",
            "interval": "1m",
            "includePrePost": "false"
        }
        
        # Headers to mimic browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        logger.info(f"Sending Yahoo Finance API request for {ticker}")
        # Send request
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code != 200:
            logger.warning(f"Yahoo Finance API returned status {response.status_code} for {ticker}")
            return None
            
        # Parse JSON response
        data = response.json()
        
        # Check if we have valid data
        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            logger.warning(f"Unexpected Yahoo Finance data structure for {ticker}")
            return None
            
        # Extract price data
        chart_data = data["chart"]["result"][0]
        
        # Get current price (last available price)
        meta = chart_data["meta"]
        quote = chart_data["indicators"]["quote"][0]
        
        # Get the last valid close price
        close_prices = quote.get("close", [])
        current_price = None
        
        # Find the last non-null close price
        for price in reversed(close_prices):
            if price is not None:
                current_price = price
                break
                
        if current_price is None and "regularMarketPrice" in meta:
            current_price = meta["regularMarketPrice"]
            
        if current_price is None:
            logger.warning(f"Could not find valid price for {ticker} in Yahoo Finance data")
            return None
            
        # Calculate change and percent change
        previous_close = meta.get("previousClose", current_price)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close else 0
        
        # Create result
        result = {
            'symbol': ticker,
            'price': float(current_price),
            'change': float(change),
            'change_percent': float(change_percent),
            'prev_close': float(previous_close),
            'currency': meta.get("currency", "USD"),
            'source': 'yahoo_finance',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Successfully retrieved Yahoo Finance data for {ticker}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance for {ticker}: {e}")
        return {
            'symbol': ticker,
            'error': str(e),
            'source': 'yahoo_finance',
            'timestamp': datetime.now().isoformat()
        }

def test_get_price(ticker):
    """Test getting a single price"""
    print(f"\n=== Testing price retrieval for {ticker} ===")
    price = get_yahoo_finance_price(ticker)
    if price is not None:
        print(f"SUCCESS: Price for {ticker} = {price}")
    else:
        print(f"ERROR: Could not retrieve price for {ticker}")
    return price

def test_get_price_data(ticker):
    """Test getting detailed price data"""
    print(f"\n=== Testing detailed price data for {ticker} ===")
    data = get_yahoo_finance_price_data(ticker)
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
        data = get_yahoo_finance_price_data(ticker)
        if data and 'error' not in data:
            results[ticker] = {
                'price': data['price'],
                'change': data['change'],
                'change_percent': data['change_percent'],
                'source': data.get('source', 'unknown')
            }
            print(f"SUCCESS: {ticker} = {data['price']} (change: {data['change']:.2f}, %: {data['change_percent']:.2f}%)")
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
    
    # Test some other market tickers
    test_multiple_tickers(['GC=F', 'BTC-USD', 'EURUSD=X'])
    
    print("\nTests completed!")
