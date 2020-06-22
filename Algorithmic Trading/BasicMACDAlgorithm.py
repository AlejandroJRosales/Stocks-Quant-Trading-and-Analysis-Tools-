import alpaca_trade_api as tradeapi
import time
import datetime
import talib
import numpy as np
import yfinance as yf
from sample_config import *

APCA_API_BASE_URL = "https://paper-api.alpaca.markets"


class LongShort:
    def __init__(self, stock_universe, last_decisions):
        self.alpaca = tradeapi.REST(API_KEY, SECRET_KEY, APCA_API_BASE_URL, 'v2')
        self.stock_universe = stock_universe
        self.last_decisions = last_decisions

    def run(self):
        # First, cancel any existing orders so they don't impact our buying power.
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.cancel_order(order.id)

        while True:
            try:
                if self.alpaca.get_clock().is_open:
                    self.rebalance()
                else:
                    self.await_market_open()

                # Wait for 1 hour to look at markets again
                time.sleep(60 * 60)
            except:
                print("Not Connected to Internet... Retrying in 5 minutes")
                time.sleep(60 * 5)
            print()

    # Wait for market to open.
    def await_market_open(self):
        clock = self.alpaca.get_clock()
        opening_time = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
        curr_time = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
        time_to_open = int((opening_time - curr_time) / 60)
        print(str(time_to_open) + " minutes til market open.")
        time.sleep(time_to_open)

    def rebalance(self):
        algo = TradingAlgorithms()

        for stock in self.stock_universe:
            current_decision = algo.intro_algo(stock)

            if self.last_decisions[stock] != current_decision and current_decision == "Buy":
                self.buy(stock)
            elif self.last_decisions[stock] != current_decision and current_decision == "Sell":
                self.sell(stock)
            else:
                print(f"HELD {stock}")

    def buy(self, stock):
        # Get how much buying power we have
        portfolio_cash = float(self.alpaca.get_account().cash)
        buying_power_per_stock = portfolio_cash // len(self.stock_universe)

        # get how many stock we can buy
        ticker_price = yf.Ticker(stock).info['ask']
        qty = buying_power_per_stock // ticker_price
        try:
            self.alpaca.submit_order(stock, qty, 'buy', 'market', 'day')
            self.last_decisions[stock] = "Buy"
            print(f"BOUGHT {qty} SHARES OF {stock}")
        except:
            print(f"BUYING OF {qty} {stock} DID NOT GO THROUGH")

    def sell(self, stock):
        positions = self.alpaca.list_positions()
        qty = abs(int(float(positions[stock].qty)))

        try:
            if qty > 0:
                self.alpaca.submit_order(stock, qty, 'sell', 'market', 'day')
                self.last_decisions[stock] = "Sell"
                print(f"SOLD {qty} SHARES OF {stock}")
        except:
            print(f"SELLING OF {qty} {stock} DID NOT GO THROUGH")


class TradingAlgorithms:
    def __init__(self):
        self.period = "6mo"

    def get_high_low_close(self, stock):
        high_low_close = dict()
        ticker = yf.Ticker(stock)
        high_low_close['high'] = np.array([close for close in ticker.history(period=self.period)["Close"]])
        high_low_close['low'] = np.array([high for high in ticker.history(period=self.period)["High"]])
        high_low_close['close'] = np.array([low for low in ticker.history(period=self.period)["Low"]])

        return high_low_close

    # Create the MACD signal and pass in the three parameters: fast period, slow period, and the signal.
    def macdIndicator(self, hist):
        macd_raw, signal, hist2 = talib.MACD(hist['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        macd = macd_raw[-1] - signal[-1]

        return macd

    def intro_algo(self, stock):
        macd = self.macdIndicator(self.get_high_low_close(stock))
        if macd < 0:
            return "Sell"

        elif macd > 0:
            return "Buy"


def initialize():
    # The stocks to be monitored
    stock_universe = ['APPN', 'GMED']

    # Initialize the stock starting point
    algo = TradingAlgorithms()
    last_decisions = {stock: algo.intro_algo(stock) for stock in stock_universe}

    # Run the LongShort class
    ls = LongShort(stock_universe=stock_universe, last_decisions=last_decisions)
    ls.run()


initialize()
