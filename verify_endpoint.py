import requests
import sys

try:
    response = requests.get("http://127.0.0.1:8000/api/mystic-pulse/AAPL?period=3y", timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Data keys:", list(data.keys()))
        print("Data length:", len(data.get('data', [])))
    else:
        print("Response:", response.text)
except Exception as e:
    print(f"Error: {e}")
