# hpcrypto/utils.py
from binance.client import Client
from binance.exceptions import BinanceAPIException
from django.core.cache import cache
import logging
import time

logger = logging.getLogger(__name__)

def get_binance_price(user, ticker, cache_time=60):
    """
    Fetch price from Binance for a given ticker with improved caching.
    
    Args:
        user: The user object (to get API credentials)
        ticker: The ticker symbol (e.g., "BTC", "ETH")
        cache_time: Cache duration in seconds (default: 60 seconds)
        
    Returns:
        float: Current price or None if error
    """
    # Format ticker for Binance if needed
    if ticker.endswith('USDT') or ticker.endswith('USDC'):
        binance_ticker = ticker
    else:
        # Try USDT pair first, as it's more common
        binance_ticker = f"{ticker}USDT"
    
    # Check cache first
    cache_key = f"binance_price_{binance_ticker}"
    cached_price = cache.get(cache_key)
    if cached_price:
        logger.debug(f"Cache hit for {binance_ticker}: {cached_price}")
        return cached_price
    
    # Get global API rate limit cache to prevent too many requests
    rate_limit_key = "binance_api_last_call"
    last_call_time = cache.get(rate_limit_key)
    current_time = time.time()
    
    # If we've made a call in the last 0.5 second, wait a bit
    if last_call_time and current_time - last_call_time < 0.5:
        wait_time = 0.5 - (current_time - last_call_time)
        logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before API call")
        time.sleep(wait_time)
    
    try:
        # Get user's Binance credentials
        profile = getattr(user, 'profile', None)
        if not profile or not profile.binance_api_key or not profile.binance_api_secret_enc:
            logger.warning(f"User {user.id} missing Binance API credentials")
            return None
        
        api_key = profile.binance_api_key
        api_secret = profile.get_binance_api_secret()
        
        # Create client and fetch price
        client = Client(api_key, api_secret)
        
        try:
            ticker_data = client.get_symbol_ticker(symbol=binance_ticker)
            price = float(ticker_data['price'])
        except BinanceAPIException as e:
            # If the first attempt fails with USDT and it wasn't explicitly specified,
            # try with USDC instead
            if not ticker.endswith('USDT') and not ticker.endswith('USDC') and "USDT" in binance_ticker:
                logger.info(f"USDT pair not found for {ticker}, trying USDC pair")
                binance_ticker = f"{ticker}USDC"
                ticker_data = client.get_symbol_ticker(symbol=binance_ticker)
                price = float(ticker_data['price'])
                # Update cache key for the actual pair we used
                cache_key = f"binance_price_{binance_ticker}"
            else:
                # If it was explicitly specified or second attempt also failed, re-raise
                raise
        
        # Update rate limit cache
        cache.set(rate_limit_key, time.time(), 60)
        
        # Cache price
        cache.set(cache_key, price, cache_time)
        logger.debug(f"Updated price for {binance_ticker}: {price}")
        
        return price
        
    except BinanceAPIException as e:
        logger.error(f"Binance API error for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching Binance price for {ticker}: {e}")
        return None

