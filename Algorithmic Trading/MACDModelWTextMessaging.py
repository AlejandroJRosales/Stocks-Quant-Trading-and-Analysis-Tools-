import time
import datetime
import pandas as pd
import yfinance as yf
from twilio.rest import Client
from ta.trend import MACD
import alpaca_trade_api as tradeapi

APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
APCA_API_KEY = 'Your API Key'
APC_SECRET_KEY = 'Your Secret Key'
TWIL_ACCOUNT_SID = 'Your Twilio sid'
TWIL_AUTH_TOKEN = 'Your Twilio token'
client = Client(TWIL_ACCOUNT_SID, TWIL_AUTH_TOKEN)


class LongShort:
    def __init__(self, stock_universe, last_decisions):
        self.alpaca = tradeapi.REST(APCA_API_KEY, APC_SECRET_KEY, APCA_API_BASE_URL, 'v2')
        self.algo = TradingAlgorithms()
        self.text_message = TextMessage()
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
        for stock in self.stock_universe:
            current_decision = self.algo.intro_algo(stock)

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
            message = f"BOUGHT {qty} SHARES OF {stock}"
        except:
            message = f"BUYING OF {qty} {stock} DID NOT GO THROUGH"

        print(message)
        self.text_message.send(message)

    def sell(self, stock):
        positions = self.alpaca.list_positions()
        qty = abs(int(float(positions[stock].qty)))

        try:
            if qty > 0:
                self.alpaca.submit_order(stock, qty, 'sell', 'market', 'day')
                self.last_decisions[stock] = "Sell"
                message = f"SOLD {qty} SHARES OF {stock}"
            else:
                message = f"SELLING OF {qty} {stock} DID NOT GO THROUGH"
        except:
            message = f"SELLING OF {qty} {stock} DID NOT GO THROUGH"

        print(message)
        self.text_message.send(message)


class TradingAlgorithms:
    def __init__(self):
        self.period = "2mo"

    def get_high_low_close(self, stock):
        high_low_close = dict()
        ticker = yf.Ticker(stock)
        high_low_close['high'] = pd.Series([close for close in ticker.history(period=self.period)["High"]])
        high_low_close['low'] = pd.Series([high for high in ticker.history(period=self.period)["Low"]])
        high_low_close['close'] = pd.Series([low for low in ticker.history(period=self.period)["Close"]])

        return high_low_close

    # Create the MACD signal and pass in the three parameters: fast period, slow period, and the signal.
    def macd_indicator(self, hist):
        indicator_macd = MACD(hist['close'], n_fast=12, n_slow=26, n_sign=9)
        macd_raw = indicator_macd.macd()[41]
        macd_signal = indicator_macd.macd_signal()[41]
        macd = macd_raw - macd_signal

        return macd

    def intro_algo(self, stock):
        macd = self.macd_indicator(self.get_high_low_close(stock))
        if macd < 0:
            return "Sell"

        elif macd > 0:
            return "Buy"


class TextMessage:
    def __init__(self):
        self.numbers = ['+1xxxxxxxx']
        self.dev_number = '+1xxxxxxxxx'

    def send(self, body, private=False):
        if not private:
            for number in self.numbers:
                client.messages.create(
                    body=body,
                    from_='+Twilio Account Phone Number',
                    to=number
                )

        else:
            client.messages.create(
                body=body,
                from_='+Twilio Account Phone Number',
                to=self.dev_number
            )


def initialize():
    try:
        # The stocks to be monitored
        stock_universe = ['ABBV', 'NVTA', 'PYPL', 'SQ', 'TREX', 'ZNGA', 'APPN', 'GMED']

        # Initialize the stock starting point
        algo = TradingAlgorithms()
        last_decisions = {stock: algo.intro_algo(stock) for stock in stock_universe}

        # Run the LongShort class
        ls = LongShort(stock_universe=stock_universe, last_decisions=last_decisions)
        ls.run()

    except:
        text_message = TextMessage()
        text_message.send("Fatal error, assistance required.", private=True)


initialize()
