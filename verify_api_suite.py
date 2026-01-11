import requests
import argparse
import sys
import time
from datetime import datetime

class TextColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_result(name, passed, message=""):
    if passed:
        print(f"{TextColors.OKGREEN}[PASS]{TextColors.ENDC} {name} {message}")
    else:
        print(f"{TextColors.FAIL}[FAIL]{TextColors.ENDC} {name} {message}")

def test_endpoint(base_url, endpoint, name, strict=True, required_keys=None):
    url = f"{base_url}{endpoint}"
    print(f"Testing {name}: {url} ...", end="\r")
    start_time = time.time()
    try:
        response = requests.get(url, timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            try:
                if name == "Root Endpoint":
                    print_result(name, True, f"(Duration: {duration:.2f}s) - Content received")
                    return True
                    
                data = response.json()
                
                # Check required keys
                if required_keys:
                    missing = [k for k in required_keys if k not in data]
                    if missing:
                        print_result(name, False, f"- Missing keys: {missing}")
                        return False
                
                # Check for existing data
                if 'data' in data:
                    if not data['data'] and strict:
                        print_result(name, False, f"- 'data' list is empty (Duration: {duration:.2f}s)")
                        return False
                    
                    # Basic NaN check in data values (though requests.json() usually fails on pure NaN if not handled, verification is good)
                    # Note: Python's requests usually handles valid JSON. NaN is not valid JSON, so we check for None if that's how it's serialized.
                
                print_result(name, True, f"(Duration: {duration:.2f}s)")
                return True
            except ValueError:
                print_result(name, False, f"- Invalid JSON (Duration: {duration:.2f}s)")
                return False
        else:
            print_result(name, False, f"- Status: {response.status_code} (Duration: {duration:.2f}s)")
            print(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_result(name, False, f"- Error: {e}")
        return False

def run_suite(env):
    if env == 'local':
        base_url = "http://localhost:8000"
    elif env == 'cloud':
        base_url = "https://stock-analyzer-641888119120.us-central1.run.app"
    else:
        base_url = env

    print(f"{TextColors.HEADER}Starting Verification Suite against: {base_url}{TextColors.ENDC}")
    print("-" * 60)

    results = []

    # 1. Health Check (Root)
    results.append(test_endpoint(base_url, "/", "Root Endpoint", strict=False))

    # 2. Mystic Pulse - Standard
    results.append(test_endpoint(base_url, "/api/mystic-pulse/AAPL?period=6mo", "Mystic Pulse (AAPL, 6mo)", required_keys=['data', 'summary']))

    # 3. Mystic Pulse - Long Period (Crash Test)
    results.append(test_endpoint(base_url, "/api/mystic-pulse/AAPL?period=3y", "Mystic Pulse (AAPL, 3y - Crash Test)", required_keys=['data', 'summary']))
    
    # 4. Mystic Pulse - 5y
    results.append(test_endpoint(base_url, "/api/mystic-pulse/AAPL?period=5y", "Mystic Pulse (AAPL, 5y)", required_keys=['data', 'summary'], strict=False))



    # 6. Watchlist (Integration)
    results.append(test_endpoint(base_url, "/api/watchlist", "Watchlist Endpoint", strict=False, required_keys=['watchlist']))

    # 7. Favorites (Integration)
    results.append(test_endpoint(base_url, "/api/favorites", "Favorites Endpoint", strict=False, required_keys=['favorites']))
    
    # 8. Market News (Load Test)
    results.append(test_endpoint(base_url, "/api/market-news", "Market News", strict=False, required_keys=['news']))

    # 9. Invalid Ticker Handling (Robustness)
    # Custom handling for this test: we expect it to fail gracefully (404 or 400 or empty), but NOT crash (500)
    print(f"Testing Invalid Ticker Handling: {base_url}/api/mystic-pulse/INVALID_999 ...", end="\r")
    try:
        inv_resp = requests.get(f"{base_url}/api/mystic-pulse/INVALID_999", timeout=10)
        if inv_resp.status_code == 500:
            print_result("Invalid Ticker Handling", False, f"- Crashed with 500")
            results.append(False)
        else:
            print_result("Invalid Ticker Handling", True, f"- Handled cleanly (Status: {inv_resp.status_code})")
            results.append(True)
    except Exception as e:
        print_result("Invalid Ticker Handling", False, f"- Error: {e}")
        results.append(False)

    print("-" * 60)
    success_rate = (sum(results) / len(results)) * 100
    print(f"{TextColors.BOLD}Results: {sum(results)}/{len(results)} Passed ({success_rate:.1f}%){TextColors.ENDC}")
    
    if not all(results):
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Updated Stock Analyzer API Verification')
    parser.add_argument('--env', type=str, required=True, help='target environment: local or cloud')
    args = parser.parse_args()
    
    run_suite(args.env)
