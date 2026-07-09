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
    topic_lower = topic.lower()

    if "rsi" in topic_lower:
        return (
            "## 📈 RSI — Relative Strength Index\n\n"
            "RSI measures momentum on a **0–100 scale**.\n\n"
            "| RSI Range | Meaning | Action |\n|---|---|---|\n"
            "| < 30 | Oversold | 🟢 Potential BUY |\n"
            "| 30–40 | Approaching oversold | Consider buying |\n"
            "| 40–60 | Neutral | Hold / Wait |\n"
            "| 60–70 | Approaching overbought | Consider selling |\n"
            "| > 70 | Overbought | 🔴 Potential SELL |\n\n"
            "**Formula:** RSI = 100 − (100 / (1 + RS)) where RS = Avg Gain / Avg Loss over 14 days\n\n"
            "**Best used with:** MACD and volume confirmation.\n\n"
            "*Ask me: \"What is the RSI for AAPL?\" to see live data.*"
        )
    if "macd" in topic_lower:
        return (
            "## 📈 MACD — Moving Average Convergence Divergence\n\n"
            "MACD shows the relationship between two EMAs.\n\n"
            "| Component | Calculation |\n|---|---|\n"
            "| MACD Line | EMA(12) − EMA(26) |\n"
            "| Signal Line | EMA(9) of MACD |\n"
            "| Histogram | MACD − Signal |\n\n"
            "**Signals:**\n"
            "- 🟢 **Bullish crossover** — MACD crosses above Signal → BUY\n"
            "- 🔴 **Bearish crossover** — MACD crosses below Signal → SELL\n"
            "- Histogram growing → momentum increasing\n\n"
            "*Ask me: \"Analyze TSLA\" to see live MACD readings.*"
        )
    if "bollinger" in topic_lower or "bb" in topic_lower:
        return (
            "## 📈 Bollinger Bands\n\n"
            "Three lines: Middle (SMA20), Upper (+2σ), Lower (−2σ)\n\n"
            "| Position | Meaning |\n|---|---|\n"
            "| Near lower band | Oversold → potential BUY |\n"
            "| Near upper band | Overbought → potential SELL |\n"
            "| Band squeeze | Low volatility → big move incoming |\n"
            "| Band expansion | High volatility → trend continuation |\n\n"
            "*Ask me to analyze any stock to see its Bollinger Band position.*"
        )
    if "adx" in topic_lower:
        return (
            "## 📈 ADX — Average Directional Index\n\n"
            "ADX measures **trend strength** (not direction) on a 0–100 scale.\n\n"
            "| ADX Value | Trend Strength |\n|---|---|\n"
            "| < 20 | No trend (ranging) |\n"
            "| 20–25 | Weak trend |\n"
            "| 25–40 | Strong trend |\n"
            "| > 40 | Very strong trend |\n\n"
            "**+DI > −DI** → Uptrend | **−DI > +DI** → Downtrend\n\n"
            "*Best used to confirm signals from RSI and MACD.*"
        )
    if "vwap" in topic_lower:
        return (
            "## 📈 VWAP — Volume Weighted Average Price\n\n"
            "VWAP = Σ(Price × Volume) / Σ(Volume)\n\n"
            "**Key rules:**\n"
            "- Price **above VWAP** → bullish, institutional buying\n"
            "- Price **below VWAP** → bearish, institutional selling\n"
            "- Used by institutions as a benchmark\n"
            "- Most useful for **intraday trading**\n\n"
            "*Ask me to analyze any stock for a full signal.*"
        )
    if "stop loss" in topic_lower or "stop-loss" in topic_lower:
        return (
            "## 🛡️ Stop Loss — Risk Management\n\n"
            "A stop-loss automatically exits a trade to limit losses.\n\n"
            "**Common methods:**\n"
            "- **ATR-based:** Stop = Entry − (1.5 × ATR) — adapts to volatility\n"
            "- **Fixed %:** 5–8% below entry price\n"
            "- **Support level:** Just below key support\n"
            "- **Bollinger Lower Band:** Dynamic stop\n\n"
            "**Rule:** Never risk more than **2% of capital** on a single trade.\n\n"
            "*Ask me to analyze a stock and I'll calculate a specific stop-loss.*"
        )

    return (
        f"## 📚 {topic}\n\n"
        "I can explain these trading concepts in detail:\n\n"
        "- **RSI** — momentum oscillator\n"
        "- **MACD** — trend & momentum\n"
        "- **Bollinger Bands** — volatility\n"
        "- **ADX** — trend strength\n"
        "- **VWAP** — volume-weighted price\n"
        "- **Stop Loss** — risk management\n"
        "- **EMA/SMA** — moving averages\n\n"
        "*Ask me: \"What is RSI?\" or \"Explain MACD\"*"
    )


