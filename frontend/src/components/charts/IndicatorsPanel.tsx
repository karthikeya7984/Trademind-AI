"use client";

interface Indicators {
  rsi?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
  ma20?: number | null;
  ma50?: number | null;
  ma200?: number | null;
  bb_upper?: number | null;
  bb_lower?: number | null;
  bb_pct?: number | null;
  stoch_k?: number | null;
  stoch_d?: number | null;
  atr?: number | null;
  vol_ratio?: number | null;
}

function usd(v: number) {
  return `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function IndicatorsPanel({ indicators }: { indicators: Indicators }) {
  const getRSIColor = (rsi: number) => {
    if (rsi > 70) return "text-red-400";
    if (rsi < 30) return "text-neon-green";
    return "text-yellow-400";
  };

  const getRSILabel = (rsi: number) => {
    if (rsi > 70) return "Overbought";
    if (rsi < 30) return "Oversold";
    return "Neutral";
  };

  const metrics = [
    {
      label: "RSI (14)",
      value: indicators.rsi != null ? indicators.rsi.toFixed(1) : "N/A",
      color: indicators.rsi != null ? getRSIColor(indicators.rsi) : "text-muted-foreground",
      desc: indicators.rsi != null ? getRSILabel(indicators.rsi) : "",
      bar: indicators.rsi != null ? indicators.rsi : null,
      barMax: 100,
    },
    {
      label: "MACD",
      value: indicators.macd != null ? indicators.macd.toFixed(4) : "N/A",
      color: indicators.macd != null ? (indicators.macd > 0 ? "text-neon-green" : "text-red-400") : "text-muted-foreground",
      desc: indicators.macd != null
        ? (indicators.macd_hist != null
            ? (indicators.macd_hist > 0 ? "Bullish crossover" : "Bearish crossover")
            : (indicators.macd > 0 ? "Bullish" : "Bearish"))
        : "",
    },
    {
      label: "Stochastic K",
      value: indicators.stoch_k != null ? indicators.stoch_k.toFixed(1) : "N/A",
      color: indicators.stoch_k != null
        ? (indicators.stoch_k < 20 ? "text-neon-green" : indicators.stoch_k > 80 ? "text-red-400" : "text-yellow-400")
        : "text-muted-foreground",
      desc: indicators.stoch_k != null
        ? (indicators.stoch_k < 20 ? "Oversold" : indicators.stoch_k > 80 ? "Overbought" : "Neutral")
        : "",
      bar: indicators.stoch_k != null ? indicators.stoch_k : null,
      barMax: 100,
    },
    {
      label: "MA 20",
      value: indicators.ma20 != null ? usd(indicators.ma20) : "N/A",
      color: "text-neon-blue",
      desc: "20-day moving average",
    },
    {
      label: "MA 50",
      value: indicators.ma50 != null ? usd(indicators.ma50) : "N/A",
      color: "text-neon-purple",
      desc: "50-day moving average",
    },
    {
      label: "MA 200",
      value: indicators.ma200 != null ? usd(indicators.ma200) : "N/A",
      color: "text-blue-400",
      desc: "200-day moving average",
    },
    {
      label: "BB Upper",
      value: indicators.bb_upper != null ? usd(indicators.bb_upper) : "N/A",
      color: "text-yellow-400",
      desc: "Bollinger Band upper",
    },
    {
      label: "BB Lower",
      value: indicators.bb_lower != null ? usd(indicators.bb_lower) : "N/A",
      color: "text-yellow-400",
      desc: "Bollinger Band lower",
    },
    {
      label: "BB Position",
      value: indicators.bb_pct != null ? `${(indicators.bb_pct * 100).toFixed(1)}%` : "N/A",
      color: indicators.bb_pct != null
        ? (indicators.bb_pct < 0.2 ? "text-neon-green" : indicators.bb_pct > 0.8 ? "text-red-400" : "text-yellow-400")
        : "text-muted-foreground",
      desc: indicators.bb_pct != null
        ? (indicators.bb_pct < 0.2 ? "Near lower band" : indicators.bb_pct > 0.8 ? "Near upper band" : "Mid band")
        : "",
      bar: indicators.bb_pct != null ? indicators.bb_pct * 100 : null,
      barMax: 100,
    },
    {
      label: "ATR (14)",
      value: indicators.atr != null ? usd(indicators.atr) : "N/A",
      color: "text-orange-400",
      desc: "Average True Range",
    },
    {
      label: "Vol Ratio",
      value: indicators.vol_ratio != null ? `${indicators.vol_ratio.toFixed(2)}x` : "N/A",
      color: indicators.vol_ratio != null
        ? (indicators.vol_ratio > 1.5 ? "text-neon-green" : indicators.vol_ratio < 0.5 ? "text-red-400" : "text-muted-foreground")
        : "text-muted-foreground",
      desc: indicators.vol_ratio != null
        ? (indicators.vol_ratio > 1.5 ? "High volume" : indicators.vol_ratio < 0.5 ? "Low volume" : "Normal volume")
        : "",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {metrics.map((m) => (
        <div key={m.label} className="glass p-4 rounded-xl">
          <div className="text-xs text-muted-foreground mb-1">{m.label}</div>
          <div className={`text-xl font-bold ${m.color}`}>{m.value}</div>
          {m.desc && <div className="text-xs text-muted-foreground mt-1">{m.desc}</div>}
          {m.bar != null && (
            <div className="mt-2 bg-muted rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full transition-all"
                style={{
                  width: `${Math.min((m.bar / m.barMax) * 100, 100)}%`,
                  background: m.bar > 70 ? "#f87171" : m.bar < 30 ? "#00ff88" : "#facc15",
                }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
