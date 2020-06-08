import numpy as np
import scipy.stats
import yfinance as yf
import random


def get_mean_confidence_intervals(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t.ppf((1 + confidence) / 2., n-1)

    return m, m-h, m+h


def get_close_prices(stock, period='2mo'):
    ticker = yf.Ticker(stock)
    close_prices = [close for close in ticker.history(period=period)["Close"] if random.random() < 0.5]

    return close_prices

stocks = ['APPN', 'GMED']
for stock in stocks:
    mci = get_mean_confidence_intervals(get_close_prices(stock))
    print(f'Stock: {stock}\n95% Confidence Interval\nMean: {mci[0]}\nLower Bound: {mci[1]}\nUpper Bound : {mci[2]}\n\n')
