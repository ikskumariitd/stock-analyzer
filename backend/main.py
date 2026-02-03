from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import lxml # Ensure lxml is available for read_html
from sp100_tickers import SP100_TICKERS
from scipy.stats import norm  # For Black-Scholes delta calculation

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from mystic_pulse import calculate_mystic_pulse, get_mystic_pulse_summary
from watchlist import get_watchlist_storage

# Load environment variables
load_dotenv()

# Initialize Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# ============================================
# Cache Infrastructure
# ============================================
from threading import Lock
import time as time_module
from gcs_cache import GCSCache

# Initialize global cache (GCS)
cache = GCSCache()
print(f"Cache initialized with bucket: {cache.bucket_name}")

app = FastAPI()

# Common stock symbols for quick lookup
POPULAR_STOCKS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc. Class C",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "META": "Meta Platforms Inc.",
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel Corporation",
    "NFLX": "Netflix Inc.",
    "DIS": "The Walt Disney Company",
    "PYPL": "PayPal Holdings Inc.",
    "COIN": "Coinbase Global Inc.",
    "HOOD": "Robinhood Markets Inc.",
    "SOFI": "SoFi Technologies Inc.",
    "PLTR": "Palantir Technologies",
    "ROKU": "Roku Inc.",
    "SQ": "Block Inc.",
    "SHOP": "Shopify Inc.",
    "SPOT": "Spotify Technology",
    "UBER": "Uber Technologies",
    "LYFT": "Lyft Inc.",
    "SNAP": "Snap Inc.",
    "PINS": "Pinterest Inc.",
    "TWTR": "Twitter Inc.",
    "ZM": "Zoom Video Communications",
    "DOCU": "DocuSign Inc.",
    "CRWD": "CrowdStrike Holdings",
    "DDOG": "Datadog Inc.",
    "NET": "Cloudflare Inc.",
    "SNOW": "Snowflake Inc.",
    "MSTR": "MicroStrategy Inc.",
    "MARA": "Marathon Digital Holdings",
    "RIOT": "Riot Platforms Inc.",
    "SMCI": "Super Micro Computer",
    "ARM": "Arm Holdings",
    "DELL": "Dell Technologies",
    "HPE": "Hewlett Packard Enterprise",
    "IBM": "IBM Corporation",
    "ORCL": "Oracle Corporation",
    "CRM": "Salesforce Inc.",
    "ADBE": "Adobe Inc.",
    "NOW": "ServiceNow Inc.",
    "WDAY": "Workday Inc.",
    "TEAM": "Atlassian Corporation",
    "MU": "Micron Technology",
    "QCOM": "Qualcomm Inc.",
    "AVGO": "Broadcom Inc.",
    "TXN": "Texas Instruments",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA Corporation",
    "ASML": "ASML Holding",
    "TSM": "Taiwan Semiconductor",
    "BABA": "Alibaba Group",
    "JD": "JD.com Inc.",
    "PDD": "PDD Holdings",
    "BIDU": "Baidu Inc.",
    "NIO": "NIO Inc.",
    "XPEV": "XPeng Inc.",
    "LI": "Li Auto Inc.",
    "RIVN": "Rivian Automotive",
    "LCID": "Lucid Group",
    "F": "Ford Motor Company",
    "GM": "General Motors",
    "TM": "Toyota Motor",
    "BA": "Boeing Company",
    "LMT": "Lockheed Martin",
    "RTX": "RTX Corporation",
    "NOC": "Northrop Grumman",
    "GD": "General Dynamics",
    "CAT": "Caterpillar Inc.",
    "DE": "Deere & Company",
    "UNP": "Union Pacific",
    "UPS": "United Parcel Service",
    "FDX": "FedEx Corporation",
    "DAL": "Delta Air Lines",
    "UAL": "United Airlines",
    "AAL": "American Airlines",
    "LUV": "Southwest Airlines",
    "CCL": "Carnival Corporation",
    "RCL": "Royal Caribbean",
    "MAR": "Marriott International",
    "HLT": "Hilton Worldwide",
    "ABNB": "Airbnb Inc.",
    "BKNG": "Booking Holdings",
    "EXPE": "Expedia Group",
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "WFC": "Wells Fargo",
    "C": "Citigroup Inc.",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "SCHW": "Charles Schwab",
    "BLK": "BlackRock Inc.",
    "V": "Visa Inc.",
    "MA": "Mastercard Inc.",
    "AXP": "American Express",
    "COF": "Capital One",
    "DFS": "Discover Financial",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer Inc.",
    "MRK": "Merck & Co.",
    "ABBV": "AbbVie Inc.",
    "LLY": "Eli Lilly",
    "UNH": "UnitedHealth Group",
    "CVS": "CVS Health",
    "WBA": "Walgreens Boots Alliance",
    "WMT": "Walmart Inc.",
    "TGT": "Target Corporation",
    "COST": "Costco Wholesale",
    "HD": "Home Depot",
    "LOW": "Lowe's Companies",
    "NKE": "Nike Inc.",
    "LULU": "Lululemon Athletica",
    "SBUX": "Starbucks Corporation",
    "MCD": "McDonald's Corporation",
    "KO": "Coca-Cola Company",
    "PEP": "PepsiCo Inc.",
    "PG": "Procter & Gamble",
    "CL": "Colgate-Palmolive",
    "KMB": "Kimberly-Clark",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron Corporation",
    "COP": "ConocoPhillips",
    "OXY": "Occidental Petroleum",
    "SLB": "Schlumberger",
    "HAL": "Halliburton Company",
    "NEE": "NextEra Energy",
    "DUK": "Duke Energy",
    "SO": "Southern Company",
    "D": "Dominion Energy",
    "T": "AT&T Inc.",
    "VZ": "Verizon Communications",
    "TMUS": "T-Mobile US",
    "CMCSA": "Comcast Corporation",
    "CHTR": "Charter Communications",
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ Trust",
    "IWM": "iShares Russell 2000",
    "DIA": "SPDR Dow Jones",
    "VOO": "Vanguard S&P 500",
    "VTI": "Vanguard Total Stock",
    "ARKK": "ARK Innovation ETF",
    "GLD": "SPDR Gold Shares",
    "SLV": "iShares Silver Trust",
    "USO": "United States Oil Fund",
    "GDXU": "MicroSectors Gold 3x",
    "TSLL": "Direxion Tesla Bull 2x",
    "SOXL": "Direxion Semiconductor Bull 3x",
    "TQQQ": "ProShares UltraPro QQQ",
    "SQQQ": "ProShares UltraPro Short QQQ",
    "UVXY": "ProShares Ultra VIX",
    "TEM": "Tempus AI Inc.",
    "BBAI": "BigBear.ai Holdings",
    "OPEN": "Opendoor Technologies",
    "APLD": "Applied Digital",
    "FUTU": "Futu Holdings",
    "QBTS": "D-Wave Quantum Inc.",
    "RGTI": "Rigetti Computing",
    "QUBT": "Quantum Computing Inc.",
    "IONQ": "IonQ Inc.",
    "APP": "AppLovin Corporation",
    "RKLB": "Rocket Lab USA",
    "AFRM": "Affirm Holdings",
    "UPST": "Upstart Holdings",
}

