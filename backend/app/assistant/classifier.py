"""
classifier.py
─────────────
Determines whether a user query is stock-related.
No LLM required — pure keyword + ticker matching.

Rules:
  1. Known dashboard ticker  → accept, return ticker
  2. Known company name      → accept, return ticker
  3. Financial keyword       → accept, no ticker
  4. Dynamic ticker pattern  → accept only if 2-5 uppercase letters
     that are NOT in a strict stop-word list
  5. Everything else         → reject
"""

import re

# ── Ticker universe — mirrors dashboard ALL_STOCKS exactly ────────────────────
KNOWN_TICKERS = {
    # Technology
    "AAPL","MSFT","NVDA","GOOGL","GOOG","META","AMD","INTC","ORCL","CRM",
    "ADBE","QCOM","TXN","PLTR","SNOW","NET","SHOP",
    # Consumer
    "AMZN","TSLA","NFLX","BABA","UBER","ABNB","NKE","SBUX","MCD","WMT",
    # Finance
    "JPM","BAC","GS","MS","BRK-B","V","MA","PYPL","COIN","HOOD",
    # Healthcare
    "JNJ","PFE","MRNA","UNH","ABBV","LLY",
    # Energy
    "XOM","CVX","COP","SLB",
    # ETF
    "SPY","QQQ","DIA","IWM",
}

# ── Company name → ticker — mirrors dashboard ALL_STOCKS exactly ──────────────
COMPANY_NAMES = {
    # Technology
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "google": "GOOGL", "alphabet": "GOOGL", "meta": "META", "facebook": "META",
    "amd": "AMD", "advanced micro devices": "AMD", "intel": "INTC",
    "oracle": "ORCL", "salesforce": "CRM", "adobe": "ADBE",
    "qualcomm": "QCOM", "texas instruments": "TXN", "palantir": "PLTR",
    "snowflake": "SNOW", "cloudflare": "NET", "shopify": "SHOP",
    # Consumer
    "amazon": "AMZN", "tesla": "TSLA", "netflix": "NFLX",
    "alibaba": "BABA", "uber": "UBER", "airbnb": "ABNB",
    "nike": "NKE", "starbucks": "SBUX", "mcdonald": "MCD", "mcdonalds": "MCD",
    "walmart": "WMT",
    # Finance
    "jpmorgan": "JPM", "jp morgan": "JPM", "bank of america": "BAC",
    "goldman sachs": "GS", "goldman": "GS", "morgan stanley": "MS",
    "berkshire": "BRK-B", "visa": "V", "mastercard": "MA",
    "paypal": "PYPL", "coinbase": "COIN", "robinhood": "HOOD",
    # Healthcare
    "johnson and johnson": "JNJ", "johnson": "JNJ", "pfizer": "PFE",
    "moderna": "MRNA", "unitedhealth": "UNH", "abbvie": "ABBV",
    "eli lilly": "LLY", "lilly": "LLY",
    # Energy
    "exxon": "XOM", "exxonmobil": "XOM", "chevron": "CVX",
    "conocophillips": "COP", "schlumberger": "SLB",
    # ETF / Index
    "s&p 500": "SPY", "sp500": "SPY", "s&p": "SPY",
    "nasdaq 100": "QQQ", "nasdaq": "QQQ",
    "dow jones": "DIA", "russell 2000": "IWM",
}

# ── Financial keywords — must be clearly finance-related ─────────────────────
FINANCIAL_KEYWORDS = {
    # Actions
    "buy","sell","hold","invest","trade","purchase","short","long",
    # Instruments
    "stock","stocks","share","shares","equity","etf","option","futures","bond",
    "mutual fund","index fund","crypto","bitcoin","btc","ethereum","eth",
    # Indicators
    "rsi","macd","ema","sma","vwap","atr","adx","obv","bollinger bands",
    "moving average","stochastic","momentum","divergence","crossover",
    # Analysis
    "technical analysis","fundamental analysis","predict","forecast",
    "price target","support level","resistance level","breakout","candlestick",
    "volatility","beta","sharpe ratio",
    # Financials
    "earnings","revenue","profit","loss","margin","p/e ratio","eps","dividend",
    "market cap","valuation","ipo","stock split","buyback",
    # Market
    "stock market","bull market","bear market","market rally","correction",
    "recession","inflation","federal reserve","interest rate",
    "portfolio","watchlist","backtest","trading strategy",
    # Budget / recommendation
    "which stock","which stocks","best stock","top stock",
    "recommend","suggest","afford","budget",
    "should i buy","should i sell","worth buying","price of",
}

