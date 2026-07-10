"""
intent.py
─────────
Detects the user's intent from their query.
Returns one of: PRICE | PREDICTION | COMPARE | EDUCATION |
                RECOMMENDATION | RISK | MARKET | BUDGET | UNKNOWN
"""

import re
from dataclasses import dataclass


@dataclass
class Intent:
    type: str           # intent label
    symbol: str | None  # primary symbol
    symbol2: str | None # secondary symbol (for COMPARE)
    budget: float | None
    raw: str
    count: int          # how many results requested (default 5)
    price_filter: str | None  # "low", "high", or None
    sort_by: str        # "score" | "price_asc" | "price_desc"


INTENT_PATTERNS = {
    "PRICE": [
        r"\bprice\b", r"\btrading at\b", r"\bcurrent(ly)?\b", r"\bhow much\b",
        r"\bwhat is .{0,20} (price|worth|value|trading)\b",
        r"\bquote\b", r"\blast price\b",
    ],
    "PREDICTION": [
        r"\bpredict\b", r"\bforecast\b", r"\btomorrow\b", r"\bnext week\b",
        r"\bwill .{0,20} (go|rise|fall|drop|increase|decrease)\b",
        r"\bprice target\b", r"\bwhere .{0,20} (headed|going)\b",
        r"\bshould i (buy|sell|invest)\b",
    ],
    "COMPARE": [
        r"\bcompare\b", r"\bvs\b", r"\bversus\b", r"\bbetter\b",
        r"\bwhich (is|one|stock)\b", r"\bor\b.{0,30}\bstock\b",
    ],
    "EDUCATION": [
        r"\bwhat is\b", r"\bexplain\b", r"\bhow does\b", r"\bdefine\b",
        r"\bmeaning of\b", r"\bteach me\b", r"\bwhat (are|does)\b",
        r"\brsi\b.{0,20}\bwork\b", r"\bmacd\b.{0,20}\bwork\b",
    ],
    "RECOMMENDATION": [
        r"\bbest stock\b", r"\btop stock\b", r"\brecommend\b", r"\bsuggest\b",
        r"\bwhich stock(s)?\b", r"\bwhat (should|to) (i )?(buy|invest)\b",
        r"\bgood (stock|investment|buy)\b", r"\bworth buying\b",
        r"\bwhich (can|should|to) (i )?buy\b",
        r"\b(gain|make|earn).{0,20}profit\b",
        r"\bprofit(able)?\b",
        r"\bto (buy|invest|purchase).{0,20}(profit|gain|return|money)\b",
        r"\b(best|good|top).{0,20}(buy|invest|purchase)\b",
        r"\bwhere (should|can) i invest\b",
        r"\bwhat (to|can i) buy\b",
        # Catch "top N stocks", "top 3 low price stocks", "top 5 stock prices"
        r"\btop\s+\d+\s+stock",
        r"\btop\s+\d+.{0,30}\bstock",
        r"\b\d+\s+(best|top|cheap|low.?price)\s+stock",
        r"\b(low.?price|cheap|penny|affordable).{0,20}stock",
        r"\bstock.{0,20}(low.?price|cheap|penny|affordable)",
        r"\bhigh.{0,20}demand.{0,20}stock",
        r"\bstock.{0,20}high.{0,20}demand",
    ],
    "RISK": [
        r"\brisk\b", r"\bvolatil\b", r"\bdrawdown\b", r"\bvar\b",
        r"\bsafe\b", r"\bdangerous\b", r"\bstop.?loss\b", r"\bbeta\b",
        r"\bhow risky\b",
    ],
    "MARKET": [
        r"\bmarket\b", r"\btoday\b", r"\boverall\b", r"\bmovers\b",
        r"\bgainers\b", r"\blosers\b", r"\btrending\b", r"\bsector\b",
        r"\bsp500\b", r"\bs&p\b", r"\bnasdaq\b", r"\bdow\b",
    ],
    "BUDGET": [
        r"\bbudget\b", r"\bafford\b",
        r"\bi have \$?\s*\d+",
        r"\b\$?\s*\d+\s*(dollars?|usd|rupees?|rs\.?|inr)",
        r"\bunder \$?\s*\d+",
        r"\bbelow \$?\s*\d+",
        r"\bless than \$?\s*\d+",
        r"\bwithin \$?\s*\d+",
        r"\b\$\d+\b.{0,20}\b(invest|buy|spend)\b",
        r"\bhow many shares\b",
        r"\bwith \$?\s*\d+",
        r"\bready to buy",
        r"\bcan i buy with",
        r"\bstocks? (to buy|i can buy|under|below|within)",
    ],
}


