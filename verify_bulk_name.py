import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_bulk_name():
    # Use > 10 tickers to trigger bulk mode
    tickers = ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA", "META", "NVDA", "AMD", "INTC", "NFLX", "DIS"]
    
    payload = {
        "tickers": tickers,
        "refresh": True # Force refresh to hit the new logic
    }
    
    print(f"Sending bulk request for {len(tickers)} tickers...")
    try:
        res = requests.post(f"{BASE_URL}/api/analyze-batch", json=payload, timeout=60)
        if res.status_code != 200:
            print(f"Failed: {res.text}")
            return False
            
        data = res.json()
        print(f"Received {len(data)} results.")
        
        goog = next((r for r in data if r['symbol'] == 'GOOG'), None)
        if goog:
            print(f"GOOG name: '{goog['name']}'")
            if goog['name'] == "Alphabet Inc. Class C":
                print("SUCCESS: Retrieved correct full name from POPULAR_STOCKS")
                return True
            elif goog['name'] == "GOOG":
                print("FAILURE: Name is still matching symbol")
                return False
            else:
                print(f"WARNING: Name is '{goog['name']}' (Unexpected)")
                return True
        else:
            print("GOOG not found in results")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_bulk_name()
