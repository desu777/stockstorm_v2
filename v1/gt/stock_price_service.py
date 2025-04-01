import json
import time
import random
import requests
import logging
from datetime import datetime
from django.core.cache import cache

logger = logging.getLogger(__name__)

class StockPriceService:
    """
    Service for fetching stock prices from multiple sources with fallback mechanisms
    """
    
    @staticmethod
    def get_price(ticker, cache_time=240, exchange="NASDAQ"):
        """
        Get the current stock price, trying multiple sources with fallback
        
        Args:
            ticker (str): Stock ticker symbol
            cache_time (int): Time in seconds to cache results
            exchange (str): Stock exchange
            
        Returns:
            float: Current stock price or None if all sources fail
        """
        cache_key = f"stock_price_{ticker}"
        cached_price = cache.get(cache_key)
        
        if cached_price is not None:
            return cached_price
            
        # Try Google Finance first
        price = StockPriceService._get_google_finance_price(ticker, exchange)
        
        # If Google Finance fails, try Yahoo Finance
        if price is None:
            price = StockPriceService._get_yahoo_finance_price(ticker)
            
        # If we got a price, cache it
        if price is not None:
            cache.set(cache_key, price, cache_time)
            
        return price
    
    @staticmethod
    def get_price_data(ticker, cache_time=240, exchange="NASDAQ"):
        """
        Get detailed stock price data with fallback mechanisms
        
        Args:
            ticker (str): Stock ticker symbol
            cache_time (int): Time in seconds to cache results
            exchange (str): Stock exchange
            
        Returns:
            dict: Dictionary with stock data or error information
        """
        cache_key = f"stock_price_data_{ticker}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        # Try Google Finance first
        data = StockPriceService._get_google_finance_price_data(ticker, exchange)
        
        # If Google Finance fails, try Yahoo Finance
        if data is None or 'error' in data:
            data = StockPriceService._get_yahoo_finance_price_data(ticker)
            
        # If we got valid data, cache it
        if data is not None and 'error' not in data:
            cache.set(cache_key, data, cache_time)
            
        return data
    
    @staticmethod
    def _get_google_finance_price(ticker, exchange="NASDAQ"):
        """
        Try to get stock price from Google Finance
        
        Args:
            ticker (str): Stock ticker symbol
            exchange (str): Stock exchange
            
        Returns:
            float: Current stock price or None if an error occurred
        """
        try:
            data = StockPriceService._get_google_finance_price_data(ticker, exchange)
            if data and 'price' in data:
                return data['price']
            return None
        except Exception as e:
            logger.error(f"Error getting Google Finance price for {ticker}: {e}")
            return None
    
    @staticmethod
    def _get_google_finance_price_data(ticker, exchange="NASDAQ"):
        """
        Get detailed stock data from Google Finance
        
        Args:
            ticker (str): Stock ticker symbol
            exchange (str): Stock exchange
            
        Returns:
            dict: Dictionary with stock data or None if an error occurred
        """
        try:
            # Start a session to maintain cookies
            session = requests.Session()
            
            # First visit the Google Finance page to get cookies
            finance_page_url = f"https://www.google.com/finance/quote/{ticker}:{exchange}"
            session.get(finance_page_url, timeout=5)
            
            # Prepare API URL with query parameters
            url = "https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute"
            
            params = {
                "rpcids": "xh8wxf",
                "source-path": f"/finance/quote/{ticker}:{exchange}",
                "f.sid": "-4555936157889558623",
                "bl": "boq_finance-ui_20250326.00_p0",
                "hl": "en",
                "soc-app": "162",
                "soc-platform": "1",
                "soc-device": "1",
                "_reqid": str(random.randint(100000, 999999)),
                "rt": "c"
            }
            
            # Enhanced headers with more browser-like values
            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://www.google.com",
                "Referer": finance_page_url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "X-Same-Domain": "1",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty"
            }
            
            # Prepare data as proper form parameters
            current_time = int(time.time() * 1000)
            req_data = f'[[[null,["{ticker}","{exchange}"]]]]'
            
            data = {
                'f.req': f'[[["xh8wxf","{req_data}",null,"27"]]]',
                'at': f'ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}'
            }
            
            # Send request with timeout
            response = session.post(url, params=params, headers=headers, data=data, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"Google Finance API returned status {response.status_code} for {ticker}")
                return None
            
            # Process response
            text = response.text
            
            # Remove )]}'
            if text.startswith(")]}'\\n"):
                text = text[5:]
            elif text.startswith(")]}'"):
                text = text[4:]
                
            # Parse JSON
            start_idx = text.find('[')
            if start_idx == -1:
                logger.warning(f"Invalid Google Finance response format for {ticker}")
                return None
            
            data = json.loads(text[start_idx:])
            
            # Check data structure
            if not data or not data[0] or len(data[0]) < 3 or not data[0][2]:
                logger.warning(f"Unexpected Google Finance data structure for {ticker}")
                return None
            
            # Parse stock data
            stock_data_json = json.loads(data[0][2])
            
            # Extract price data
            try:
                price_data = stock_data_json[0][0][0][5]
                previous_close = stock_data_json[0][0][0][8]
                
                # Create result
                result = {
                    'symbol': ticker,
                    'price': float(price_data[0]),
                    'change': float(price_data[1]),
                    'change_percent': float(price_data[2]),
                    'prev_close': previous_close,
                    'currency': stock_data_json[0][0][0][4],
                    'source': 'google_finance',
                    'timestamp': datetime.now().isoformat()
                }
                
                return result
            except (IndexError, KeyError, ValueError) as e:
                logger.error(f"Error parsing Google Finance data for {ticker}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching from Google Finance for {ticker}: {e}")
            return {
                'symbol': ticker,
                'error': str(e),
                'source': 'google_finance',
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def _get_yahoo_finance_price(ticker):
        """
        Get stock price from Yahoo Finance API
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            float: Current stock price or None if an error occurred
        """
        try:
            data = StockPriceService._get_yahoo_finance_price_data(ticker)
            if data and 'price' in data:
                return data['price']
            return None
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance price for {ticker}: {e}")
            return None
    
    @staticmethod
    def _get_yahoo_finance_price_data(ticker):
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
