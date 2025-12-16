"""
Mystic Pulse v2.0 Indicator
===========================
Python implementation of TradingView "Mystic Pulse V2.0 [CHE]" by chervolino.

Based on the official Pine Script source code.
This indicator measures directional persistence using adaptive DI streaks with 
gradient intensity visualization.
"""

import numpy as np
import pandas as pd


def wilder_smooth(series: pd.Series, length: int) -> pd.Series:
    """
    Wilder's smoothing method (recursive).
    Pine Script equivalent: smoothed := na(smoothed[1]) ? val : (smoothed[1] - (smoothed[1]/length) + val)
    """
    result = np.zeros(len(series))
    result[0] = series.iloc[0] if not pd.isna(series.iloc[0]) else 0
    
    for i in range(1, len(series)):
        val = series.iloc[i] if not pd.isna(series.iloc[i]) else 0
        result[i] = result[i-1] - (result[i-1] / length) + val
    
    return pd.Series(result, index=series.index)


def sma_smooth(series: pd.Series, length: int) -> pd.Series:
    """
    Simple Moving Average for OHLC pre-smoothing.
    """
    if length <= 1:
        return series
    return series.rolling(window=length, min_periods=1).mean()


def norm_in_window(series: pd.Series, window_len: int) -> pd.Series:
    """
    Normalize value within a rolling window (min-max normalization).
    """
    min_v = series.rolling(window=window_len, min_periods=1).min()
    max_v = series.rolling(window=window_len, min_periods=1).max()
    span_v = max_v - min_v
    span_safe = span_v.replace(0, 1)  # Avoid division by zero
    return (series - min_v) / span_safe


def gamma_adj(series: pd.Series, gamma: float) -> pd.Series:
    """
    Apply gamma adjustment for contrast control.
    """
    clamped = series.clip(0, 1)
    return np.power(clamped, gamma)


