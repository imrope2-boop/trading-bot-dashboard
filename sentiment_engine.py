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