# Configure CORS for frontend communication (still useful if using external dev server, but less critical now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
# Mount static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# ============================================
# Cache Management Endpoints
# ============================================

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get current cache statistics."""
    stats = cache.stats()
    return {
        "success": True,
        "stats": stats,
        "backend": "GCS"
    }

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cached data."""
    stats_before = cache.stats()
    cleared_count = cache.clear()
    return {
        "success": True,
        "message": "Cache cleared successfully",
        "cleared_entries": cleared_count,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# Watchlist Management Endpoints
# ============================================

@app.get("/api/watchlist")
async def get_watchlist():
    """Get current watchlist."""
    storage = get_watchlist_storage()
    watchlist = storage.get_watchlist()
    return {
        "success": True,
        "watchlist": watchlist,
        "is_writable": storage.is_writable,
        "storage_backend": storage.storage_backend
    }

@app.delete("/api/watchlist")
async def clear_watchlist():
    """Clear all stocks from watchlist."""
    storage = get_watchlist_storage()
    result = storage.clear_watchlist()
    return result

@app.post("/api/watchlist/{symbol}")
async def add_to_watchlist(symbol: str):
    """Add stock to watchlist."""
    storage = get_watchlist_storage()
    result = storage.add_stock(symbol)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.delete("/api/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove stock from watchlist."""
    storage = get_watchlist_storage()
    result = storage.remove_stock(symbol)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ============================================
# Favorites Management Endpoints
# ============================================
from favorites import get_favorites_storage

@app.get("/api/favorites")
async def get_favorites():
    """Get current favorites."""
    storage = get_favorites_storage()
    favorites = storage.get_favorites()
    return {
        "success": True,
        "favorites": favorites,
        "storage_backend": storage.storage_backend
    }

@app.delete("/api/favorites")
async def clear_favorites():
    """Clear all stocks from favorites."""
    storage = get_favorites_storage()
    result = storage.clear_favorites()
    return result

@app.post("/api/favorites/{symbol}")
async def add_to_favorites(symbol: str):
    """Add stock to favorites."""
    storage = get_favorites_storage()
    result = storage.add_favorite(symbol)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.delete("/api/favorites/{symbol}")
async def remove_from_favorites(symbol: str):
    """Remove stock from favorites."""
    storage = get_favorites_storage()
    result = storage.remove_favorite(symbol)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


def get_sentiment(ticker_symbol):
    # Retrieve news (yfinance might be limited, but we try)
    try:
        ticker = yf.Ticker(ticker_symbol)
        news = ticker.news
        if not news:
            return "Neutral", "No recent news found to analyze sentiment."
        
        sentiments = []
        for article in news[:5]: # Analyze top 5 articles
            title = article.get('title', '')
            blob = TextBlob(title)
            sentiments.append(blob.sentiment.polarity)
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        if avg_sentiment > 0.1:
            return "Bullish", f"Recent news suggests positive sentiment ({avg_sentiment:.2f})."
        elif avg_sentiment < -0.1:
            return "Bearish", f"Recent news suggests negative sentiment ({avg_sentiment:.2f})."
        else:
            return "Neutral", f"Recent news is mixed or neutral ({avg_sentiment:.2f})."
    except Exception as e:
        print(f"Error fetching sentiment: {e}")
        return "Unknown", "Could not analyze sentiment."

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import timedelta

# ============================================
# Options Delta Calculation (Black-Scholes)
# ============================================

def calculate_option_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'put') -> float:
    """
    Calculate option delta using Black-Scholes model.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free rate (e.g., 0.045 for 4.5%)
        sigma: Implied volatility (decimal, e.g., 0.80 for 80%)
        option_type: 'call' or 'put'
    
    Returns:
        Delta value (-1 to 0 for puts, 0 to 1 for calls)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == 'call':
        return float(norm.cdf(d1))
    else:  # put
        return float(norm.cdf(d1) - 1)


def get_30_delta_put(ticker_symbol: str, current_price: float, use_cache: bool = True) -> dict:
    """
    Find the put option closest to 30 delta (~30 DTE) and calculate seller's ROI.
    
    Returns dict with:
        - delta30_strike: Strike price of the ~30 delta put
        - delta30_bid: Bid price
        - delta30_delta: Actual delta value
        - delta30_roi: Seller's ROI % (bid/strike * 100)
        - delta30_roi_annual: Annualized ROI %
        - delta30_dte: Days to expiration
        - delta30_expiry: Expiration date string
    """
    import math
    ticker_symbol = ticker_symbol.upper().strip()
    cache_key = f"delta30:{ticker_symbol}"
    
    # Check cache first
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            cached["_cached"] = True
            created_ts = cache.get_created_timestamp(cache_key)
            cached["_cache_age_minutes"] = round((time_module.time() - created_ts) / 60, 1) if created_ts else 0
            return cached
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    try:
        stock = yf.Ticker(ticker_symbol)
        options_dates = stock.options
        
        if not options_dates or len(options_dates) == 0:
            return {"delta30_error": "No options available"}
        
        # Find expiry closest to 30 DTE
        today = datetime.now()
        target_date = today + timedelta(days=30)
        
        best_expiry = min(options_dates, 
                          key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d") - target_date).days))
        
        expiry_date = datetime.strptime(best_expiry, "%Y-%m-%d")
        dte = (expiry_date - today).days
        
        if dte <= 0:
            return {"delta30_error": "No valid expiration dates"}
        
        T = dte / 365.0
        risk_free_rate = 0.045  # ~4.5%
        
        chain = stock.option_chain(best_expiry)
        puts = chain.puts.copy()
        
        if puts.empty:
            return {"delta30_error": "No put options available"}
        
        # Calculate delta for each put option
        puts['calculated_delta'] = puts.apply(
            lambda row: calculate_option_delta(
                S=current_price,
                K=row['strike'],
                T=T,
                r=risk_free_rate,
                sigma=row['impliedVolatility'] if row['impliedVolatility'] > 0 else 0.5
            ),
            axis=1
        )
        
        # Filter for OTM puts only (strike < current price)
        puts = puts[puts['strike'] < current_price]
        
        if puts.empty:
            return {"delta30_error": "No OTM puts available"}
        
        # Find put closest to -0.30 delta
        puts['delta_diff'] = abs(puts['calculated_delta'] + 0.30)
        best_idx = puts['delta_diff'].idxmin()
        best_put = puts.loc[best_idx]
        
        # Calculate seller's ROI
        bid_price = best_put['bid'] if best_put['bid'] > 0 else best_put['lastPrice'] * 0.95
        strike = best_put['strike']
        
        if strike > 0 and bid_price > 0:
            roi = (bid_price / strike) * 100
            roi_annual = roi * (365 / dte)
        else:
            roi = 0
            roi_annual = 0
        
        result = {
            "delta30_strike": sanitize(strike),
            "delta30_bid": sanitize(bid_price),
            "delta30_last": sanitize(best_put['lastPrice']),
            "delta30_ask": sanitize(best_put['ask']),
            "delta30_delta": sanitize(best_put['calculated_delta']),
            "delta30_iv": sanitize(best_put['impliedVolatility'] * 100),
            "delta30_roi": sanitize(roi),
            "delta30_roi_annual": sanitize(roi_annual),
            "delta30_dte": dte,
            "delta30_expiry": best_expiry
        }
        
        # Cache the result
        if use_cache and "delta30_error" not in result:
            result["_cached"] = False
            cache.set(cache_key, result.copy())
        
        return result
        
    except Exception as e:
        print(f"Error getting 30 delta put for {ticker_symbol}: {e}")
        return {"delta30_error": str(e)}


def calculate_volatility_metrics(ticker_symbol: str, use_cache: bool = True):
    """
    Calculate IV Rank and related volatility metrics for CSP strategy.
    Returns dict with current_iv, iv_rank, hv_30, hv_rank, iv_hv_ratio, and recommendation.
    """
    ticker_symbol = ticker_symbol.upper().strip()
    cache_key = f"volatility:{ticker_symbol}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            # Check if cache has the new delta30 fields - if not, invalidate and refetch
            if "delta30_strike" not in cached and "delta30_error" not in cached:
                # Stale cache without delta30 data - refetch
                pass
            else:
                cached["_cached"] = True
                created_ts = cache.get_created_timestamp(cache_key)
                cached["_cache_age_minutes"] = round((time_module.time() - created_ts) / 60, 1) if created_ts else 0
                return cached
    import math
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Get 1 year of historical data for HV calculations
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 60:
            return {"error": "Insufficient historical data for volatility calculation"}
        
        current_price = hist['Close'].iloc[-1]
        
        # Calculate Historical Volatility (30-day, annualized)
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1))
        
        # Rolling 30-day HV over the year
        rolling_hv = log_returns.rolling(window=30).std() * np.sqrt(252) * 100
        current_hv_30 = rolling_hv.iloc[-1]
        
        # HV Rank: where current HV sits in 52-week range
        hv_min = rolling_hv.min()
        hv_max = rolling_hv.max()
        if hv_max > hv_min:
            hv_rank = ((current_hv_30 - hv_min) / (hv_max - hv_min)) * 100
        else:
            hv_rank = 50  # Default if no range
        
        # Try to get IV and 30-delta data from options chain (single fetch)
        current_iv = None
        iv_rank = None
        iv_hv_ratio = None
        delta30_data = {}
        
        try:
            options_dates = stock.options
            if options_dates and len(options_dates) > 0:
                # Find expiration closest to 30 DTE
                today = datetime.now()
                target_dte = 30
                best_expiry = None
                best_diff = float('inf')
                
                for exp_str in options_dates:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                    dte = (exp_date - today).days
                    if 7 <= dte <= 60:  # Look for 7-60 DTE
                        diff = abs(dte - target_dte)
                        if diff < best_diff:
                            best_diff = diff
                            best_expiry = exp_str
                
                if best_expiry:
                    expiry_date = datetime.strptime(best_expiry, "%Y-%m-%d")
                    actual_dte = (expiry_date - today).days
                    chain = stock.option_chain(best_expiry)
                    puts = chain.puts.copy()
                    
                    if not puts.empty:
                        # Find ATM put (strike closest to current price) for IV
                        puts['strike_diff'] = abs(puts['strike'] - current_price)
                        atm_put = puts.loc[puts['strike_diff'].idxmin()]
                        
                        # Get IV (yfinance returns as decimal, e.g., 0.35 = 35%)
                        if 'impliedVolatility' in atm_put and atm_put['impliedVolatility'] > 0:
                            current_iv = atm_put['impliedVolatility'] * 100
                            
                            # IV/HV Ratio
                            if current_hv_30 > 0:
                                iv_hv_ratio = current_iv / current_hv_30
                            
                            iv_rank = hv_rank  # Proxy: assume IV rank tracks HV rank loosely
                        
                        # Calculate 30-delta put data (using same options chain)
                        if actual_dte > 0:
                            T = actual_dte / 365.0
                            risk_free_rate = 0.045
                            
                            # Calculate delta for each put option
                            puts['calculated_delta'] = puts.apply(
                                lambda row: calculate_option_delta(
                                    S=current_price,
                                    K=row['strike'],
                                    T=T,
                                    r=risk_free_rate,
                                    sigma=row['impliedVolatility'] if row['impliedVolatility'] > 0 else 0.5
                                ),
                                axis=1
                            )
                            
                            # Filter for OTM puts only
                            otm_puts = puts[puts['strike'] < current_price]
                            
                            if not otm_puts.empty:
                                # Find put closest to -0.30 delta
                                otm_puts = otm_puts.copy()
                                otm_puts['delta_diff'] = abs(otm_puts['calculated_delta'] + 0.30)
                                best_idx = otm_puts['delta_diff'].idxmin()
                                best_put = otm_puts.loc[best_idx]
                                
                                bid_price = best_put['bid'] if best_put['bid'] > 0 else best_put['lastPrice'] * 0.95
                                strike = best_put['strike']
                                
                                if strike > 0 and bid_price > 0:
                                    roi = (bid_price / strike) * 100
                                    roi_annual = roi * (365 / actual_dte)
                                else:
                                    roi = 0
                                    roi_annual = 0
                                
                                delta30_data = {
                                    "delta30_strike": sanitize(strike),
                                    "delta30_bid": sanitize(bid_price),
                                    "delta30_last": sanitize(best_put['lastPrice']),
                                    "delta30_ask": sanitize(best_put['ask']),
                                    "delta30_delta": sanitize(best_put['calculated_delta']),
                                    "delta30_iv": sanitize(best_put['impliedVolatility'] * 100),
                                    "delta30_roi": sanitize(roi),
                                    "delta30_roi_annual": sanitize(roi_annual),
                                    "delta30_dte": actual_dte,
                                    "delta30_expiry": best_expiry
                                }
                            
        except Exception as e:
            print(f"Options data error for {ticker_symbol}: {e}")
        
        # Generate recommendation
        recommendation = generate_csp_recommendation(current_iv, iv_rank, hv_rank, iv_hv_ratio)
        
        result = {
            "symbol": ticker_symbol,
            "current_price": sanitize(current_price),
            "current_iv": sanitize(current_iv),
            "iv_rank": sanitize(iv_rank),
            "hv_30": sanitize(current_hv_30),
            "hv_rank": sanitize(hv_rank),
            "hv_52w_low": sanitize(hv_min),
            "hv_52w_high": sanitize(hv_max),
            "iv_hv_ratio": sanitize(iv_hv_ratio),
            "recommendation": recommendation
        }
        
        # Merge 30-delta put data into result
        if delta30_data:
            result.update(delta30_data)

        if use_cache and "error" not in result:
             result["_cached"] = False
             cache.set(cache_key, result.copy())
        
        return result
        
    except Exception as e:
        print(f"Volatility calculation error for {ticker_symbol}: {e}")
        return {"error": str(e)}


def generate_csp_recommendation(current_iv, iv_rank, hv_rank, iv_hv_ratio):
    """Generate CSP trading recommendation based on volatility metrics."""
    
    # Use HV rank if IV rank not available
    rank = iv_rank if iv_rank is not None else hv_rank
    
    if rank is None:
        return "Unable to calculate - insufficient data"
    
    # IV/HV ratio interpretation
    ratio_text = ""
    if iv_hv_ratio is not None:
        if iv_hv_ratio > 1.2:
            ratio_text = "Options are expensive relative to historical vol. "
        elif iv_hv_ratio < 0.8:
            ratio_text = "Options are cheap relative to historical vol. "
    
    # Rank-based recommendation
    if rank >= 75:
        return f"🟣 Excellent for CSP - Very high IV ({rank:.0f}%). {ratio_text}Premium is rich."
    elif rank >= 50:
        return f"🟢 Good for CSP - Above average IV ({rank:.0f}%). {ratio_text}Decent premium."
    elif rank >= 25:
        return f"🟡 Moderate - Below average IV ({rank:.0f}%). {ratio_text}Consider waiting."
    else:
        return f"🔴 Poor for CSP - Low IV ({rank:.0f}%). {ratio_text}Premium is thin."


def calculate_csp_metrics(ticker_symbol: str, use_cache: bool = True):
    """
    Calculate CSP-specific metrics: 52-week range, ATR, support/resistance, earnings.
    """
    ticker_symbol = ticker_symbol.upper().strip()
    cache_key = f"csp:{ticker_symbol}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
             cached["_cached"] = True
             created_ts = cache.get_created_timestamp(cache_key)
             cached["_cache_age_minutes"] = round((time_module.time() - created_ts) / 60, 1) if created_ts else 0
             return cached
    import math
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # Get historical data for calculations
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 20:
            return {"error": "Insufficient historical data"}
        
        current_price = hist['Close'].iloc[-1]
        
        # === 52-Week Range ===
        week52_high = info.get('fiftyTwoWeekHigh', hist['High'].max())
        week52_low = info.get('fiftyTwoWeekLow', hist['Low'].min())
        
        if week52_high and week52_low and week52_high > week52_low:
            price_position = ((current_price - week52_low) / (week52_high - week52_low)) * 100
        else:
            price_position = 50
        
        # === ATR (Average True Range) ===
        # Calculate ATR manually for reliability
        high = hist['High']
        low = hist['Low']
        close = hist['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(window=14).mean().iloc[-1]
        atr_percent = (atr_14 / current_price) * 100 if current_price > 0 else 0
        
        # Suggested strikes based on ATR
        suggested_strikes = [
            sanitize(current_price - atr_14),       # 1 ATR below
            sanitize(current_price - (2 * atr_14)), # 2 ATR below
            sanitize(current_price - (3 * atr_14))  # 3 ATR below
        ]
        
        # === Support/Resistance Levels ===
        # Use pivot points + recent swing levels
        
        # Classic Pivot Points (using last day's data)
        prev_high = hist['High'].iloc[-2]
        prev_low = hist['Low'].iloc[-2]
        prev_close = hist['Close'].iloc[-2]
        pivot = (prev_high + prev_low + prev_close) / 3
        
        # Support levels
        s1 = (2 * pivot) - prev_high
        s2 = pivot - (prev_high - prev_low)
        s3 = prev_low - 2 * (prev_high - pivot)
        
        # Resistance levels
        r1 = (2 * pivot) - prev_low
        r2 = pivot + (prev_high - prev_low)
        r3 = prev_high + 2 * (pivot - prev_low)
        
        # Also find recent swing lows (last 20 days)
        recent_20 = hist.tail(20)
        swing_lows = []
        for i in range(2, len(recent_20) - 2):
            if (recent_20['Low'].iloc[i] < recent_20['Low'].iloc[i-1] and 
                recent_20['Low'].iloc[i] < recent_20['Low'].iloc[i-2] and
                recent_20['Low'].iloc[i] < recent_20['Low'].iloc[i+1] and 
                recent_20['Low'].iloc[i] < recent_20['Low'].iloc[i+2]):
                swing_lows.append(recent_20['Low'].iloc[i])
        
        # Combine and sort support levels
        all_supports = [s1, s2, s3] + swing_lows
        all_supports = [s for s in all_supports if s < current_price]
        all_supports = sorted(set([sanitize(s) for s in all_supports if s]), reverse=True)[:3]
        
        support_levels = all_supports if all_supports else [sanitize(s1), sanitize(s2)]
        resistance_levels = [sanitize(r1), sanitize(r2), sanitize(r3)]
        
        # === Earnings Calendar ===
        next_earnings = None
        days_to_earnings = None
        earnings_warning = False
        today = pd.Timestamp.now().normalize()
        
        # Method 1: Try earnings_dates
        try:
            earnings_dates = stock.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                future_dates = earnings_dates[earnings_dates.index >= today]
                if not future_dates.empty:
                    next_earnings_date = future_dates.index[0]
                    next_earnings = next_earnings_date.strftime("%Y-%m-%d")
                    days_to_earnings = (next_earnings_date - today).days
                    if days_to_earnings >= 0:
                        earnings_warning = days_to_earnings <= 30
        except Exception as e:
            print(f"Earnings dates error for {ticker_symbol}: {e}")
        
        # Method 2: Try calendar if no earnings date found
        if next_earnings is None:
            try:
                cal = stock.calendar
                if cal is not None:
                    # Check for 'Earnings Date' key
                    if 'Earnings Date' in cal:
                        earnings_date = cal['Earnings Date']
                        if earnings_date:
                            if isinstance(earnings_date, list):
                                earnings_date = earnings_date[0] if earnings_date else None
                            if earnings_date:
                                earnings_ts = pd.Timestamp(earnings_date)
                                days_diff = (earnings_ts - today).days
                                if days_diff >= 0:
                                    next_earnings = str(earnings_date)[:10]
                                    days_to_earnings = days_diff
                                    earnings_warning = days_to_earnings <= 30
                    # Also check DataFrame format
                    elif isinstance(cal, pd.DataFrame) and 'Earnings Date' in cal.columns:
                        ed = cal['Earnings Date'].dropna()
                        if not ed.empty:
                            for date_val in ed:
                                earnings_ts = pd.Timestamp(date_val)
                                if earnings_ts >= today:
                                    next_earnings = earnings_ts.strftime("%Y-%m-%d")
                                    days_to_earnings = (earnings_ts - today).days
                                    earnings_warning = days_to_earnings <= 30
                                    break
            except Exception as e:
                print(f"Calendar error for {ticker_symbol}: {e}")
        
        # Method 3: Check info for earnings-related fields
        if next_earnings is None:
            try:
                # Some stocks have earnings timestamp in info
                earnings_timestamp = info.get('earningsTimestamp') or info.get('mostRecentQuarter')
                if earnings_timestamp:
                    # This is usually a Unix timestamp
                    if isinstance(earnings_timestamp, (int, float)):
                        from datetime import datetime as dt
                        earnings_dt = dt.fromtimestamp(earnings_timestamp)
                        # Estimate next earnings: quarterly = ~90 days from last
                        next_est = earnings_dt + timedelta(days=90)
                        while next_est.date() < dt.now().date():
                            next_est = next_est + timedelta(days=90)
                        next_earnings = next_est.strftime("%Y-%m-%d")
                        days_to_earnings = (next_est.date() - dt.now().date()).days
                        earnings_warning = days_to_earnings <= 30 if days_to_earnings else False
            except Exception as e:
                print(f"Info earnings error for {ticker_symbol}: {e}")
        
        result = {
            "symbol": ticker_symbol,
            "current_price": sanitize(current_price),
            
            # 52-Week Range
            "week52_high": sanitize(week52_high),
            "week52_low": sanitize(week52_low),
            "price_position": sanitize(price_position),
            
            # ATR
            "atr_14": sanitize(atr_14),
            "atr_percent": sanitize(atr_percent),
            "suggested_strikes": suggested_strikes,
            
            # Support/Resistance
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "pivot": sanitize(pivot),
            
            # Earnings
            "next_earnings": next_earnings,
            "days_to_earnings": days_to_earnings,
            "earnings_warning": earnings_warning
        }

        if use_cache and "error" not in result:
             result["_cached"] = False
             cache.set(cache_key, result.copy())
             
        return result
        
    except Exception as e:
        print(f"CSP metrics error for {ticker_symbol}: {e}")
        return {"error": str(e)}


class BatchRequest(BaseModel):
    tickers: List[str]
    refresh: bool = False

def _analyze_ticker(ticker: str):
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)
    
    # Get historical data (1 year to be safe for 200 SMA)
    hist = stock.history(period="1y")
    
    if hist.empty:
        raise ValueError(f"Stock data not found for {ticker}")
    
    current_price = hist['Close'].iloc[-1]
    
    # Calculate 1-day change
    if len(hist) >= 2:
        previous_close = hist['Close'].iloc[-2]
        change_1d = current_price - previous_close
        change_1d_pct = (change_1d / previous_close) * 100
    else:
        previous_close = current_price
        change_1d = 0
        change_1d_pct = 0
    
    # Calculate Indicators
    # RSI
    hist['RSI'] = ta.rsi(hist['Close'], length=14)
    
    # Bollinger Bands
    bbands = ta.bbands(hist['Close'], length=20)
    if bbands is not None:
        hist = pd.concat([hist, bbands], axis=1)
        # We'll dynamically find them to be safe
        bb_upper_col = [c for c in hist.columns if c.startswith('BBU')][0]
        bb_lower_col = [c for c in hist.columns if c.startswith('BBL')][0]
        bb_upper = hist[bb_upper_col].iloc[-1]
        bb_lower = hist[bb_lower_col].iloc[-1]
    else:
        bb_upper = 0
        bb_lower = 0

    # SMAs
    hist['SMA_5'] = ta.sma(hist['Close'], length=5)
    hist['SMA_50'] = ta.sma(hist['Close'], length=50)
    hist['SMA_200'] = ta.sma(hist['Close'], length=200)

    # Sanitize inputs for JSON (replace NaN with None)
    import math
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    # Get Market Cap (try fast_info first)
    market_cap = None
    try:
        market_cap = stock.fast_info['market_cap']
    except:
        try:
            market_cap = stock.info.get('marketCap')
        except:
            market_cap = None

    # Get Stock Name
    stock_name = None
    try:
        # Prefer short name for table display, fallback to long name
        stock_name = stock.info.get('shortName') or stock.info.get('longName') 
    except:
        stock_name = None

    data = {
        "symbol": ticker,
        "name": sanitize(stock_name),
        "market_cap": sanitize(market_cap),
        "price": sanitize(round(current_price, 2)),
        "change_1d": sanitize(round(change_1d, 2)),
        "change_1d_pct": sanitize(round(change_1d_pct, 2)),
        "indicators": {
            "RSI": sanitize(round(hist['RSI'].iloc[-1], 2)),
            "BB_Upper": sanitize(round(bb_upper, 2)),
            "BB_Lower": sanitize(round(bb_lower, 2)),
            "SMA_5": sanitize(round(hist['SMA_5'].iloc[-1], 2)),
            "SMA_50": sanitize(round(hist['SMA_50'].iloc[-1], 2)),
            "SMA_200": sanitize(round(hist['SMA_200'].iloc[-1], 2))
        }
    }
    
    # Sentiment
    sentiment_mood, sentiment_desc = get_sentiment(ticker)
    data["sentiment"] = {
        "mood": sentiment_mood,
        "description": sentiment_desc
    }
    
    # Generate Human Readable Summary
    rsi_val = data['indicators']['RSI']
    sma_200_val = data['indicators']['SMA_200']
    
    rsi_desc = "neutral"
    if rsi_val is not None:
        if rsi_val > 70: rsi_desc = "overbought"
        elif rsi_val < 30: rsi_desc = "oversold"
        
    sma_desc = "unknown"
    if sma_200_val is not None:
         sma_desc = "above" if current_price > sma_200_val else "below"

    summary_lines = [
        f"The current price of {ticker} is ${data['price']}.",
        f"Market sentiment is currently {sentiment_mood.lower()}.",
        f"RSI is at {rsi_val}, which indicates the stock is {rsi_desc}.",
        f"The stock is trading {sma_desc} its 200-day moving average."
    ]
    data["summary"] = " ".join(summary_lines)
    
    return data

def _analyze_ticker_cached(ticker: str, use_cache: bool = True):
    """Analyze ticker with caching support."""
    ticker = ticker.upper().strip()
    cache_key = f"stock:{ticker}"
    
    # Check cache first
    cached = None
    if use_cache:
        cached = cache.get(cache_key)
    if cached is not None:
        # Return cached data with cache indicator
        cached["_cached"] = True
        
        # Helper to calculate age from timestamp
        created_ts = cache.get_created_timestamp(cache_key)
        age_min = 0
        if created_ts:
             age_min = round((time_module.time() - created_ts) / 60, 1)

        cached["_cache_age_minutes"] = age_min
        return cached
    
    # Fetch fresh data
    result = _analyze_ticker(ticker)
    result["_cached"] = False
    result["_cache_age_minutes"] = 0
    
    # Store in cache
    cache.set(cache_key, result.copy())
    
    return result

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    try:
        return _analyze_ticker_cached(ticker)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_indicators(hist, ticker: str):
    """
    Calculate technical indicators for a given history DataFrame.
    Returns dictionary with indicators and price data.
    """
    import math
    
    if hist.empty:
        return None
        
    current_price = hist['Close'].iloc[-1]
    
    # Calculate 1-day change
    if len(hist) >= 2:
        previous_close = hist['Close'].iloc[-2]
        change_1d = current_price - previous_close
        change_1d_pct = (change_1d / previous_close) * 100
    else:
        previous_close = current_price
        change_1d = 0
        change_1d_pct = 0
    
    # Calculate Indicators
    # RSI
    hist['RSI'] = ta.rsi(hist['Close'], length=14)
    
    # Bollinger Bands
    bbands = ta.bbands(hist['Close'], length=20)
    if bbands is not None:
        # We'll dynamically find them to be safe
        bb_cols = [c for c in bbands.columns]
        # pandas_ta usually names them BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        bb_upper_col = next((c for c in bb_cols if c.startswith('BBU')), None)
        bb_lower_col = next((c for c in bb_cols if c.startswith('BBL')), None)
        
        bb_upper = bbands[bb_upper_col].iloc[-1] if bb_upper_col else 0
        bb_lower = bbands[bb_lower_col].iloc[-1] if bb_lower_col else 0
    else:
        bb_upper = 0
        bb_lower = 0

    # SMAs
    hist['SMA_5'] = ta.sma(hist['Close'], length=5)
    hist['SMA_50'] = ta.sma(hist['Close'], length=50)
    hist['SMA_200'] = ta.sma(hist['Close'], length=200)

    # Sanitize inputs for JSON (replace NaN with None)
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    # Helper for safe access
    def get_last(series):
        if series is None or series.empty: return None
        val = series.iloc[-1]
        return sanitize(val)

    data = {
        "price": sanitize(round(current_price, 2)),
        "change_1d": sanitize(round(change_1d, 2)),
        "change_1d_pct": sanitize(round(change_1d_pct, 2)),
        "indicators": {
            "RSI": sanitize(round(get_last(hist['RSI']), 2)),
            "BB_Upper": sanitize(round(bb_upper, 2)),
            "BB_Lower": sanitize(round(bb_lower, 2)),
            "SMA_5": sanitize(round(get_last(hist['SMA_5']), 2)),
            "SMA_50": sanitize(round(get_last(hist['SMA_50']), 2)),
            "SMA_200": sanitize(round(get_last(hist['SMA_200']), 2))
        }
    }
    
    # Brief summary generation based on indicators
    rsi_val = data['indicators']['RSI']
    sma_200_val = data['indicators']['SMA_200']
    
    rsi_desc = "neutral"
    if rsi_val is not None:
        if rsi_val > 70: rsi_desc = "overbought"
        elif rsi_val < 30: rsi_desc = "oversold"
        
    sma_desc = "unknown"
    if sma_200_val is not None and current_price:
         sma_desc = "above" if current_price > sma_200_val else "below"

    summary_lines = [
        f"The current price of {ticker} is ${data['price']}.",
        f"RSI is at {rsi_val}, which indicates the stock is {rsi_desc}.",
        f"The stock is trading {sma_desc} its 200-day moving average."
    ]
    data["summary"] = " ".join(summary_lines)
    
    return data

async def perform_bulk_analysis(tickers: List[str], refresh: bool = False):
    """
    Reusable function to perform bulk analysis on a list of tickers.
    returns: List[Dict] results
    """
    if not tickers:
        return []
    
    # Ensure tickers are unique and clean
    tickers = list(set([t.upper().strip() for t in tickers if t.strip()]))
    
    print(f"Starting bulk analysis for {len(tickers)} tickers...")
    start_time = time_module.time()
    
    results = []
    
    import math
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val
    
    # 1. Check cache for all
    tickers_to_fetch = []
    cached_results = {}
    
    for t in tickers:
        cache_key = f"stock:{t}"
        cached = None
        if not refresh:
            cached = cache.get(cache_key)
        if cached:
            cached["_cached"] = True
            cached_results[t] = cached
        else:
            tickers_to_fetch.append(t)
    
    if not tickers_to_fetch:
        print(f"All {len(tickers)} tickers found in cache.")
        return [cached_results[t] for t in tickers if t in cached_results]

    # 2. Bulk download history
    try:
        # group_by='ticker' gives MultiIndex columns: (Ticker, PriceType)
        # threads=True is default but explicit is good
        print(f"Fetching fresh data for {len(tickers_to_fetch)} tickers...")
        bulk_hist = yf.download(tickers_to_fetch, period="1y", group_by='ticker', threads=True, progress=False)

        # Bulk fetch metadata (Market Cap) in parallel
        print("Fetching market caps...")
        meta_map = {}
        
        def fetch_meta(t_symbol):
            try:
                # fast_info is generally faster than .info
                # Access as dictionary, failed keys raise KeyError which we catch
                stock = yf.Ticker(t_symbol)
                try:
                    return t_symbol, stock.fast_info['market_cap']
                except:
                    # Fallback to slower .info
                    return t_symbol, stock.info.get('marketCap')
            except Exception as e:
                print(f"Error fetching metadata for {t_symbol}: {e}")
                return t_symbol, None

        if tickers_to_fetch:
            loop = asyncio.get_event_loop()
            # Use higher worker count for I/O bound tasks
            with ThreadPoolExecutor(max_workers=min(len(tickers_to_fetch), 50)) as executor:
                tasks = [loop.run_in_executor(executor, fetch_meta, t) for t in tickers_to_fetch]
                results_meta = await asyncio.gather(*tasks)
                meta_map = {t: mc for t, mc in results_meta}

        
        # Process each ticker
        for t in tickers_to_fetch:
            try:
                # Extract history for this ticker
                # If only 1 ticker fetched, yfinance might not return MultiIndex columns if group_by not forced properly
                # But with group_by='ticker', it usually does.
                # Handle case where download failed or no data
                t_hist = pd.DataFrame()
                
                if len(tickers_to_fetch) == 1:
                    # yf.download behavior varies slightly if list has 1 item vs multiple
                    if isinstance(bulk_hist.columns, pd.MultiIndex):
                            if t in bulk_hist.columns.levels[0]:
                                t_hist = bulk_hist[t]
                    else:
                            t_hist = bulk_hist # Should be just the DF
                else:
                    if t in bulk_hist.columns.levels[0]:
                            t_hist = bulk_hist[t]
                    
                # Clean empty rows
                if not t_hist.empty:
                    t_hist = t_hist.dropna(how='all')
                
                if t_hist.empty:
                    results.append({"symbol": t, "error": "No price data"})
                    continue
                    
                # Calculate indicators
                indic_data = _calculate_indicators(t_hist, t)
                
                if not indic_data:
                    results.append({"symbol": t, "error": "Calculation error"})
                    continue
                    
                # Construct final object
                # For bulk, we skip expensive calls (Info, Sentiment)
                # Use defaults or fast lookups
                
                final_obj = {
                    "symbol": t,
                    "name": POPULAR_STOCKS.get(t, t), # Look up name or default to symbol
                    "market_cap": sanitize(meta_map.get(t)), # Use fetched market cap
                    "price": indic_data["price"],
                    "change_1d": indic_data["change_1d"],
                    "change_1d_pct": indic_data["change_1d_pct"],
                    "indicators": indic_data["indicators"],
                    "sentiment": {
                        "mood": "Neutral",
                        "description": "Sentiment analysis skipped for bulk search."
                    },
                    "summary": indic_data["summary"],
                    "_cached": False,
                    "_cache_age_minutes": 0,
                    "_is_bulk": True # Flag for frontend if needed
                }
                
                # Cache it
                cache.set(f"stock:{t}", final_obj)
                results.append(final_obj)
                
            except Exception as e:
                print(f"Error processing {t} in bulk: {e}")
                results.append({"symbol": t, "error": str(e)})

    except Exception as e:
            print(f"Bulk download failed: {e}")
            return [{"symbol": t, "error": "Bulk fetch failed"} for t in tickers]

    # Combine cached and new
    final_results = []
    
    # Store results in a dict for O(1) lookup
    new_results_map = {r['symbol']: r for r in results if 'symbol' in r}
    
    for t in tickers:
        if t in cached_results:
            final_results.append(cached_results[t])
        elif t in new_results_map:
            final_results.append(new_results_map[t])
        else:
            final_results.append({"symbol": t, "error": "Processing failed"})
                
    print(f"Bulk analysis finished in {time_module.time() - start_time:.2f}s")
    return final_results


@app.post("/api/analyze-batch")
async def analyze_batch(request: BatchRequest):
    """
    Analyze multiple tickers.
    Optimized for bulk: >10 tickers (uses yf.download mechanics).
    """
    tickers = [t.upper().strip() for t in request.tickers if t.strip()]
    refresh = request.refresh
    
    if not tickers:
        return []

    # --- BULK MODE (>10 tickers) ---
    if len(tickers) > 10:
        return await perform_bulk_analysis(tickers)

    # --- LEGACY/DETAILED MODE (<=10 tickers) ---
    else:
        def analyze_single_ticker(ticker: str):
            """Wrapper function for parallel execution with caching."""
            try:
                # Pass refresh flag as use_cache argument (refresh=True -> use_cache=False)
                return _analyze_ticker_cached(ticker, use_cache=not refresh)
            except Exception as e:
                return {
                    "symbol": ticker.upper(),
                    "error": str(e)
                }
        
        max_workers = min(32, len(tickers) + 4)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = [loop.run_in_executor(executor, analyze_single_ticker, ticker) 
                     for ticker in tickers]
            results = await asyncio.gather(*tasks)
        
        return results

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = "3y", include_bb: bool = True, refresh: bool = False):
    """Get price history for charting. Period can be: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y, 10y, max
    
    Parameters:
    - ticker: Stock symbol
    - period: History period to return (default: 3y) - data is filtered from cached full history
    - include_bb: Include Bollinger Bands (default: true)
    - refresh: Force fresh data fetch, bypassing cache (default: false)
    
    Caching strategy: Full 10y history is cached per ticker. Period filtering happens on response.
    """
    import math
    from datetime import datetime, timedelta
    
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    # Period to days mapping for filtering
    period_days = {
        "1d": 1,
        "5d": 5, "5day": 5,
        "1mo": 30, "1m": 30,
        "3mo": 90, "3m": 90,
        "6mo": 180, "6m": 180,
        "1y": 365, "1year": 365,
        "2y": 730, "2year": 730,
        "3y": 1095, "3year": 1095,
        "5y": 1825, "5year": 1825,
        "10y": 3650, "10year": 3650,
        "max": 99999
    }
    
    try:
        ticker = ticker.upper().strip()
        period = period.lower().strip()
        # Cache key is just ticker - we cache full history
        cache_key = f"history:{ticker}"
        
        full_history = None
        
        # Check cache first (unless refresh requested)
        if not refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                full_history = cached.get("full_history", [])
        
        # Fetch fresh data if needed
        if full_history is None or refresh:
            stock = yf.Ticker(ticker)
            # Always fetch 10y to have full data
            hist = stock.history(period="10y")
            
            if hist.empty:
                raise HTTPException(status_code=404, detail=f"No history found for {ticker}")
            
            # Calculate Bollinger Bands on full data
            if len(hist) >= 20:
                hist['BB_Middle'] = hist['Close'].rolling(window=20).mean()
                rolling_std = hist['Close'].rolling(window=20).std()
                hist['BB_Upper'] = hist['BB_Middle'] + (rolling_std * 2)
                hist['BB_Lower'] = hist['BB_Middle'] - (rolling_std * 2)
            
            full_history = []
            for date, row in hist.iterrows():
                data_point = {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": sanitize(row["Open"]),
                    "high": sanitize(row["High"]),
                    "low": sanitize(row["Low"]),
                    "close": sanitize(row["Close"]),
                    "volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 0
                }
                
                if 'BB_Upper' in hist.columns:
                    data_point["bb_upper"] = sanitize(row.get("BB_Upper"))
                    data_point["bb_middle"] = sanitize(row.get("BB_Middle"))
                    data_point["bb_lower"] = sanitize(row.get("BB_Lower"))
                
                full_history.append(data_point)
            
            # Cache the full history
            cache.set(cache_key, {"full_history": full_history})
        
        # Filter history based on requested period
        days = period_days.get(period, 1095)  # Default to 3y
        if days < 99999 and full_history:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            filtered_history = [h for h in full_history if h["date"] >= cutoff_date]
        else:
            filtered_history = full_history
        
        # Optionally exclude BB data if not requested
        if not include_bb and filtered_history:
            for item in filtered_history:
                item.pop("bb_upper", None)
                item.pop("bb_middle", None)
                item.pop("bb_lower", None)
        
        # Check if this was from cache
        is_cached = not refresh and cache.get(cache_key) is not None
        created_ts = cache.get_created_timestamp(cache_key) if is_cached else 0
        cache_age = round((time_module.time() - created_ts) / 60, 1) if created_ts else 0
        
        return {
            "symbol": ticker,
            "period": period,
            "history": filtered_history,
            "_cached": is_cached,
            "_cache_age_minutes": cache_age
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"History error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class BatchHistoryRequest(BaseModel):
    tickers: List[str]
    period: str = "3y"
    include_bb: bool = False

@app.post("/api/history-batch")
async def get_history_batch(request: BatchHistoryRequest):
    """
    Get price history for multiple tickers efficiently.
    Uses concurrency to fetch from cache/source.
    """
    if not request.tickers:
        return {}
    
    # helper for single fetch (wrapper around get_history logic)
    # we can call the function directly if we extract logic, or call via loop
    # calling internal logic is better to avoid HTTP overhead
    
    async def fetch_single(ticker):
        try:
            # Reusing get_history logic by calling it directly? 
            # Ideally get_history should be refactored, but calling it as a function is fine if it wasn't async def (it is async def)
            # Since it's async def, we can await it directly.
            result = await get_history(ticker, request.period, request.include_bb)
            return ticker, result
        except Exception as e:
            return ticker, None

    results = {}
    
    # Process in chunks to avoid overwhelming if list is huge
    chunk_size = 20
    for i in range(0, len(request.tickers), chunk_size):
        chunk = request.tickers[i:i + chunk_size]
        tasks = [fetch_single(t) for t in chunk]
        batch_results = await asyncio.gather(*tasks)
        
        for ticker, data in batch_results:
            if data:
                results[ticker] = data["history"]
    
    return results

@app.get("/api/volatility/{ticker}")
async def get_volatility(ticker: str, refresh: bool = False):
    """Get volatility metrics for CSP strategy including IV Rank, HV, and recommendation.
    
    Parameters:
    - ticker: Stock symbol
    - refresh: Force fresh data fetch, bypassing cache (default: false)
    """
    try:
        result = calculate_volatility_metrics(ticker, use_cache=not refresh)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Volatility error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/csp-metrics/{ticker}")
async def get_csp_metrics(ticker: str, refresh: bool = False):
    """Get CSP-specific metrics: 52-week range, ATR, support/resistance, earnings calendar.
    
    Parameters:
    - ticker: Stock symbol
    - refresh: Force fresh data fetch, bypassing cache (default: false)
    """
    try:
        result = calculate_csp_metrics(ticker, use_cache=not refresh)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"CSP metrics error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CSPBatchRequest(BaseModel):
    tickers: List[str]
    refresh: bool = False


@app.post("/api/csp-batch")
async def get_csp_batch(request: CSPBatchRequest):
    """
    Get CSP summary data for multiple tickers at once.
    Returns lightweight data for the CSP Opportunity Summary table:
    - Basic price info (price, change, RSI)
    - Volatility metrics (IV, rank, HV)
    - 52-week range
    - Company name
    
    This is optimized for fast loading of the CSP table before full analysis.
    """
    import math
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    tickers = list(set([t.upper().strip() for t in request.tickers if t.strip()]))
    
    if not tickers:
        return {"stocks": [], "csp_data": {}}
    
    print(f"CSP batch request for {len(tickers)} tickers...")
    start_time = time_module.time()
    
    results = []
    csp_data = {}
    
    async def fetch_stock_csp_data(ticker: str):
        """Fetch basic stock info + CSP metrics for one ticker."""
        try:
            stock = yf.Ticker(ticker)
            
            # Get recent history for price and RSI
            hist = stock.history(period="3mo")
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate 1-day change
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change_1d = current_price - prev_close
                change_1d_pct = (change_1d / prev_close) * 100
            else:
                change_1d = 0
                change_1d_pct = 0
            
            # Calculate RSI
            import pandas_ta as ta
            hist['RSI'] = ta.rsi(hist['Close'], length=14)
            rsi = hist['RSI'].iloc[-1] if not hist['RSI'].empty else None
            
            # Get company name
            name = POPULAR_STOCKS.get(ticker, None)
            if not name:
                try:
                    name = stock.info.get('shortName') or stock.info.get('longName') or ticker
                except:
                    name = ticker
            
            stock_info = {
                "symbol": ticker,
                "name": name,
                "price": sanitize(current_price),
                "change_1d": sanitize(change_1d),
                "change_1d_pct": sanitize(change_1d_pct),
                "indicators": {
                    "RSI": sanitize(rsi)
                }
            }
            
            # Fetch CSP-specific data (volatility and metrics)
            vol_data = calculate_volatility_metrics(ticker, use_cache=not request.refresh)
            csp_metrics = calculate_csp_metrics(ticker, use_cache=not request.refresh)
            
            # Merge CSP data
            csp_combined = {}
            if vol_data and "error" not in vol_data:
                csp_combined.update(vol_data)
            if csp_metrics and "error" not in csp_metrics:
                csp_combined.update(csp_metrics)
            
            return stock_info, csp_combined
            
        except Exception as e:
            print(f"CSP batch error for {ticker}: {e}")
            return None
    
    # Fetch all in parallel
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=min(len(tickers), 20)) as executor:
        tasks = [loop.run_in_executor(executor, lambda t=t: asyncio.run(
            # We need to call the async-friendly version
            asyncio.get_event_loop().run_in_executor(None, lambda: None)
        ) or fetch_stock_csp_data_sync(t)) for t in tickers]
        
    # Simpler sync approach - works better for yfinance
    def fetch_stock_csp_data_sync(ticker: str):
        """Sync version for thread pool."""
        try:
            stock = yf.Ticker(ticker)
            
            # Get recent history for price and RSI
            hist = stock.history(period="3mo")
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate 1-day change
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change_1d = current_price - prev_close
                change_1d_pct = (change_1d / prev_close) * 100
            else:
                change_1d = 0
                change_1d_pct = 0
            
            # Calculate RSI
            import pandas_ta as ta
            hist['RSI'] = ta.rsi(hist['Close'], length=14)
            rsi = hist['RSI'].iloc[-1] if not hist['RSI'].empty else None
            
            # Get company name
            name = POPULAR_STOCKS.get(ticker, None)
            if not name:
                try:
                    name = stock.info.get('shortName') or stock.info.get('longName') or ticker
                except:
                    name = ticker
            
            stock_info = {
                "symbol": ticker,
                "name": name,
                "price": sanitize(current_price),
                "change_1d": sanitize(change_1d),
                "change_1d_pct": sanitize(change_1d_pct),
                "indicators": {
                    "RSI": sanitize(rsi)
                }
            }
            
            # Fetch CSP-specific data (volatility and metrics)
            vol_data = calculate_volatility_metrics(ticker, use_cache=not request.refresh)
            csp_metrics = calculate_csp_metrics(ticker, use_cache=not request.refresh)
            
            # Merge CSP data
            csp_combined = {}
            if vol_data and "error" not in vol_data:
                csp_combined.update(vol_data)
            if csp_metrics and "error" not in csp_metrics:
                csp_combined.update(csp_metrics)
            
            return ticker, stock_info, csp_combined
            
        except Exception as e:
            print(f"CSP batch error for {ticker}: {e}")
            return ticker, None, {}
    
    # Use thread pool for parallel fetching
    with ThreadPoolExecutor(max_workers=min(len(tickers), 20)) as executor:
        fetch_results = list(executor.map(fetch_stock_csp_data_sync, tickers))
    
    for result in fetch_results:
        if result:
            ticker, stock_info, csp_combined = result
            if stock_info:
                results.append(stock_info)
                csp_data[ticker] = csp_combined
    
    print(f"CSP batch completed in {time_module.time() - start_time:.2f}s for {len(results)} stocks")
    
    return {
        "stocks": results,
        "csp_data": csp_data
    }


@app.get("/api/search-stocks/{query}")
async def search_stocks(query: str):
    """
    Search for stocks matching the query.
    Uses yfinance to lookup ticker info.
    Returns top matches with symbol, name, and exchange.
    """
    import re
    
    try:
        query = query.upper().strip()
        
        if len(query) < 1:
            return {"results": []}
        
        results = []
        
        # First, check for exact matches
        if query in POPULAR_STOCKS:
            results.append({
                "symbol": query,
                "name": POPULAR_STOCKS[query],
                "exchange": "NASDAQ/NYSE"
            })
        
        # Then find partial matches (symbol starts with query)
        for symbol, name in POPULAR_STOCKS.items():
            if symbol != query and symbol.startswith(query):
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "exchange": "NASDAQ/NYSE"
                })
        
        # Also search by company name
        query_lower = query.lower()
        for symbol, name in POPULAR_STOCKS.items():
            if query_lower in name.lower() and symbol not in [r["symbol"] for r in results]:
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "exchange": "NASDAQ/NYSE"
                })
        
        # If query looks like a ticker and not in our list, try to validate with yfinance
        if len(results) == 0 and len(query) <= 5 and query.isalpha():
            try:
                stock = yf.Ticker(query)
                info = stock.info
                if info and info.get('shortName') or info.get('longName'):
                    results.append({
                        "symbol": query,
                        "name": info.get('shortName') or info.get('longName') or query,
                        "exchange": info.get('exchange', 'Unknown')
                    })
            except:
                pass
        
        # Limit to top 10 results
        return {"results": results[:10]}
        
    except Exception as e:
        print(f"Stock search error: {e}")
        return {"results": [], "error": str(e)}


@app.get("/api/mystic-pulse/{ticker}")
async def get_mystic_pulse(ticker: str, period: str = "1y", adx_length: int = 9, smoothing_factor: int = 1, refresh: bool = False):
    """
    Get Mystic Pulse v2.0 indicator data for a stock.
    
    Parameters:
    - ticker: Stock symbol (e.g., AAPL)
    - period: History period to return (default: 1y). Options: 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y
    - adx_length: ADX smoothing length (default: 9)
    - smoothing_factor: OHLC SMA pre-smoothing length (default: 1)
    - refresh: Force fresh data fetch, bypassing cache (default: false)
    
    Caching strategy: Full 10y Mystic Pulse data is cached per ticker. Period filtering happens on response.
    
    Returns OHLC data with Mystic Pulse values including:
    - di_plus, di_minus: Directional Index values
    - positive_intensity, negative_intensity: Normalized streak intensities (0-1)
    - dominant_direction: 1 (bullish), -1 (bearish), 0 (neutral)
    - pulse_color: RGB color string for visualization
    """
    import math
    from datetime import datetime, timedelta
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 4) if isinstance(val, float) else val
    
    # Period to days mapping for filtering
    period_days = {
        "1mo": 30, "1m": 30,
        "3mo": 90, "3m": 90,
        "6mo": 180, "6m": 180,
        "1y": 365, "1year": 365,
        "2y": 730, "2year": 730,
        "3y": 1095, "3year": 1095,
        "5y": 1825, "5year": 1825,
        "10y": 3650, "10year": 3650,
        "max": 99999
    }
    
    try:
        ticker = ticker.upper().strip()
        period = period.lower().strip()
        # Cache key is ticker + indicator params only (not period)
        cache_key = f"mystic_pulse:{ticker}:{adx_length}:{smoothing_factor}"
        
        full_data = None
        
        # Check cache first (unless refresh requested)
        if not refresh:
            cached = cache.get(cache_key)
            if cached is not None:
                full_data = cached.get("full_data", [])
        
        # Fetch and calculate fresh data if needed
        if full_data is None or refresh:
            stock = yf.Ticker(ticker)
            # Always fetch 10y for full data
            hist = stock.history(period="10y")
            
            if hist.empty or len(hist) < 30:
                raise HTTPException(status_code=400, detail=f"Insufficient data for {ticker}")
            
            # Calculate Mystic Pulse on full data
            pulse_df = calculate_mystic_pulse(
                hist, 
                adx_length=adx_length, 
                smoothing_factor=smoothing_factor
            )
            
            # Prepare full data points
            full_data = []
            for date, row in pulse_df.iterrows():
                full_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": sanitize(row["Open"]),
                    "high": sanitize(row["High"]),
                    "low": sanitize(row["Low"]),
                    "close": sanitize(row["Close"]),
                    "volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 0,
                    "plus_di": sanitize(row.get("di_plus")),
                    "minus_di": sanitize(row.get("di_minus")),
                    "positive_intensity": sanitize(row.get("positive_intensity")),
                    "negative_intensity": sanitize(row.get("negative_intensity")),
                    "dominant_direction": int(row.get("dominant_direction", 0)),
                    "pulse_color": row.get("pulse_color", "rgb(128,128,128)")
                })
            
            # Cache the full data
            cache.set(cache_key, {"full_data": full_data})
        
        # Filter data based on requested period
        days = period_days.get(period, 365)  # Default to 1y
        if days < 99999 and full_data:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            filtered_data = [d for d in full_data if d["date"] >= cutoff_date]
        else:
            filtered_data = full_data
        
        # Generate summary from filtered data (use last entry for summary)
        if filtered_data:
            last = filtered_data[-1]
            prev = filtered_data[-2] if len(filtered_data) > 1 else last
            
            trend_score = last.get("dominant_direction", 0)
            strength = abs(last.get("positive_intensity", 0) if trend_score > 0 else last.get("negative_intensity", 0))
            
            if trend_score > 0:
                trend = "bullish"
            elif trend_score < 0:
                trend = "bearish"
            else:
                trend = "neutral"
            
            summary = {
                "trend": trend,
                "strength": round(float(strength), 3),
                "momentum": "steady",
                "trend_score": trend_score,
                "di_plus": last.get("plus_di", 0),
                "di_minus": last.get("minus_di", 0),
                "positive_intensity": last.get("positive_intensity", 0),
                "negative_intensity": last.get("negative_intensity", 0),
                "pulse_color": last.get("pulse_color", "rgb(128,128,128)")
            }
        else:
            summary = {"error": "No data available"}
        
        # Check if this was from cache
        is_cached = not refresh and cache.get(cache_key) is not None
        
        return {
            "symbol": ticker,
            "period": period,
            "adx_length": adx_length,
            "smoothing_factor": smoothing_factor,
            "data": filtered_data,
            "summary": summary,
            "_cached": is_cached
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Mystic Pulse error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/market-news")
async def get_market_news(tickers: str = ""):
    """
    Get top market news that could affect overall market sentiment or individual stocks.
    Pass comma-separated tickers to include stock-specific news, or leave empty for general market news.
    """
    from datetime import datetime
    import math
    
    def sanitize(val):
        if val is None:
            return None
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val
    
    try:
        all_news = []
        seen_titles = set()  # To avoid duplicates
        
        # Always include general market tickers for broader market sentiment
        market_tickers = ["SPY", "QQQ", "DIA"]
        
        # Add user-specified tickers
        if tickers:
            user_tickers = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            market_tickers.extend(user_tickers)
        
        # Remove duplicates while preserving order
        unique_tickers = list(dict.fromkeys(market_tickers))
        
        # Parallel fetch for news
        def fetch_ticker_news(t_symbol):
            try:
                stock_obj = yf.Ticker(t_symbol)
                return stock_obj.news
            except:
                return []

        news_results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(fetch_ticker_news, t): t for t in unique_tickers}
            for future in future_to_ticker:
                t_sym = future_to_ticker[future]
                try:
                    news_results[t_sym] = future.result()
                except:
                    news_results[t_sym] = []
        
        for ticker_symbol in unique_tickers:
            try:
                news = news_results.get(ticker_symbol, [])
                
                if news:
                    for article in news[:5]:  # Get top 5 per ticker
                        # Handle both old and new yfinance formats
                        content = article.get('content', article)
                        
                        title = content.get('title', '')
                        if not title:
                            continue
                        
                        # Skip if we've seen this title
                        if title in seen_titles:
                            continue
                        seen_titles.add(title)
                        
                        # Calculate sentiment
                        blob = TextBlob(title)
                        sentiment_score = blob.sentiment.polarity
                        
                        if sentiment_score > 0.1:
                            sentiment = "bullish"
                        elif sentiment_score < -0.1:
                            sentiment = "bearish"
                        else:
                            sentiment = "neutral"
                        
                        # Extract publish time - handle both formats
                        publish_time = article.get('providerPublishTime', 0)
                        pub_date_str = content.get('pubDate', '')
                        
                        if pub_date_str:
                            try:
                                # New format: ISO string like "2025-12-12T17:19:04Z"
                                publish_date = datetime.strptime(pub_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                                publish_time = int(publish_date.timestamp())
                            except:
                                publish_date = datetime.now()
                        elif publish_time:
                            publish_date = datetime.fromtimestamp(publish_time)
                        else:
                            publish_date = datetime.now()
                        
                        # Get publisher - handle both formats
                        provider = content.get('provider', {})
                        publisher = provider.get('displayName', content.get('publisher', 'Unknown')) if isinstance(provider, dict) else 'Unknown'
                        
                        # Get link - handle both formats
                        click_through = content.get('clickThroughUrl', {})
                        link = click_through.get('url', article.get('link', '')) if isinstance(click_through, dict) else article.get('link', '')
                        
                        # Get thumbnail - handle both formats
                        thumbnail_data = content.get('thumbnail', article.get('thumbnail', {}))
                        thumbnail_url = ''
                        if thumbnail_data:
                            resolutions = thumbnail_data.get('resolutions', [])
                            if resolutions and len(resolutions) > 0:
                                thumbnail_url = resolutions[0].get('url', '')
                        
                        all_news.append({
                            "title": title,
                            "link": link,
                            "publisher": publisher,
                            "published": publish_date.strftime("%Y-%m-%d %H:%M"),
                            "timestamp": publish_time,
                            "related_ticker": ticker_symbol if ticker_symbol not in ["SPY", "QQQ", "DIA"] else "Market",
                            "sentiment": sentiment,
                            "sentiment_score": round(sentiment_score, 3),
                            "thumbnail": thumbnail_url
                        })
            except Exception as e:
                print(f"Error fetching news for {ticker_symbol}: {e}")
                continue
        
        # Sort by timestamp (newest first) and take top 10
        all_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        top_news = all_news[:10]
        
        return {
            "news": top_news,
            "count": len(top_news),
            "tickers_scanned": unique_tickers
        }
        
    except Exception as e:
        print(f"Market news error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Email configuration
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "iks.kumar.iitd@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "iks.kumar.iitd@gmail.com")


class EmailRequest(BaseModel):
    stocks: List[Dict[str, Any]]
    csp_data: Dict[str, Any]


@app.post("/api/send-email")
async def send_email_report(request: EmailRequest):
    """Send CSP Opportunity Summary via email."""
    
    if not EMAIL_PASSWORD:
        raise HTTPException(status_code=500, detail="Email not configured. Missing EMAIL_PASSWORD.")
    
    try:
        stocks = request.stocks
        csp_data = request.csp_data
        
        # Build HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                h1 {{ color: #1a1a2e; margin-bottom: 8px; }}
                .subtitle {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
                th {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                tr:hover {{ background-color: #f9f9f9; }}
                .positive {{ color: #27ae60; font-weight: 600; }}
                .negative {{ color: #e74c3c; font-weight: 600; }}
                .excellent {{ color: #9b59b6; }}
                .good {{ color: #27ae60; }}
                .moderate {{ color: #f39c12; }}
                .poor {{ color: #e74c3c; }}
                .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 CSP Opportunity Summary</h1>
                <p class="subtitle">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
                
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Company</th>
                            <th>Price</th>
                            <th>1D Change</th>
                            <th>RSI</th>
                            <th>52W Low</th>
                            <th>52W High</th>
                            <th>IV/HV Rank</th>
                            <th>CSP Rating</th>
                        </tr>
                    </thead>
                    <tbody>

        """
        
        # Sort stocks by CSP rating (IV/HV rank) - same order as UI
        def get_rank(stock):
            symbol = stock.get('symbol', '')
            vol_data = csp_data.get(symbol, {})
            iv_rank = vol_data.get('iv_rank')
            hv_rank = vol_data.get('hv_rank')
            rank = iv_rank if iv_rank is not None else hv_rank
            return rank if rank is not None else -1
        
        sorted_stocks = sorted(
            [s for s in stocks if not s.get('error')],
            key=get_rank,
            reverse=True  # Best (highest rank) first
        )
        
        for stock in sorted_stocks:
            symbol = stock.get('symbol', 'N/A')
            price = stock.get('price', 0)
            change_1d = stock.get('change_1d', 0)
            change_1d_pct = stock.get('change_1d_pct', 0)
            rsi = stock.get('indicators', {}).get('RSI', None)
            
            vol_data = csp_data.get(symbol, {})
            week52_low = vol_data.get('week52_low')
            week52_high = vol_data.get('week52_high')
            iv_rank = vol_data.get('iv_rank')
            hv_rank = vol_data.get('hv_rank')
            rank = iv_rank if iv_rank is not None else hv_rank
            
            # Determine CSP rating
            if rank is not None:
                if rank >= 75:
                    rating_text, rating_class = "Excellent", "excellent"
                elif rank >= 50:
                    rating_text, rating_class = "Good", "good"
                elif rank >= 25:
                    rating_text, rating_class = "Moderate", "moderate"
                else:
                    rating_text, rating_class = "Poor", "poor"
            else:
                rating_text, rating_class = "N/A", ""
            
            change_class = "positive" if change_1d >= 0 else "negative"
            change_sign = "+" if change_1d >= 0 else ""
            
            html_content += f"""
                <tr>
                            <td><strong>{symbol}</strong></td>
                            <td style="font-size: 0.9em; color: #555;">{stock.get('name', symbol)}</td>
                            <td>${price:.2f}</td>
                            <td class="{change_class}">{change_sign}{change_1d:.2f} ({change_sign}{change_1d_pct:.2f}%)</td>
                            <td>{f'{rsi:.1f}' if rsi else 'N/A'}</td>
                            <td>{f'${week52_low:.2f}' if week52_low else 'N/A'}</td>
                            <td>{f'${week52_high:.2f}' if week52_high else 'N/A'}</td>
                            <td>{f'{rank:.0f}%' if rank else 'N/A'}</td>
                            <td class="{rating_class}">{rating_text}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>This report was generated by Stock Analyzer Pro.</p>
                    <p>🟣 Excellent (IV Rank ≥75%) | 🟢 Good (≥50%) | 🟡 Moderate (≥25%) | 🔴 Poor (<25%)</p>
                    <p style="margin-top: 12px;">
                        <a href="https://stock-analyzer-641888119120.us-central1.run.app/" 
                           style="color: #667eea; text-decoration: none; font-weight: 600;">
                           🚀 Open Stock Analyzer Pro
                        </a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 CSP Opportunity Summary - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        
        return {"success": True, "message": f"Email sent to {EMAIL_RECIPIENT}"}
        
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="Email authentication failed. Check credentials.")
    except Exception as e:
        print(f"Email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduled-email")
@app.get("/api/scheduled-email")  # Allow GET for Cloud Scheduler
async def scheduled_email_report():
    """
    Fetch fresh data for all watchlist tickers and send CSP summary email.
    This endpoint is designed to be called by Cloud Scheduler.
    """
    import json
    
    if not EMAIL_PASSWORD:
        raise HTTPException(status_code=500, detail="Email not configured. Missing EMAIL_PASSWORD.")
    
    try:
        # Load watchlist from config.json
        config_path = os.path.join(frontend_path, "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        tickers = config.get('defaultWatchlist', [])
        
        if not tickers:
            raise HTTPException(status_code=400, detail="No tickers in watchlist")
        
        print(f"Scheduled email: Fetching data for {len(tickers)} tickers...")
        
        # Fetch fresh stock data for all tickers (BULK OPTIMIZED)
        stocks = await perform_bulk_analysis(tickers)
        
        # Fetch CSP metrics for all tickers (PARALLEL)
        # We need options data which is not bulk-fetchable yet via yfinance standard
        def fetch_csp_data(stock):
            if stock.get('error') or not stock.get('symbol'):
                return None
            try:
                symbol = stock['symbol']
                vol_result = calculate_volatility_metrics(symbol)
                metrics_result = calculate_csp_metrics(symbol)
                return (symbol, {**vol_result, **metrics_result})
            except Exception as e:
                print(f"Error fetching CSP data for {stock.get('symbol')}: {e}")
                return None
        
        valid_stocks = [s for s in stocks if not s.get('error') and s.get('symbol')]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            csp_tasks = [loop.run_in_executor(executor, fetch_csp_data, stock) 
                         for stock in valid_stocks]
            csp_results = await asyncio.gather(*csp_tasks)
        
        # Build csp_data dictionary from results
        csp_data = {}
        for result in csp_results:
            if result:
                symbol, data = result
                csp_data[symbol] = data
        
        print(f"Scheduled email: Data fetched, generating email...")
        
        # Build and send email (reuse the email generation logic)
        # Sort stocks by CSP rating (IV/HV rank)
        def get_rank(stock):
            symbol = stock.get('symbol', '')
            vol_data = csp_data.get(symbol, {})
            iv_rank = vol_data.get('iv_rank')
            hv_rank = vol_data.get('hv_rank')
            rank = iv_rank if iv_rank is not None else hv_rank
            return rank if rank is not None else -1
        
        sorted_stocks = sorted(
            [s for s in stocks if not s.get('error')],
            key=get_rank,
            reverse=True
        )
        
        # Build HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                h1 {{ color: #1a1a2e; margin-bottom: 8px; }}
                .subtitle {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
                th {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; }}
                tr:hover {{ background-color: #f9f9f9; }}
                .positive {{ color: #27ae60; font-weight: 600; }}
                .negative {{ color: #e74c3c; font-weight: 600; }}
                .excellent {{ color: #9b59b6; font-weight: 600; }}
                .good {{ color: #27ae60; font-weight: 600; }}
                .moderate {{ color: #f39c12; font-weight: 600; }}
                .poor {{ color: #e74c3c; font-weight: 600; }}
                .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Daily CSP Opportunity Summary</h1>
                <p class="subtitle">Scheduled Report - {datetime.now().strftime("%Y-%m-%d %H:%M")} SGT</p>
                
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Company</th>
                            <th>Price</th>
                            <th>1D Change</th>
                            <th>RSI</th>
                            <th>52W Low</th>
                            <th>52W High</th>
                            <th>IV/HV Rank</th>
                            <th>CSP Rating</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for stock in sorted_stocks:
            symbol = stock.get('symbol', 'N/A')
            price = stock.get('price', 0)
            change_1d = stock.get('change_1d', 0)
            change_1d_pct = stock.get('change_1d_pct', 0)
            rsi = stock.get('indicators', {}).get('RSI', None)
            
            vol_data = csp_data.get(symbol, {})
            week52_low = vol_data.get('week52_low')
            week52_high = vol_data.get('week52_high')
            iv_rank = vol_data.get('iv_rank')
            hv_rank = vol_data.get('hv_rank')
            rank = iv_rank if iv_rank is not None else hv_rank
            
            if rank is not None:
                if rank >= 75:
                    rating_text, rating_class = "🟣 Excellent", "excellent"
                elif rank >= 50:
                    rating_text, rating_class = "🟢 Good", "good"
                elif rank >= 25:
                    rating_text, rating_class = "🟡 Moderate", "moderate"
                else:
                    rating_text, rating_class = "🔴 Poor", "poor"
            else:
                rating_text, rating_class = "N/A", ""
            
            change_class = "positive" if change_1d >= 0 else "negative"
            change_sign = "+" if change_1d >= 0 else ""
            
            html_content += f"""
                        <tr>
                            <td><strong>{symbol}</strong></td>
                            <td style="font-size: 0.9em; color: #555;">{stock.get('name', symbol)}</td>
                            <td>${price:.2f}</td>
                            <td class="{change_class}">{change_sign}{change_1d:.2f} ({change_sign}{change_1d_pct:.2f}%)</td>
                            <td>{f'{rsi:.1f}' if rsi else 'N/A'}</td>
                            <td>{f'${week52_low:.2f}' if week52_low else 'N/A'}</td>
                            <td>{f'${week52_high:.2f}' if week52_high else 'N/A'}</td>
                            <td>{f'{rank:.0f}%' if rank else 'N/A'}</td>
                            <td class="{rating_class}">{rating_text}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>This is an automated daily report from Stock Analyzer Pro.</p>
                    <p>🟣 Excellent (IV Rank ≥75%) | 🟢 Good (≥50%) | 🟡 Moderate (≥25%) | 🔴 Poor (<25%)</p>
                    <p style="margin-top: 12px;">
                        <a href="https://stock-analyzer-641888119120.us-central1.run.app/" 
                           style="color: #667eea; text-decoration: none; font-weight: 600;">
                           🚀 Open Stock Analyzer Pro
                        </a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create and send email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Daily CSP Summary - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        
        print(f"Scheduled email sent successfully to {EMAIL_RECIPIENT}")
        return {"success": True, "message": f"Scheduled email sent to {EMAIL_RECIPIENT}", "tickers_analyzed": len(sorted_stocks)}
        
    except Exception as e:
        print(f"Scheduled email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# YouTube Stock Extraction Feature
# ============================================

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import urllib.request
import json as json_lib

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# YouTube channels to monitor - using @handle format
YOUTUBE_CHANNELS = {
    "ZipTrader": "@ZipTrader"  # ZipTrader handle
}


def get_channel_videos(channel_handle: str, max_results: int = 5) -> List[Dict]:
    """Fetch latest videos from a YouTube channel using web scraping."""
    try:
        # Use handle-based URL (more reliable)
        if channel_handle.startswith("@"):
            url = f"https://www.youtube.com/{channel_handle}/videos"
        else:
            url = f"https://www.youtube.com/channel/{channel_handle}/videos"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        print(f"  Fetching URL: {url}")
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=15)
        html = response.read().decode('utf-8')
        print(f"  HTML length: {len(html)} chars")
        
        # Extract video IDs from the page
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        unique_ids = list(dict.fromkeys(video_ids))[:max_results]
        print(f"  Found {len(unique_ids)} unique video IDs")
        
        # Extract video titles
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}\]', html)
        
        # Extract publish dates (e.g., "1 day ago", "2 weeks ago")
        publish_texts = re.findall(r'"publishedTimeText":\{"simpleText":"([^"]+)"\}', html)
        
        videos = []
        for i, vid_id in enumerate(unique_ids):
            title = titles[i] if i < len(titles) else f"Video {i+1}"
            publish_date = publish_texts[i] if i < len(publish_texts) else "Unknown"
            videos.append({
                "video_id": vid_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "published": publish_date
            })
            print(f"  Video {i+1}: {vid_id} - {title[:50]}...")
        
        return videos
    except Exception as e:
        print(f"Error fetching channel videos: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_video_transcript(video_id: str) -> str:
    """Get transcript/captions for a YouTube video."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        try:
            # 1. Try listing transcripts (robust method for v0.6.0+)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Find English transcript (manual or auto-generated)
            # This looks for 'en' or variations
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']) 
            transcript_data = transcript.fetch()
            
        except Exception:
            # Fallback for older interface if needed, or if listing fails
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
            
        full_text = " ".join([t['text'] for t in transcript_data])
        return full_text
        
    except Exception as e:
        print(f"Error getting transcript for {video_id}: {e}")
        return ""


@app.get("/api/debug-models")
def list_gemini_models():
    """List available Gemini models for debugging."""
    if not GEMINI_API_KEY:
        return {"error": "No API Key"}
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return {"models": models}
    except Exception as e:
        return {"error": str(e)}


def get_video_description(video_id: str) -> str:
    """Fetch video description via web scraping as a fallback."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request, timeout=10)
        html = response.read().decode('utf-8')
        
        # Method 1: Meta tag (simplest)
        # <meta name="description" content="...">
        match = re.search(r'<meta name="description" content="([^"]+)">', html)
        if match:
            desc = match.group(1)
            # Unescape HTML entities
            import html as html_lib
            return html_lib.unescape(desc)
            
        return ""
    except Exception as e:
        print(f"Error fetching description for {video_id}: {e}")
        return ""


def extract_stocks_with_gemini(transcript: str, video_title: str) -> List[Dict]:
    """Use Gemini AI to extract stock tickers from video transcript."""
    if not GEMINI_API_KEY:
        return []
    
    try:
        model = genai.GenerativeModel('gemini-3-pro-preview')
        
        # Prepare content, truncating if too long
        content_text = transcript[:15000]
        
        prompt = f"""Analyze this YouTube video content (transcript or description) about stocks and extract all stock tickers mentioned.

Video Title: {video_title}

Content:
{content_text}

Instructions:
1. Identify stock tickers (e.g., AAPL, TSLA, PLTR).
2. Determine sentiment for each (BULLISH, BEARISH, NEUTRAL).
3. Provide a brief reason (max 10 words) based on the text.
4. Output strict JSON array format.

Output Format:
[
  {{
    "ticker": "TICKER",
    "sentiment": "BULLISH",
    "reason": "Brief reason"
  }}
]

If no stocks are mentioned, return empty list [].
Only return valid JSON, no other text."""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean markdown formatting from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        stocks = json_lib.loads(response_text)
        return stocks if isinstance(stocks, list) else []
        
    except Exception as e:
        print(f"Gemini extraction error: {e}")
        return []


@app.get("/api/youtube-stocks")
async def get_youtube_stock_recommendations():
    """
    Fetch latest videos from monitored YouTube channels and extract stock recommendations.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        all_recommendations = []
        
        for channel_name, channel_id in YOUTUBE_CHANNELS.items():
            print(f"Fetching videos from {channel_name}...")
            # Optimization: Only fetch the latest 1 video per channel for faster analysis
            videos = get_channel_videos(channel_id, max_results=1)
            
            for video in videos:
                print(f"  Processing: {video['title']}")
                
                # 1. Try Transcript
                content = get_video_transcript(video['video_id'])
                content_type = "transcript"
                
                # 2. Fallback to Description
                if not content or len(content) < 50:
                    print(f"  No transcript for {video['video_id']}, trying description...")
                    content = get_video_description(video['video_id'])
                    content_type = "description"
                
                if content:
                    print(f"  Analyzing {content_type} ({len(content)} chars)...")
                    stocks = extract_stocks_with_gemini(content, video['title'])
                    
                    for stock in stocks:
                        all_recommendations.append({
                            "ticker": stock.get('ticker', '').upper(),
                            "sentiment": stock.get('sentiment', 'NEUTRAL'),
                            "reason": stock.get('reason', ''),
                            "source": channel_name,
                            "video_title": video['title'],
                            "video_url": video['url'],
                            "published": video.get('published', 'Unknown')
                        })
        
        # Consolidate by ticker (combine mentions from multiple videos)
        consolidated = {}
        for rec in all_recommendations:
            ticker = rec['ticker']
            if ticker not in consolidated:
                consolidated[ticker] = {
                    "ticker": ticker,
                    "sentiment": rec['sentiment'],
                    "mentions": 1,
                    "sources": [{"channel": rec['source'], "video": rec['video_title'], "url": rec['video_url'], "reason": rec['reason'], "published": rec.get('published', 'Unknown')}]
                }
            else:
                consolidated[ticker]['mentions'] += 1
                consolidated[ticker]['sources'].append({
                    "channel": rec['source'],
                    "video": rec['video_title'],
                    "url": rec['video_url'],
                    "reason": rec['reason'],
                    "published": rec.get('published', 'Unknown')
                })
        
        # Sort by mentions (most mentioned first)
        sorted_recommendations = sorted(consolidated.values(), key=lambda x: x['mentions'], reverse=True)
        
        return {
            "success": True,
            "recommendations": sorted_recommendations,
            "channels_scanned": list(YOUTUBE_CHANNELS.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"YouTube stocks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/youtube-video-list")
def get_youtube_video_list():
    """Fetch latest video titles without Gemini analysis."""
    try:
        results = []
        for channel_name, channel_id in YOUTUBE_CHANNELS.items():
            videos = get_channel_videos(channel_id, max_results=5)
            for v in videos:
                v['channel'] = channel_name
            results.extend(videos)
        return {"success": True, "videos": results}
    except Exception as e:
        print(f"Video list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sp100")
async def get_sp100_data(refresh: bool = False):
    """Fetch S&P 100 data."""
    # 1. Get Tickers
    tickers = []
    try:
        tickers = SP100_TICKERS
    except Exception as e:
        print(f"Error fetching S&P 100 list: {e}")
        tickers = SP100_TICKERS

    # 2. Fetch Data in Bulk
    # Use the optimized bulk analysis function
    return await perform_bulk_analysis(tickers, refresh=refresh)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

