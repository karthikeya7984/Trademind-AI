"use client";
import { useState, useRef, useEffect } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";
import { format, parseISO } from "date-fns";
import { TrendingUp, TrendingDown } from "lucide-react";

interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface Props {
  data: Bar[];
  symbol?: string;
  predictedPrices?: number[];
}

const PERIODS = [
  { label: "1D", days: 1 },
  { label: "1W", days: 7 },
  { label: "1M", days: 30 },
  { label: "1Y", days: 365 },
  { label: "All", days: 0 },
];

function fmt(v: string, period: string) {
  try {
    // Handle both ISO strings and strings with timezone offset
    const clean = v.split("T")[0]; // take date part only for daily data
    const d = new Date(v);
    if (isNaN(d.getTime())) return v;
    if (period === "1D") return format(d, "HH:mm");
    if (period === "1W") return format(d, "EEE dd");
    if (period === "1M") return format(d, "MMM dd");
    return format(d, "MMM yy");
  } catch { return v; }
}

function usd(v: number) {
  return `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ─── Graph 1: Price History Area Chart ──────────────────────────────────────
export function PriceHistoryChart({ data, predictedPrices = [], symbol }: Props) {
  const [period, setPeriod] = useState("1Y");

  const days = PERIODS.find((p) => p.label === period)?.days ?? 365;
  const sliced = days === 0 ? data : data.slice(-days);

  const lastClose = sliced.at(-1)?.close ?? 0;
  const firstClose = sliced[0]?.close ?? lastClose;
  const isUp = lastClose >= firstClose;
  const changePct = firstClose ? ((lastClose - firstClose) / firstClose) * 100 : 0;
  const strokeColor = isUp ? "#00ff88" : "#f87171";

  const chartData = [
    ...sliced.map((d) => ({ date: d.date, price: d.close })),
    ...predictedPrices.map((p, i) => ({ date: `+${i + 1}d`, predicted: p })),
  ];

  const prices = sliced.map((d) => d.close).filter(Boolean);
  const minP = prices.length ? Math.min(...prices) * 0.98 : 0;
  const maxP = prices.length ? Math.max(...prices) * 1.02 : 100;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-[#0f172a] border border-white/10 rounded-lg p-3 text-xs">
        <div className="text-muted-foreground mb-1">{fmt(label, period)}</div>
        {payload.map((p: any) => (
          <div key={p.name} style={{ color: p.color }} className="font-semibold">
            {p.name === "price" ? "Price" : "Forecast"}: {usd(p.value)}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base flex items-center gap-2">
            📈 {symbol} — Price History
          </h3>
          <div className={`text-sm mt-0.5 flex items-center gap-1 ${isUp ? "text-neon-green" : "text-red-400"}`}>
            {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {isUp ? "+" : ""}{changePct.toFixed(2)}% over {period}
          </div>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button key={p.label} onClick={() => setPeriod(p.label)}
              className={`px-3 py-1.5 text-xs rounded-lg font-semibold transition-all ${
                period === p.label
                  ? "bg-neon-green/20 text-neon-green border border-neon-green/40"
                  : "text-muted-foreground hover:text-foreground border border-transparent hover:border-border"
              }`}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="g1up" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="g1dn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="g1fc" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748b" }}
            tickFormatter={(v) => fmt(v, period)} interval="preserveStartEnd"
            axisLine={false} tickLine={false} />
          <YAxis domain={[minP, maxP]} tick={{ fontSize: 10, fill: "#64748b" }}
            tickFormatter={(v) => `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
            width={76} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          {lastClose > 0 && <ReferenceLine y={lastClose} stroke="rgba(255,255,255,0.12)" strokeDasharray="4 4" />}
          <Area type="monotone" dataKey="price" stroke={strokeColor} strokeWidth={2}
            fill={isUp ? "url(#g1up)" : "url(#g1dn)"} dot={false} connectNulls />
          {predictedPrices.length > 0 && (
            <Area type="monotone" dataKey="predicted" stroke="#00d4ff" strokeWidth={2}
              strokeDasharray="6 3" fill="url(#g1fc)" dot={false} connectNulls />
          )}
        </AreaChart>
      </ResponsiveContainer>

      {/* OHLC summary */}
      <div className="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-border/30">
        {[
          { label: "Open",  value: sliced.at(-1)?.open ?? 0 },
          { label: "High",  value: Math.max(...sliced.map((d) => d.high ?? 0)) },
          { label: "Low",   value: Math.min(...sliced.filter((d) => d.low > 0).map((d) => d.low).filter(Boolean)) || 0 },
          { label: "Close", value: lastClose },
        ].map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-xs text-muted-foreground mb-1">{s.label}</div>
            <div className="text-sm font-semibold">{usd(s.value)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Graph 2: Candlestick Chart (SVG) ───────────────────────────────────────
export function CandlestickChart({ data, symbol }: Props) {
  const last7 = data.slice(-7);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; d: Bar } | null>(null);

  const allPrices = last7.flatMap((d) => [d.high, d.low]).filter((v) => v > 0);
  if (allPrices.length === 0) return null;

  const minP = Math.min(...allPrices);
  const maxP = Math.max(...allPrices);
  const priceRange = maxP - minP || 1;

  const W = 600; const H = 280;
  const PAD = { top: 20, bottom: 30, left: 80, right: 20 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const priceToY = (p: number) => PAD.top + ((maxP - p) / priceRange) * chartH;
  const slotW = chartW / last7.length;
  const candleW = Math.max(slotW * 0.55, 10);

  // Y-axis ticks
  const ticks = 5;
  const yTicks = Array.from({ length: ticks }, (_, i) => minP + (priceRange * i) / (ticks - 1));

  const parseDate = (v: string) => {
    try { const d = new Date(v); return isNaN(d.getTime()) ? null : d; } catch { return null; }
  };

  const upDays = last7.filter((d) => d.close >= d.open).length;
  const downDays = last7.length - upDays;

  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-base flex items-center gap-2">
            🕯️ {symbol} — 7-Day Candlestick
          </h3>
          <div className="flex items-center gap-3 mt-1 text-xs">
            <span className="flex items-center gap-1.5 text-neon-green">
              <span className="w-3 h-3 rounded-sm bg-neon-green inline-block" />
              {upDays} Bullish
            </span>
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="w-3 h-3 rounded-sm bg-red-400 inline-block" />
              {downDays} Bearish
            </span>
          </div>
        </div>
        <span className="text-xs text-muted-foreground border border-border/40 px-2 py-1 rounded-lg">
          Last 7 Trading Days
        </span>
      </div>

      <div ref={containerRef} className="relative w-full overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 380 }}
          onMouseLeave={() => setTooltip(null)}>

          {/* Grid lines */}
          {yTicks.map((t, i) => (
            <g key={i}>
              <line x1={PAD.left} y1={priceToY(t)} x2={W - PAD.right} y2={priceToY(t)}
                stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
              <text x={PAD.left - 6} y={priceToY(t) + 4} textAnchor="end"
                fontSize={9} fill="#64748b">
                ${t.toLocaleString("en-US", { maximumFractionDigits: 0 })}
              </text>
            </g>
          ))}

          {/* Candles */}
          {last7.map((d2, i) => {
            const isGreen = d2.close >= d2.open;
            const color = isGreen ? "#00ff88" : "#f87171";
            const cx = PAD.left + i * slotW + slotW / 2;
            const bodyTop = priceToY(Math.max(d2.open, d2.close));
            const bodyBot = priceToY(Math.min(d2.open, d2.close));
            const bodyH = Math.max(bodyBot - bodyTop, 2);
            const wickTop = priceToY(d2.high);
            const wickBot = priceToY(d2.low);

            return (
              <g key={i} style={{ cursor: "pointer" }}
                onMouseEnter={() => setTooltip({ x: cx, y: bodyTop, d: d2 })}>
                <line x1={cx} y1={wickTop} x2={cx} y2={bodyTop} stroke={color} strokeWidth={1.5} />
                <line x1={cx} y1={bodyBot} x2={cx} y2={wickBot} stroke={color} strokeWidth={1.5} />
                <rect x={cx - candleW / 2} y={bodyTop} width={candleW} height={bodyH}
                  fill={color} fillOpacity={isGreen ? 0.85 : 0.9} rx={2} />
                {/* X label */}
                <text x={cx} y={H - 8} textAnchor="middle" fontSize={9} fill="#64748b">
                  {(() => { try { const d = parseDate(d2.date); return d ? format(d, "EEE") : ""; } catch { return ""; } })()}
                </text>
                <text x={cx} y={H - 18} textAnchor="middle" fontSize={8} fill="#475569">
                  {(() => { try { const d = parseDate(d2.date); return d ? format(d, "dd") : ""; } catch { return ""; } })()}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {tooltip && (() => {
          const d = tooltip.d;
          const isGreen = d.close >= d.open;
          const pct = d.open ? ((d.close - d.open) / d.open) * 100 : 0;
          const pd = parseDate(d.date);
          return (
            <div className="absolute top-4 right-4 bg-[#0f172a] border border-white/10 rounded-lg p-3 text-xs space-y-1 pointer-events-none z-10">
              <div className="font-semibold text-foreground">
                {pd ? format(pd, "EEEE, MMM dd") : d.date}
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-muted-foreground">
                <span>Open: <span className="text-foreground font-medium">{usd(d.open)}</span></span>
                <span>Close: <span className={`font-medium ${isGreen ? "text-neon-green" : "text-red-400"}`}>{usd(d.close)}</span></span>
                <span>High: <span className="text-neon-green font-medium">{usd(d.high)}</span></span>
                <span>Low: <span className="text-red-400 font-medium">{usd(d.low)}</span></span>
              </div>
              <div className={`font-bold text-sm ${isGreen ? "text-neon-green" : "text-red-400"}`}>
                {isGreen ? "▲" : "▼"} {Math.abs(pct).toFixed(2)}%
              </div>
            </div>
          );
        })()}
      </div>

      {/* Day summary strip */}
      <div className="grid grid-cols-7 gap-1 mt-4 pt-3 border-t border-border/30">
        {last7.map((d, i) => {
          const isGreen = d.close >= d.open;
          const pct = d.open ? ((d.close - d.open) / d.open) * 100 : 0;
          const pd = parseDate(d.date);
          return (
            <div key={i} className="text-center">
              <div className="text-xs text-muted-foreground mb-1">
                {pd ? format(pd, "EEE") : ""}
              </div>
              <div className={`w-7 h-7 rounded mx-auto mb-1 flex items-center justify-center text-xs font-bold
                ${isGreen ? "bg-neon-green/20 border border-neon-green/50 text-neon-green" : "bg-red-400/20 border border-red-400/50 text-red-400"}`}>
                {isGreen ? "↑" : "↓"}
              </div>
              <div className={`text-xs font-semibold ${isGreen ? "text-neon-green" : "text-red-400"}`}>
                {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Default export ───────────────────────────────────────────────────────────
export default function PriceChart({ data, predictedPrices, symbol }: Props) {
  return <PriceHistoryChart data={data} predictedPrices={predictedPrices} symbol={symbol} />;
}
