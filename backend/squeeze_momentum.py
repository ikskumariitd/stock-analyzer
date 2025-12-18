"""
Squeeze Momentum Indicator [LazyBear]
=====================================
Python implementation of TradingView "Squeeze Momentum Indicator" by LazyBear.

This indicator detects when price is "squeezing" (Bollinger Bands inside
Keltner Channels) and shows momentum direction/strength via histogram.

Key states:
- Squeeze ON: BB inside KC (black dot in TradingView)
- Squeeze OFF: BB outside KC (gray dot in TradingView)
- No Squeeze: Neither condition (blue in original, we'll use gray)
"""

import numpy as np
import pandas as pd


def calculate_squeeze_momentum(
    df: pd.DataFrame,
    bb_length: int = 20,
    bb_mult: float = 2.0,
    kc_length: int = 20,
    kc_mult: float = 1.5,
    use_true_range: bool = True
) -> pd.DataFrame:
    """
    Calculate Squeeze Momentum Indicator values.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'Open', 'High', 'Low', 'Close' columns
    bb_length : int
        Bollinger Bands period (default: 20)
    bb_mult : float
        Bollinger Bands standard deviation multiplier (default: 2.0)
    kc_length : int
        Keltner Channel period (default: 20)
    kc_mult : float
        Keltner Channel ATR multiplier (default: 1.5)
    use_true_range : bool
        Use True Range for KC (default: True)
    
    Returns:
    --------
    pd.DataFrame with added columns for Squeeze Momentum indicator
    """
    result = df.copy()
    close = result['Close']
    high = result['High']
    low = result['Low']
    
    # === Calculate Bollinger Bands ===
    basis = close.rolling(window=bb_length).mean()
    dev = bb_mult * close.rolling(window=bb_length).std()
    upper_bb = basis + dev
    lower_bb = basis - dev
    
    # === Calculate Keltner Channels ===
    ma = close.rolling(window=kc_length).mean()
    
    if use_true_range:
        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        range_ma = true_range.rolling(window=kc_length).mean()
    else:
        # Simple range
        range_vals = high - low
        range_ma = range_vals.rolling(window=kc_length).mean()
    
    upper_kc = ma + range_ma * kc_mult
    lower_kc = ma - range_ma * kc_mult
    
    # === Detect Squeeze States ===
    # sqzOn: BB is inside KC
    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    # sqzOff: BB is outside KC
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
    # noSqz: neither
    no_sqz = ~sqz_on & ~sqz_off
    
    result['squeeze_on'] = sqz_on
    result['squeeze_off'] = sqz_off
    result['no_squeeze'] = no_sqz
    
    # === Calculate Momentum Value ===
    # val = linreg(close - avg(avg(highest(high, KC_length), lowest(low, KC_length)), sma(close, KC_length)), KC_length, 0)
    
    # Highest high and lowest low over KC period
    highest_high = high.rolling(window=kc_length).max()
    lowest_low = low.rolling(window=kc_length).min()
    
    # avg(highest, lowest)
    hl_avg = (highest_high + lowest_low) / 2
    
    # sma(close, KC_length)
    sma_close = close.rolling(window=kc_length).mean()
    
    # avg(hl_avg, sma_close)
    avg_val = (hl_avg + sma_close) / 2
    
    # source - avg_val
    source_diff = close - avg_val
    
    # Linear regression value using numpy polyfit (no scipy needed)
    # Pine Script linreg(source, length, offset) returns the value at offset bars back
    # For offset=0, it's the current projected value from linear regression
    
    momentum_vals = np.zeros(len(result))
    
    for i in range(kc_length - 1, len(result)):
        y = source_diff.iloc[i - kc_length + 1:i + 1].values
        if len(y) == kc_length and not np.any(np.isnan(y)):
            x = np.arange(kc_length)
            # Use numpy polyfit for linear regression (returns [slope, intercept])
            coeffs = np.polyfit(x, y, 1)
            slope, intercept = coeffs[0], coeffs[1]
            # Value at the last point (offset 0)
            momentum_vals[i] = intercept + slope * (kc_length - 1)
        else:
            momentum_vals[i] = 0
    
    result['momentum'] = momentum_vals
    
    # === Determine Colors ===
    # bcolor = iff(val > 0, 
    #              iff(val > nz(val[1]), lime, green),
    #              iff(val < nz(val[1]), red, maroon))
    
    colors = []
    prev_val = 0
    
    for i in range(len(result)):
        val = momentum_vals[i]
        prev_val = momentum_vals[i-1] if i > 0 else 0
        
        if val > 0:
            if val > prev_val:
                # Lime (bright green) - momentum increasing
                colors.append('#00FF00')
            else:
                # Green (darker) - momentum positive but decreasing
                colors.append('#008000')
        else:
            if val < prev_val:
                # Red (bright) - momentum decreasing
                colors.append('#FF0000')
            else:
                # Maroon (darker) - momentum negative but increasing
                colors.append('#800000')
    
    result['color'] = colors
    
    # === Squeeze State Color ===
    # scolor = noSqz ? blue : sqzOn ? black : gray
    squeeze_colors = []
    for i in range(len(result)):
        if no_sqz.iloc[i]:
            squeeze_colors.append('#808080')  # Gray for no squeeze
        elif sqz_on.iloc[i]:
            squeeze_colors.append('#000000')  # Black for squeeze ON
        else:
            squeeze_colors.append('#808080')  # Gray for squeeze OFF
    
    result['squeeze_color'] = squeeze_colors
    
    return result


def get_squeeze_momentum_summary(df: pd.DataFrame) -> dict:
    """
    Get summary statistics for Squeeze Momentum indicator.
    """
    if df.empty:
        return {"error": "Empty DataFrame"}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    momentum = latest.get('momentum', 0)
    prev_momentum = prev.get('momentum', 0)
    squeeze_on = bool(latest.get('squeeze_on', False))
    squeeze_off = bool(latest.get('squeeze_off', False))
    
    # Determine trend
    if momentum > 0:
        if momentum > prev_momentum:
            direction = "bullish_strengthening"
            trend = "bullish"
        else:
            direction = "bullish_weakening"
            trend = "bullish"
    else:
        if momentum < prev_momentum:
            direction = "bearish_strengthening"
            trend = "bearish"
        else:
            direction = "bearish_weakening"
            trend = "bearish"
    
    # Squeeze state
    if squeeze_on:
        squeeze_state = "squeeze_on"
        squeeze_text = "🔴 Squeeze ON - Building pressure"
    elif squeeze_off:
        squeeze_state = "squeeze_off"
        squeeze_text = "🟢 Squeeze Released - Breakout potential"
    else:
        squeeze_state = "neutral"
        squeeze_text = "⚪ No squeeze detected"
    
    return {
        "trend": trend,
        "direction": direction,
        "momentum": round(float(momentum), 4),
        "prev_momentum": round(float(prev_momentum), 4),
        "squeeze_on": squeeze_on,
        "squeeze_off": squeeze_off,
        "squeeze_state": squeeze_state,
        "squeeze_text": squeeze_text,
        "color": latest.get('color', '#808080'),
        "squeeze_color": latest.get('squeeze_color', '#808080')
    }
