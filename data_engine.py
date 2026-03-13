import yfinance as yf
import pandas as pd
import pandas_ta as ta

# All ~50 coins available on Wealthsimple
WEALTHSIMPLE_COINS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "DOT-USD", "MATIC-USD", "LTC-USD", "LINK-USD",
    "UNI-USD", "AAVE-USD", "ATOM-USD", "XLM-USD", "ALGO-USD",
    "AVAX-USD", "FTM-USD", "SAND-USD", "MANA-USD", "CRV-USD",
    "COMP-USD", "MKR-USD", "SNX-USD", "YFI-USD", "SUSHI-USD",
    "BAT-USD", "ZRX-USD", "ENJ-USD", "CHZ-USD", "STORJ-USD",
    "GRT-USD", "1INCH-USD", "ANKR-USD", "BAND-USD", "REN-USD",
    "NMR-USD", "OXT-USD", "CTSI-USD", "SKL-USD", "FARM-USD",
    "BCH-USD", "ETC-USD", "DASH-USD", "ZEC-USD", "XTZ-USD",
    "EOS-USD", "TRX-USD", "VET-USD", "THETA-USD", "FIL-USD"
]

def get_coin_data(ticker):
    """Fetch 5-minute candle data and calculate indicators for a single coin."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="5m")

        if df is None or len(df) < 52:
            return None

        # Calculate indicators
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=5)
        df['AvgVolume'] = df['Volume'].rolling(window=10).mean()

        return df

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def check_entry_conditions(ticker):
    """
    Check all technical entry conditions for a coin.
    Returns a dict with pass/fail for each condition and overall result.
    """
    df = get_coin_data(ticker)

    if df is None:
        return None

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Get price 10 minutes ago (2 candles back on 5-min chart)
    price_10min_ago = df.iloc[-3]['Close'] if len(df) >= 3 else None

    current_price = latest['Close']
    price_drop_pct = ((price_10min_ago - current_price) / price_10min_ago * 100) if price_10min_ago else 0

    conditions = {
        "ticker": ticker,
        "current_price": round(current_price, 4),
        "uptrend": (
            current_price > latest['EMA20'] and
            current_price > latest['EMA50']
        ),
        "price_drop_in_range": 2.5 <= price_drop_pct <= 4.0,
        "price_drop_pct": round(price_drop_pct, 2),
        "volume_surge": (
            latest['Volume'] >= 2 * latest['AvgVolume']
            if latest['AvgVolume'] > 0 else False
        ),
        "volume_ratio": round(latest['Volume'] / latest['AvgVolume'], 2) if latest['AvgVolume'] > 0 else 0,
        "rsi_in_range": 28 <= latest['RSI'] <= 45 if pd.notna(latest['RSI']) else False,
        "rsi": round(latest['RSI'], 2) if pd.notna(latest['RSI']) else None,
        "higher_low": latest['Low'] > prev['Low'],
        "ema20": round(latest['EMA20'], 4) if pd.notna(latest['EMA20']) else None,
        "ema50": round(latest['EMA50'], 4) if pd.notna(latest['EMA50']) else None,
    }
import requests
from datetime import datetime

# ── 1. FEAR & GREED INDEX ──────────────────────────────────────────────────────

def get_fear_and_greed():
    """
    Fetches the current Crypto Fear & Greed Index from alternative.me
    Score 0-25   = Extreme Fear  → VETO
    Score 26-49  = Fear          → OK
    Score 50-74  = Greed         → OK
    Score 75-100 = Extreme Greed → OK
    """
    try:
        response = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = response.json()
        score = int(data['data'][0]['value'])
        label = data['data'][0]['value_classification']

        veto = score <= 25

        return {
            "source": "Fear & Greed Index",
            "score": score,
            "label": label,
            "veto": veto,
            "reason": f"Extreme Fear detected (score: {score}) — market is panicking" if veto else None
        }

    except Exception as e:
        print(f"Fear & Greed API error: {e}")
        return {
            "source": "Fear & Greed Index",
            "score": None,
            "label": "Unknown",
            "veto": False,
            "reason": None
        }


# ── 2. COINGECKO MARKET CAP DIRECTION ─────────────────────────────────────────

def get_market_cap_trend():
    """
    Fetches global crypto market cap from CoinGecko.
    Checks if market cap 24h change is sharply negative (worse than -3%)
    If so → VETO
    """
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=10
        )
        data = response.json()['data']

        market_cap_change = data['market_cap_change_percentage_24h_usd']
        btc_dominance = round(data['market_cap_percentage']['btc'], 2)

        veto = market_cap_change < -3.0

        return {
            "source": "CoinGecko Market Cap",
            "market_cap_change_24h": round(market_cap_change, 2),
            "btc_dominance": btc_dominance,
            "veto": veto,
            "reason": f"Market cap dropped {round(market_cap_change, 2)}% in 24h — broad market declining" if veto else None
        }

    except Exception as e:
        print(f"CoinGecko API error: {e}")
        return {
            "source": "CoinGecko Market Cap",
            "market_cap_change_24h": None,
            "btc_dominance": None,
            "veto": False,
            "reason": None
        }


# ── 3. CRYPTOPANIC NEWS SENTIMENT ─────────────────────────────────────────────

def get_news_sentiment(ticker):
    """
    Fetches recent news for a specific coin from CryptoPanic public feed.
    Strips -USD suffix to get clean coin symbol (e.g. BTC-USD → BTC)
    If recent news is mostly negative → VETO
    """
    try:
        coin = ticker.replace("-USD", "").replace("-CAD", "")

        response = requests.get(
            f"https://cryptopanic.com/api/free/v1/posts/?auth_token=public&currencies={coin}&filter=important",
            timeout=10
        )
        data = response.json()

        posts = data.get('results', [])

        if not posts:
            return {
                "source": "CryptoPanic News",
                "coin": coin,
                "negative_count": 0,
                "total_count": 0,
                "veto": False,
                "reason": None
            }

        negative = sum(1 for p in posts if p.get('votes', {}).get('negative', 0) > p.get('votes', {}).get('positive', 0))
        total = len(posts)
        negative_ratio = negative / total if total > 0 else 0

        veto = negative_ratio >= 0.6

        return {
            "source": "CryptoPanic News",
            "coin": coin,
            "negative_count": negative,
            "total_count": total,
            "negative_ratio": round(negative_ratio, 2),
            "veto": veto,
            "reason": f"{int(negative_ratio*100)}% of recent {coin} news is negative" if veto else None
        }

    except Exception as e:
        print(f"CryptoPanic API error: {e}")
        return {
            "source": "CryptoPanic News",
            "coin": ticker,
            "veto": False,
            "reason": None
        }


# ── MASTER SENTIMENT CHECK ─────────────────────────────────────────────────────

def check_sentiment(ticker):
    """
    Runs all 3 sentiment checks.
    If ANY single source vetoes → trade is blocked.
    Returns full sentiment report.
    """
    print(f"\nRunning sentiment checks for {ticker}...")

    fg = get_fear_and_greed()
    mc = get_market_cap_trend()
    news = get_news_sentiment(ticker)

    sources = [fg, mc, news]
    vetoed = any(s['veto'] for s in sources)
    veto_reasons = [s['reason'] for s in sources if s['veto']]

    report = {
        "ticker": ticker,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_approved": not vetoed,
        "veto_reasons": veto_reasons,
        "fear_and_greed": fg,
        "market_cap": mc,
        "news": news
    }

    return report


def print_sentiment_report(report):
    """Prints a clean readable sentiment report."""
    print(f"\n{'='*50}")
    print(f"SENTIMENT REPORT — {report['ticker']} — {report['timestamp']}")
    print(f"{'='*50}")

    fg = report['fear_and_greed']
    mc = report['market_cap']
    news = report['news']

    print(f"\n1. Fear & Greed Index")
    print(f"   Score:  {fg['score']} ({fg['label']})")
    print(f"   Veto:   {'❌ YES — ' + fg['reason'] if fg['veto'] else '✅ No'}")

    print(f"\n2. CoinGecko Market Cap")
    print(f"   24h Change:     {mc['market_cap_change_24h']}%")
    print(f"   BTC Dominance:  {mc['btc_dominance']}%")
    print(f"   Veto:           {'❌ YES — ' + mc['reason'] if mc['veto'] else '✅ No'}")

    print(f"\n3. CryptoPanic News ({news.get('coin', '')})")
    print(f"   Negative News:  {news.get('negative_count', 0)}/{news.get('total_count', 0)}")
    print(f"   Veto:           {'❌ YES — ' + news['reason'] if news['veto'] else '✅ No'}")

    print(f"\n{'='*50}")
    if report['trade_approved']:
        print(f"✅ SENTIMENT APPROVED — safe to evaluate technical entry")
    else:
        print(f"🚫 TRADE VETOED")
        for reason in report['veto_reasons']:
            print(f"   → {reason}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    ticker = input("Enter a coin ticker to test (e.g. BTC-USD): ").upper()
    report = check_sentiment(ticker)
    print_sentiment_report(report)