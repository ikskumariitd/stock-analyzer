"""
Ripster EMA Clouds Calculation Module

Calculates 3 EMA cloud pairs to identify trend direction and momentum:
- Cloud 1: 5 & 12 Period EMAs (Short-term)
- Cloud 2: 34 & 50 Period EMAs (Medium-term)
- Cloud 3: 72 & 89 Period EMAs (Longer-term)
"""

import pandas as pd
import pandas_ta as ta


# EMA Cloud Configurations: (fast_period, slow_period, name)
EMA_CLOUDS = [
    (5, 12, "short_term"),
    (34, 50, "medium_term"),
    (72, 89, "long_term"),
]


def calculate_ripster_ema_clouds(hist: pd.DataFrame) -> dict:
    """
    Calculate Ripster EMA Clouds from price history.
    
    Args:
        hist: DataFrame with OHLCV data (must have 'Close' column)
        
    Returns:
        dict with:
        - clouds: list of cloud data with ema_fast, ema_slow, state (bullish/bearish)
        - summary: overall trend alignment info
    """
    if hist.empty or len(hist) < 89:  # Need at least 89 periods for longest EMA
        return {"error": "Insufficient data", "clouds": [], "summary": {}}
    
    clouds = []
    bullish_count = 0
    
    for fast_period, slow_period, name in EMA_CLOUDS:
        # Calculate EMAs
        ema_fast = ta.ema(hist['Close'], length=fast_period)
        ema_slow = ta.ema(hist['Close'], length=slow_period)
        
        if ema_fast is None or ema_slow is None:
            continue
            
        # Get latest values
        fast_val = ema_fast.iloc[-1] if not ema_fast.empty else None
        slow_val = ema_slow.iloc[-1] if not ema_slow.empty else None
        
        if fast_val is None or slow_val is None:
            state = "neutral"
        elif fast_val > slow_val:
            state = "bullish"
            bullish_count += 1
        else:
            state = "bearish"
        
        clouds.append({
            "name": name,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "ema_fast": round(float(fast_val), 2) if fast_val else None,
            "ema_slow": round(float(slow_val), 2) if slow_val else None,
            "state": state,
        })
    
    # Generate summary
    total_clouds = len(clouds)
    bearish_count = total_clouds - bullish_count
    
    if bullish_count == total_clouds:
        overall_trend = "strong_bullish"
    elif bullish_count >= 2:
        overall_trend = "bullish"
    elif bearish_count == total_clouds:
        overall_trend = "strong_bearish"
    elif bearish_count >= 2:
        overall_trend = "bearish"
    else:
        overall_trend = "mixed"
    
    summary = {
        "bullish_clouds": bullish_count,
        "bearish_clouds": bearish_count,
        "total_clouds": total_clouds,
        "overall_trend": overall_trend,
    }
    
    return {
        "clouds": clouds,
        "summary": summary,
    }
