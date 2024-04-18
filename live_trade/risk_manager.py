import oandapyV20
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import oandapyV20.endpoints.pricing as pricing
from oandapyV20.endpoints.accounts import AccountDetails, AccountSummary
from oandapyV20.exceptions import V20Error
from notification import send_email_notification
from ta.volatility import AverageTrueRange
import pandas as pd

access_token = "11928ef469320f1326a6b491a86178db-cab9f79fea13dba2dd5a93ab5aef7c68"
account_id = "101-003-28814564-001"

accountID = account_id
access_token = access_token
client = oandapyV20.API(access_token=access_token, environment="practice")

def fetch_candlestick_data_for_ATR(instrument_name, slow):
    # Initialize the Oanda API client
    api = API(access_token=access_token, environment="practice")

    # Define the parameters for the candlestick data request
    params1 = {
        'count': slow,
        'granularity': 'H1',
        'price': 'M',  # Midpoint candlestick prices
    }
    
    # Request the candlestick data from Oanda API
    candles_request = InstrumentsCandles(instrument=instrument_name, params=params1)
    response = api.request(candles_request)

    # Extract the closing, highest and lowest prices from the response
    close_prices = [float(candle['mid']['c']) for candle in response['candles']]
    high_prices = [float(candle['mid']['h']) for candle in response['candles']]
    low_prices = [float(candle['mid']['l']) for candle in response['candles']]
    
    return close_prices, high_prices, low_prices


def get_current_price(instrument):
    params = {
        "instruments": instrument
    }
    request = pricing.PricingInfo(accountID=account_id, params=params)
    response = client.request(request)

    if 'prices' in response and response['prices']:
        return float(response['prices'][0]['bids'][0]['price'])

    return None

def get_instrument_precision(instrument):
    instrument_precision = {
        "AUD_USD": 4,
        "CAD_USD": 4,
        "EUR_USD": 4,
        "NZD_USD": 4,
        "GBP_USD": 4,
        "SGD_USD": 4,
        "HKD_USD": 4,
        "CNY_USD": 4
        }
    return instrument_precision.get(instrument)  # Set a default precision value if instrument not found


def get_current_balance():
    request = AccountDetails(accountID=accountID)
    response = client.request(request)

    if response and 'account' in response:
        account_info = response['account']
        balance = float(account_info['balance'])
        return balance
        
    
    return None

def get_quantity(instrument, trade_direction, streak, capital):
    
    current_price = get_current_price(instrument)
    take_profit_percentage = 0.55
    stop_loss_percentage = 0.05

    # get data to calculate average true range
    close_prices, high_prices, low_prices = fetch_candlestick_data_for_ATR(instrument, 70)
    
    atr_data = pd.DataFrame()
    
    atr_data["Close_Price"] = close_prices
    atr_data["High_Price"] = high_prices
    atr_data["Low_Price"] = low_prices
    
    
    atr_data["Fast_ATR"] = AverageTrueRange(high=atr_data["High_Price"], low=atr_data["Low_Price"], close=atr_data["Close_Price"], window=3).average_true_range()
    atr_data["Slow_ATR"] = AverageTrueRange(high=atr_data["High_Price"], low=atr_data["Low_Price"], close=atr_data["Close_Price"], window=70).average_true_range()

    
    if trade_direction == "BUY":
            take_profit_price = round(current_price * (1 + take_profit_percentage), get_instrument_precision(instrument))
            stop_loss_price = round(current_price * (1 - stop_loss_percentage), get_instrument_precision(instrument))
        
    elif trade_direction == "SELL" :
        take_profit_price = round(current_price * (1 - take_profit_percentage), get_instrument_precision(instrument))
        stop_loss_price = round(current_price * (1 + stop_loss_percentage), get_instrument_precision(instrument))
    else:
        print("Invalid trade direction")
        return
   
    #if fast ATR is higher, trade with capital based on streak and multiplier of 2.8
    if trade_direction == "BUY":
        if streak == 1:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = round(capital * 2.8 * 0.4 / get_current_price(instrument))
                close = False
            else:
                position_size = round(capital * 1 * 0.4 / get_current_price(instrument))
                close = False
        elif streak == 2:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = round(capital * 2.8 * 0.5 / get_current_price(instrument))
                close = False
            else:
                position_size = round(capital * 1 * 0.5 / get_current_price(instrument))
                close = False
        elif streak == 3:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = round(capital * 2.8 / get_current_price(instrument))
                close = False
            else:
                position_size = round(capital * 1/ get_current_price(instrument))
                close = False
        elif streak == -2:
            position_size = 0.4
            close = True
        elif streak == -1:
            position_size = 0.5
            close = True
    
        
    else:
        if streak == -1:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = - round(capital * 2.8 * 0.4 / get_current_price(instrument))
                close = False
            else:
                position_size = - round(capital * 1 * 0.4 / get_current_price(instrument))
                close = False
        elif streak == -2:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = - round(capital * 2.8 * 0.5 / get_current_price(instrument))
                close = False
            else:
                position_size = - round(capital * 1 * 0.5 / get_current_price(instrument))
                close = False
        elif streak == 3:
            if atr_data["Fast_ATR"].iloc[-1] > atr_data["Slow_ATR"].iloc[-1]:
                position_size = - round(capital * 2.8 / get_current_price(instrument))
                close = False
            else:
                position_size = - round(capital * 1/ get_current_price(instrument))
                close = False
        elif streak == 2:
            position_size = 0.4
            close = True
        elif streak == 1:
            position_size = 0.5
            close = True

    return stop_loss_price, take_profit_price, position_size, close


