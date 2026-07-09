"""
classifier.py
─────────────
Determines whether a user query is stock-related.
No LLM required — pure keyword + ticker matching.
"""

import re

# ── Ticker universe ────────────────────────────────────────────────────────────
KNOWN_TICKERS = {
    "AAPL","MSFT","NVDA","GOOGL","GOOG","META","AMZN","TSLA","AMD","INTC",
    "ORCL","CRM","ADBE","QCOM","TXN","PLTR","SNOW","NET","SHOP","NFLX",
    "BABA","UBER","ABNB","NKE","SBUX","MCD","WMT","JPM","BAC","GS","MS",
    "BRK","V","MA","PYPL","COIN","HOOD","JNJ","PFE","MRNA","UNH","ABBV",
    "LLY","XOM","CVX","COP","SLB","SPY","QQQ","DIA","IWM","VTI","VOO",
    "SOFI","RIVN","LCID","NIO","XPEV","BYND","ROKU","SNAP","PINS","TWTR",
    "LYFT","DASH","RBLX","U","DKNG","PENN","MGM","WYNN","LVS","CHWY",
    "ETSY","EBAY","BIDU","JD","PDD","SE","GRAB","GOTO","CPNG","MELI",
}

# ── Company name → ticker map ──────────────────────────────────────────────────
COMPANY_NAMES = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA", "google": "GOOGL",
    "alphabet": "GOOGL", "meta": "META", "facebook": "META", "amazon": "AMZN",
    "tesla": "TSLA", "amd": "AMD", "intel": "INTC", "oracle": "ORCL",
    "salesforce": "CRM", "adobe": "ADBE", "qualcomm": "QCOM",
    "texas instruments": "TXN", "palantir": "PLTR", "snowflake": "SNOW",
    "cloudflare": "NET", "shopify": "SHOP", "netflix": "NFLX",
    "alibaba": "BABA", "uber": "UBER", "airbnb": "ABNB", "nike": "NKE",
    "starbucks": "SBUX", "mcdonald": "MCD", "walmart": "WMT",
    "jpmorgan": "JPM", "jp morgan": "JPM", "bank of america": "BAC",
    "goldman sachs": "GS", "morgan stanley": "MS", "berkshire": "BRK",
    "visa": "V", "mastercard": "MA", "paypal": "PYPL", "coinbase": "COIN",
    "robinhood": "HOOD", "johnson": "JNJ", "pfizer": "PFE", "moderna": "MRNA",
    "unitedhealth": "UNH", "abbvie": "ABBV", "eli lilly": "LLY", "lilly": "LLY",
    "exxon": "XOM", "chevron": "CVX", "conocophillips": "COP",
    "s&p": "SPY", "nasdaq": "QQQ", "dow jones": "DIA", "russell": "IWM",
}

# ── Financial keywords ─────────────────────────────────────────────────────────
FINANCIAL_KEYWORDS = {
    # Actions
    "buy","sell","hold","invest","trade","purchase","short","long","exit","enter",
    # Instruments
    "stock","stocks","share","shares","equity","etf","option","future","bond","fund","index",
    "crypto","bitcoin","btc","ethereum","eth",
    # Indicators
    "rsi","macd","ema","sma","vwap","atr","adx","obv","bollinger","stochastic",
    "moving average","momentum","oscillator","divergence","crossover",
    # Analysis
    "price","chart","technical","fundamental","analysis","predict","forecast",
    "signal","trend","support","resistance","breakout","reversal","pattern",
    "candlestick","volume","volatility","beta","alpha","correlation",
    # Financials
    "earnings","revenue","profit","loss","margin","pe","eps","dividend",
    "market cap","valuation","ipo","split","buyback","guidance",
    # Market
    "market","nasdaq","nyse","sp500","dow","vix","bull","bear","rally",
    "correction","crash","recession","inflation","fed","interest rate",
    "portfolio","watchlist","backtest","strategy","risk","return",
    # Money / budget
    "dollar","dollars","usd","rupee","rupees","inr",
    "price target","stop loss","take profit","entry",
    "under","below","afford","budget","invest","investment",
    "ready to buy","which stock","which stocks",
}

REJECTION_MESSAGE = (
    "I am a **Stock AI Assistant**.\n\n"
    "I only answer questions related to:\n"
    "- US stock analysis & price prediction\n"
    "- Technical indicators (RSI, MACD, EMA, Bollinger Bands, etc.)\n"
    "- Buy / Hold / Sell recommendations\n"
    "- Market overview & sector analysis\n"
    "- Portfolio & risk management\n\n"
    "Please ask me something like:\n"
    "- *\"Should I buy AAPL?\"*\n"
    "- *\"Predict Tesla tomorrow\"*\n"
    "- *\"What is the RSI for NVDA?\"*\n"
    "- *\"Compare Apple and Microsoft\"*"
)


def classify(prompt: str) -> tuple[bool, str | None]:
    """
    Returns (is_stock_related, detected_ticker_or_None).
    Fast — no network calls, no LLM.
    """
    text  = prompt.lower().strip()
    upper = prompt.upper()

    # 1. Check for known tickers (word boundary match)
    for ticker in KNOWN_TICKERS:
        if re.search(rf'\b{ticker}\b', upper):
            return True, ticker

    # 2. Check company names
    for name, ticker in COMPANY_NAMES.items():
        if name in text:
            return True, ticker

    # 3. Check financial keywords
    words = set(re.findall(r'\b\w[\w\s]*\b', text))
    for kw in FINANCIAL_KEYWORDS:
        if kw in text:
            return True, None

    # 4. Generic uppercase 1-5 char word that looks like a ticker
    matches = re.findall(r'\b([A-Z]{1,5})\b', upper)
    skip = {"I","A","THE","AND","OR","IN","ON","AT","TO","MY","ME","IS","IT",
            "DO","GO","NO","SO","UP","AI","US","UK","EU","UN","WHO","WHY",
            "HOW","CAN","NOW","GET","FOR","USD","INR","BUY","SELL","YES","NO"}
    for m in matches:
        if m not in skip and len(m) >= 2:
            return True, m

    return False, None


def extract_ticker(prompt: str) -> str | None:
    """Extract the most likely ticker from a prompt."""
    _, ticker = classify(prompt)
    return ticker
