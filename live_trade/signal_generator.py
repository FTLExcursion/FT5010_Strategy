import numpy as np
from oandapyV20 import API
#API processes requests that can be created fro the endpoints
from oandapyV20.endpoints.instruments import InstrumentsCandles
from ta.utils import dropna
from ta.volatility import BollingerBands
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
import pandas as pd

access_token = "11928ef469320f1326a6b491a86178db-cab9f79fea13dba2dd5a93ab5aef7c68"
account_id = "101-003-28814564-001"

accountID = account_id
access_token = access_token


def fetch_candlestick_data(instrument_name, lookback_count):
    # Initialize the Oanda API client
    api = API(access_token=access_token, environment="practice")

    # Define the parameters for the candlestick data request
    params = {
        'count': lookback_count,
        'granularity': 'H1',
        'price': 'M',  # Midpoint candlestick prices
    }

    # Request the candlestick data from Oanda API
    candles_request = InstrumentsCandles(instrument=instrument_name, params=params)
    response = api.request(candles_request)

    # Extract the close prices from the response
    close_prices = [float(candle['mid']['c']) for candle in response['candles']]

    return close_prices

def generate_signal(instrument_name, lookback_count, stma_period, ltma_period):
    # Fetch candlestick data
    close_prices = fetch_candlestick_data(instrument_name, lookback_count)

    # Calculate short-term moving average (STMA)
    stma = np.mean(close_prices[-stma_period:])

    # Calculate long-term moving average (LTMA)
    ltma = np.mean(close_prices[-ltma_period:])

    # Check for crossover
    if stma > ltma:
        signal = "BUY"
    else:
        signal = "SELL"

    return signal

def generate_signal_our_strategy(instrument_name, lookback_count, strategy_params, streak):
    """
    instrument_name: str, stock
    lookback_count: int, number of lookback period for our strategy
    strategy_params: dict, parameters for our strategy
    """
    print ("generating signals - getting parameters")
    window_bol = strategy_params['window_bol']
    window_bol_dev = strategy_params['window_bol_dev']
    window_rsi = strategy_params['window_rsi']
    window_open = strategy_params['window_open']
    rsi_upper_bound = strategy_params['rsi_upper_bound']
    bb_upper_bound = strategy_params['bb_upper_bound']
    rsi_lower_bound = strategy_params['rsi_lower_bound']
    bb_lower_bound = strategy_params['bb_lower_bound']

    print ("generating signals - getting data")
    # Fetch candlestick data
    close_prices = fetch_candlestick_data(instrument_name, lookback_count)
    # store close prices into a dataframe
    df = pd.DataFrame(close_prices, columns=["Close"])
    # generate signals
    int_bollinger = BollingerBands(close=df["Close"], window=window_bol, window_dev=window_bol_dev, fillna=True).bollinger_pband()
    int_rsi = RSIIndicator(close=df["Close"], window=window_rsi, fillna=True).rsi()
    df['bollinger'] = int_bollinger
    df['rsi'] = int_rsi
    
    print ("generating signals - comparing")
    
    if df["rsi"].iloc[-1] > np.nanpercentile(df["rsi"][-window_open:-1], rsi_upper_bound) and df["bollinger"].iloc[-1] > np.nanpercentile(df["bollinger"][-window_open:-1], bb_upper_bound):
       signal = "SELL"
       
       # based on previous streak, change the streak if we generate buy or sell signals
       if streak in [-2,-1,0,2,3]:
          streak -= 1
          position = 1 if streak > 0 else -1
       elif streak in [1]:
          streak = -1   
          position = -1
       else:
           position = -1

    elif df["rsi"].iloc[-1] < np.nanpercentile(df["rsi"][-window_open:-1], rsi_lower_bound) and df["bollinger"].iloc[-1] < np.nanpercentile(df["bollinger"][-window_open:-1], bb_lower_bound):
       signal = "BUY"       
       if streak in [-3,-2,0,1,2]:
          streak += 1
          position = 1 if streak > 0 else -1
       elif streak in [-1]:
          streak = 1 
          position = 1
       else:
           position = 1
    else:
       signal = None
       streak = 0
       position = 0

    return signal, streak, position
