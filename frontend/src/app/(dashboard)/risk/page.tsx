"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { Shield, Search, Loader2, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { formatPercent } from "@/lib/utils";

export default function RiskPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [input, setInput] = useState("AAPL");

  const { data: risk, isLoading } = useQuery({
    queryKey: ["risk", symbol],
    queryFn: () => api.get(`/risk/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSymbol(input.toUpperCase());
  };

  const RiskLevelIcon = ({ level }: { level: string }) => {
    if (level === "HIGH") return <AlertTriangle className="w-5 h-5 text-red-400" />;
    if (level === "MEDIUM") return <Info className="w-5 h-5 text-yellow-400" />;
    return <CheckCircle className="w-5 h-5 text-neon-green" />;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Shield className="w-6 h-6 text-neon-green" /> Risk Analysis</h1>
          <p className="text-muted-foreground text-sm mt-1">VaR, volatility, drawdown, and risk scoring</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input value={input} onChange={(e) => setInput(e.target.value.toUpperCase())}
              className="bg-muted border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-36" />
          </div>
          <button type="submit" className="btn-primary text-sm px-4 py-2">Analyze</button>
        </form>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-neon-green" /></div>
      ) : risk && !risk.error ? (
        <div className="space-y-6">
          {/* Risk Score */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">{risk.symbol}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <RiskLevelIcon level={risk.risk_level} />
                  <span className={`font-semibold ${risk.risk_level === "HIGH" ? "text-red-400" : risk.risk_level === "MEDIUM" ? "text-yellow-400" : "text-neon-green"}`}>
                    {risk.risk_level} RISK
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-5xl font-bold" style={{ color: risk.risk_score > 70 ? "#f87171" : risk.risk_score > 40 ? "#facc15" : "#00ff88" }}>
                  {risk.risk_score}
                </div>
                <div className="text-xs text-muted-foreground">Risk Score / 100</div>
              </div>
            </div>

            {/* Risk Score Bar */}
            <div className="bg-muted rounded-full h-3 mb-6">
              <motion.div
                initial={{ width: 0 }} animate={{ width: `${risk.risk_score}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="h-3 rounded-full"
                style={{ background: `linear-gradient(to right, #00ff88, ${risk.risk_score > 70 ? "#f87171" : risk.risk_score > 40 ? "#facc15" : "#00ff88"})` }}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: "Volatility (Annual)", value: `${risk.volatility}%`, color: "text-neon-blue" },
                { label: "VaR 95%", value: `${risk.var_95}%`, color: "text-yellow-400" },
                { label: "VaR 99%", value: `${risk.var_99}%`, color: "text-red-400" },
                { label: "Beta", value: risk.beta, color: "text-neon-purple" },
                { label: "Sharpe Ratio", value: risk.sharpe_ratio, color: risk.sharpe_ratio >= 1 ? "text-neon-green" : "text-yellow-400" },
                { label: "Current Price", value: `$${risk.current_price}`, color: "text-foreground" },
              ].map((m) => (
                <div key={m.label} className="glass p-4 rounded-xl text-center">
                  <div className={`text-xl font-bold ${m.color}`}>{m.value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{m.label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Drawdown & Stop Loss */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card">
              <h3 className="font-semibold mb-4">Max Drawdown</h3>
              <div className="text-3xl font-bold text-red-400">{risk.max_drawdown}%</div>
              <p className="text-sm text-muted-foreground mt-2">Maximum peak-to-trough decline over the past year</p>
              <div className="mt-4 bg-muted rounded-full h-2">
                <div className="bg-red-400 h-2 rounded-full" style={{ width: `${Math.min(Math.abs(risk.max_drawdown), 100)}%` }} />
              </div>
            </div>

            <div className="glass-card">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400" /> Stop-Loss Recommendation
              </h3>
              <div className="text-3xl font-bold text-yellow-400">${risk.stop_loss_recommendation}</div>
              <p className="text-sm text-muted-foreground mt-2">Suggested stop-loss based on 2x daily VaR</p>
              <div className="mt-4 p-3 bg-yellow-400/10 border border-yellow-400/20 rounded-lg text-xs text-yellow-400">
                ⚠️ This is not financial advice. Always use your own risk tolerance.
              </div>
            </div>
          </div>
        </div>
      ) : risk && risk.error ? (
        <div className="glass-card text-center py-12">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-red-400 font-medium">{risk.error}</p>
          <p className="text-muted-foreground text-sm mt-1">Try a valid stock symbol like AAPL, TSLA, MSFT</p>
        </div>
      ) : !risk ? (
        <div className="glass-card text-center py-12 text-muted-foreground">
          Enter a stock symbol to analyze risk metrics
        </div>
      ) : null}
    </div>
  );
}
