"""
Simplified test script for Yahoo Finance API integration
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

# Create global cache instance for testing
cache = SimpleCache()

def get_yahoo_finance_price(ticker, cache_time=240):
    """
    Get stock price from Yahoo Finance API with caching
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Cache duration in seconds
        
    Returns:
        float: Current stock price or None if an error occurred
    """
    cache_key = f"stock_price_{ticker}"
    cached_price = cache.get(cache_key)
    
    if cached_price is not None:
        logger.info(f"Using cached price for {ticker}")
        return cached_price
    
    try:
        data = get_yahoo_finance_price_data(ticker)
        if data and 'price' in data:
            price = data['price']
            cache.set(cache_key, price, cache_time)
            return price
        return None
    except Exception as e:
        logger.error(f"Error getting Yahoo Finance price for {ticker}: {e}")
        return None

def get_yahoo_finance_price_data(ticker, cache_time=240):
    """
    Get detailed stock data from Yahoo Finance with caching
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Cache duration in seconds
        
    Returns:
        dict: Dictionary with stock data or None if an error occurred
    """
    cache_key = f"stock_price_data_{ticker}"
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        logger.info(f"Using cached data for {ticker}")
        return cached_data
    
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
        # Cache the result
        cache.set(cache_key, result, cache_time)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance for {ticker}: {e}")
        return {
            'symbol': ticker,
            'error': str(e),
            'source': 'yahoo_finance',
            'timestamp': datetime.now().isoformat()
        }

def get_bulk_stock_prices(tickers, cache_time=240):
    """
    Fetch prices for multiple stock tickers in an efficient way.
    
    Args:
        tickers: List of stock symbols
        cache_time: Cache duration in seconds
        
    Returns:
        dict: Mapping of ticker symbols to prices
    """
    results = {}
    
    # Check cache for each ticker first
    tickers_to_fetch = []
    for ticker in tickers:
        cache_key = f"stock_price_{ticker}"
        cached_price = cache.get(cache_key)
        if cached_price:
            results[ticker] = cached_price
            logger.info(f"Using cached price for {ticker}")
        else:
            tickers_to_fetch.append(ticker)
    
    # If all tickers were cached, return the results
    if not tickers_to_fetch:
        return results
    
    # Fetch each ticker individually
    for ticker in tickers_to_fetch:
        try:
            price = get_yahoo_finance_price(ticker, cache_time=cache_time)
            results[ticker] = price
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance price for {ticker}: {e}")
    
    return results

def test_get_price(ticker):
    """Test getting a single price"""
    print(f"\n=== Testing price retrieval for {ticker} ===")
    start_time = time.time()
    price = get_yahoo_finance_price(ticker)
    elapsed = time.time() - start_time
    
    if price is not None:
        print(f"SUCCESS: Price for {ticker} = {price} (retrieved in {elapsed:.2f}s)")
    else:
        print(f"ERROR: Could not retrieve price for {ticker}")
    return price

def test_get_price_data(ticker):
    """Test getting detailed price data"""
    print(f"\n=== Testing detailed price data for {ticker} ===")
    start_time = time.time()
    data = get_yahoo_finance_price_data(ticker)
    elapsed = time.time() - start_time
    
    if data and 'error' not in data:
        print(f"SUCCESS: Data for {ticker} (retrieved in {elapsed:.2f}s):")
        print(json.dumps(data, indent=2))
    else:
        print(f"ERROR: Could not retrieve detailed data for {ticker}")
        if data and 'error' in data:
            print(f"Error message: {data['error']}")
    return data

def test_multiple_tickers(tickers):
    """Test getting prices for multiple tickers"""
    print(f"\n=== Testing multiple tickers {tickers} ===")
    start_time = time.time()
    results = get_bulk_stock_prices(tickers)
    elapsed = time.time() - start_time
    
    print(f"Retrieved {len(results)} prices in {elapsed:.2f}s")
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
    price1 = get_yahoo_finance_price(ticker)
    first_request_time = time.time() - start_time
    print(f"First request time: {first_request_time:.4f}s, price: {price1}")
    
    # Second request should be cached (much faster)
    start_time = time.time()
    price2 = get_yahoo_finance_price(ticker)
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

def test_crypto_tickers():
    """Test getting cryptocurrency prices"""
    print("\n=== Testing cryptocurrency tickers ===")
    crypto_tickers = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD']
    
    results = get_bulk_stock_prices(crypto_tickers)
    
    for ticker, price in results.items():
        if price is not None:
            print(f"SUCCESS: {ticker} = {price}")
        else:
            print(f"ERROR: Could not retrieve price for {ticker}")
    
    return results

def test_forex_tickers():
    """Test getting forex pairs"""
    print("\n=== Testing forex tickers ===")
    forex_tickers = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
    
    results = get_bulk_stock_prices(forex_tickers)
    
    for ticker, price in results.items():
        if price is not None:
            print(f"SUCCESS: {ticker} = {price}")
        else:
            print(f"ERROR: Could not retrieve price for {ticker}")
    
    return results

if __name__ == "__main__":
    print("Starting Yahoo Finance API tests...")
    
    # Test single stock price
    test_get_price('AAPL')
    
    # Test detailed stock data
    test_get_price_data('MSFT')
    
    # Test multiple stocks
    test_multiple_tickers(['NVDA', 'TSLA', 'AMZN', 'GOOG'])
    
    # Test caching
    test_caching()
    
    # Test cryptocurrencies
    test_crypto_tickers()
    
    # Test forex pairs
    test_forex_tickers()
    
    print("\nAll tests completed!")
