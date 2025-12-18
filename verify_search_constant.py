import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_search_constant():
    # Searching for "AAPL" should return "Apple Inc." from the dictionary
    query = "AAPL"
    print(f"Searching for '{query}'...")
    try:
        res = requests.get(f"{BASE_URL}/api/search-stocks/{query}")
        if res.status_code != 200:
            print(f"Failed: {res.text}")
            return False
        data = res.json()
        results = data.get('results', [])
        if len(results) > 0:
            name = results[0]['name']
            print(f"Result: {name}")
            if name == "Apple Inc.":
                print("SUCCESS: Accessed POPULAR_STOCKS correctly")
                return True
            else:
                print(f"FAILURE: Got '{name}' instead of 'Apple Inc.'")
                return False
        else:
            print("No results found")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if not test_search_constant():
        sys.exit(1)
