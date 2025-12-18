import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
SYMBOL = "AAPL"
PERIODS = ["6mo", "1y", "3y", "5y"]

def test_mystic_pulse_periods():
    print(f"Testing Mystic Pulse API for symbol: {SYMBOL}")
    
    for period in PERIODS:
        print(f"  Testing period: {period}...", end=" ")
        try:
            url = f"{BASE_URL}/api/mystic-pulse/{SYMBOL}?period={period}"
            res = requests.get(url)
            
            if res.status_code != 200:
                print(f"FAILED (Status: {res.status_code})")
                print(f"    Response: {res.text}")
                return False
            
            data = res.json()
            if not data.get("data"):
                print("FAILED (No data returned)")
                return False
                
            data_points = len(data["data"])
            print(f"SUCCESS (Returned {data_points} points)")
            
            # Basic sanity check on data points count (should increase with period)
            # This is rough estimation as trading days vary
            expected_min = {
                "6mo": 100,
                "1y": 200,
                "3y": 600,
                "5y": 1000
            }
            
            if data_points < expected_min[period]:
                print(f"    WARNING: Data points ({data_points}) seem low for {period}")

        except Exception as e:
            print(f"ERROR: {e}")
            return False
            
    return True

if __name__ == "__main__":
    if not test_mystic_pulse_periods():
        sys.exit(1)
    print("\nAll period tests passed!")
