import json
import time
import requests
from datetime import datetime

def test_google_finance_price(ticker, exchange="NASDAQ"):
    """
    Standalone test function for Google Finance API without Django dependencies
    Using approach similar to the JavaScript example
    """
    print(f"Testing Google Finance API for {ticker}:{exchange}...")
    
    # Google Finance API URL
    url = f"https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute?rpcids=xh8wxf&source-path=%2Ffinance%2Fquote%2F{ticker}%3A{exchange}&f.sid=-4555936157889558623&bl=boq_finance-ui_20250326.00_p0&hl=pl&soc-app=162&soc-platform=1&soc-device=1&_reqid=2259984&rt=c"
    
    # Required headers
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://www.google.com",
        "Referer": "https://www.google.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Request body data - EXACTLY as in the JavaScript example
    body = f'f.req=[[["xh8wxf","[[[null,[\"{ticker}\",\"{exchange}\"]]]]",null,"27"]]]&at=ANCgWpQJf6_tQ2jv3Gjhtm9qjh4x:{int(time.time() * 1000)}'
    
    try:
        # Make POST request to Google Finance API
        response = requests.post(url, headers=headers, data=body)
        print(f"Response status: {response.status_code}")
        
        # Parse the response
        content = response.text
        print(f"Response starts with: {content[:50]}...")
        
        # Remove prefix if present
        if content.startswith(")]}'"):
            content = content[4:]
            print("Removed )]}'")
        
        try:
            # Parse using the approach from JavaScript example
            data_start_index = content.find('[')
            if data_start_index == -1:
                print("ERROR: Could not find start of JSON data")
                return None
                
            json_text = content[data_start_index:]
            print(f"JSON text starts with: {json_text[:50]}...")
            
            # Parse the data exactly as in the JavaScript example
            data = json.loads(json_text)
            stock_data_json = json.loads(data[0][2])
            price_data = stock_data_json[0][0][0][5]
            
            result = {
                'symbol': ticker,
                'price': price_data[0],
                'change': price_data[1],
                'change_percent': price_data[2],
                'prev_close': stock_data_json[0][0][0][8],
                'name': stock_data_json[0][0][0][2] # Company name
            }
            
            print("\nSUCCESS! Extracted data:")
            for key, value in result.items():
                print(f"{key}: {value}")
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON decode error: {e}")
            print(f"Content sample that failed to parse: {json_text[:200]}...")
            return None
            
        except (IndexError, KeyError) as e:
            print(f"ERROR: Failed to extract data from JSON: {e}")
            print(f"JSON structure: {data[:50]}...")
            return None
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Test with NVDA
    test_google_finance_price("NVDA")
    
    # Test with a few other tickers to verify
    test_google_finance_price("AAPL")
    test_google_finance_price("MSFT")
