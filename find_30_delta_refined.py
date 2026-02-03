import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

def black_scholes_put(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def find_iv(price, S, K, T, r):
    if price <= 0: return 0
    try:
        return brentq(lambda x: black_scholes_put(S, K, T, r, x) - price, 0.01, 5.0)
    except:
        return 0

def calculate_delta(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1

def get_30_delta_smci():
    ticker = "SMCI"
    stock = yf.Ticker(ticker)
    current_price = stock.history(period="1d")['Close'].iloc[-1]
    print(f"Current Price: ${current_price:.2f}")

    today = datetime.now()
    target_date = today + timedelta(days=30)
    best_expiry = min(stock.options, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - target_date).days))
    expiry_date = datetime.strptime(best_expiry, "%Y-%m-%d")
    dte = (expiry_date - today).days
    T = dte / 365.0
    r = 0.045
    
    print(f"Selected Expiry: {best_expiry} ({dte} DTE)")
    
    chain = stock.option_chain(best_expiry)
    puts = chain.puts.copy()
    
    # Calculate IV from lastPrice if impliedVolatility is nonsense
    puts['calc_iv'] = puts.apply(lambda row: find_iv(row['lastPrice'], current_price, row['strike'], T, r), axis=1)
    
    # Calculate delta using calc_iv
    puts['calc_delta'] = puts.apply(lambda row: calculate_delta(current_price, row['strike'], T, r, row['calc_iv']), axis=1)
    
    # Filter for OTM puts and valid deltas
    relevant = puts[(puts['strike'] < current_price) & (puts['calc_delta'] < 0)].copy()
    relevant['delta_diff'] = abs(relevant['calc_delta'] + 0.30)
    
    # Sort and show top results
    results = relevant.sort_values('delta_diff').head(5)
    
    print("\nCalculated Results (based on lastPrice):")
    print(results[['strike', 'lastPrice', 'ask', 'calc_iv', 'calc_delta']].to_string(index=False))
    
    if not results.empty:
        best = results.iloc[0]
        print(f"\n--- Recommended 30 Delta Put ---")
        print(f"Strike: ${best['strike']:.2f}")
        print(f"Delta: {best['calc_delta']:.3f} (Estimated)")
        print(f"Last Price: ${best['lastPrice']:.2f}")
        print(f"Ask Price: ${best['ask']:.2f}")
        print(f"Estimated IV: {best['calc_iv']*100:.1f}%")
        print(f"DTE: {dte}")

if __name__ == "__main__":
    get_30_delta_smci()
