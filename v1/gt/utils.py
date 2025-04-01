# gt/utils.py
import os
import logging
import time
import json
import re
from decimal import Decimal
import requests
from django.core.cache import cache
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_alpha_vantage_api_key():
    """Get Alpha Vantage API key from environment variable"""
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        logger.warning("ALPHA_VANTAGE_API_KEY not found in environment variables, using default key")
        api_key = 'PI2559COXZU5J33F'  # Fallback key from .env
    return api_key

def get_stock_price(ticker, cache_time=240):
    """
    Get the current stock price using Yahoo Finance API
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Time in seconds to cache results
        
    Returns:
        float: Current stock price or None if all sources fail
    """
    cache_key = f"stock_price_{ticker}"
    cached_price = cache.get(cache_key)
    
    if cached_price is not None:
        return cached_price
        
    # Get price from Yahoo Finance
    price = get_yahoo_finance_price(ticker)
        
    # If we got a price, cache it
    if price is not None:
        cache.set(cache_key, price, cache_time)
        
    return price

def get_stock_price_advanced(ticker, cache_time=240):
    """
    Get detailed stock price data from Yahoo Finance
    
    Args:
        ticker (str): Stock ticker symbol
        cache_time (int): Time in seconds to cache results
        
    Returns:
        dict: Dictionary with stock data including price, change, percent change
    """
    cache_key = f"stock_price_advanced_{ticker}"
    cached_data = cache.get(cache_key)
    
    if cached_data is not None:
        return cached_data
        
    # Get data from Yahoo Finance
    data = get_yahoo_finance_price_advanced(ticker)
        
    # If we got valid data, cache it
    if data is not None and 'error' not in data:
        cache.set(cache_key, data, cache_time)
        
    return data

def get_yahoo_finance_price(ticker):
    """
    Get stock price from Yahoo Finance API
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        float: Current stock price or None if an error occurred
    """
    try:
        data = get_yahoo_finance_price_advanced(ticker)
        if data and 'price' in data:
            return data['price']
        return None
    except Exception as e:
        logger.error(f"Error getting Yahoo Finance price for {ticker}: {e}")
        return None

def get_yahoo_finance_price_advanced(ticker):
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
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance for {ticker}: {e}")
        return {
            'symbol': ticker,
            'error': str(e),
            'source': 'yahoo_finance',
            'timestamp': datetime.now().isoformat()
        }

def get_stock_daily_data(ticker, days=100):
    """
    Function kept for backward compatibility
    Now returns the current price data only
    
    Args:
        ticker: The stock symbol
        days: Number of days (unused)
        
    Returns:
        dict: Dictionary containing price data
    """
    return get_stock_price_advanced(ticker)

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
        else:
            tickers_to_fetch.append(ticker)
    
    # If all tickers were cached, return the results
    if not tickers_to_fetch:
        return results
    
    # Fetch each ticker individually
    for ticker in tickers_to_fetch:
        try:
            price = get_stock_price(ticker, cache_time=cache_time)
            results[ticker] = price
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance price for {ticker}: {e}")
            logger.exception(e)  # Log full exception details with traceback
    
    return results