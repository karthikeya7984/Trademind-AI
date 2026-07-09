"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import {
  PieChart, Zap, Loader2, TrendingUp, TrendingDown, ShoppingCart,
  Info, X, Brain, Target, ShieldAlert, Minus,
} from "lucide-react";
import { PieChart as RechartsPie, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { useRouter } from "next/navigation";

const COLORS = ["#00ff88", "#00d4ff", "#7c3aed", "#ff006e", "#f59e0b", "#10b981"];

interface PredictionRow {
  symbol: string;
  boughtPrice: number;
  signal: "BUY" | "SELL" | "HOLD";
  targetPrice: number;
  stopLoss: number;
  confidence: number;
  action: string;
}

export default function PortfolioPage() {
  const router = useRouter();
  const [optimizeSymbols, setOptimizeSymbols] = useState("");
  const [showPredModal, setShowPredModal] = useState(false);
  const [predictions, setPredictions] = useState<PredictionRow[]>([]);
  const [loadingPreds, setLoadingPreds] = useState(false);

  const { data: portfolio = [], isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => api.get("/portfolio/").then((r) => r.data),
  });

  const { data: optimization, mutate: runOptimize, isPending: optimizing } = useMutation({
    mutationFn: (symbols: string[]) =>
      api.post("/portfolio/optimize", symbols).then((r) => r.data),
  });

  const totalValue = portfolio.reduce(
    (sum: number, p: any) => sum + p.quantity * p.average_buy_price,
    0
  );
  const pieData = portfolio.map((p: any) => ({
    name: p.stock_symbol,
    value: p.quantity * p.average_buy_price,
  }));

  const handleOptimize = async () => {
    const syms = optimizeSymbols
      ? optimizeSymbols.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
      : portfolio.map((p: any) => p.stock_symbol);

    if (syms.length === 0) return;

    // Run portfolio optimization
    runOptimize(syms);

    // Fetch AI predictions for each symbol in parallel
    setLoadingPreds(true);
    setShowPredModal(true);
    setPredictions([]);

    try {
      const results = await Promise.allSettled(
        syms.map((sym: string) => api.get(`/predictions/${sym}`).then((r) => r.data))
      );

      const rows: PredictionRow[] = results.map((res, i) => {
        const sym = syms[i];
        // Find bought price from portfolio
        const holding = portfolio.find((p: any) => p.stock_symbol === sym);
        const boughtPrice = holding ? holding.average_buy_price : 0;

        if (res.status === "fulfilled" && !res.value?.error) {
          const d = res.value;
          return {
            symbol:      sym,
            boughtPrice,
            signal:      d.signal as "BUY" | "SELL" | "HOLD",
            targetPrice: d.predicted_price ?? d.entry_price ?? 0,
            stopLoss:    d.stop_loss ?? 0,
            confidence:  d.confidence_score ?? 0.5,
            action:      d.advice?.action ?? d.signal,
          };
        }
        return {
          symbol: sym, boughtPrice,
          signal: "HOLD", targetPrice: 0, stopLoss: 0, confidence: 0, action: "N/A",
        };
      });

      setPredictions(rows);
    } finally {
      setLoadingPreds(false);
    }
  };

  const SignalBadge = ({ signal }: { signal: string }) => {
    if (signal === "BUY")
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-neon-green/15 text-neon-green border border-neon-green/30">
          <TrendingUp className="w-3 h-3" /> BUY
        </span>
      );
    if (signal === "SELL")
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-red-400/15 text-red-400 border border-red-400/30">
          <TrendingDown className="w-3 h-3" /> SELL
        </span>
      );
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-400/15 text-yellow-400 border border-yellow-400/30">
        <Minus className="w-3 h-3" /> HOLD
      </span>
    );
  };

  const ActionBadge = ({ action }: { action: string }) => {
    const map: Record<string, string> = {
      INVEST: "text-neon-green", WITHDRAW: "text-red-400", HOLD: "text-yellow-400",
    };
    return (
      <span className={`text-xs font-semibold ${map[action] ?? "text-muted-foreground"}`}>
        {action}
      </span>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <PieChart className="w-6 h-6 text-neon-green" /> Portfolio
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Auto-synced from your trades — no manual entry needed
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold neon-text">{formatCurrency(totalValue)}</div>
          <div className="text-xs text-muted-foreground">Total Invested Value</div>
        </div>
      </div>

      {/* Empty state */}
      {!isLoading && portfolio.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card flex flex-col items-center justify-center py-16 text-center"
        >
          <ShoppingCart className="w-12 h-12 text-muted-foreground mb-4" />
          <h3 className="font-semibold text-lg mb-2">No Holdings Yet</h3>
          <p className="text-muted-foreground text-sm mb-6 max-w-sm">
            Your portfolio is automatically updated when you buy stocks in the Trading simulator.
          </p>
          <button
            onClick={() => router.push("/trading")}
            className="btn-primary flex items-center gap-2 px-6 py-2.5 text-sm"
          >
            <TrendingUp className="w-4 h-4" /> Go to Trading
          </button>
        </motion.div>
      )}

      {portfolio.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Holdings */}
          <div className="lg:col-span-2 space-y-4">
            <div className="glass-card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Holdings ({portfolio.length})</h3>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Info className="w-3 h-3" /> Auto-synced from trades
                </div>
              </div>
              <div className="space-y-3">
                {portfolio.map((p: any, i: number) => {
                  const positionValue = p.quantity * p.average_buy_price;
                  const allocationPct = totalValue > 0 ? (positionValue / totalValue) * 100 : 0;
                  return (
                    <motion.div
                      key={p.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center justify-between p-4 bg-muted/50 rounded-xl border border-border/50 hover:border-neon-green/20 transition-all"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-black flex-shrink-0"
                          style={{ background: COLORS[i % COLORS.length] }}
                        >
                          {p.stock_symbol[0]}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">{p.stock_symbol}</span>
                            <span className="text-xs bg-neon-green/10 text-neon-green border border-neon-green/20 rounded-full px-2 py-0.5 flex items-center gap-1">
                              <TrendingUp className="w-2.5 h-2.5" /> BUY
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {p.quantity} shares @ {formatCurrency(p.average_buy_price)} avg
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">{formatCurrency(positionValue)}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {allocationPct.toFixed(1)}% of portfolio
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-3 gap-3">
              <div className="glass-card text-center py-4">
                <div className="text-xl font-bold text-neon-green">{portfolio.length}</div>
                <div className="text-xs text-muted-foreground mt-1">Positions</div>
              </div>
              <div className="glass-card text-center py-4">
                <div className="text-xl font-bold text-neon-blue">
                  {portfolio.reduce((s: number, p: any) => s + p.quantity, 0).toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Total Shares</div>
              </div>
              <div className="glass-card text-center py-4">
                <div className="text-xl font-bold text-neon-green">{formatCurrency(totalValue)}</div>
                <div className="text-xs text-muted-foreground mt-1">Invested</div>
              </div>
            </div>
          </div>

          {/* Right panel */}
          <div className="space-y-4">
            {/* Pie chart */}
            {pieData.length > 0 && (
              <div className="glass-card">
                <h3 className="font-semibold mb-4">Allocation</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <RechartsPie>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
                      {pieData.map((_: any, i: number) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: any) => formatCurrency(v)}
                      contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)" }}
                    />
                  </RechartsPie>
                </ResponsiveContainer>
                <div className="space-y-2 mt-2">
                  {pieData.map((p: any, i: number) => (
                    <div key={p.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="font-medium">{p.name}</span>
                      </div>
                      <span className="text-muted-foreground">
                        {((p.value / totalValue) * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Optimizer */}
            <div className="glass-card">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-neon-green" /> AI Optimizer
              </h3>
              <div className="space-y-3">
                <input
                  value={optimizeSymbols}
                  onChange={(e) => setOptimizeSymbols(e.target.value)}
                  placeholder={
                    portfolio.length > 0
                      ? portfolio.map((p: any) => p.stock_symbol).join(",")
                      : "AAPL,TSLA,NVDA,MSFT"
                  }
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                />
                <button
                  onClick={handleOptimize}
                  disabled={optimizing || loadingPreds || (portfolio.length === 0 && !optimizeSymbols)}
                  className="btn-primary w-full text-sm flex items-center justify-center gap-2"
                >
                  {(optimizing || loadingPreds) && <Loader2 className="w-4 h-4 animate-spin" />}
                  {optimizing || loadingPreds ? "Analyzing..." : "Optimize Portfolio"}
                </button>
              </div>

              {optimization && (
                <div className="mt-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="glass p-3 rounded-lg text-center">
                      <div className="text-lg font-bold text-neon-green">{optimization.expected_return}%</div>
                      <div className="text-xs text-muted-foreground">Expected Return</div>
                    </div>
                    <div className="glass p-3 rounded-lg text-center">
                      <div className="text-lg font-bold text-neon-blue">{optimization.sharpe_ratio}</div>
                      <div className="text-xs text-muted-foreground">Sharpe Ratio</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {Object.entries(optimization.allocation).map(([sym, pct]: [string, any]) => (
                      <div key={sym} className="flex items-center justify-between text-sm">
                        <span className="font-medium">{sym}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-muted rounded-full h-1.5">
                            <div className="bg-neon-green h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-neon-green w-12 text-right">{pct}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── AI Predictions Modal ── */}
      <AnimatePresence>
        {showPredModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
            onClick={(e) => { if (e.target === e.currentTarget) setShowPredModal(false); }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.92, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 20 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="glass-card w-full max-w-2xl max-h-[80vh] flex flex-col"
              style={{ border: "1px solid rgba(0,255,136,0.2)" }}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between mb-4 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-neon-green" />
                  <h2 className="font-bold text-lg">AI Predictions</h2>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                    Live Analysis
                  </span>
                </div>
                <button
                  onClick={() => setShowPredModal(false)}
                  className="w-7 h-7 rounded-lg bg-muted hover:bg-muted/80 flex items-center justify-center transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Loading state */}
              {loadingPreds && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
                  <p className="text-sm text-muted-foreground">Running AI analysis on your holdings...</p>
                </div>
              )}

              {/* Table */}
              {!loadingPreds && predictions.length > 0 && (
                <div className="overflow-auto flex-1">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0">
                      <tr className="border-b border-border">
                        <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground bg-muted/80 rounded-tl-lg">
                          Stock
                        </th>
                        <th className="text-right py-2.5 px-3 text-xs font-semibold text-muted-foreground bg-muted/80">
                          Bought Price
                        </th>
                        <th className="text-center py-2.5 px-3 text-xs font-semibold text-muted-foreground bg-muted/80">
                          Signal
                        </th>
                        <th className="text-right py-2.5 px-3 text-xs font-semibold text-muted-foreground bg-muted/80">
                          <span className="flex items-center justify-end gap-1">
                            <Target className="w-3 h-3" /> Target
                          </span>
                        </th>
                        <th className="text-right py-2.5 px-3 text-xs font-semibold text-muted-foreground bg-muted/80 rounded-tr-lg">
                          <span className="flex items-center justify-end gap-1">
                            <ShieldAlert className="w-3 h-3" /> Stop Loss
                          </span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {predictions.map((row, i) => {
                        const pnlPct = row.boughtPrice > 0
                          ? ((row.targetPrice - row.boughtPrice) / row.boughtPrice) * 100
                          : 0;
                        const isProfit = pnlPct >= 0;
                        return (
                          <motion.tr
                            key={row.symbol}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.06 }}
                            className="border-b border-border/40 hover:bg-muted/30 transition-colors"
                          >
                            {/* Stock name */}
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-2">
                                <div
                                  className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-black flex-shrink-0"
                                  style={{ background: COLORS[i % COLORS.length] }}
                                >
                                  {row.symbol[0]}
                                </div>
                                <div>
                                  <div className="font-semibold">{row.symbol}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {Math.round(row.confidence * 100)}% conf
                                  </div>
                                </div>
                              </div>
                            </td>

                            {/* Bought price */}
                            <td className="py-3 px-3 text-right">
                              <div className="font-medium">
                                {row.boughtPrice > 0 ? formatCurrency(row.boughtPrice) : "—"}
                              </div>
                              <div className={`text-xs ${isProfit ? "text-neon-green" : "text-red-400"}`}>
                                {row.boughtPrice > 0 && row.targetPrice > 0
                                  ? `${isProfit ? "+" : ""}${pnlPct.toFixed(1)}% to target`
                                  : ""}
                              </div>
                            </td>

                            {/* Signal */}
                            <td className="py-3 px-3 text-center">
                              <div className="flex flex-col items-center gap-1">
                                <SignalBadge signal={row.signal} />
                                <ActionBadge action={row.action} />
                              </div>
                            </td>

                            {/* Target price */}
                            <td className="py-3 px-3 text-right">
                              <div className="font-semibold text-neon-green">
                                {row.targetPrice > 0 ? formatCurrency(row.targetPrice) : "—"}
                              </div>
                            </td>

                            {/* Stop loss */}
                            <td className="py-3 px-3 text-right">
                              <div className="font-semibold text-red-400">
                                {row.stopLoss > 0 ? formatCurrency(row.stopLoss) : "—"}
                              </div>
                            </td>
                          </motion.tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Footer */}
              {!loadingPreds && predictions.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border/40 flex-shrink-0">
                  <p className="text-xs text-muted-foreground text-center">
                    AI predictions based on RSI, MACD, Bollinger Bands & moving averages. Not financial advice.
                  </p>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
