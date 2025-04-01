import json
import time
import random
import requests
from datetime import datetime

def test_google_finance_price(ticker, exchange="NASDAQ"):
    """
    Test function for the updated Google Finance API implementation
    """
    print(f"Testing Google Finance API for {ticker}:{exchange}...")
    
    # Google Finance API URL with proper encoding
    url = "https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute"
    
    # Required headers
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://www.google.com",
        "Referer": f"https://www.google.com/finance/quote/{ticker}:{exchange}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Query parameters
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
    
    # Request body data in the exact format required
    current_time = int(time.time() * 1000)
    req_data = f'[[[null,["{ticker}","{exchange}"]]]]'
    
    body = {
        'f.req': f'[[["xh8wxf","{req_data}",null,"27"]]]',
        'at': f'ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{current_time}'
    }
    
    try:
        # Make POST request to Google Finance API
        response = requests.post(url, headers=headers, params=params, data=body)
        print(f"Response status: {response.status_code}")
        
        # Parse the response (remove )]}' prefix if present)
        content = response.text
        print(f"Response starts with: {content[:50]}...")
        
        if content.startswith(")]}'"):
            content = content[4:]
            print("Removed )]}'")
        
        # Find the start of the JSON data
        data_start_index = content.find('[')
        if data_start_index == -1:
            print("ERROR: Could not find start of JSON data")
            return None
            
        # In case there are multiple JSON arrays in the response, we need to properly extract just the first one
        json_text = content[data_start_index:]
        
        # Find where the first JSON array ends
        bracket_count = 0
        end_index = 0
        
        for i, char in enumerate(json_text):
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_index = i + 1
                    break
        
        if end_index > 0:
            json_text = json_text[:end_index]
            
        print(f"Extracted JSON: {json_text[:100]}...")
        
        try:
            # Parse the JSON structure
            data = json.loads(json_text)
            
            if isinstance(data, list) and len(data) > 0 and len(data[0]) > 2:
                stock_data_json = json.loads(data[0][2])
                
                # Print the structure to understand it better
                print(f"Stock data structure: {str(stock_data_json)[:200]}...")
                
                # Extract data elements
                if len(stock_data_json) > 0 and len(stock_data_json[0]) > 0:
                    main_data = stock_data_json[0][0][0]
                    company_name = main_data[2] if len(main_data) > 2 else ticker
                    price_data = main_data[5] if len(main_data) > 5 else None
                    prev_close = main_data[8] if len(main_data) > 8 else None
                    
                    if price_data and len(price_data) >= 3:
                        # Parse price data elements
                        current_price = float(price_data[0])
                        price_change = float(price_data[1])
                        price_change_percent = float(price_data[2])
                        
                        # Create result object
                        result = {
                            'symbol': ticker,
                            'name': company_name,
                            'price': current_price,
                            'change': price_change,
                            'change_percent': price_change_percent,
                            'prev_close': prev_close,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print("\nSUCCESS! Extracted data:")
                        for key, value in result.items():
                            print(f"{key}: {value}")
                            
                        return result
                    else:
                        print("ERROR: Price data not found in the expected structure")
                else:
                    print("ERROR: Stock data JSON structure is not as expected")
            else:
                print("ERROR: Unexpected response format")
                print(f"Response data: {data}")
                
            return None
            
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            print(f"ERROR parsing JSON: {e}")
            print(f"Content sample that failed to parse: {json_text[:200]}...")
            return None
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with NVDA
    test_google_finance_price("NVDA")
    
    # Add a random delay between requests (1-3 seconds)
    time.sleep(random.uniform(1, 3))
    
    # Test with a few other tickers
    test_google_finance_price("AAPL")
    
    # Add a random delay between requests
    time.sleep(random.uniform(1, 3))
    
    test_google_finance_price("MSFT")
