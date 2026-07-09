"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { BarChart3, Search, Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { formatPercent, formatCurrency } from "@/lib/utils";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function BacktestSection() {
  const [symbol, setSymbol] = useState("AAPL");
  const [input, setInput] = useState("AAPL");
  const [capital, setCapital] = useState("100000");

  const backtestMutation = useMutation({
    mutationFn: ({ symbol, capital }: { symbol: string; capital: string }) =>
      api.get(`/backtest/${symbol}?period=1y&initial_capital=${capital}`).then((r) => r.data),
  });

  const handleRun = (e: React.FormEvent) => {
    e.preventDefault();
    const nextSymbol = input.toUpperCase();
    setSymbol(nextSymbol);
    backtestMutation.mutate({ symbol: nextSymbol, capital });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleRun} className="flex gap-2 flex-1">
          <input value={input} onChange={(e) => setInput(e.target.value.toUpperCase())}
            placeholder="Symbol" className="bg-muted border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-28" />
          <input value={capital} onChange={(e) => setCapital(e.target.value)}
            placeholder="Capital" type="number" className="bg-muted border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-32" />
          <button type="submit" disabled={backtestMutation.isPending} className="btn-primary text-sm px-4 py-2 flex items-center gap-2">
            {backtestMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
            Run Backtest
          </button>
        </form>
      </div>

      {backtestMutation.data && !backtestMutation.data.error && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Return", value: formatPercent(backtestMutation.data.total_return), positive: backtestMutation.data.total_return >= 0 },
              { label: "Sharpe Ratio", value: backtestMutation.data.sharpe_ratio, positive: backtestMutation.data.sharpe_ratio >= 1 },
              { label: "Max Drawdown", value: `${backtestMutation.data.max_drawdown}%`, positive: false },
              { label: "Win Rate", value: `${backtestMutation.data.win_rate}%`, positive: backtestMutation.data.win_rate >= 50 },
            ].map((m) => (
              <div key={m.label} className="glass p-4 rounded-xl text-center">
                <div className={`text-xl font-bold ${m.positive ? "text-neon-green" : "text-red-400"}`}>{m.value}</div>
                <div className="text-xs text-muted-foreground mt-1">{m.label}</div>
              </div>
            ))}
          </div>

          <div className="glass-card">
            <h4 className="font-medium mb-3 text-sm">Recent Trades ({backtestMutation.data.total_trades} total)</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {backtestMutation.data.trades.map((t: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-xs py-1.5 border-b border-border/30 last:border-0">
                  <span className="text-muted-foreground">{t.exit_date?.slice(0, 10)}</span>
                  <span>{formatCurrency(t.entry_price)} → {formatCurrency(t.exit_price)}</span>
                  <span className={t.pnl >= 0 ? "text-neon-green" : "text-red-400"}>
                    {t.pnl >= 0 ? "+" : ""}{formatCurrency(t.pnl)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
