import json
import time
import random
import requests
from datetime import datetime

def get_stock_price(symbol, exchange="NASDAQ"):
    """
    Get stock price from Google Finance API with robust error handling
    """
    try:
        # Start a session to maintain cookies
        session = requests.Session()
        
        # First visit the Google Finance page to get cookies
        finance_page_url = f"https://www.google.com/finance/quote/{symbol}:{exchange}"
        session.get(finance_page_url)
        
        # Prepare API URL with query parameters
        url = "https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute"
        
        params = {
            "rpcids": "xh8wxf",
            "source-path": f"/finance/quote/{symbol}:{exchange}",
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
        
        # Prepare data as proper form parameters (not a formatted string)
        current_time = int(time.time() * 1000)
        req_data = f'[[[null,["{symbol}","{exchange}"]]]]'
        
        data = {
            'f.req': f'[[["xh8wxf","{req_data}",null,"27"]]]',
            'at': f'ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}'
        }
        
        print(f"Sending request for {symbol}:{exchange}...")
        response = session.post(url, params=params, headers=headers, data=data)
        
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.text[:200]}...")
            raise Exception(f"HTTP error! Status: {response.status_code}")
        
        # Process response
        text = response.text
        print(f"Received response of length {len(text)} characters")
        
        # Remove )]}'
        if text.startswith(")]}'\\n"):
            text = text[5:]
        elif text.startswith(")]}'"):
            text = text[4:]
            
        # Parse JSON
        start_idx = text.find('[')
        if start_idx == -1:
            raise Exception("Invalid response format - array start not found")
        
        data = json.loads(text[start_idx:])
        
        # Check data structure
        if not data or not data[0] or len(data[0]) < 3 or not data[0][2]:
            raise Exception("Unexpected data structure in response")
        
        # Parse stock data
        stock_data_json = json.loads(data[0][2])
        
        # Debug first bit of the structure
        print(f"Stock data structure preview: {json.dumps(stock_data_json)[:200]}...")
        
        # Extract price data
        price_data = stock_data_json[0][0][0][5]
        previous_close = stock_data_json[0][0][0][8]
        
        # Create result
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
        import traceback
        traceback.print_exc()
        return {
            'symbol': symbol,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# Test with a single stock
if __name__ == "__main__":
    result = get_stock_price('TSLA')
    print("\nFinal result:")
    print(json.dumps(result, indent=2))