def _extract_budget(text: str) -> float | None:
    text = text.lower().replace(",", "")
    # Match: $1000, 1000 dollars, 1000 usd, 1000 rupees, under 1000, below 500
    m = re.search(
        r'(?:under|below|within|have|with|budget of|\$)?\s*'
        r'(\d+(?:\.\d+)?)\s*'
        r'(k|thousand|dollars?|usd|rupees?|rs\.?|inr)?',
        text
    )
    if m:
        amount = float(m.group(1))
        suffix = (m.group(2) or "").lower().rstrip(".")
        if suffix in ("k", "thousand"):
            amount *= 1000
        elif suffix in ("lakh", "lac"):
            amount *= 100_000
        if amount >= 10:
            return amount
    return None


def detect_intent(prompt: str, context_symbol: str | None = None) -> Intent:
    """
    Detect intent from user prompt.
    context_symbol: last known symbol from memory (for pronoun resolution).
    """
    text = prompt.lower().strip()

    # Detect intent type
    # RECOMMENDATION must be checked before PRICE to avoid "top 5 stock prices"
    # matching \bprice\b and routing to a single-ticker price lookup.
    PRIORITY_ORDER = [
        "RECOMMENDATION", "BUDGET", "COMPARE", "EDUCATION",
        "PREDICTION", "RISK", "MARKET", "PRICE",
    ]
    detected = "UNKNOWN"
    for intent_type in PRIORITY_ORDER:
        patterns = INTENT_PATTERNS.get(intent_type, [])
        for pattern in patterns:
            if re.search(pattern, text):
                detected = intent_type
                break
        if detected != "UNKNOWN":
            break

    # Extract symbols
    from app.assistant.classifier import KNOWN_TICKERS, COMPANY_NAMES, _STOP_WORDS
    upper = prompt.upper()
    symbol  = None
    symbol2 = None

    found = []
    for ticker in KNOWN_TICKERS:
        escaped = re.escape(ticker)
        if re.search(rf'\b{escaped}\b', upper):
            found.append(ticker)
    # Check company names (longest first to avoid partial matches)
    for name in sorted(COMPANY_NAMES, key=len, reverse=True):
        ticker = COMPANY_NAMES[name]
        if name in text and ticker not in found:
            found.append(ticker)
    # Dynamic ticker fallback — skip if intent is already a list/recommendation query
    if not found and detected not in ("RECOMMENDATION", "BUDGET", "MARKET"):
        dyn = re.findall(r'\b([A-Z]{2,5})\b', upper)
        for m in dyn:
            if m not in _STOP_WORDS and m not in {"BUY","SELL","HOLD","ETF","IPO","GDP","VIX","ATR"}:
                found.append(m)
                break

    if found:
        symbol  = found[0]
        symbol2 = found[1] if len(found) > 1 else None
    elif context_symbol:
        # Pronoun resolution: "should I buy now?" → use last symbol
        symbol = context_symbol

    budget = _extract_budget(text)

    # Refine UNKNOWN: if budget found → BUDGET, if symbol found → PREDICTION
    if detected == "UNKNOWN":
        if budget:
            detected = "BUDGET"
        elif symbol:
            detected = "PREDICTION"

    # If any intent has a budget amount, treat as BUDGET (e.g. "best stocks under $500")
    if budget and detected in ("RECOMMENDATION", "PREDICTION", "UNKNOWN"):
        detected = "BUDGET"

    # ── Parse count modifier ("top 3", "top 10", "give me 7") ─────────────────
    count_match = re.search(r'\b(?:top|best|give me|show me)?\s*(\d+)\s*(?:stocks?|picks?|results?)?\b', text)
    count = int(count_match.group(1)) if count_match else 5
    count = max(1, min(count, 20))  # clamp 1-20

    # ── Parse price filter & sort ─────────────────────────────────────────────
    price_filter = None
    sort_by = "score"
    if re.search(r'\b(low.?price|cheap|penny|affordable|lowest price)\b', text):
        price_filter = "low"
        sort_by = "price_asc"
    elif re.search(r'\b(high.?price|expensive|highest price|most expensive)\b', text):
        price_filter = "high"
        sort_by = "price_desc"

    return Intent(
        type=detected,
        symbol=symbol,
        symbol2=symbol2,
        budget=budget,
        raw=prompt,
        count=count,
        price_filter=price_filter,
        sort_by=sort_by,
    )
