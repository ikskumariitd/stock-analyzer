import requests
import json
import numpy as np
from datetime import datetime

STOCKS = ["AAPL"]
PERIODS = ["6mo", "3y"]
BASE_URL = "https://stock-analyzer-641888119120.us-central1.run.app"

def check_data(stock, period):
    url = f"{BASE_URL}/api/mystic-pulse/{stock}?period={period}"
    print(f"Checking {stock} {period}...")
    start_time = datetime.now()
    try:
        res = requests.get(url, timeout=60)
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  Request took {elapsed:.2f} seconds")
        if res.status_code != 200:
            print(f"FAIL: Status {res.status_code}")
            return
        
        data = res.json().get("data", [])
        if not data:
            print("FAIL: No data returned")
            return
        
        print(f"  Received {len(data)} points")
        
        # Check integrity
        dates = []
        null_prices = 0
        nan_prices = 0
        
        for i, item in enumerate(data):
            # Check Date
            d_str = item.get("date")
            dates.append(d_str)
            
            # Check Prices
            for field in ["open", "high", "low", "close"]:
                val = item.get(field)
                if val is None:
                    null_prices += 1
                elif isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                    nan_prices += 1
        
        # Check sort order
        sorted_dates = sorted(dates)
        if dates != sorted_dates:
            print("  FAIL: Dates are NOT sorted!")
            # Find first unsorted
            for i in range(len(dates)-1):
                if dates[i] > dates[i+1]:
                    print(f"    Deviation at {i}: {dates[i]} > {dates[i+1]}")
                    break
        else:
            print("  Dates are sorted.")
            
        if len(dates) != len(set(dates)):
             print("  FAIL: Duplicate dates found!")
        
        if null_prices > 0:
            print(f"  FAIL: Found {null_prices} NULL prices")
        if nan_prices > 0:
            print(f"  FAIL: Found {nan_prices} NaN prices")
            
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")

for p in PERIODS:
    check_data("AAPL", p)
