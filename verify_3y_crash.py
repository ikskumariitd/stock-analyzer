import yfinance as yf
import pandas as pd
import numpy as np
from backend.mystic_pulse import calculate_mystic_pulse

def test_3y_calculation():
    symbol = "AAPL"
    print(f"Fetching 3y data for {symbol}...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="3y")
    
    if df.empty:
        print("Error: No data fetched.")
        return

    print(f"Data fetched: {len(df)} rows.")

    try:
        result = calculate_mystic_pulse(df)
        print("Calculation successful.")
        
        # Check for NaN values in critical columns
        critical_cols = ['dominant_direction', 'positive_intensity', 'negative_intensity', 'trend_score']
        for col in critical_cols:
            if result[col].isnull().any():
                print(f"WARNING: NaN found in column {col}")
                print(result[result[col].isnull()])
            
            # Check for infinite values
            if np.isinf(result[col]).any():
                print(f"WARNING: Infinite value found in column {col}")

        # specific check for the new histogram logic dependencies
        # direction > 0 ? intensity : ...
        # if intensity is NaN, frontend calculation might become NaN, which Lightweight Charts might dislike? 
        # Actually Lightweight charts usually handles NaN by not rendering, but let's see.
        
        print("Sample of last 5 rows:")
        print(result[critical_cols].tail())

    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_3y_calculation()
