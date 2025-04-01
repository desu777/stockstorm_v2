import json
import time
import random
import requests
from datetime import datetime
from django.core.cache import cache

def get_google_finance_price(ticker, cache_time=240, exchange="NASDAQ"):
    """
    Get the current stock price using Google Finance API.
    This function follows the same pattern as the provided JavaScript example.
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Time in seconds to cache results, default 240 seconds
        exchange (str): Stock exchange, default "NASDAQ"
    
    Returns:
        float: Current stock price or None if an error occurred
    """
    cache_key = f"google_finance_price_{ticker}_{exchange}"
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    try:
        # 1. Prepare URL with proper encoding
        reqid = random.randint(1000000, 9999999)
        url = f"https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?rpcids=xh8wxf&source-path=%2Ffinance%2Fquote%2F{ticker}%3A{exchange}&f.sid=-4555936157889558623&bl=boq_finance-ui_20250326.00_p0&hl=en&soc-app=162&soc-platform=1&soc-device=1&_reqid={reqid}&rt=c"
        
        # 2. Prepare request body with proper format
        current_time = int(time.time() * 1000)
        body = f'f.req=[[["xh8wxf","[[[null,[\"{ticker}\",\"{exchange}\"]]]]",null,"27"]]]&at=ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}'
        
        # 3. Send request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://www.google.com",
            "Referer": "https://www.google.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.post(url, headers=headers, data=body)
        
        # 4. Check response status
        if response.status_code != 200:
            raise Exception(f"HTTP error! Status: {response.status_code}")
        
        # 5. Get response content
        text = response.text
        
        # 6. Remove prefix )]}' if present
        if text.startswith(")]}'"):
            text = text[4:]
        
        # 7. Parse first part of response
        start_idx = text.find('[')
        if start_idx == -1:
            raise Exception("Invalid response format - array start not found")
        
        data = json.loads(text[start_idx:])
        
        # 8. Check if we have the expected data structure
        if not data or not data[0] or len(data[0]) < 3 or not data[0][2]:
            raise Exception("Unexpected data structure in response")
        
        # 9. Parse stock data JSON
        stock_data_json = json.loads(data[0][2])
        
        # 10. Extract specific price data
        price_data = stock_data_json[0][0][0][5]
        
        # Extract current price (first element in price_data)
        current_price = float(price_data[0])
        
        # Cache the result
        cache.set(cache_key, current_price, cache_time)
        
        return current_price
        
    except Exception as e:
        # Log the error but don't crash
        import logging
        logging.error(f"Error fetching Google Finance price for {ticker}: {str(e)}")
        return None

def get_google_finance_price_advanced(ticker, cache_time=240, exchange="NASDAQ"):
    """
    Get detailed stock data using Google Finance API.
    This function follows the same pattern as the provided JavaScript example.
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Time in seconds to cache results, default 240 seconds
        exchange (str): Stock exchange, default "NASDAQ"
    
    Returns:
        dict: Dictionary with stock data or None if an error occurred
    """
    cache_key = f"google_finance_price_advanced_{ticker}_{exchange}"
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    try:
        # 1. Prepare URL with proper encoding
        reqid = random.randint(1000000, 9999999)
        url = f"https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?rpcids=xh8wxf&source-path=%2Ffinance%2Fquote%2F{ticker}%3A{exchange}&f.sid=-4555936157889558623&bl=boq_finance-ui_20250326.00_p0&hl=en&soc-app=162&soc-platform=1&soc-device=1&_reqid={reqid}&rt=c"
        
        # 2. Prepare request body with proper format
        current_time = int(time.time() * 1000)
        body = f'f.req=[[["xh8wxf","[[[null,[\"{ticker}\",\"{exchange}\"]]]]",null,"27"]]]&at=ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}'
        
        # 3. Send request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://www.google.com",
            "Referer": "https://www.google.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.post(url, headers=headers, data=body)
        
        # 4. Check response status
        if response.status_code != 200:
            raise Exception(f"HTTP error! Status: {response.status_code}")
        
        # 5. Get response content
        text = response.text
        
        # 6. Remove prefix )]}' if present
        if text.startswith(")]}'"):
            text = text[4:]
        
        # 7. Parse first part of response
        start_idx = text.find('[')
        if start_idx == -1:
            raise Exception("Invalid response format - array start not found")
        
        data = json.loads(text[start_idx:])
        
        # 8. Check if we have the expected data structure
        if not data or not data[0] or len(data[0]) < 3 or not data[0][2]:
            raise Exception("Unexpected data structure in response")
        
        # 9. Parse stock data JSON
        stock_data_json = json.loads(data[0][2])
        
        # 10. Extract specific price data
        price_data = stock_data_json[0][0][0][5]
        previous_close = stock_data_json[0][0][0][8]
        currency = stock_data_json[0][0][0][4]
        
        # Create result object matching the JavaScript example
        result = {
            'symbol': ticker,
            'price': float(price_data[0]),
            'change': float(price_data[1]),
            'change_percent': float(price_data[2]),
            'prev_close': previous_close,
            'currency': currency,
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache the result
        cache.set(cache_key, result, cache_time)
        
        return result
        
    except Exception as e:
        # Log the error but don't crash
        import logging
        logging.error(f"Error fetching Google Finance advanced data for {ticker}: {str(e)}")
        
        # Return error object
        return {
            'symbol': ticker,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
