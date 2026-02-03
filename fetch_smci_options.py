import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy.stats import norm

def calculate_delta(S, K, T, r, sigma, option_type='put'):
    """
    Calculate option delta using Black-Scholes model.
    S: Current stock price
    K: Strike price
    T: Time to expiration in years
    r: Risk-free rate (e.g., 0.05 for 5%)
    sigma: Implied volatility (e.g., 0.80 for 80%)
    option_type: 'call' or 'put'
    """
    if T <= 0 or sigma <= 0:
        return 0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == 'call':
        return norm.cdf(d1)
    else:  # put
        return norm.cdf(d1) - 1

def get_options_data(ticker_symbol):
    print(f"Fetching data for {ticker_symbol}...")
    stock = yf.Ticker(ticker_symbol)
    
    # Get current price
    hist = stock.history(period="1d")
    if hist.empty:
        print("Could not get current price.")
        return
    current_price = hist['Close'].iloc[-1]
    print(f"Current Price: ${current_price:.2f}")

    options_dates = stock.options
    if not options_dates:
        print("No options dates found.")
        return

    # Find expiry closest to 30 DTE
    today = datetime.now()
    target_date = today + timedelta(days=30)
    
    best_expiry = min(options_dates, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - target_date).days))
    expiry_date = datetime.strptime(best_expiry, "%Y-%m-%d")
    dte = (expiry_date - today).days
    
    print(f"Selected Expiry: {best_expiry} ({dte} DTE)")
    
    chain = stock.option_chain(best_expiry)
    puts = chain.puts.copy()
    
    # Risk-free rate (approximate)
    risk_free_rate = 0.045  # ~4.5%
    
    # Time to expiration in years
    T = dte / 365.0
    
    # Calculate delta for each put option
    puts['delta'] = puts.apply(
        lambda row: calculate_delta(
            S=current_price,
            K=row['strike'],
            T=T,
            r=risk_free_rate,
            sigma=row['impliedVolatility']
        ),
        axis=1
    )
    
    # Filter for OTM puts only
    puts = puts[puts['strike'] < current_price]
    
    # Calculate Seller's ROI: (Bid Price / Strike) * 100
    # Annualized ROI: ROI * (365 / DTE)
    puts['roi'] = (puts['bid'] / puts['strike']) * 100
    puts['roi_annual'] = puts['roi'] * (365 / dte)
    
    # Sort by delta (closest to -0.30)
    puts['delta_diff'] = abs(puts['delta'] + 0.30)
    near_30_delta = puts.sort_values('delta_diff').head(10)
    
    # Format for display
    display_df = near_30_delta[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility', 'delta', 'roi', 'roi_annual', 'openInterest']].copy()
    display_df['impliedVolatility'] = (display_df['impliedVolatility'] * 100).round(1)
    display_df['delta'] = display_df['delta'].round(3)
    display_df['roi'] = display_df['roi'].round(2)
    display_df['roi_annual'] = display_df['roi_annual'].round(1)
    display_df.columns = ['Strike', 'Last', 'Bid', 'Ask', 'IV%', 'Delta', 'ROI%', 'Ann.ROI%', 'OI']
    
    print("\nPut Options near 30 Delta (Sorted by Delta proximity to -0.30):")
    print(display_df.to_string(index=False))
    
    # Highlight the best 30 delta option
    best_30d = near_30_delta.iloc[0]
    print(f"\n--- Best 30 Delta Put ---")
    print(f"Strike: ${best_30d['strike']:.2f}")
    print(f"Delta: {best_30d['delta']:.3f}")
    print(f"Price: ${best_30d['lastPrice']:.2f} (Bid: ${best_30d['bid']:.2f} / Ask: ${best_30d['ask']:.2f})")
    print(f"IV: {best_30d['impliedVolatility']*100:.1f}%")
    print(f"Seller's ROI: {best_30d['roi']:.2f}% ({best_30d['roi_annual']:.1f}% annualized)")
    print(f"DTE: {dte}")

if __name__ == "__main__":
    get_options_data("SMCI")
