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
    detected = "UNKNOWN"
    for intent_type, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                detected = intent_type
                break
        if detected != "UNKNOWN":
            break

    # Extract symbols
    from app.assistant.classifier import KNOWN_TICKERS, COMPANY_NAMES
    upper = prompt.upper()
    symbol  = None
    symbol2 = None

    found = []
    for ticker in KNOWN_TICKERS:
        if re.search(rf'\b{ticker}\b', upper):
            found.append(ticker)
    for name, ticker in COMPANY_NAMES.items():
        if name in text and ticker not in found:
            found.append(ticker)

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

    return Intent(
        type=detected,
        symbol=symbol,
        symbol2=symbol2,
        budget=budget,
        raw=prompt,
    )
