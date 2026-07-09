"use client";
import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { BarChart3, TrendingUp, TrendingDown, Loader2, DollarSign, FlaskConical, Brain, ArrowUpCircle, ArrowDownCircle, PauseCircle } from "lucide-react";
import BacktestSection from "@/components/dashboard/BacktestSection";
import toast from "react-hot-toast";
import { format } from "date-fns";

export default function TradingPage() {
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("AAPL");
  const [qty, setQty] = useState("1");
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy");

  const { data: account } = useQuery({
    queryKey: ["trading-account"],
    queryFn: () => api.get("/trading/account").then((r) => r.data),
  });

  const { data: tradeHistory = [] } = useQuery({
    queryKey: ["trade-history"],
    queryFn: () => api.get("/trading/history").then((r) => r.data),
  });

  const { data: quote } = useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.get(`/market/quote/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    refetchInterval: 10_000,
  });

  const router = useRouter();

  const tradeMutation = useMutation({
    mutationFn: (data: any) => api.post("/trading/trade", data).then((r) => r.data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["trading-account"] });
      qc.invalidateQueries({ queryKey: ["trade-history"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      toast.success(`${tradeType.toUpperCase()} order executed!`);
      if (variables.trade_type === "buy") {
        setTimeout(() => router.push("/portfolio"), 1000);
      }
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Trade failed"),
  });

  const handleTrade = (e: React.FormEvent) => {
    e.preventDefault();
    const price = quote?.price || 100;
    tradeMutation.mutate({
      stock_symbol: symbol.toUpperCase(),
      trade_type: tradeType,
      quantity: parseFloat(qty),
      amount: price * parseFloat(qty),
    });
  };

  const { data: aiPrediction } = useQuery({
    queryKey: ["prediction", symbol],
    queryFn: () => api.get(`/predictions/${symbol}`).then((r) => r.data),
    enabled: symbol.length >= 1,
    staleTime: 300_000,
  });

  const advice = aiPrediction?.advice;
  const adviceConfig = advice ? ({
    INVEST: { color: "border-neon-green/30 bg-neon-green/5", textColor: "text-neon-green", icon: ArrowUpCircle },
    WITHDRAW: { color: "border-red-400/30 bg-red-400/5", textColor: "text-red-400", icon: ArrowDownCircle },
    HOLD: { color: "border-yellow-400/30 bg-yellow-400/5", textColor: "text-yellow-400", icon: PauseCircle },
  } as Record<string, { color: string; textColor: string; icon: React.ElementType }>)[advice.action as string] || { color: "border-border bg-muted/30", textColor: "text-muted-foreground", icon: PauseCircle } : null;

  const estimatedCost = (quote?.price || 0) * parseFloat(qty || "0");

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="w-6 h-6 text-neon-green" /> Paper Trading Simulator</h1>
        <p className="text-muted-foreground text-sm mt-1">Practice trading with virtual money — no real risk</p>
      </div>

      {/* Account Stats */}
      {account && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: "Virtual Balance", value: formatCurrency(account.balance), icon: DollarSign, color: "text-neon-green" },
            { label: "P&L", value: formatCurrency(account.profit_loss), icon: account.profit_loss >= 0 ? TrendingUp : TrendingDown, color: account.profit_loss >= 0 ? "text-neon-green" : "text-red-400" },
            { label: "Total Trades", value: tradeHistory.length.toString(), icon: BarChart3, color: "text-neon-blue" },
          ].map((stat) => (
            <div key={stat.label} className="stat-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">{stat.label}</span>
                <stat.icon className={`w-4 h-4 ${stat.color}`} />
              </div>
              <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            </div>
          ))}
        </div>
      )}

        {/* AI Advice Banner */}
        {advice && adviceConfig && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={`glass-card border ${adviceConfig.color} mb-0`}>
            <div className="flex items-center gap-3">
              <adviceConfig.icon className={`w-6 h-6 ${adviceConfig.textColor} shrink-0`} />
              <div>
                <div className={`font-bold text-sm ${adviceConfig.textColor}`}>
                  AI says: {advice.action} · {advice.urgency} urgency
                </div>
                <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{advice.reason}</div>
              </div>
              <Brain className="w-4 h-4 text-neon-purple ml-auto shrink-0" />
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trade Form */}
        <div className="glass-card">
          <h3 className="font-semibold mb-4">Execute Trade</h3>
          <form onSubmit={handleTrade} className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Stock Symbol</label>
              <input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50" />
            </div>

            {quote && (
              <div className="glass p-3 rounded-lg flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Current Price</span>
                <span className="font-bold">{formatCurrency(quote.price || 0)}</span>
              </div>
            )}

            <div>
              <label className="text-sm font-medium mb-1.5 block">Quantity</label>
              <input type="number" value={qty} onChange={(e) => setQty(e.target.value)} min="0.01" step="0.01"
                className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50" />
            </div>

            <div className="flex gap-3">
              {(["buy", "sell"] as const).map((t) => (
                <button key={t} type="button" onClick={() => setTradeType(t)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    tradeType === t
                      ? t === "buy" ? "bg-neon-green/20 text-neon-green border border-neon-green/30" : "bg-red-400/20 text-red-400 border border-red-400/30"
                      : "bg-muted text-muted-foreground border border-border"
                  }`}>
                  {t === "buy" ? <TrendingUp className="w-4 h-4 inline mr-1" /> : <TrendingDown className="w-4 h-4 inline mr-1" />}
                  {t.toUpperCase()}
                </button>
              ))}
            </div>

            {estimatedCost > 0 && (
              <div className="glass p-3 rounded-lg flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Estimated {tradeType === "buy" ? "Cost" : "Proceeds"}</span>
                <span className="font-bold">{formatCurrency(estimatedCost)}</span>
              </div>
            )}

            <button type="submit" disabled={tradeMutation.isPending}
              className={`w-full py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
                tradeType === "buy" ? "bg-neon-green/20 text-neon-green border border-neon-green/30 hover:bg-neon-green/30" : "bg-red-400/20 text-red-400 border border-red-400/30 hover:bg-red-400/30"
              }`}>
              {tradeMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {tradeMutation.isPending ? "Executing..." : `${tradeType.toUpperCase()} ${symbol}`}
            </button>
          </form>
        </div>

        {/* Trade History */}
        <div className="glass-card">
          <h3 className="font-semibold mb-4">Trade History</h3>
          {tradeHistory.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-8">No trades yet</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {tradeHistory.map((trade: any, i: number) => (
                <motion.div key={trade.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${trade.trade_type === "buy" ? "bg-neon-green/20" : "bg-red-400/20"}`}>
                      {trade.trade_type === "buy" ? <TrendingUp className="w-4 h-4 text-neon-green" /> : <TrendingDown className="w-4 h-4 text-red-400" />}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{trade.stock_symbol}</div>
                      <div className="text-xs text-muted-foreground">{trade.quantity} shares</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${trade.trade_type === "buy" ? "negative" : "positive"}`}>
                      {trade.trade_type === "buy" ? "-" : "+"}{formatCurrency(trade.amount)}
                    </div>
                    <div className="text-xs text-muted-foreground">{format(new Date(trade.timestamp), "MMM d, HH:mm")}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Backtesting */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <FlaskConical className="w-4 h-4 text-neon-purple" /> Strategy Backtester
        </h3>
        <BacktestSection />
      </div>
    </div>
  );
}
