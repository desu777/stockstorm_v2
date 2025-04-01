import json
import time
import random
import requests
from datetime import datetime

def get_stock_price(symbol, exchange="NASDAQ"):
    """
    Get stock price from Google Finance API
    Following the exact pattern from the JavaScript example
    """
    try:
        # 1. Prepare URL with proper encoding
        reqid = random.randint(1000000, 9999999)
        url = f"https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?rpcids=xh8wxf&source-path=%2Ffinance%2Fquote%2F{symbol}%3A{exchange}&f.sid=-4555936157889558623&bl=boq_finance-ui_20250326.00_p0&hl=pl&soc-app=162&soc-platform=1&soc-device=1&_reqid={reqid}&rt=c"
        
        # 2. Prepare request body with the same pattern as JavaScript example
        current_time = int(time.time() * 1000)
        body = f'f.req=[[["xh8wxf","[[[null,[\"{symbol}\",\"{exchange}\"]]]]",null,"27"]]]&at=ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}&'
        
        # 3. Send request
        print(f"Sending request for {symbol}:{exchange}...")
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
        print(f"Received response of length {len(text)} characters")
        
        # 6. Remove prefix )]}' if present
        if text.startswith(")]}'\\n"):
            text = text[5:]
        elif text.startswith(")]}'"):
            text = text[4:]
            
        # 7. Parse first part of response
        start_idx = text.find('[')
        if start_idx == -1:
            raise Exception("Invalid response format - array start not found")
        
        data = json.loads(text[start_idx:])
        
        # 8. Check if we have the expected data structure
        if not data or not data[0] or not data[0][2]:
            raise Exception("Unexpected data structure in response")
        
        # 9. Parse stock data JSON
        stock_data_json = json.loads(data[0][2])
        
        # 10. Debug data structures
        print(f"Price data structure: {json.dumps(stock_data_json[0][0][0])[:200]}...")
        
        # 11. Extract specific price data
        price_data = stock_data_json[0][0][0][5]
        previous_close = stock_data_json[0][0][0][8]
        
        # 12. Create result object
        result = {
            'symbol': symbol,
            'price': float(price_data[0]),
            'change': float(price_data[1]),
            'change_percent': float(price_data[2]),
            'previous_close': previous_close,
            'currency': stock_data_json[0][0][0][4],
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Successfully retrieved data for {symbol}: {result['price']} {result['currency']}")
        return result
        
    except Exception as e:
        print(f"Error retrieving data for {symbol}:", e)
        return {
            'symbol': symbol,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def monitor_stocks(symbols, interval=60):
    """
    Monitor multiple stocks with delay
    """
    try:
        print(f"--- Updating price data: {datetime.now().isoformat()} ---")
        
        for symbol in symbols:
            try:
                data = get_stock_price(symbol)
                if 'error' not in data:
                    sign = '+' if data['change'] > 0 else ''
                    print(f"{symbol}: {data['price']} ({sign}{data['change']:.2f}, {data['change_percent']:.2f}%)")
                else:
                    print(f"{symbol}: Error - {data['error']}")
                
                # Add random delay between requests (1-3 seconds)
                delay = 1 + random.random() * 2
                time.sleep(delay)
            except Exception as e:
                print(f"Error for {symbol}:", e)
        
        print(f"Next update in {interval} seconds")
    except Exception as e:
        print(f"Error in monitor_stocks:", e)

# Example usage
if __name__ == "__main__":
    # Single stock fetch
    print("\n=== SINGLE STOCK TEST ===")
    data = get_stock_price('NVDA')
    print('Single fetch result:', data)
    
    # Monitor multiple stocks
    print("\n=== MULTIPLE STOCKS TEST ===")
    monitor_stocks(['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN'])