def build_recommendation_response(picks: list[dict]) -> str:
    if not picks:
        return (
            "## 📊 Stock Recommendations\n\n"
            "Unable to fetch live data right now. Try asking about a specific stock:\n"
            "- *\"Analyze AAPL\"*\n"
            "- *\"Should I buy NVDA?\"*\n"
            "- *\"Compare MSFT and GOOGL\"*"
        )

    # Separate into strong signals and others
    strong = [p for p in picks if p["signal"] in ("STRONG BUY", "BUY")]
    others = [p for p in picks if p["signal"] not in ("STRONG BUY", "BUY")]
    display = (strong or others)[:5]  # always show top 5

    is_after_hours = not strong
    header = "## 🏆 Top Stock Picks\n"
    if is_after_hours:
        header += "\n> 📌 **Note:** US markets are currently closed. Signals are based on the latest available data — use these for planning your next session.\n"

    lines = [header]
    for i, p in enumerate(display, 1):
        emoji = SIGNAL_EMOJI.get(p["signal"], "🔄")
        lines.append(
            f"**{i}. {emoji} {p['symbol']}** — {p['signal']} "
            f"(Score: {p['score']:.0f}/100, Confidence: {p['confidence']:.0f}%)\n"
            f"   Entry: ${p['entry']:,.2f} | Target: ${p['target']:,.2f} | "
            f"Stop: ${p['stop_loss']:,.2f} | Upside: {p['upside_pct']:+.1f}%\n"
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
            f"## 💰 Stocks for ${budget:,.0f} Budget\n\n"
            f"Unable to fetch live data right now. Consider these ETFs which support fractional shares:\n"
            f"- **SPY** — S&P 500 ETF\n"
            f"- **QQQ** — NASDAQ 100 ETF\n"
            f"- **VTI** — Total Market ETF\n\n"
            f"*Ask me: \"Analyze SPY\" for a full signal.*"
        )

    affordable = [p for p in picks if p.get("price", 0) <= budget]
    display    = affordable[:5] if affordable else picks[:5]
    over_budget = not affordable

    lines = [f"## 💰 Best Stocks for ${budget:,.0f} Budget\n"]
    if over_budget:
        lines.append(f"> 💡 No stocks in the scan list are priced under ${budget:,.0f}. Showing top picks — consider **fractional shares** on brokers like Robinhood or Webull.\n")

    for p in display:
        qty   = int(budget // p["price"]) if p.get("price") and p["price"] > 0 else 0
        emoji = SIGNAL_EMOJI.get(p.get("signal", "HOLD"), "🔄")
        shares_note = f"~**{qty} shares**" if qty > 0 else "fractional shares"
        lines.append(
            f"**{emoji} {p['symbol']}** — ~${p.get('price',0):,.2f}/share\n"
            f"   Signal: {p.get('signal','N/A')} | Score: {p.get('score',0):.0f}/100 | "
            f"You can buy {shares_note}\n"
        )

    lines.append(
        "\n💡 **Tip:** Diversify — don't put all your budget in one stock.\n"
        "*Not financial advice. Always do your own research.*"
    )
    return "\n".join(lines)
