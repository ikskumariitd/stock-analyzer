import yfinance as yf
from datetime import datetime

def debug_options(ticker):
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")['Close'].iloc[-1]
    print(f"Current Price: ${price:.2f}")
    
    expiry = "2026-03-06"
    print(f"Checking expiry: {expiry}")
    
    chain = stock.option_chain(expiry)
    puts = chain.puts
    
    # Filter for strikes near current price
    relevant_puts = puts[(puts['strike'] >= price * 0.7) & (puts['strike'] <= price * 1.1)]
    
    print("\nRaw Puts near price:")
    print(relevant_puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].tail(10).to_string(index=False))

if __name__ == "__main__":
    debug_options("SMCI")
