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
from typing import List, Dict, Any

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
async def get_history(ticker: str, period: str = "3y"):
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
        
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": sanitize(row["Open"]),
                "high": sanitize(row["High"]),
                "low": sanitize(row["Low"]),
                "close": sanitize(row["Close"]),
                "volume": int(row["Volume"]) if not math.isnan(row["Volume"]) else 0
            })
        
        return {
            "symbol": ticker,
            "history": history_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"History error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