def get_bulk_binance_prices(user, tickers, cache_time=60):
    """
    Fetch prices for multiple tickers in an efficient way.
    
    Args:
        user: The user object (to get API credentials)
        tickers: List of ticker symbols
        cache_time: Cache duration in seconds
        
    Returns:
        dict: Mapping of ticker symbols to prices
    """
    results = {}
    
    # Get user's Binance credentials
    profile = getattr(user, 'profile', None)
    if not profile or not profile.binance_api_key or not profile.binance_api_secret_enc:
        logger.warning(f"User {user.id} missing Binance API credentials")
        return get_public_binance_prices(tickers, cache_time)
    
    # Create Binance client only once
    try:
        api_key = profile.binance_api_key
        api_secret = profile.get_binance_api_secret()
        client = Client(api_key, api_secret)
        
        # Prepare list of Binance-formatted tickers
        binance_tickers = []
        ticker_mapping = {}  # Maps binance format back to original format
        usdt_tickers = set()  # Track which tickers we try with USDT
        
        for ticker in tickers:
            if ticker.endswith('USDT') or ticker.endswith('USDC'):
                binance_ticker = ticker
            else:
                # Default to USDT pair first
                binance_ticker = f"{ticker}USDT"
                usdt_tickers.add(ticker)  # Mark this as a ticker we assumed USDT for
            
            # Check cache first
            cache_key = f"binance_price_{binance_ticker}"
            cached_price = cache.get(cache_key)
            if cached_price:
                results[ticker] = cached_price
            else:
                binance_tickers.append(binance_ticker)
                ticker_mapping[binance_ticker] = ticker
        
        # If we still have tickers to fetch
        if binance_tickers:
            # Get all tickers at once
            prices = client.get_all_tickers()
            price_by_symbol = {price_data['symbol']: float(price_data['price']) for price_data in prices}
            
            # Process results for tickers we have
            for binance_ticker, original_ticker in ticker_mapping.items():
                if binance_ticker in price_by_symbol:
                    price = price_by_symbol[binance_ticker]
                    results[original_ticker] = price
                    
                    # Cache this price
                    cache_key = f"binance_price_{binance_ticker}"
                    cache.set(cache_key, price, cache_time)
                elif original_ticker in usdt_tickers:
                    # If we assumed USDT but it's not found, try USDC
                    usdc_ticker = f"{original_ticker}USDC"
                    if usdc_ticker in price_by_symbol:
                        price = price_by_symbol[usdc_ticker]
                        results[original_ticker] = price
                        
                        # Cache this price
                        cache_key = f"binance_price_{usdc_ticker}"
                        cache.set(cache_key, price, cache_time)
                        logger.info(f"Used USDC pair instead of USDT for {original_ticker}")
    
    except BinanceAPIException as e:
        logger.error(f"Binance API error in bulk price fetch: {e}")
        # Fall back to public API
        return get_public_binance_prices(tickers, cache_time)
    except Exception as e:
        logger.error(f"Error in bulk price fetch: {e}")
        # Fall back to public API
        return get_public_binance_prices(tickers, cache_time)
    
    return results

def get_public_binance_prices(tickers, cache_time=60):
    """
    Fetch prices for multiple tickers using the public Binance API without authentication.
    
    Args:
        tickers: List of ticker symbols
        cache_time: Cache duration in seconds
        
    Returns:
        dict: Mapping of ticker symbols to prices
    """
    results = {}
    
    try:
        # Create client without authentication
        client = Client("", "")
        
        # Prepare list of Binance-formatted tickers
        binance_tickers = []
        ticker_mapping = {}  # Maps binance format back to original format
        usdt_tickers = set()  # Track which tickers we try with USDT
        
        for ticker in tickers:
            if ticker.endswith('USDT') or ticker.endswith('USDC'):
                binance_ticker = ticker
            else:
                # Default to USDT pair first
                binance_ticker = f"{ticker}USDT"
                usdt_tickers.add(ticker)  # Mark this as a ticker we assumed USDT for
            
            # Check cache first
            cache_key = f"binance_price_{binance_ticker}"
            cached_price = cache.get(cache_key)
            if cached_price:
                results[ticker] = cached_price
            else:
                binance_tickers.append(binance_ticker)
                ticker_mapping[binance_ticker] = ticker
        
        # If we still have tickers to fetch
        if binance_tickers:
            # Get all tickers at once
            prices = client.get_all_tickers()
            price_by_symbol = {price_data['symbol']: float(price_data['price']) for price_data in prices}
            
            # Process results for tickers we have
            for binance_ticker, original_ticker in ticker_mapping.items():
                if binance_ticker in price_by_symbol:
                    price = price_by_symbol[binance_ticker]
                    results[original_ticker] = price
                    
                    # Cache this price
                    cache_key = f"binance_price_{binance_ticker}"
                    cache.set(cache_key, price, cache_time)
                elif original_ticker in usdt_tickers:
                    # If we assumed USDT but it's not found, try USDC
                    usdc_ticker = f"{original_ticker}USDC"
                    if usdc_ticker in price_by_symbol:
                        price = price_by_symbol[usdc_ticker]
                        results[original_ticker] = price
                        
                        # Cache this price
                        cache_key = f"binance_price_{usdc_ticker}"
                        cache.set(cache_key, price, cache_time)
                        logger.info(f"Used USDC pair instead of USDT for {original_ticker}")
        
    except BinanceAPIException as e:
        logger.error(f"Binance public API error in bulk price fetch: {e}")
    except Exception as e:
        logger.error(f"Error in public bulk price fetch: {e}")
    
    return results