from signal_generator import generate_signal, generate_signal_our_strategy
from risk_manager import get_quantity,  place_market_order, get_open_positions, get_current_balance, calculate_total_unrealised_pnl, close_all_trades, close_specific_trades
from notification import send_email_notification
import time
import oandapyV20
import math
import threading


#access_token = "11928ef469320f1326a6b491a86178db-cab9f79fea13dba2dd5a93ab5aef7c68"
#account_id = "101-003-28814564-001"
access_token = "666a8bdc424d973bc4034abb604850f6-92e471b05dce2aabe372ab9dbcead817"
account_id = "101-003-28603626-001"

accountID = account_id
access_token = access_token
client = oandapyV20.API(access_token=access_token, environment="practice")

stop_event = threading.Event()


def find_quantities_and_trade(instrument, trade_direction, streak, capital, pre_streak):     
    global takeprofit
    global stoploss
    
    
    #close current order if we generate opposite signal (long -> short or short -> long)
    if abs(pre_streak - streak) == 2:
        capital = close_specific_trades(client, account_id, instrument, capital, 1)
        inposition[instrument] = False
    # determining the quantity of instrument to trade, as well as the stoploss and takeprofit levels
    # NOTE: utilise the streak to determine the quantity of instrument to trade
    stoploss, takeprofit, quantity, close = get_quantity(instrument,trade_direction, streak, capital)
   
    if close == False:
        print("==" * 25)
        print("Oanda quantities") 
        print("Instrument:", instrument, " | Vol :", quantity, " | StopLoss :", stoploss, " | Takeprofit :", takeprofit)         
    #Place orders
        capital, result = place_market_order(instrument, quantity, takeprofit, stoploss, capital)
    
    else: # if we generate opposite signal but still same position side, just partially close some trades
        capital = close_specific_trades(client, account_id, instrument, capital, quantity)
     # if trade successfully, set inposition as true, else change new streak to 0 
    if result == True:
        inposition[instrument] = True  
    else:
        streak = 0
    time.sleep(3)
    return capital

def run():
    #helper variables
    # instrument is essentially what you are trading; in this case, it is the currency pair EUR/USD
    # NOTE: The denominator (USD) is bought/sold when the trade is being executed 


    global inposition
    # instrument = 'AUD_USD', 'EUR_USD', 'NZD_USD', 'GBP_USD'
    lookback_count = 1300
    inposition = {"AUD_USD": False,
                "EUR_USD": False,
                "NZD_USD": False,
                "GBP_USD": False}

    opening_balance = get_current_balance()

    # set risk factor and risk reward
    risk_factor = 0.03#0.016 / 100
    stoploss_pnl =  {"AUD_USD": opening_balance/4 * risk_factor,
                "EUR_USD": opening_balance/4 * risk_factor,
                "NZD_USD": opening_balance/4 * risk_factor,
                "GBP_USD": opening_balance/4 * risk_factor}
    risk_reward = 1.5  # 3/4
    target_pnl =    {"AUD_USD": opening_balance/4 * risk_reward,
                "EUR_USD": opening_balance/4 * risk_reward,
                "NZD_USD": opening_balance/4 * risk_reward,
                "GBP_USD": opening_balance/4 * risk_reward}#stoploss_pnl * risk_reward

    # NOTE: Format of the all_forex_pairs is "CURRENCY: [streak, position,allocated capital]"
    all_forex_pairs = {
                    "AUD_USD": [0,0,opening_balance/4],
                    #"CAD_USD": [0,0,opening_balance/8],
                    "EUR_USD": [0,0,opening_balance/4],
                    "NZD_USD": [0,0,opening_balance/4],
                    "GBP_USD": [0,0,opening_balance/4]}
                    #"SGD_USD": [0,0,opening_balance/8],
                    #"HKD_USD": [0,0,opening_balance/8],
                    #"CNY_USD": [0,0,opening_balance/8]}

    last_print_time = time.time()
    time_interval = 1*60

    print("==" * 25)
    print("")
    print("==" * 25)
    print("Starting balance : {:.2f}".format(opening_balance))
    print("Take Profit initial : {:.2f}".format(target_pnl["AUD_USD"]))
    print("Stop loss initial : {:.2f}".format(stoploss_pnl["AUD_USD"]))
    print("==" * 25)

    while not stop_event.is_set():       
        #try:
        for instrument, params in all_forex_pairs.items():
            print("starting instrument{}", instrument)
            # NOTE: obtain the streak and position from the all_forex_pairs dictionary
            streak, position,capital = params
                # First, generate the direction signal for trading.
    
        
            strategy_params = {
                    'window_bol': 23,
                    'window_bol_dev': 2.9,
                    'window_rsi': 16,
                    'window_open': 1300,
                    'rsi_upper_bound': 50,
                    'bb_upper_bound': 50,
                    'rsi_lower_bound': 40,
                    'bb_lower_bound': 40
                }
            streak1 = streak
            trade_direction, streak, position = generate_signal_our_strategy(instrument, lookback_count, strategy_params, streak)
                
            if trade_direction is None:
                pass
            else:
                    # after generating the signal, check opportunity and trade if there is an opportunity
                    
                print("Found opportunity in {}".format(instrument))
                capital = find_quantities_and_trade(instrument,trade_direction, streak, capital, streak1)
                
                #reset stop loss and take profit point if when get new entries
                if inposition[instrument] == True:
                    if streak1 == 0:
                        stoploss_pnl[instrument] = capital / 0.6 * risk_factor
                        target_pnl[instrument] = capital / 0.6 * risk_reward
                
                    #send_email_notification()  
            # NOTE: UPDATE the streak and position in the all_forex_pairs dictionary
            all_forex_pairs[instrument] = [streak, position,capital]    
                
            if inposition[instrument] == True:    
                # then check the pnl and close the trade if the pnl is greater than target or less than stoploss
                positions_dict = get_open_positions(instrument)
                long_pnl, short_pnl, total_pnl = calculate_total_unrealised_pnl(positions_dict)    
                current_time = time.time()
                #check pnl
                if current_time - last_print_time >= time_interval:
                    print(f" Target:  {target_pnl[instrument]:.2f} | StopLoss: {stoploss_pnl[instrument] :.2f} | PNL:  {total_pnl:.2f} ")
                    last_print_time = current_time
                #exit check
                if (total_pnl > target_pnl[instrument]) or total_pnl < -(stoploss_pnl[instrument]): 
                    if (total_pnl > target_pnl[instrument]):  
                        msg = f"Profit Trade, Target : {target_pnl[instrument]:.2f} | Actual: {total_pnl:.2f}"                                  
                    elif total_pnl < -(stoploss_pnl[instrument]):                                         
                        msg = f"Loss Trade, Target:  {target_pnl[instrument]:.2f} | Actual: {total_pnl:.2f} " 
                    print(msg) 
                    capital = close_specific_trades(client, accountID, instrument, capital, 1)
                    streak = 0
                    position = 0
                    all_forex_pairs[instrument] = [streak, position,capital]  
                    print("Closing all Trades of the instrument")
                    print("Current balance: {:.2f}".format(get_current_balance()))

                    inposition[instrument] = False
                    subject = "Closing Trades"
                    body = msg
                    #send_email_notification(subject, body)
                    

                else:      
                    pass
                current_balance = get_current_balance()
                print("current balance is {}", current_balance)
                print ("inposition is {}", inposition)
                    
        #except:
        #        pass
        
        time.sleep(1)

if __name__ == '__main__':
    run()