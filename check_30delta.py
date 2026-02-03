import yfinance as yf
from datetime import datetime
import numpy as np
from scipy.stats import norm

def calculate_delta(S, K, T, r, sigma):
    """Calculate put delta using Black-Scholes."""
    if T <= 0 or sigma <= 0:
        return 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1

def check_30_delta(ticker, target_expiry):
    """Check 30-delta put for a specific expiry date."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period='1d')
    current_price = hist['Close'].iloc[-1]
    print(f"Current {ticker} Price: ${current_price:.2f}")

    options_dates = stock.options
    print(f"Available expiries: {list(options_dates)}")

    if target_expiry in options_dates:
        expiry_date = datetime.strptime(target_expiry, '%Y-%m-%d')
        dte = (expiry_date - datetime.now()).days
        T = dte / 365.0
        r = 0.045  # Risk-free rate

        chain = stock.option_chain(target_expiry)
        puts = chain.puts.copy()

        # Calculate delta for each put
        puts['delta'] = puts.apply(
            lambda row: calculate_delta(
                current_price, row['strike'], T, r,
                row['impliedVolatility'] if row['impliedVolatility'] > 0 else 0.5
            ),
            axis=1
        )

        # Filter OTM puts only
        puts = puts[puts['strike'] < current_price]

        # Calculate ROI
        puts['roi'] = (puts['bid'] / puts['strike']) * 100
        puts['roi_annual'] = puts['roi'] * (365 / dte) if dte > 0 else 0

        # Find closest to -0.30 delta
        puts['delta_diff'] = abs(puts['delta'] + 0.30)
        puts = puts.sort_values('delta_diff')

        print(f"\n{'='*60}")
        print(f"Expiry: {target_expiry} ({dte} DTE)")
        print(f"{'='*60}")
        
        print(f"\nTop 5 Puts near 30 Delta:")
        print("-" * 80)
        print(f"{'Strike':>10} {'Delta':>10} {'Bid':>10} {'Ask':>10} {'IV%':>10} {'ROI%':>10} {'Ann.ROI%':>10}")
        print("-" * 80)
        
        for _, row in puts.head(5).iterrows():
            iv_pct = row['impliedVolatility'] * 100
            print(f"${row['strike']:>8.0f} {row['delta']:>10.3f} ${row['bid']:>8.2f} ${row['ask']:>8.2f} {iv_pct:>9.1f}% {row['roi']:>9.2f}% {row['roi_annual']:>9.1f}%")

        # Best 30-delta put
        best = puts.iloc[0]
        print(f"\n{'='*60}")
        print("*** BEST 30-DELTA PUT ***")
        print(f"{'='*60}")
        print(f"Strike:      ${best['strike']:.0f}")
        print(f"Delta:       {best['delta']:.3f}")
        print(f"Bid/Ask:     ${best['bid']:.2f} / ${best['ask']:.2f}")
        print(f"Last Price:  ${best['lastPrice']:.2f}")
        print(f"IV:          {best['impliedVolatility']*100:.1f}%")
        print(f"Seller ROI:  {best['roi']:.2f}%")
        print(f"Annualized:  {best['roi_annual']:.1f}%")
        print(f"Open Int:    {int(best['openInterest'])}")
        print(f"Volume:      {int(best['volume']) if best['volume'] > 0 else 'N/A'}")
    else:
        print(f"\nExpiry {target_expiry} not found!")
        print("Available expiries:")
        for exp in options_dates:
            print(f"  - {exp}")

if __name__ == "__main__":
    check_30_delta("SMCI", "2026-03-06")
