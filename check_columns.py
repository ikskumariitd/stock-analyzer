import yfinance as yf
ticker = "AAPL"
stock = yf.Ticker(ticker)
options = stock.options
if options:
    chain = stock.option_chain(options[0])
    print(f"Puts columns: {chain.puts.columns.tolist()}")
else:
    print("No options found for AAPL")
