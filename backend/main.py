from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from textblob import TextBlob
from datetime import datetime

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

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

def calculate_volatility_metrics(ticker_symbol: str):
    """
    Calculate IV Rank and related volatility metrics for CSP strategy.
    Returns dict with current_iv, iv_rank, hv_30, hv_rank, iv_hv_ratio, and recommendation.
    """
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
        
        # Try to get IV from options chain
        current_iv = None
        iv_rank = None
        iv_hv_ratio = None
        
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
                    chain = stock.option_chain(best_expiry)
                    puts = chain.puts
                    
                    if not puts.empty:
                        # Find ATM put (strike closest to current price)
                        puts['strike_diff'] = abs(puts['strike'] - current_price)
                        atm_put = puts.loc[puts['strike_diff'].idxmin()]
                        
                        # Get IV (yfinance returns as decimal, e.g., 0.35 = 35%)
                        if 'impliedVolatility' in atm_put and atm_put['impliedVolatility'] > 0:
                            current_iv = atm_put['impliedVolatility'] * 100
                            
                            # IV/HV Ratio
                            if current_hv_30 > 0:
                                iv_hv_ratio = current_iv / current_hv_30
                            
                            # For IV Rank, we use HV Rank as proxy since we don't have historical IV
                            # A more sophisticated approach would store daily IV readings
                            # For now, use current IV vs HV range as an approximation
                            iv_rank = hv_rank  # Proxy: assume IV rank tracks HV rank loosely
                            
        except Exception as e:
            print(f"Options data error for {ticker_symbol}: {e}")
        
        # Generate recommendation
        recommendation = generate_csp_recommendation(current_iv, iv_rank, hv_rank, iv_hv_ratio)
        
        return {
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


def calculate_csp_metrics(ticker_symbol: str):
    """
    Calculate CSP-specific metrics: 52-week range, ATR, support/resistance, earnings.
    """
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
        
        try:
            # Try to get earnings dates
            earnings_dates = stock.earnings_dates
            if earnings_dates is not None and not earnings_dates.empty:
                today = datetime.now()
                future_dates = earnings_dates[earnings_dates.index > pd.Timestamp(today)]
                if not future_dates.empty:
                    next_earnings_date = future_dates.index[0]
                    next_earnings = next_earnings_date.strftime("%Y-%m-%d")
                    days_to_earnings = (next_earnings_date - pd.Timestamp(today)).days
                    earnings_warning = days_to_earnings <= 30
        except Exception as e:
            print(f"Earnings data error for {ticker_symbol}: {e}")
            # Try alternative: calendar
            try:
                cal = stock.calendar
                if cal is not None and 'Earnings Date' in cal:
                    earnings_date = cal['Earnings Date']
                    if earnings_date:
                        if isinstance(earnings_date, list):
                            earnings_date = earnings_date[0]
                        next_earnings = str(earnings_date)[:10]
                        days_to_earnings = (pd.Timestamp(earnings_date) - pd.Timestamp(datetime.now())).days
                        earnings_warning = days_to_earnings <= 30 if days_to_earnings else False
            except:
                pass
        
        return {
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
        
    except Exception as e:
        print(f"CSP metrics error for {ticker_symbol}: {e}")
        return {"error": str(e)}


class BatchRequest(BaseModel):
    tickers: List[str]

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

    data = {
        "symbol": ticker,
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

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    try:
        return _analyze_ticker(ticker)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-batch")
async def analyze_batch(request: BatchRequest):
    results = []
    for ticker in request.tickers:
        try:
            data = _analyze_ticker(ticker)
            results.append(data)
        except Exception as e:
            # For batch, we return the error in the object so frontend can show per-card error
            results.append({
                "symbol": ticker.upper(),
                "error": str(e)
            })
    return results

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = "3y", include_bb: bool = True):
    """Get price history for charting. Period can be: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y, 10y, max"""
    import math
    
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return round(val, 2) if isinstance(val, float) else val
    
    try:
        ticker = ticker.upper().strip()
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No history found for {ticker}")
        
        # Calculate Bollinger Bands if requested
        if include_bb and len(hist) >= 20:
            # 20-period SMA
            hist['BB_Middle'] = hist['Close'].rolling(window=20).mean()
            # 20-period standard deviation
            rolling_std = hist['Close'].rolling(window=20).std()
            # Upper and lower bands (2 standard deviations)
            hist['BB_Upper'] = hist['BB_Middle'] + (rolling_std * 2)
            hist['BB_Lower'] = hist['BB_Middle'] - (rolling_std * 2)
        
        history_data = []
        for date, row in hist.iterrows():
            data_point = {
                "date": date.strftime("%Y-%m-%d"),
                "open": sanitize(row["Open"]),
                "high": sanitize(row["High"]),
                "low": sanitize(row["Low"]),
                "close": sanitize(row["Close"]),
                "volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 0
            }
            
            # Add BB data if available
            if include_bb and 'BB_Upper' in hist.columns:
                data_point["bb_upper"] = sanitize(row.get("BB_Upper"))
                data_point["bb_middle"] = sanitize(row.get("BB_Middle"))
                data_point["bb_lower"] = sanitize(row.get("BB_Lower"))
            
            history_data.append(data_point)
        
        return {
            "symbol": ticker,
            "history": history_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"History error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/volatility/{ticker}")
async def get_volatility(ticker: str):
    """Get volatility metrics for CSP strategy including IV Rank, HV, and recommendation."""
    try:
        ticker = ticker.upper().strip()
        result = calculate_volatility_metrics(ticker)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Volatility error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/csp-metrics/{ticker}")
async def get_csp_metrics(ticker: str):
    """Get CSP-specific metrics: 52-week range, ATR, support/resistance, earnings calendar."""
    try:
        ticker = ticker.upper().strip()
        result = calculate_csp_metrics(ticker)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"CSP metrics error for {ticker}: {e}")
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
        
        for ticker_symbol in unique_tickers:
            try:
                stock = yf.Ticker(ticker_symbol)
                news = stock.news
                
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
        
        # Fetch fresh stock data for all tickers
        stocks = []
        for ticker in tickers:
            try:
                data = _analyze_ticker(ticker)
                stocks.append(data)
            except Exception as e:
                print(f"Error analyzing {ticker}: {e}")
                stocks.append({"symbol": ticker, "error": str(e)})
        
        # Fetch CSP metrics for all tickers
        csp_data = {}
        for stock in stocks:
            if stock.get('error') or not stock.get('symbol'):
                continue
            try:
                symbol = stock['symbol']
                vol_result = calculate_volatility_metrics(symbol)
                metrics_result = calculate_csp_metrics(symbol)
                csp_data[symbol] = {**vol_result, **metrics_result}
            except Exception as e:
                print(f"Error fetching CSP data for {stock.get('symbol')}: {e}")
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