def get_open_positions(instrument_name):
    request = positions.PositionDetails(accountID=account_id, instrument= instrument_name) 
    response = client.request(request)
    open_positions = response.get("position", [])
    return open_positions

def calculate_total_unrealised_pnl(positions_dict):
    long_pnl = 0
    short_pnl = 0
    total_pnl = 0

    long_unrealized_pnl = float(positions_dict['long']['unrealizedPL'])
    short_unrealized_pnl = float(positions_dict['short']['unrealizedPL'])

    long_pnl += long_unrealized_pnl
    short_pnl += short_unrealized_pnl
    total_pnl = long_pnl + short_pnl

    return long_pnl, short_pnl, total_pnl



def place_market_order(instrument, units, take_profit_price, stop_loss_price, capital):
    data = {
        "order": {
            "units": str(units),
            "instrument": instrument,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "takeProfitOnFill": {
                "price": str(float(take_profit_price)),
            },
            "stopLossOnFill": {
                "price": str(float(stop_loss_price)),
            }
        }
    }
    
    try:
        request = orders.OrderCreate(accountID, data=data)
        response = client.request(request)
        print("Oanda Orders placed successfully!")
        subject = "Oanda Trades Initiated"
        body = "Oanda Trades Initiated"
        capital -= get_current_price(instrument) * units
        result = True
        #send_email_notification(subject, body)
    except V20Error as e:
        print("Error placing Oanda orders:")
        print(e)
        subject = "Failed to Take Oanda Trades"
        body = "Failed to Take Oanda Trades"
        result = False
        #send_email_notification(subject, body)
    return capital, result


def close_specific_trades(client, account_id, instrument_name, capital, percentage):
    # Get a list of all open trades for the account
    trades_request = trades.OpenTrades(accountID=account_id)
    response = client.request(trades_request)

    if len(response['trades']) > 0:
        for trade in response['trades']:
            #find the trade which is relevant to the instrument
            if trade['instrument'] == instrument_name:
                trade_id = trade['id']
                trade_unit = str(int(trade['currentUnits']) * percentage)
                current_price = get_current_price(instrument_name)
            
                try:
                    # Create a market order to close the trade
                    data = {
                        "units": str(trade_unit),
                        }
                    order_request = trades.TradeClose(accountID=account_id, tradeID=trade_id, data=data)
                    response = client.request(order_request)
                    print(f"Trade {trade_id} closed successfully.")
                    capital += current_price * float(trade_unit)
                    
                except oandapyV20.exceptions.V20Error as e:
                        print(f"Failed to close trade {trade_id}. Error: {e}")
    else:
        print("No open trades to close.")
    return capital




def close_all_trades():
    # Get a list of all open trades for the account
    trades_request = trades.OpenTrades(accountID=account_id)
    response = client.request(trades_request)

    if len(response['trades']) > 0:
        for trade in response['trades']:
            trade_id = trade['id']
            try:
                # Create a market order to close the trade
                data = {
                    "units": "ALL",
                }
                order_request = trades.TradeClose(accountID=account_id, tradeID=trade_id, data=data)
                response = client.request(order_request)
                print(f"Trade {trade_id} closed successfully.")
            except oandapyV20.exceptions.V20Error as e:
                print(f"Failed to close trade {trade_id}. Error: {e}")
        return "All trades have been closed."
    else:
        print("No open trades to close.")
        return "No open trades to close."

def fetch_account_equity():
    # Endpoint to get account details
    account = AccountSummary(account_id)
    response = client.request(account)

    # The response is a dictionary that includes the account properties
    account_properties = response.get('account', {})
    equity = account_properties.get('NAV', 'Unknown')  # NAV is the net asset value, similar to equity

    return equity
