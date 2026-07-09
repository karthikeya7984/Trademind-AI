"use client";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, TrendingUp, TrendingDown, Brain, Building2, Target,
  BarChart3, ArrowUpRight, ArrowDownRight, Loader2, ExternalLink,
} from "lucide-react";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";

function fmt(n: number | null | undefined, prefix = "$") {
  if (n == null) return "—";
  if (n >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`;
  return `${prefix}${n.toLocaleString()}`;
}

interface Props {
  symbol: string | null;
  onClose: () => void;
}

export default function StockDetailModal({ symbol, onClose }: Props) {
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["stock-detail", symbol],
    queryFn: () => api.get(`/market/stock/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 120_000,
  });

  const { data: history, isLoading: histLoading } = useQuery({
    queryKey: ["history-mini", symbol],
    queryFn: () => api.get(`/market/history/${symbol}?period=1mo&interval=1d`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 300_000,
  });

  const { data: prediction, isLoading: predLoading } = useQuery({
    queryKey: ["prediction", symbol],
    queryFn: () => api.get(`/predictions/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 300_000,
  });

  const isUp = (detail?.change_pct ?? 0) >= 0;
  const chartData = (history ?? []).map((d: any) => ({ date: d.date, price: d.close }));
  const ov = detail?.overview ?? {};

  const signalCls = (s: string) =>
    s === "BUY" ? "text-neon-green bg-neon-green/10 border-neon-green/30" :
    s === "SELL" ? "text-red-400 bg-red-400/10 border-red-400/30" :
    "text-yellow-400 bg-yellow-400/10 border-yellow-400/30";

  return (
    <AnimatePresence>
      {symbol && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 280 }}
            className="fixed right-0 top-0 h-full w-full max-w-md bg-[#0b1120] border-l border-white/10 z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-neon-green/15 border border-neon-green/30 flex items-center justify-center">
                  <span className="text-neon-green font-black text-xs">{symbol?.slice(0, 2)}</span>
                </div>
                <div>
                  <h2 className="font-bold text-base leading-tight">{symbol}</h2>
                  {ov.name && <p className="text-xs text-muted-foreground truncate max-w-[200px]">{ov.name}</p>}
                </div>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/8 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {detailLoading ? (
                <div className="flex items-center justify-center h-40">
                  <Loader2 className="w-6 h-6 animate-spin text-neon-green" />
                </div>
              ) : (
                <>
                  {/* Price Block */}
                  <div className="rounded-2xl bg-white/4 border border-white/8 p-4">
                    <div className="text-3xl font-black mb-1">{formatCurrency(detail?.price)}</div>
                    <div className={`flex items-center gap-1.5 text-sm font-medium ${isUp ? "text-neon-green" : "text-red-400"}`}>
                      {isUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                      {formatCurrency(detail?.change)} ({formatPercent(detail?.change_pct ?? 0)}) today
                    </div>

                    {/* Mini Chart */}
                    {!histLoading && chartData.length > 0 && (
                      <div className="mt-3 -mx-1">
                        <ResponsiveContainer width="100%" height={80}>
                          <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                            <defs>
                              <linearGradient id="mg" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={isUp ? "#00ff88" : "#f87171"} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={isUp ? "#00ff88" : "#f87171"} stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <XAxis dataKey="date" hide />
                            <YAxis domain={["auto", "auto"]} hide />
                            <Tooltip
                              content={({ active, payload }) =>
                                active && payload?.length ? (
                                  <div className="text-xs bg-[#0f172a] border border-white/10 rounded px-2 py-1">
                                    {formatCurrency(payload[0].value as number)}
                                  </div>
                                ) : null
                              }
                            />
                            <Area type="monotone" dataKey="price"
                              stroke={isUp ? "#00ff88" : "#f87171"} strokeWidth={1.5}
                              fill="url(#mg)" dot={false} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {/* OHLC */}
                    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-white/8 text-xs">
                      {[
                        { l: "Open", v: detail?.open },
                        { l: "High", v: detail?.high, cls: "text-neon-green" },
                        { l: "Low", v: detail?.low, cls: "text-red-400" },
                        { l: "Prev", v: detail?.prev_close },
                      ].map(({ l, v, cls }) => (
                        <div key={l}>
                          <div className="text-muted-foreground mb-0.5">{l}</div>
                          <div className={`font-semibold ${cls ?? ""}`}>{formatCurrency(v)}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* AI Prediction */}
                  <div className="rounded-2xl bg-white/4 border border-white/8 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Brain className="w-4 h-4 text-neon-green" />
                      <span className="font-semibold text-sm">AI Signal</span>
                    </div>
                    {predLoading ? (
                      <div className="flex justify-center py-4">
                        <Loader2 className="w-5 h-5 animate-spin text-neon-green" />
                      </div>
                    ) : prediction && !prediction.error ? (
                      <div className="space-y-3">
                        <div className={`text-center py-3 rounded-xl border font-black text-2xl tracking-widest ${signalCls(prediction.signal)}`}>
                          {prediction.signal}
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-white/4 rounded-xl p-3 text-center">
                            <div className="text-muted-foreground mb-1">Target (7d)</div>
                            <div className="font-bold text-neon-green">{formatCurrency(prediction.predicted_price)}</div>
                          </div>
                          <div className="bg-white/4 rounded-xl p-3 text-center">
                            <div className="text-muted-foreground mb-1">Confidence</div>
                            <div className="font-bold text-neon-blue">{Math.round(prediction.confidence_score * 100)}%</div>
                          </div>
                        </div>
                        {prediction.advice?.reason && (
                          <p className="text-xs text-muted-foreground leading-relaxed bg-white/3 rounded-xl p-3">
                            {prediction.advice.reason}
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground text-center py-2">No prediction available</p>
                    )}
                  </div>

                  {/* Fundamentals */}
                  {ov.name && (
                    <div className="rounded-2xl bg-white/4 border border-white/8 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Building2 className="w-4 h-4 text-neon-blue" />
                        <span className="font-semibold text-sm">Fundamentals</span>
                        {ov.sector && (
                          <span className="ml-auto text-xs bg-white/8 px-2 py-0.5 rounded-full text-muted-foreground">{ov.sector}</span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {[
                          { l: "Market Cap", v: fmt(ov.market_cap) },
                          { l: "P/E Ratio", v: ov.pe_ratio ?? "—" },
                          { l: "EPS", v: ov.eps != null ? `$${ov.eps}` : "—" },
                          { l: "Div. Yield", v: ov.dividend_yield != null ? `${(ov.dividend_yield * 100).toFixed(2)}%` : "—" },
                          { l: "52W High", v: ov.week_52_high != null ? formatCurrency(ov.week_52_high) : "—", cls: "text-neon-green" },
                          { l: "52W Low", v: ov.week_52_low != null ? formatCurrency(ov.week_52_low) : "—", cls: "text-red-400" },
                          { l: "Beta", v: ov.beta ?? "—" },
                          { l: "Analyst Target", v: ov.analyst_target != null ? formatCurrency(ov.analyst_target) : "—", cls: "text-neon-green" },
                        ].map(({ l, v, cls }) => (
                          <div key={l} className="bg-white/3 rounded-lg p-2.5">
                            <div className="text-muted-foreground mb-0.5">{l}</div>
                            <div className={`font-semibold ${cls ?? ""}`}>{String(v)}</div>
                          </div>
                        ))}
                      </div>
                      {ov.description && (
                        <p className="text-xs text-muted-foreground mt-3 leading-relaxed line-clamp-3">{ov.description}</p>
                      )}
                    </div>
                  )}

                  {/* Volume */}
                  {detail?.volume > 0 && (
                    <div className="rounded-2xl bg-white/4 border border-white/8 p-4 flex items-center gap-3">
                      <BarChart3 className="w-4 h-4 text-muted-foreground" />
                      <div className="text-sm">
                        <span className="text-muted-foreground">Volume </span>
                        <span className="font-semibold">{fmt(detail.volume, "")}</span>
                      </div>
                      {ov.exchange && (
                        <span className="ml-auto text-xs text-muted-foreground">{ov.exchange}</span>
                      )}
                    </div>
                  )}

                  {/* Link to Predictions */}
                  <a
                    href={`/predictions?symbol=${symbol}`}
                    className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border border-neon-green/30 text-neon-green text-sm font-medium hover:bg-neon-green/10 transition-colors"
                  >
                    <Target className="w-4 h-4" /> Full AI Analysis
                    <ExternalLink className="w-3 h-3 ml-auto" />
                  </a>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
