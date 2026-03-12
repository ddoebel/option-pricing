import yfinance as yf

ticker = yf.Ticker("AAPL")

expirations = ticker.options
print(expirations)

chain = ticker.option_chain(expirations[0])

calls = chain.calls
puts = chain.puts