def calculate_mystic_pulse(
    df: pd.DataFrame,
    adx_length: int = 9,
    smoothing_factor: int = 1,
    collect_length: int = 100,
    gamma_bars: float = 0.7,
    gamma_plots: float = 0.8
) -> pd.DataFrame:
    """
    Calculate Mystic Pulse v2.0 indicator values.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'Open', 'High', 'Low', 'Close' columns
    adx_length : int
        ADX smoothing length for Wilder smoothing (default: 9)
    smoothing_factor : int
        OHLC SMA length for pre-smoothing (default: 1 = no smoothing)
    collect_length : int
        Gradient window for normalization (default: 100)
    gamma_bars : float
        Gamma for bars/shapes intensity (default: 0.7)
    gamma_plots : float
        Gamma for counter plots (default: 0.8)
    
    Returns:
    --------
    pd.DataFrame with added columns for Mystic Pulse indicator
    """
    result = df.copy()
    
    # === Step 1: Pre-smooth OHLC with SMA ===
    open_s = sma_smooth(result['Open'], smoothing_factor)
    high_s = sma_smooth(result['High'], smoothing_factor)
    low_s = sma_smooth(result['Low'], smoothing_factor)
    close_s = sma_smooth(result['Close'], smoothing_factor)
    
    # === Step 2: Calculate True Range and Directional Movement ===
    prev_close = close_s.shift(1)
    prev_high = high_s.shift(1)
    prev_low = low_s.shift(1)
    
    # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    tr1 = high_s - low_s
    tr2 = (high_s - prev_close).abs()
    tr3 = (low_s - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # +DM: if (high - prev_high) > (prev_low - low) then max(high - prev_high, 0) else 0
    up_move = high_s - prev_high
    down_move = prev_low - low_s
    
    dm_plus = np.where(
        (up_move > down_move) & (up_move > 0),
        up_move, 0
    )
    dm_minus = np.where(
        (down_move > up_move) & (down_move > 0),
        down_move, 0
    )
    
    dm_plus = pd.Series(dm_plus, index=result.index).fillna(0)
    dm_minus = pd.Series(dm_minus, index=result.index).fillna(0)
    
    # === Step 3: Apply Wilder Smoothing ===
    smoothed_tr = wilder_smooth(true_range.fillna(0), adx_length)
    smoothed_dm_plus = wilder_smooth(dm_plus, adx_length)
    smoothed_dm_minus = wilder_smooth(dm_minus, adx_length)
    
    # === Step 4: Calculate +DI and -DI ===
    denom = smoothed_tr.replace(0, np.nan)
    di_plus = (smoothed_dm_plus / denom * 100).fillna(0)
    di_minus = (smoothed_dm_minus / denom * 100).fillna(0)
    
    result['di_plus'] = di_plus
    result['di_minus'] = di_minus
    
    # === Step 5: Calculate Streak Counters ===
    # Positive count: increments when di_plus > di_plus[1] AND di_plus > di_minus
    # Negative count: increments when di_minus > di_minus[1] AND di_minus > di_plus
    # Opposite counter resets to 0
    
    positive_count = np.zeros(len(result))
    negative_count = np.zeros(len(result))
    
    prev_di_plus = di_plus.shift(1).fillna(0)
    prev_di_minus = di_minus.shift(1).fillna(0)
    
    for i in range(1, len(result)):
        # Check for positive increment
        if di_plus.iloc[i] > prev_di_plus.iloc[i] and di_plus.iloc[i] > di_minus.iloc[i]:
            positive_count[i] = positive_count[i-1] + 1
            negative_count[i] = 0
        # Check for negative increment
        elif di_minus.iloc[i] > prev_di_minus.iloc[i] and di_minus.iloc[i] > di_plus.iloc[i]:
            negative_count[i] = negative_count[i-1] + 1
            positive_count[i] = 0
        else:
            # Maintain previous counts
            positive_count[i] = positive_count[i-1]
            negative_count[i] = negative_count[i-1]
    
    result['positive_count'] = positive_count
    result['negative_count'] = negative_count
    
    # === Step 6: Calculate Trend Score ===
    trend_score = positive_count - negative_count
    result['trend_score'] = trend_score
    
    # === Step 7: Windowed Normalization ===
    pos_series = pd.Series(positive_count, index=result.index)
    neg_series = pd.Series(negative_count, index=result.index)
    trend_abs = pd.Series(np.abs(trend_score), index=result.index)
    
    mag_norm = norm_in_window(trend_abs, collect_length)
    pos_norm = norm_in_window(pos_series, collect_length)
    neg_norm = norm_in_window(neg_series, collect_length)
    
    # === Step 8: Apply Gamma Adjustment ===
    mag_norm_gamma = gamma_adj(mag_norm, gamma_bars)
    pos_norm_gamma = gamma_adj(pos_norm, gamma_plots)
    neg_norm_gamma = gamma_adj(neg_norm, gamma_plots)
    
    result['mag_intensity'] = mag_norm_gamma
    result['positive_intensity'] = pos_norm_gamma
    result['negative_intensity'] = neg_norm_gamma
    
    # === Step 9: Determine Dominant Direction ===
    dominant = np.where(trend_score > 0, 1, np.where(trend_score < 0, -1, 0))
    result['dominant_direction'] = dominant
    
    # === Step 10: Calculate Colors ===
    # Up colors: dark green (#005A00) to neon green (#00FF66)
    # Down colors: dark red (#7A0000) to neon red (#FF1A1A)
    
    colors = []
    for i in range(len(result)):
        score = trend_score[i]
        intensity = mag_norm_gamma.iloc[i]
        
        if score > 0:
            # Bullish - Green gradient
            r = int(0 + 0 * intensity)
            g = int(90 + 165 * intensity)  # 90 (dark) to 255 (neon)
            b = int(0 + 102 * intensity)   # 0 to 102
            colors.append(f"rgb({r},{g},{b})")
        elif score < 0:
            # Bearish - Red gradient
            r = int(122 + 133 * intensity)  # 122 (dark) to 255 (neon)
            g = int(0 + 26 * intensity)     # 0 to 26
            b = int(0 + 26 * intensity)     # 0 to 26
            colors.append(f"rgb({r},{g},{b})")
        else:
            # Neutral - Gray
            colors.append("rgb(128,128,128)")
    
    result['pulse_color'] = colors
    
    return result


def get_mystic_pulse_summary(df: pd.DataFrame) -> dict:
    """
    Get summary statistics for Mystic Pulse indicator.
    """
    if df.empty:
        return {"error": "Empty DataFrame"}
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    trend_score = latest.get('trend_score', 0)
    pos_int = latest.get('positive_intensity', 0)
    neg_int = latest.get('negative_intensity', 0)
    mag_int = latest.get('mag_intensity', 0)
    
    # Determine trend
    if trend_score > 0:
        trend = "bullish"
        strength = mag_int
    elif trend_score < 0:
        trend = "bearish"
        strength = mag_int
    else:
        trend = "neutral"
        strength = 0
    
    # Determine momentum
    prev_score = prev.get('trend_score', 0)
    if abs(trend_score) > abs(prev_score):
        momentum = "strengthening"
    elif abs(trend_score) < abs(prev_score):
        momentum = "weakening"
    else:
        momentum = "steady"
    
    return {
        "trend": trend,
        "strength": round(float(strength), 3),
        "momentum": momentum,
        "trend_score": int(trend_score),
        "di_plus": round(float(latest.get('di_plus', 0)), 2),
        "di_minus": round(float(latest.get('di_minus', 0)), 2),
        "positive_count": int(latest.get('positive_count', 0)),
        "negative_count": int(latest.get('negative_count', 0)),
        "positive_intensity": round(float(pos_int), 3),
        "negative_intensity": round(float(neg_int), 3),
        "pulse_color": latest.get('pulse_color', 'rgb(128,128,128)')
    }
