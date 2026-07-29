"""
response.py
───────────
Structured response generator.
Converts PredictionResult + intent into clean markdown responses.
No LLM — every answer is dynamically generated from real data.
"""

from app.assistant.predictor import PredictionResult
from app.assistant.intent import Intent

SIGNAL_EMOJI = {
    "STRONG BUY":  "🚀",
    "BUY":         "✅",
    "HOLD":        "🔄",
    "SELL":        "⚠️",
    "STRONG SELL": "🔴",
}

SIGNAL_COLOR_LABEL = {
    "STRONG BUY":  "**STRONG BUY**",
    "BUY":         "**BUY**",
    "HOLD":        "**HOLD**",
    "SELL":        "**SELL**",
    "STRONG SELL": "**STRONG SELL**",
}


def _fmt(v: float | None, prefix="$", decimals=2) -> str:
    if v is None:
        return "N/A"
    return f"{prefix}{v:,.{decimals}f}" if prefix == "$" else f"{v:.{decimals}f}{prefix}"


def build_prediction_response(result: PredictionResult, intent: Intent) -> str:
    emoji  = SIGNAL_EMOJI.get(result.signal, "🔄")
    label  = SIGNAL_COLOR_LABEL.get(result.signal, result.signal)
    ind    = result.indicators

    price = result.indicators.get("price") or result.entry or 0
    shares_1k  = int(1_000  // price) if price > 0 else 0
    shares_5k  = int(5_000  // price) if price > 0 else 0
    shares_10k = int(10_000 // price) if price > 0 else 0

    lines = [
        f"## {emoji} {result.symbol} — {label}",
        "",
        f"**Score:** {result.score:.0f}/100 &nbsp;|&nbsp; "
        f"**Confidence:** {result.confidence:.0f}% &nbsp;|&nbsp; "
        f"**Trend:** {result.trend.capitalize()}",
        "",
        "### 📊 Trade Setup",
        f"| | Price |",
        f"|---|---|",
        f"| Entry | {_fmt(result.entry)} |",
        f"| Target | {_fmt(result.target)} |",
        f"| Stop Loss | {_fmt(result.stop_loss)} |",
        f"| Upside | {result.upside_pct:+.1f}% |",
        f"| Risk/Reward | 1:{result.risk_reward:.1f} |",
        "",
        "### 🛒 How Many Shares Can You Buy?",
        f"| Budget | Shares |",
        f"|---|---|",
        f"| $1,000 | {'~' + str(shares_1k) + ' shares' if shares_1k > 0 else 'fractional only'} |",
        f"| $5,000 | {'~' + str(shares_5k) + ' shares' if shares_5k > 0 else 'fractional only'} |",
        f"| $10,000 | {'~' + str(shares_10k) + ' shares' if shares_10k > 0 else 'fractional only'} |",
        "",
        "### 📈 Key Indicators",
        f"- **RSI(14):** {_fmt(ind.get('rsi'), '', 1)} "
        f"{'🟢 Oversold' if (ind.get('rsi') or 50) < 30 else '🔴 Overbought' if (ind.get('rsi') or 50) > 70 else '⚪ Neutral'}",
        f"- **MACD:** {_fmt(ind.get('macd'), '', 4)} vs Signal {_fmt(ind.get('macd_signal'), '', 4)} "
        f"{'🟢 Bullish' if (ind.get('macd') or 0) > (ind.get('macd_signal') or 0) else '🔴 Bearish'}",
        f"- **EMA20/50/200:** {_fmt(ind.get('ema20'))} / {_fmt(ind.get('ema50'))} / {_fmt(ind.get('ema200'))}",
        f"- **Bollinger:** {_fmt(ind.get('bb_lower'))} — {_fmt(ind.get('bb_upper'))} "
        f"(Position: {(ind.get('bb_pct') or 0.5)*100:.0f}%)",
        f"- **ADX:** {_fmt(ind.get('adx'), '', 1)} "
        f"({'Strong trend' if (ind.get('adx') or 0) > 25 else 'Weak/ranging'})",
        f"- **Volume Ratio:** {_fmt(ind.get('vol_ratio'), '', 2)}x average",
        f"- **ATR(14):** {_fmt(ind.get('atr'))}",
        "",
        "### 💡 Why This Signal",
    ]

    for i, reason in enumerate(result.reasons, 1):
        lines.append(f"{i}. {reason}")

    if result.warnings:
        lines.append("")
        lines.append("### ⚠️ Risk Warnings")
        for w in result.warnings:
            lines.append(f"- {w}")

    lines += [
        "",
        "---",
        "*Not financial advice. Always do your own research before investing.*",
    ]

    return "\n".join(lines)


def build_price_response(symbol: str, quote: dict) -> str:
    price     = quote.get("price", 0)
    change    = quote.get("change", 0)
    change_pct = quote.get("change_pct", 0)
    volume    = quote.get("volume", 0)
    high      = quote.get("high", 0)
    low       = quote.get("low", 0)
    direction = "▲" if change >= 0 else "▼"
    color     = "🟢" if change >= 0 else "🔴"

    return (
        f"## {color} {symbol} — Current Price\n\n"
        f"**${price:,.2f}** {direction} {abs(change):.2f} ({change_pct:+.2f}% today)\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| Today's High | ${high:,.2f} |\n"
        f"| Today's Low  | ${low:,.2f} |\n"
        f"| Volume       | {volume:,} |\n\n"
        f"*Ask me to predict {symbol} or analyze it for a full BUY/SELL signal.*"
    )


def build_compare_response(sym1: str, r1: PredictionResult,
                            sym2: str, r2: PredictionResult) -> str:
    winner = sym1 if r1.score > r2.score else sym2

    return (
        f"## ⚖️ {sym1} vs {sym2} — Comparison\n\n"
        f"| Metric | {sym1} | {sym2} |\n|---|---|---|\n"
        f"| Signal | {SIGNAL_EMOJI.get(r1.signal,'')} {r1.signal} | {SIGNAL_EMOJI.get(r2.signal,'')} {r2.signal} |\n"
        f"| Score | {r1.score:.0f}/100 | {r2.score:.0f}/100 |\n"
        f"| Confidence | {r1.confidence:.0f}% | {r2.confidence:.0f}% |\n"
        f"| Trend | {r1.trend.capitalize()} | {r2.trend.capitalize()} |\n"
        f"| Entry | ${r1.entry:,.2f} | ${r2.entry:,.2f} |\n"
        f"| Target | ${r1.target:,.2f} | ${r2.target:,.2f} |\n"
        f"| Stop Loss | ${r1.stop_loss:,.2f} | ${r2.stop_loss:,.2f} |\n"
        f"| Upside | {r1.upside_pct:+.1f}% | {r2.upside_pct:+.1f}% |\n"
        f"| Risk/Reward | 1:{r1.risk_reward:.1f} | 1:{r2.risk_reward:.1f} |\n"
        f"| RSI | {r1.indicators.get('rsi', 0):.1f} | {r2.indicators.get('rsi', 0):.1f} |\n\n"
        f"**🏆 Better Pick: {winner}** (Score: {max(r1.score, r2.score):.0f}/100)\n\n"
        f"*Not financial advice. Always do your own research.*"
    )


def build_risk_response(symbol: str, risk: dict, result: PredictionResult) -> str:
    level = risk.get("risk_level", "MEDIUM")
    emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "🟡")

    return (
        f"## {emoji} {symbol} — Risk Analysis\n\n"
        f"**Risk Level: {level}** | Risk Score: {risk.get('risk_score', 0)}/100\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| Annual Volatility | {risk.get('volatility', 0):.1f}% |\n"
        f"| VaR (95%) | {risk.get('var_95', 0):.2f}% per day |\n"
        f"| VaR (99%) | {risk.get('var_99', 0):.2f}% per day |\n"
        f"| Max Drawdown | {risk.get('max_drawdown', 0):.1f}% |\n"
        f"| Sharpe Ratio | {risk.get('sharpe_ratio', 0):.2f} |\n"
        f"| Beta | {risk.get('beta', 1):.2f} |\n"
        f"| Recommended Stop Loss | ${risk.get('stop_loss_recommendation', 0):,.2f} |\n\n"
        f"**Current Signal:** {SIGNAL_EMOJI.get(result.signal,'')} {result.signal} "
        f"(Score: {result.score:.0f}/100)\n\n"
        f"*Not financial advice. Always do your own research.*"
    )


def build_education_response(topic: str) -> str:
    t = topic.lower()

    if "rsi" in t:
        return (
            "## 📈 RSI — Relative Strength Index\n\n"
            "RSI measures **how fast and how much** a stock's price has moved recently, on a 0–100 scale. "
            "Think of it as a speedometer for price momentum.\n\n"
            "| RSI Level | What It Means | What Traders Do |\n|---|---|---|\n"
            "| < 30 | Oversold — sellers exhausted | 🟢 Look for BUY entry |\n"
            "| 30–40 | Recovering from oversold | Consider accumulating |\n"
            "| 40–60 | Neutral zone | Hold / wait for signal |\n"
            "| 60–70 | Approaching overbought | Tighten stop-loss |\n"
            "| > 70 | Overbought — buyers exhausted | 🔴 Consider taking profit |\n\n"
            "**Formula:** `RSI = 100 − (100 / (1 + RS))` where RS = Average Gain ÷ Average Loss over 14 days\n\n"
            "**How to use it in a trade:**\n"
            "1. RSI drops below 30 → wait for it to cross back above 30 → BUY signal\n"
            "2. RSI rises above 70 → wait for it to cross back below 70 → SELL signal\n"
            "3. **Divergence:** Price makes new high but RSI doesn't → reversal warning\n\n"
            "**Best combined with:** MACD crossover + volume spike for confirmation.\n\n"
            "*Try: \"Analyze AAPL\" to see the live RSI reading.*"
        )

    if "macd" in t:
        return (
            "## 📈 MACD — Moving Average Convergence Divergence\n\n"
            "MACD shows **trend direction and momentum** by comparing two moving averages. "
            "It tells you when a trend is starting, strengthening, or reversing.\n\n"
            "| Component | Formula | What It Shows |\n|---|---|---|\n"
            "| MACD Line | EMA(12) − EMA(26) | Short vs long-term momentum |\n"
            "| Signal Line | EMA(9) of MACD | Smoothed trigger line |\n"
            "| Histogram | MACD − Signal | Momentum strength (growing = accelerating) |\n\n"
            "**Key signals:**\n"
            "- 🟢 **Bullish crossover** — MACD crosses *above* Signal line → BUY\n"
            "- 🔴 **Bearish crossover** — MACD crosses *below* Signal line → SELL\n"
            "- **Histogram growing** → momentum accelerating in that direction\n"
            "- **Zero line cross** — MACD crosses above 0 = confirmed uptrend\n\n"
            "**Real example:** If AAPL's MACD crosses above its signal line while the histogram turns positive, "
            "that's a bullish crossover — traders often enter long here.\n\n"
            "**Best combined with:** RSI (confirm not overbought) + volume (confirm buying pressure).\n\n"
            "*Try: \"Analyze TSLA\" to see live MACD readings.*"
        )

    if "bollinger" in t or "bb" in t:
        return (
            "## 📈 Bollinger Bands\n\n"
            "Bollinger Bands show **price volatility** using three lines around a moving average. "
            "When the bands are wide, the market is volatile. When narrow, it's calm — and a big move is often coming.\n\n"
            "| Band | Formula | Meaning |\n|---|---|---|\n"
            "| Upper Band | SMA(20) + 2×StdDev | Resistance / overbought zone |\n"
            "| Middle Band | SMA(20) | Trend baseline |\n"
            "| Lower Band | SMA(20) − 2×StdDev | Support / oversold zone |\n\n"
            "**How to trade with Bollinger Bands:**\n"
            "- Price touches **lower band** → potential bounce → BUY signal\n"
            "- Price touches **upper band** → potential pullback → SELL signal\n"
            "- **Band squeeze** (bands very close) → low volatility → expect a breakout soon\n"
            "- **Band expansion** → high volatility → trend is strong, ride it\n\n"
            "**Best combined with:** RSI (confirm oversold/overbought) + volume.\n\n"
            "*Try: \"Analyze NVDA\" to see its current Bollinger Band position.*"
        )

    if "ema" in t or "sma" in t or "moving average" in t:
        return (
            "## 📈 Moving Averages — EMA & SMA\n\n"
            "Moving averages **smooth out price noise** to show the underlying trend direction.\n\n"
            "| Type | How It Works | Best For |\n|---|---|---|\n"
            "| SMA (Simple) | Average of last N closing prices | Long-term trend |\n"
            "| EMA (Exponential) | Weighted — recent prices count more | Short-term signals |\n\n"
            "**Key levels traders watch:**\n"
            "- **EMA 20** — short-term trend (swing traders)\n"
            "- **EMA 50** — medium-term trend (position traders)\n"
            "- **EMA 200** — long-term trend (investors)\n\n"
            "**Golden Cross vs Death Cross:**\n"
            "- 🟢 **Golden Cross** — EMA50 crosses *above* EMA200 → strong BUY signal\n"
            "- 🔴 **Death Cross** — EMA50 crosses *below* EMA200 → strong SELL signal\n\n"
            "**Rule of thumb:** Price above EMA20 > EMA50 > EMA200 = strong uptrend. "
            "Price below all three = strong downtrend.\n\n"
            "*Try: \"Analyze MSFT\" to see live EMA readings.*"
        )

    if "adx" in t:
        return (
            "## 📈 ADX — Average Directional Index\n\n"
            "ADX measures **how strong a trend is** — not its direction. "
            "It answers: *Is the market trending or just ranging?*\n\n"
            "| ADX Value | Trend Strength | What To Do |\n|---|---|---|\n"
            "| < 20 | No trend (ranging) | Avoid trend strategies |\n"
            "| 20–25 | Weak trend forming | Wait for confirmation |\n"
            "| 25–40 | Strong trend | Trade with the trend |\n"
            "| > 40 | Very strong trend | Ride it, trail stop-loss |\n\n"
            "**Direction lines:**\n"
            "- **+DI > −DI** → Uptrend (bulls in control)\n"
            "- **−DI > +DI** → Downtrend (bears in control)\n\n"
            "**Key insight:** ADX above 25 with +DI > −DI = confirmed uptrend. "
            "This is when RSI and MACD signals are most reliable.\n\n"
            "*Try: \"Analyze GOOGL\" to see live ADX readings.*"
        )

    if "vwap" in t:
        return (
            "## 📈 VWAP — Volume Weighted Average Price\n\n"
            "VWAP is the **average price weighted by volume** throughout the trading day. "
            "Institutions use it as a benchmark — they try to buy below VWAP and sell above it.\n\n"
            "**Formula:** `VWAP = Σ(Price × Volume) / Σ(Volume)`\n\n"
            "**How to use it:**\n"
            "- Price **above VWAP** → bullish, institutions are net buyers → look for BUY entries\n"
            "- Price **below VWAP** → bearish, institutions are net sellers → avoid buying\n"
            "- Price **bounces off VWAP** → strong support/resistance level\n\n"
            "**Best for:** Intraday trading and confirming entry timing.\n\n"
            "*Try: \"Analyze SPY\" for a full signal with volume analysis.*"
        )

    if "stop loss" in t or "stop-loss" in t:
        return (
            "## 🛡️ Stop Loss — The Most Important Risk Tool\n\n"
            "A stop-loss is a **pre-set exit price** that automatically closes your trade to limit losses. "
            "It's the difference between a small loss and a catastrophic one.\n\n"
            "**Common stop-loss methods:**\n"
            "| Method | Formula | Best For |\n|---|---|---|\n"
            "| ATR-based | Entry − (1.5 × ATR) | Volatile stocks |\n"
            "| Fixed % | Entry × 0.93 (7% below) | Beginners |\n"
            "| Support level | Just below key support | Swing trading |\n"
            "| Bollinger Lower | Dynamic lower band | Mean-reversion trades |\n\n"
            "**The 2% Rule:** Never risk more than **2% of your total capital** on a single trade.\n"
            "Example: $10,000 portfolio → max loss per trade = $200\n\n"
            "**Risk/Reward:** Always aim for at least **1:2** — risk $1 to make $2.\n\n"
            "*Try: \"Analyze AAPL\" and I'll calculate a specific stop-loss for you.*"
        )

    if "support" in t or "resistance" in t:
        return (
            "## 📈 Support & Resistance\n\n"
            "**Support** is a price level where buyers step in and stop the price from falling further. "
            "**Resistance** is where sellers step in and stop the price from rising further.\n\n"
            "**How to identify them:**\n"
            "- Look for price levels where the stock has **bounced multiple times**\n"
            "- Round numbers ($100, $150, $200) often act as psychological levels\n"
            "- Previous highs become resistance; previous lows become support\n\n"
            "**Key rule — Role Reversal:**\n"
            "- When price **breaks above resistance** → that level becomes new support\n"
            "- When price **breaks below support** → that level becomes new resistance\n\n"
            "**Trading strategy:** Buy near support with stop below it. Sell near resistance.\n\n"
            "*Try: \"Analyze TSLA\" to see key price levels.*"
        )

    if "candlestick" in t or "candle" in t:
        return (
            "## 🕯️ Candlestick Patterns\n\n"
            "Each candlestick shows **4 prices** for a time period: Open, High, Low, Close.\n\n"
            "**Anatomy:** Body (Open→Close) + Wicks (High/Low extremes)\n"
            "- 🟢 Green candle = Close > Open (buyers won)\n"
            "- 🔴 Red candle = Close < Open (sellers won)\n\n"
            "**Key reversal patterns:**\n"
            "| Pattern | What It Looks Like | Signal |\n|---|---|---|\n"
            "| Doji | Tiny body, long wicks | Indecision → reversal possible |\n"
            "| Hammer | Small body, long lower wick | 🟢 Bullish reversal at bottom |\n"
            "| Shooting Star | Small body, long upper wick | 🔴 Bearish reversal at top |\n"
            "| Engulfing | Large candle swallows previous | Strong reversal signal |\n\n"
            "*Try: \"Analyze AAPL\" for a full technical analysis.*"
        )

    if "risk" in t or "reward" in t or "risk/reward" in t:
        return (
            "## ⚖️ Risk/Reward Ratio\n\n"
            "Risk/Reward (R:R) tells you **how much you stand to gain vs lose** on a trade. "
            "It's the single most important concept in trading.\n\n"
            "**Formula:** `R:R = (Target − Entry) / (Entry − Stop Loss)`\n\n"
            "**Example with AAPL:**\n"
            "- Entry: $190 | Target: $200 | Stop Loss: $185\n"
            "- Reward: $10 | Risk: $5 | **R:R = 1:2** ✅\n\n"
            "| R:R Ratio | Quality | Should You Take It? |\n|---|---|---|\n"
            "| 1:1 | Poor | ❌ No — not worth it |\n"
            "| 1:1.5 | Acceptable | ⚠️ Only with high confidence |\n"
            "| 1:2 | Good | ✅ Standard minimum |\n"
            "| 1:3+ | Excellent | 🚀 Best setups |\n\n"
            "**Key insight:** Even if you're right only 40% of the time, a 1:3 R:R makes you profitable.\n\n"
            "*Try: \"Analyze NVDA\" to see the current risk/reward setup.*"
        )

    return (
        f"## 📚 Trading Education\n\n"
        "I can explain these concepts in depth — just ask:\n\n"
        "| Topic | Ask Me |"
        "\n|---|---|"
        "\n| RSI | \"What is RSI?\" |"
        "\n| MACD | \"Explain MACD\" |"
        "\n| Bollinger Bands | \"What are Bollinger Bands?\" |"
        "\n| Moving Averages | \"What is EMA vs SMA?\" |"
        "\n| ADX | \"What is ADX?\" |"
        "\n| Support & Resistance | \"Explain support and resistance\" |"
        "\n| Stop Loss | \"How do I set a stop loss?\" |"
        "\n| Risk/Reward | \"What is risk/reward ratio?\" |"
        "\n| Candlesticks | \"Explain candlestick patterns\" |\n\n"
        "Or ask about a specific stock: *\"Analyze AAPL\"* or *\"Should I buy NVDA?\"*"
    )


def build_recommendation_response(picks: list[dict], intent=None) -> str:
    if not picks:
        return (
            "## 📊 Stock Recommendations\n\n"
            "Unable to fetch live data right now. Try asking about a specific stock:\n"
            "- *\"Analyze AAPL\"*\n"
            "- *\"Should I buy NVDA?\"*\n"
            "- *\"Compare MSFT and GOOGL\"*"
        )

    count        = getattr(intent, "count", 5)
    price_filter = getattr(intent, "price_filter", None)
    sort_by      = getattr(intent, "sort_by", "score")

    # Build header label
    if price_filter == "low":
        filter_label = "💲 Lowest-Priced"
    elif price_filter == "high":
        filter_label = "💎 Highest-Priced"
    else:
        filter_label = "🏆 Top"

    strong = [p for p in picks if p["signal"] in ("STRONG BUY", "BUY")]
    others = [p for p in picks if p["signal"] not in ("STRONG BUY", "BUY")]
    # Respect the already-sorted order from the handler; just cap at count
    display = picks[:count]

    is_after_hours = not strong
    header = f"## {filter_label} Stock Picks\n"
    if is_after_hours:
        header += "\n> 📌 **Note:** US markets are currently closed. Signals are based on the latest available data — use these for planning your next session.\n"

    # Sort label for user clarity
    if sort_by == "price_asc":
        header += "\n> 🔢 Sorted by: **Lowest Price First**\n"
    elif sort_by == "price_desc":
        header += "\n> 🔢 Sorted by: **Highest Price First**\n"
    else:
        header += "\n> 🔢 Sorted by: **Signal Score**\n"

    lines = [header]
    for i, p in enumerate(display, 1):
        emoji = SIGNAL_EMOJI.get(p["signal"], "🔄")
        price = p.get("price") or p.get("entry", 0)
        shares_1k = int(1_000 // price) if price > 0 else 0
        shares_str = f"~{shares_1k} shares per $1k" if shares_1k > 0 else "fractional shares"
        lines.append(
            f"**{i}. {emoji} {p['symbol']}** — {p['signal']} "
            f"(Score: {p['score']:.0f}/100, Confidence: {p['confidence']:.0f}%)\n"
            f"   Price: ~${price:,.2f} | Entry: ${p['entry']:,.2f} | Target: ${p['target']:,.2f} | "
            f"Stop: ${p['stop_loss']:,.2f} | Upside: {p['upside_pct']:+.1f}% | 🛒 {shares_str}\n"
        )

    lines.append("\n*Not financial advice. Always do your own research.*")
    return "\n".join(lines)


def build_market_response(movers: dict) -> str:
    gainers = movers.get("gainers", [])[:4]
    losers  = movers.get("losers",  [])[:4]

    g_lines = "\n".join(
        f"- **{g['symbol']}** +{g.get('change_pct',0):.2f}% @ ${g.get('price',0):,.2f}"
        for g in gainers if g.get("price")
    ) or "- Data loading..."

    l_lines = "\n".join(
        f"- **{l['symbol']}** {l.get('change_pct',0):.2f}% @ ${l.get('price',0):,.2f}"
        for l in losers if l.get("price")
    ) or "- Data loading..."

    return (
        f"## 📊 Today's Market Overview\n\n"
        f"### 🚀 Top Gainers\n{g_lines}\n\n"
        f"### 📉 Top Losers\n{l_lines}\n\n"
        f"*Ask me about any stock: \"Analyze NVDA\" or \"Should I buy AAPL?\"*"
    )


def build_budget_response(budget: float, picks: list[dict]) -> str:
    if not picks:
        return (
            f"## 💰 Investment Suggestions for ${budget:,.0f} Budget\n\n"
            f"Unable to fetch live data right now. Consider these ETFs which support fractional shares:\n"
            f"- **SPY** — S&P 500 ETF\n"
            f"- **QQQ** — NASDAQ 100 ETF\n\n"
            f"*Ask me: \"Analyze SPY\" for a full signal.*"
        )

    affordable = [p for p in picks if p.get("price", 0) and 0 < p["price"] <= budget]
    display    = affordable[:6] if affordable else picks[:6]
    over_budget = not affordable

    lines = [f"## 💰 Investment Suggestions for ${budget:,.0f} Budget"]
    lines.append("Here are the top stocks you can afford right now:\n")

    if over_budget:
        lines.append(
            f"> 💡 No stocks are priced under ${budget:,.0f} as whole shares. "
            f"Showing top picks — consider **fractional shares** on brokers like Robinhood or Webull.\n"
        )

    for p in display:
        price  = p.get("price", 0)
        signal = p.get("signal", "HOLD")
        conf   = p.get("confidence", 0)
        name   = p.get("name", "")
        sector = p.get("sector", "")
        emoji  = SIGNAL_EMOJI.get(signal, "🔄")
        qty    = int(budget // price) if price > 0 else 0
        shares_note = f"~{qty} shares" if qty > 0 else "fractional shares"

        name_sector = f" — {name} ({sector})" if name else ""
        conf_str    = f" ({int(conf)}% confidence)" if conf else ""

        lines.append(
            f"{emoji} **{p['symbol']}**{name_sector}\n"
            f"Price: ~${price:,.2f} | Signal: {signal}{conf_str} | You can buy **{shares_note}**\n"
        )

    # Sector split tip
    sectors = list(dict.fromkeys(p.get("sector", "") for p in display if p.get("sector")))
    if len(sectors) >= 2:
        tip = f"Consider splitting: e.g., 40% in {sectors[0]}, 30% in ETFs, 30% in other sectors."
    else:
        tip = "Consider splitting across Tech, ETFs, and other sectors for diversification."

    lines += [
        f"💡 **Tip:** Diversify across sectors. Don't put all your budget into one stock. {tip}\n",
        "⚠️ **Disclaimer:** Prices are approximate. Always verify on your broker before buying.",
    ]
    return "\n".join(lines)
