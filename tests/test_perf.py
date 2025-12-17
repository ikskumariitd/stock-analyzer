import time
import json
import urllib.request
import urllib.parse
import sys

def test_performance(port=8001):
    base_url = f"http://localhost:{port}/api"
    print(f"Testing against {base_url}")
    
    # 1. Warm-up (single ticker)
    try:
        print("Warming up...")
        urllib.request.urlopen(f"{base_url}/analyze/AAPL")
    except Exception as e:
        print(f"Warm-up failed: {e}")
        # Continue anyway, server might be starting
    
    # 2. Test Bulk (20 tickers)
    tickers = [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", 
        "GOOG", "TSLA", "META", "BRK-B", "UNH",
        "JNJ", "XOM", "V", "JPM", "PG", 
        "MA", "LLY", "HD", "CVX", "MRK"
    ]
    
    payload = json.dumps({"tickers": tickers}).encode('utf-8')
    req = urllib.request.Request(
        f"{base_url}/analyze-batch", 
        data=payload, 
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"Starting bulk request for {len(tickers)} tickers...")
    start_time = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            duration = time.time() - start_time
            
            print(f"Bulk request finished in {duration:.2f} seconds")
            print(f"Got {len(data)} results")
            
            # Validation
            if len(data) != len(tickers):
                print("FAIL: Count mismatch")
            else:
                print("PASS: Count match")
                
            # Check for error
            errors = [d for d in data if 'error' in d]
            if errors:
                print(f"WARNING: {len(errors)} errors found: {errors}")
            else:
                print("PASS: All successful")
                
            # Performance Assertion
            if duration < 5.0:
                print("PASS: Performance checks out (< 5s)")
            else:
                print(f"FAIL: Too slow ({duration:.2f}s)")
                
            # Check structure (sentiment should be skipped/neutral)
            sample = data[0]
            if sample.get('sentiment', {}).get('mood') == 'Neutral':
                print("PASS: Sentiment skipped as expected")
            else:
                print(f"WARNING: Sentiment might not be skipped properly: {sample.get('sentiment')}")

    except Exception as e:
        print(f"Bulk test failed with error: {e}")

if __name__ == "__main__":
    port = 8001
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    test_performance(port)
