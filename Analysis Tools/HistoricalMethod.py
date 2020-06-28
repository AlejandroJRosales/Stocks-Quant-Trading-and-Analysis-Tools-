"""
Check out this website to learn about how to interpret this graph: https://www.investopedia.com/articles/basics/09/simplified-measuring-interpreting-volatility.asp
"""

import yfinance as yf
import matplotlib.pyplot as plt


def get_close_prices(stock, period='18mo'):
    ticker = yf.Ticker(stock)
    close_prices = [close for day, close in enumerate(ticker.history(period=period)["Close"]) if day % 15 == 0]

    return close_prices


def calc_diff(prices):
    return [(prices[price + 1] - prices[price]) / prices[price] for price in range(len(prices) - 1)]

stocks = ['APPN', 'GMED']
for stock in stocks:
    closing_prices = get_close_prices(stock)
    differences = calc_diff(closing_prices)
    num_bins = len(differences) * 2
    print(f'Viewing {stock} stock using historical method')
    n, bins, patches = plt.hist(differences, num_bins, alpha=0.75)
    plt.show()
