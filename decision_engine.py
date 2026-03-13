import json
import os
from datetime import datetime
from data_engine import check_entry_conditions, WEALTHSIMPLE_COINS
from sentiment_engine import check_sentiment, print_sentiment_report
import json

PORTFOLIO_FILE = "C:\\TradingBot\\portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {"balance": 1000.00, "open_trade": None, "trade_history": []}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2)

def calculate_position(portfolio):
    return round(portfolio['balance'] * 0.05, 2)

def make_decision(ticker):
    portfolio = load_portfolio()
    print(f"\n=======================================")
    print(f"DECISION ENGINE - {ticker} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================")
    print(f"Portfolio Balance: ${portfolio['balance']:.2f}")
    if portfolio['open_trade']:
        print(f"Already in an open trade: {portfolio['open_trade']['ticker']}")
        return {"action": "HOLD"}
    sentiment = check_sentiment(ticker)
    print_sentiment_report(sentiment)
    if not sentiment['trade_approved']:
        log_decision(ticker, "VETOED", sentiment['veto_reasons'], portfolio)
        return {"action": "SKIP"}
    print(f"Running technical checks for {ticker}...")
    conditions = check_entry_conditions(ticker)
    if conditions is None:
        return {"action": "SKIP"}
    print(f"  Uptrend:      {'YES' if conditions['uptrend'] else 'NO'}")
    print(f"  Price Drop:   {'YES' if conditions['price_drop_in_range'] else 'NO'} ({conditions['price_drop_pct']}%)")
    print(f"  Volume:       {'YES' if conditions['volume_surge'] else 'NO'} ({conditions['volume_ratio']}x)")
    print(f"  RSI:          { 'YES' if conditions['rsi_in_range'] else 'NO'} ({conditions['rsi']})")
    print(f"  Higher Low:   {'YES' if conditions['higher_low'] else 'NO'}")
    if not conditions['all_conditions_met']:
        failed = [k for k, v in conditions.items() if k in ['uptrend','price_drop_in_range','volume_surge','rsi_in_range','higher_low'] and not v]
        log_decision(ticker, "NO_SIGNAL", failed, portfolio)
        return {"action": "SKIP"}
    entry_price = conditions['current_price']
    position_size = calculate_position(portfolio)
    trade = {"ticker": ticker, "entry_price": entry_price, "position_size": position_size, "stop_loss": round(entry_price * 0.99, 4), "take_profit_1": round(entry_price * 1.025, 4), "take_profit_2": round(entry_price * 1.04, 4), "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "status": "OPEN"}
    print(f"\nTRADE SIGNAL GENERATED")
    print(f"   Ticker:        {ticker}")
    print(f"   Entry:         ${entry_price}")
    print(f"   Position Size: ${position_size}")
    print(f"   Stop Loss:     ${trade['stop_loss']}")
    print(f"   Take Profit 1: ${trade['take_profit_1']}")
    print(f"   Take Profit 2: ${trade['take_profit_2']}")
    log_decision(ticker, "BUY", [], portfolio, trade)
    return {"action": "BUY", "trade": trade}

def log_decision(ticker, action, reasons, portfolio, trade=None):
    log_file = "C:\\TradingBot\\trade_log.json"
    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    logs.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ticker": ticker, "action": action, "reasons": reasons, "balance": portfolio['balance'], "trade": trade})
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def scan_and_decide():
    print(f"\nStarting full market scan...")
    portfolio = load_portfolio()
    if portfolio['open_trade']:
        print("Open trade exists - skipping scan")
        return
    for ticker in WEALTHSIMPLE_COINS:
        conditions = check_entry_conditions(ticker)
        if conditions and conditions['all_conditions_met']:
            result = make_decision(ticker)
            if result['action'] == 'BUY':
                return
        else:
            print(f"  {ticker} - conditions not met")
    print("No opportunities found.")

if __name__ == "__main__":
    print("Decision Engine Test")
    print("1. Test single coin")
    print("2. Run full scan")
    choice = input("\nChoose (1 or 2): ").strip()
    if choice == "1":
        ticker = input("Enter ticker: ").upper()
        make_decision(ticker)
    elif choice == "2":
        scan_and_decide()
