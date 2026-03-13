import time
import json
import os
from datetime import datetime, timedelta
from data_engine import check_entry_conditions, WEALTHSIMPLE_COINS
from sentiment_engine import check_sentiment
from decision_engine import make_decision, load_portfolio, save_portfolio, log_decision
from execution_layer import create_driver, login, execute_buy, execute_sell

SCAN_INTERVAL = 300  # 5 minutes in seconds
PORTFOLIO_FILE = "C:\\TradingBot\\portfolio.json"

def check_exit_conditions(trade, current_price):
    entry = trade['entry_price']
    entry_time = datetime.strptime(trade['entry_time'], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.now() - entry_time).total_seconds() / 60
    gain_pct = ((current_price - entry) / entry) * 100
    print(f"\n  Current Price:  ${current_price}")
    print(f"  Entry Price:    ${entry}")
    print(f"  Gain/Loss:      {gain_pct:.2f}%")
    print(f"  Time in trade:  {elapsed:.1f} minutes")
    print(f"  TP1 target:     ${trade['take_profit_1']} (2.5%)")
    print(f"  TP2 target:     ${trade['take_profit_2']} (4%)")
    print(f"  Stop Loss:      ${trade['stop_loss']}")
    if current_price <= trade['stop_loss']:
        print("  STOP LOSS HIT")
        return "stop_loss"
    if current_price >= trade['take_profit_2']:
        print("  TAKE PROFIT 2 HIT")
        return "take_profit_2"
    if current_price >= trade['take_profit_1'] and not trade.get('tp1_hit'):
        print("  TAKE PROFIT 1 HIT - selling half")
        return "take_profit_1"
    if elapsed >= 30:
        print("  TIME STOP - 30 minutes elapsed")
        return "time_stop"
    return None

def update_portfolio_after_exit(portfolio, trade, exit_type, current_price):
    entry = trade['entry_price']
    size = trade['position_size']
    if exit_type == "take_profit_1":
        pnl = (size / 2) * ((current_price - entry) / entry)
        portfolio['balance'] += pnl
        trade['tp1_hit'] = True
        trade['position_size'] = round(size / 2, 2)
        portfolio['open_trade'] = trade
        print(f"  Partial exit - PnL: ${pnl:.2f} | New balance: ${portfolio['balance']:.2f}")
    else:
        if exit_type == "take_profit_2":
            pnl = size * ((current_price - entry) / entry)
        elif exit_type == "stop_loss":
            pnl = -size * 0.01
        else:
            pnl = size * ((current_price - entry) / entry)
        portfolio['balance'] = round(portfolio['balance'] + pnl, 2)
        trade['exit_price'] = current_price
        trade['exit_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade['exit_type'] = exit_type
        trade['pnl'] = round(pnl, 2)
        trade['status'] = "CLOSED"
        portfolio['trade_history'].append(trade)
        portfolio['open_trade'] = None
        print(f"  Trade closed - PnL: ${pnl:.2f} | New balance: ${portfolio['balance']:.2f}")
    return portfolio

def monitor_open_trade(driver, portfolio):
    trade = portfolio['open_trade']
    if not trade:
        return portfolio
    ticker = trade['ticker']
    print(f"\nMONITORING OPEN TRADE: {ticker}")
    conditions = check_entry_conditions(ticker)
    if conditions is None:
        print("Could not fetch price data - skipping")
        return portfolio
    current_price = conditions['current_price']
    exit_type = check_exit_conditions(trade, current_price)
    if exit_type:
        sell_type = "half" if exit_type == "take_profit_1" else "full"
        success = execute_sell(driver, trade, sell_type)
        if success:
            portfolio = update_portfolio_after_exit(portfolio, trade, exit_type, current_price)
            save_portfolio(portfolio)
            log_decision(ticker, f"EXIT_{exit_type.upper()}", [], portfolio, trade)
        else:
            print("Sell failed - will retry next scan")
    return portfolio

def run_bot():
    print("\n" + "="*55)
    print("  CRYPTO TRADING BOT - STARTING UP")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*55)
    portfolio = load_portfolio()
    print(f"\n  Starting Balance: ${portfolio['balance']:.2f}")
    print(f"  Scan Interval:    Every 5 minutes")
    print(f"  Coins Watched:    {len(WEALTHSIMPLE_COINS)}")
    print("\nLaunching Chrome...")
    driver = create_driver()
    login(driver)
    print("\n Bot is now running autonomously.")
    print(" Press Ctrl+C at any time to stop.\n")
    scan_count = 0
    while True:
        try:
            scan_count += 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\nSCAN #{scan_count} - {now}")
            print(f"Balance: ${portfolio['balance']:.2f}")
            portfolio = load_portfolio()
            if portfolio['open_trade']:
                portfolio = monitor_open_trade(driver, portfolio)
            else:
                print(f"\nScanning {len(WEALTHSIMPLE_COINS)} coins...")
                for ticker in WEALTHSIMPLE_COINS:
                    conditions = check_entry_conditions(ticker)
                    if conditions and conditions['all_conditions_met']:
                        result = make_decision(ticker)
                        if result['action'] == 'BUY':
                            trade = result['trade']
                            if execute_buy(driver, trade):
                                portfolio = load_portfolio()
                                portfolio['open_trade'] = trade
                                save_portfolio(portfolio)
                                print(f"Trade opened: {ticker} @ ${trade['entry_price']}")
                            break
                    else:
                        print(f"  {ticker} - no signal")
            print(f"\nNext scan in 5 minutes...")
            time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            print("\nBot stopped.")
            print(f"Final balance: ${portfolio['balance']:.2f}")
            break
        except Exception as e:
            print(f"Error: {e} - resuming in 60s")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