# Strict stop-words — these uppercase words must NEVER be treated as tickers
_STOP_WORDS = {
    "I","A","AN","THE","AND","OR","IN","ON","AT","TO","MY","ME","IS","IT",
    "DO","GO","NO","SO","UP","AI","US","UK","EU","UN","WHO","WHY","HOW",
    "CAN","NOW","GET","FOR","USD","INR","YES","ARE","WAS","HAS","HAD",
    "NOT","BUT","ALL","ANY","ITS","HIM","HER","HIS","OUR","OUT","OFF",
    "NEW","OLD","BIG","TOP","LOW","HIGH","DAY","WEEK","YEAR","TIME",
    "TELL","SHOW","WHAT","WHEN","WILL","WITH","FROM","THAT","THIS","THEY",
    "GIVE","HELP","NEED","WANT","LIKE","JUST","ALSO","ONLY","VERY","MUCH",
    "GOOD","BEST","NEXT","LAST","SOME","MANY","MORE","LESS","OVER","UNDER",
    "ABOUT","AFTER","BEFORE","BETWEEN","DURING","WHILE","SINCE","UNTIL",
    "BECAUSE","THOUGH","ALTHOUGH","HOWEVER","THEREFORE","THUS",
    # Common English words that look like tickers — must never be treated as symbols
    "STOCK","STOCKS","PRICE","PRICES","SHARE","SHARES","FUND","FUNDS",
    "CHEAP","PENNY","DEMAND","PROFIT","LOSS","GAIN","GAINS","RISK",
    "PICK","PICKS","LIST","SHOW","GIVE","FIND","TELL","MAKE","TAKE",
    "LIVE","REAL","FAST","SAFE","FREE","OPEN","CLOSE","LONG","TERM",
    "CALL","PUTS","PUTS","CASH","LOAN","DEBT","EARN","SAVE","GROW",
    "PLAN","GOAL","IDEA","INFO","DATA","NEWS","TIPS","HINT","RATE",
}

REJECTION_MESSAGE = (
    "I'm a **Stock Market AI Assistant** — I only answer questions about:\n\n"
    "- 📈 Stock analysis & price predictions (AAPL, TSLA, NVDA, etc.)\n"
    "- 🔍 Technical indicators (RSI, MACD, Bollinger Bands, EMA)\n"
    "- 💡 Buy / Hold / Sell signals & trade setups\n"
    "- 🌍 Market overview, sector analysis, top movers\n"
    "- 💰 Portfolio, risk management & budget-based recommendations\n\n"
    "**Try asking:**\n"
    "- *\"Should I buy Apple?\"*\n"
    "- *\"Analyze NVDA\"*\n"
    "- *\"Compare Tesla and Ford\"*\n"
    "- *\"Best stocks under $200\"*\n"
    "- *\"What is the RSI for Microsoft?\"*"
)


def classify(prompt: str) -> tuple[bool, str | None]:
    """
    Returns (is_stock_related, detected_ticker_or_None).
    Fast — no network calls, no LLM.
    """
    text  = prompt.lower().strip()
    upper = prompt.upper()

    # 1. Known dashboard tickers (exact word boundary)
    for ticker in KNOWN_TICKERS:
        escaped = re.escape(ticker)
        if re.search(rf'\b{escaped}\b', upper):
            return True, ticker

    # 2. Known company names (substring match, longest first to avoid partial hits)
    for name in sorted(COMPANY_NAMES, key=len, reverse=True):
        if name in text:
            return True, COMPANY_NAMES[name]

    # 3. Financial keywords (exact phrase match)
    for kw in FINANCIAL_KEYWORDS:
        if kw in text:
            return True, None

    # 4. Dynamic ticker: 2-5 uppercase letters not in stop-word list
    #    This handles queries like "analyze FORD" or "what about RIVN"
    matches = re.findall(r'\b([A-Z]{2,5})\b', upper)
    for m in matches:
        if m not in _STOP_WORDS and m not in {"BUY","SELL","HOLD","ETF","IPO","GDP","VIX","ATR"}:
            return True, m

    return False, None


def extract_ticker(prompt: str) -> str | None:
    """Extract the most likely ticker from a prompt."""
    _, ticker = classify(prompt)
    return ticker
