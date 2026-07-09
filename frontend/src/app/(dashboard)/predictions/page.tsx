"use client";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine, CartesianGrid } from "recharts";
import { format } from "date-fns";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import {
  Brain, Search, TrendingUp, TrendingDown, Minus, Loader2,
  ArrowDownCircle, ArrowUpCircle, PauseCircle, AlertTriangle, Target, ShieldAlert, X
} from "lucide-react";
import { PriceHistoryChart, CandlestickChart } from "@/components/charts/PriceChart";
import IndicatorsPanel from "@/components/charts/IndicatorsPanel";

// ── Local stock catalog for instant offline suggestions ───────────────────────
const STOCK_CATALOG: { symbol: string; name: string; sector: string }[] = [
  { symbol: "AAPL",  name: "Apple Inc.",               sector: "Technology" },
  { symbol: "MSFT",  name: "Microsoft Corporation",    sector: "Technology" },
  { symbol: "NVDA",  name: "NVIDIA Corporation",        sector: "Semiconductors" },
  { symbol: "GOOGL", name: "Alphabet Inc.",             sector: "Technology" },
  { symbol: "META",  name: "Meta Platforms Inc.",       sector: "Social Media" },
  { symbol: "AMZN",  name: "Amazon.com Inc.",           sector: "E-Commerce" },
  { symbol: "TSLA",  name: "Tesla Inc.",                sector: "EV / Auto" },
  { symbol: "AMD",   name: "Advanced Micro Devices",    sector: "Semiconductors" },
  { symbol: "NFLX",  name: "Netflix Inc.",              sector: "Streaming" },
  { symbol: "INTC",  name: "Intel Corporation",         sector: "Semiconductors" },
  { symbol: "ORCL",  name: "Oracle Corporation",        sector: "Cloud / Software" },
  { symbol: "CRM",   name: "Salesforce Inc.",           sector: "Cloud / CRM" },
  { symbol: "ADBE",  name: "Adobe Inc.",                sector: "Software" },
  { symbol: "QCOM",  name: "Qualcomm Inc.",             sector: "Semiconductors" },
  { symbol: "PLTR",  name: "Palantir Technologies",     sector: "AI / Data" },
  { symbol: "SNOW",  name: "Snowflake Inc.",            sector: "Cloud / Data" },
  { symbol: "JPM",   name: "JPMorgan Chase & Co.",      sector: "Banking" },
  { symbol: "BAC",   name: "Bank of America Corp.",     sector: "Banking" },
  { symbol: "GS",    name: "Goldman Sachs Group",       sector: "Banking" },
  { symbol: "V",     name: "Visa Inc.",                 sector: "Fintech" },
  { symbol: "MA",    name: "Mastercard Inc.",           sector: "Fintech" },
  { symbol: "PYPL",  name: "PayPal Holdings",           sector: "Fintech" },
  { symbol: "JNJ",   name: "Johnson & Johnson",         sector: "Healthcare" },
  { symbol: "PFE",   name: "Pfizer Inc.",               sector: "Pharma" },
  { symbol: "UNH",   name: "UnitedHealth Group",        sector: "Healthcare" },
  { symbol: "LLY",   name: "Eli Lilly and Company",     sector: "Pharma" },
  { symbol: "XOM",   name: "ExxonMobil Corporation",    sector: "Energy" },
  { symbol: "CVX",   name: "Chevron Corporation",       sector: "Energy" },
  { symbol: "WMT",   name: "Walmart Inc.",              sector: "Retail" },
  { symbol: "COST",  name: "Costco Wholesale",          sector: "Retail" },
  { symbol: "HD",    name: "Home Depot Inc.",           sector: "Retail" },
  { symbol: "DIS",   name: "Walt Disney Company",       sector: "Entertainment" },
  { symbol: "UBER",  name: "Uber Technologies",         sector: "Transport" },
  { symbol: "ABNB",  name: "Airbnb Inc.",               sector: "Travel" },
  { symbol: "COIN",  name: "Coinbase Global",           sector: "Crypto" },
  { symbol: "SPY",   name: "SPDR S&P 500 ETF",          sector: "ETF" },
  { symbol: "QQQ",   name: "Invesco NASDAQ 100 ETF",    sector: "ETF" },
  { symbol: "BABA",  name: "Alibaba Group",             sector: "E-Commerce" },
  { symbol: "NKE",   name: "Nike Inc.",                 sector: "Consumer" },
  { symbol: "SBUX",  name: "Starbucks Corporation",     sector: "Consumer" },
  { symbol: "MCD",   name: "McDonald's Corporation",    sector: "Consumer" },
  { symbol: "SHOP",  name: "Shopify Inc.",              sector: "E-Commerce" },
  { symbol: "NET",   name: "Cloudflare Inc.",           sector: "Cloud" },
  { symbol: "MRNA",  name: "Moderna Inc.",              sector: "Biotech" },
  { symbol: "ABBV",  name: "AbbVie Inc.",               sector: "Pharma" },
  { symbol: "HOOD",  name: "Robinhood Markets",         sector: "Fintech" },
  { symbol: "RIVN",  name: "Rivian Automotive",         sector: "EV" },
  { symbol: "SOFI",  name: "SoFi Technologies",         sector: "Fintech" },
  { symbol: "RBLX",  name: "Roblox Corporation",        sector: "Gaming" },
  { symbol: "SNAP",  name: "Snap Inc.",                 sector: "Social Media" },
];

type Suggestion = { symbol: string; name: string; sector: string; source: "local" | "api" };

// ── Smart Search Component ────────────────────────────────────────────────────
function StockSearchBox({
  onSelect,
  errorSuggestions,
  onDismissError,
}: {
  onSelect: (symbol: string) => void;
  errorSuggestions?: Suggestion[];
  onDismissError?: () => void;
}) {
  const [input, setInput]             = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showDrop, setShowDrop]       = useState(false);
  const [apiLoading, setApiLoading]   = useState(false);
  const [activeIdx, setActiveIdx]     = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef  = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setShowDrop(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const getLocalSuggestions = useCallback((q: string): Suggestion[] => {
    const query = q.toLowerCase().trim();
    if (!query) return [];
    return STOCK_CATALOG.filter(
      (s) =>
        s.symbol.toLowerCase().startsWith(query) ||
        s.name.toLowerCase().includes(query) ||
        s.sector.toLowerCase().includes(query)
    )
      .slice(0, 6)
      .map((s) => ({ ...s, source: "local" as const }));
  }, []);

  const fetchApiSuggestions = useCallback(async (val: string, local: Suggestion[]) => {
    setApiLoading(true);
    try {
      const { data } = await api.get(`/market/search?q=${encodeURIComponent(val)}`);
      if (Array.isArray(data) && data.length > 0) {
        const apiSuggestions: Suggestion[] = data
          .filter((r: any) => r.symbol && r.name)
          .map((r: any) => ({
            symbol: r.symbol,
            name: r.name,
            sector: r.exchange || "NYSE / NASDAQ",
            source: "api" as const,
          }))
          .slice(0, 6);
        const localSymbols = new Set(local.map((s) => s.symbol));
        const merged = [
          ...local,
          ...apiSuggestions.filter((s) => !localSymbols.has(s.symbol)),
        ].slice(0, 7);
        setSuggestions(merged);
      }
    } catch {
      // API failed — local suggestions are still shown
    } finally {
      setApiLoading(false);
    }
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(val);
    setActiveIdx(-1);
    onDismissError?.();

    if (!val.trim()) {
      setSuggestions([]);
      setShowDrop(false);
      return;
    }

    // Instant local suggestions
    const local = getLocalSuggestions(val);
    setSuggestions(local);
    setShowDrop(true);

    // Debounced API search — always fetch to cover non-catalog stocks
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchApiSuggestions(val, local), 350);
  };

  const handleSelect = (s: Suggestion) => {
    setInput(s.symbol);
    setSuggestions([]);
    setShowDrop(false);
    onDismissError?.();
    onSelect(s.symbol);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const val = input.trim();
    if (!val) return;
    if (activeIdx >= 0 && suggestions[activeIdx]) {
      handleSelect(suggestions[activeIdx]);
      return;
    }
    // If input matches a local catalog name (not symbol), resolve to symbol
    const nameMatch = STOCK_CATALOG.find(
      (s) => s.name.toLowerCase() === val.toLowerCase()
    );
    setSuggestions([]);
    setShowDrop(false);
    onSelect(nameMatch ? nameMatch.symbol : val.toUpperCase());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDrop || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setShowDrop(false);
    }
  };

  const showErrorBox = !showDrop && errorSuggestions && errorSuggestions.length > 0;

  return (
    <div ref={wrapperRef} className="relative">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <input
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onFocus={() => input.trim() && suggestions.length > 0 && setShowDrop(true)}
            placeholder="AAPL, Tesla, Walmart..."
            autoComplete="off"
            className="bg-muted border border-border rounded-lg pl-9 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-52 transition-all"
          />
          {input && (
            <button
              type="button"
              onClick={() => { setInput(""); setSuggestions([]); setShowDrop(false); onDismissError?.(); }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
        <button type="submit" className="btn-primary text-sm px-4 py-2">Analyze</button>
      </form>

      {/* Typing suggestions dropdown */}
      <AnimatePresence>
        {showDrop && (suggestions.length > 0 || apiLoading) && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1.5 w-72 bg-[#0f172a] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
          >
            {apiLoading && suggestions.length === 0 && (
              <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted-foreground">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Searching...
              </div>
            )}

            {suggestions.map((s, i) => (
              <button
                key={s.symbol}
                type="button"
                onMouseDown={() => handleSelect(s)}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-left transition-colors
                  ${ i === activeIdx
                    ? "bg-neon-green/10 text-foreground"
                    : "hover:bg-white/5 text-foreground"
                  }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm font-bold text-neon-green w-14 shrink-0">{s.symbol}</span>
                  <div className="min-w-0">
                    <div className="text-xs font-medium truncate">{s.name}</div>
                    <div className="text-xs text-muted-foreground">{s.sector}</div>
                  </div>
                </div>
                {s.source === "api" && (
                  <span className="text-[10px] text-neon-blue/70 shrink-0 ml-2">API</span>
                )}
              </button>
            ))}

            {!apiLoading && suggestions.length === 0 && input.trim().length > 0 && (
              <div className="px-4 py-3 text-xs text-muted-foreground">
                No matches for <span className="text-foreground font-medium">"{input}"</span>.
                Try a ticker like <span className="text-neon-green">AAPL</span> or company name.
              </div>
            )}

            {apiLoading && suggestions.length > 0 && (
              <div className="flex items-center gap-1.5 px-4 py-2 text-xs text-muted-foreground border-t border-white/5">
                <Loader2 className="w-3 h-3 animate-spin" /> Searching more...
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* "Did you mean?" box — shown after a failed prediction submit */}
      <AnimatePresence>
        {showErrorBox && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1.5 w-72 bg-[#0f172a] border border-yellow-400/30 rounded-xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5">
              <span className="text-xs font-semibold text-yellow-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> Did you mean?
              </span>
              <button type="button" onClick={onDismissError} className="text-muted-foreground hover:text-foreground">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            {errorSuggestions!.map((s) => (
              <button
                key={s.symbol}
                type="button"
                onMouseDown={() => handleSelect(s)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm font-bold text-neon-green w-14 shrink-0">{s.symbol}</span>
                  <div className="min-w-0">
                    <div className="text-xs font-medium truncate">{s.name}</div>
                    <div className="text-xs text-muted-foreground">{s.sector}</div>
                  </div>
                </div>
                {s.source === "api" && (
                  <span className="text-[10px] text-neon-blue/70 shrink-0 ml-2">API</span>
                )}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SevenDayBar({ data }: { data: Array<{ date: string; open: number; close: number; high: number; low: number }> }) {
  const last7 = data.slice(-7).map((d) => {
    const change = d.close - d.open;
    const changePct = d.open !== 0 ? (change / d.open) * 100 : 0;
    return {
      date: (() => { try { return format(new Date(d.date), "EEE dd"); } catch { return d.date; } })(),
      change: parseFloat(changePct.toFixed(2)),
      close: d.close,
      open: d.open,
    };
  });

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="bg-[#0f172a] border border-white/10 rounded-lg p-3 text-xs">
        <div className="font-semibold text-foreground mb-1">{d.date}</div>
        <div className="text-muted-foreground">Open: <span className="text-foreground">${d.open.toFixed(2)}</span></div>
        <div className="text-muted-foreground">Close: <span className="text-foreground">${d.close.toFixed(2)}</span></div>
        <div className={d.change >= 0 ? "text-neon-green" : "text-red-400"}>
          {d.change >= 0 ? "▲" : "▼"} {Math.abs(d.change).toFixed(2)}%
        </div>
      </div>
    );
  };

  const positiveCount = last7.filter((d) => d.change >= 0).length;
  const negativeCount = last7.length - positiveCount;

  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Past 7 Days Trading</h3>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1 text-neon-green">
            <TrendingUp className="w-3.5 h-3.5" /> {positiveCount} Up
          </span>
          <span className="flex items-center gap-1 text-red-400">
            <TrendingDown className="w-3.5 h-3.5" /> {negativeCount} Down
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={last7} margin={{ top: 4, right: 8, left: 0, bottom: 4 }} barSize={28}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
          <YAxis
            tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            tick={{ fontSize: 10, fill: "#64748b" }}
            axisLine={false} tickLine={false} width={52}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
          <Bar dataKey="change" radius={[4, 4, 0, 0]}>
            {last7.map((entry, i) => (
              <Cell key={i} fill={entry.change >= 0 ? "#00ff88" : "#f87171"} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-7 gap-1 mt-3">
        {last7.map((d, i) => (
          <div key={i} className="text-center">
            <div className={`text-xs font-bold ${d.change >= 0 ? "text-neon-green" : "text-red-400"}`}>
              {d.change >= 0 ? "+" : ""}{d.change.toFixed(2)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PredictionsPage() {
  const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const initSymbol = searchParams?.get("symbol") ?? "AAPL";
  const [symbol, setSymbol]                   = useState(initSymbol);
  const [errorSuggestions, setErrorSuggestions] = useState<Suggestion[]>([]);
  const [lastQuery, setLastQuery]               = useState("");

  const handleSelect = (sym: string) => {
    setErrorSuggestions([]);
    setSymbol(sym.toUpperCase());
  };

  const handleDismissError = () => setErrorSuggestions([]);

  const { data: prediction, isLoading } = useQuery({
    queryKey: ["prediction", symbol],
    queryFn: () => api.get(`/predictions/${symbol}`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    refetchOnWindowFocus: false,
    placeholderData: (prev) => prev,
  });

  // When prediction returns an error, fetch suggestions for the bad query
  useEffect(() => {
    if (!prediction?.error || lastQuery === symbol) return;
    setLastQuery(symbol);
    const local = STOCK_CATALOG.filter(
      (s) =>
        s.symbol.toLowerCase().includes(symbol.toLowerCase()) ||
        s.name.toLowerCase().includes(symbol.toLowerCase())
    )
      .slice(0, 5)
      .map((s) => ({ ...s, source: "local" as const }));

    if (local.length > 0) {
      setErrorSuggestions(local);
      return;
    }
    // Fallback: hit the search API
    api.get(`/market/search?q=${encodeURIComponent(symbol)}`)
      .then(({ data }) => {
        if (Array.isArray(data) && data.length > 0) {
          setErrorSuggestions(
            data
              .filter((r: any) => r.symbol && r.name)
              .map((r: any) => ({
                symbol: r.symbol,
                name: r.name,
                sector: r.exchange || "NYSE / NASDAQ",
                source: "api" as const,
              }))
              .slice(0, 5)
          );
        }
      })
      .catch(() => {});
  }, [prediction, symbol, lastQuery]);

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["history", symbol],
    queryFn: () => api.get(`/market/history/${symbol}?period=1y&interval=1d`).then((r) => r.data),
    enabled: !!symbol,
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    placeholderData: (prev) => prev,
  });

  const SignalBadge = ({ signal }: { signal: string }) => {
    const config = {
      BUY: { color: "bg-neon-green/20 text-neon-green border-neon-green/30", icon: TrendingUp },
      SELL: { color: "bg-red-400/20 text-red-400 border-red-400/30", icon: TrendingDown },
      HOLD: { color: "bg-yellow-400/20 text-yellow-400 border-yellow-400/30", icon: Minus },
    }[signal] || { color: "bg-muted text-muted-foreground border-border", icon: Minus };

    return (
      <span className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold border ${config.color}`}>
        <config.icon className="w-4 h-4" />
        {signal}
      </span>
    );
  };

  const AdvicePanel = ({ advice }: { advice: any }) => {
    if (!advice) return null;

    const actionConfigMap: Record<string, { color: string; textColor: string; icon: React.ElementType; label: string }> = {
      INVEST: {
        color: "border-neon-green/40 bg-neon-green/5",
        textColor: "text-neon-green",
        icon: ArrowUpCircle,
        label: "TIME TO INVEST",
      },
      WITHDRAW: {
        color: "border-red-400/40 bg-red-400/5",
        textColor: "text-red-400",
        icon: ArrowDownCircle,
        label: "TIME TO WITHDRAW",
      },
      HOLD: {
        color: "border-yellow-400/40 bg-yellow-400/5",
        textColor: "text-yellow-400",
        icon: PauseCircle,
        label: "HOLD POSITION",
      },
    };
    const actionConfig = actionConfigMap[advice.action as string] || {
      color: "border-border bg-muted/30",
      textColor: "text-muted-foreground",
      icon: PauseCircle,
      label: advice.action,
    };

    const urgencyColor = ({ HIGH: "text-red-400", MEDIUM: "text-yellow-400", LOW: "text-neon-green" } as Record<string, string>)[advice.urgency as string] || "text-muted-foreground";
    const riskColor = ({ HIGH: "text-red-400", MEDIUM: "text-yellow-400", LOW: "text-neon-green" } as Record<string, string>)[advice.risk_level as string] || "text-muted-foreground";

    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`glass-card border-2 ${actionConfig.color}`}>
        <div className="flex items-center gap-3 mb-4">
          <actionConfig.icon className={`w-8 h-8 ${actionConfig.textColor}`} />
          <div>
            <div className={`text-2xl font-bold ${actionConfig.textColor}`}>{actionConfig.label}</div>
            <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
              <span>Urgency: <span className={`font-semibold ${urgencyColor}`}>{advice.urgency}</span></span>
              <span>·</span>
              <span>Risk: <span className={`font-semibold ${riskColor}`}>{advice.risk_level}</span></span>
              <span>·</span>
              <span>Horizon: <span className="font-semibold text-neon-blue">{advice.time_horizon}</span></span>
              {advice.source === "openai" && (
                <><span>·</span><span className="text-neon-purple font-semibold">GPT-4o</span></>
              )}
            </div>
          </div>
        </div>

        <p className="text-sm text-muted-foreground mb-5 leading-relaxed">{advice.reason}</p>

        <div className="grid grid-cols-3 gap-3">
          {advice.entry_price && (
            <div className="glass p-3 rounded-xl text-center">
              <Target className="w-4 h-4 text-neon-green mx-auto mb-1" />
              <div className="text-sm font-bold text-neon-green">{formatCurrency(advice.entry_price)}</div>
              <div className="text-xs text-muted-foreground mt-0.5">Entry Price</div>
            </div>
          )}
          {advice.exit_price && (
            <div className="glass p-3 rounded-xl text-center">
              <ArrowUpCircle className="w-4 h-4 text-neon-blue mx-auto mb-1" />
              <div className="text-sm font-bold text-neon-blue">{formatCurrency(advice.exit_price)}</div>
              <div className="text-xs text-muted-foreground mt-0.5">Target Price</div>
            </div>
          )}
          {advice.stop_loss && (
            <div className="glass p-3 rounded-xl text-center">
              <ShieldAlert className="w-4 h-4 text-red-400 mx-auto mb-1" />
              <div className="text-sm font-bold text-red-400">{formatCurrency(advice.stop_loss)}</div>
              <div className="text-xs text-muted-foreground mt-0.5">Stop Loss</div>
            </div>
          )}
        </div>

        <div className="mt-4 flex items-start gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg p-3">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span>This is AI-generated analysis for educational purposes only. Not financial advice. Always do your own research.</span>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="w-6 h-6 text-neon-green" /> AI Prediction Center
          </h1>
          <p className="text-muted-foreground text-sm mt-1">Live data · Technical analysis · GPT-4o invest/withdraw advice</p>
        </div>
        <StockSearchBox
          onSelect={handleSelect}
          errorSuggestions={errorSuggestions}
          onDismissError={handleDismissError}
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
        </div>
      ) : prediction && prediction.error ? (
        <div className="glass-card text-center py-12 text-muted-foreground">
          {prediction.error}
        </div>
      ) : prediction && !prediction.error ? (
        <div className="space-y-6">
          {/* Main Prediction Card */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-card">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-3xl font-bold">{prediction.symbol}</h2>
                  <SignalBadge signal={prediction.signal} />
                </div>
                <div className="text-4xl font-bold neon-text">{formatCurrency(prediction.current_price)}</div>
                <div className="text-muted-foreground mt-1">
                  AI Target (7d): <span className="text-neon-green font-semibold">{formatCurrency(prediction.predicted_price)}</span>
                  <span className={`ml-2 text-sm ${prediction.predicted_price > prediction.current_price ? "positive" : "negative"}`}>
                    ({formatPercent((prediction.predicted_price - prediction.current_price) / prediction.current_price * 100)})
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="glass p-4 rounded-xl text-center">
                  <div className="text-2xl font-bold text-neon-blue">{Math.round(prediction.confidence_score * 100)}%</div>
                  <div className="text-xs text-muted-foreground mt-1">Confidence</div>
                </div>
                <div className="glass p-4 rounded-xl text-center">
                  <div className={`text-2xl font-bold ${prediction.trend === "bullish" ? "text-neon-green" : "text-red-400"}`}>
                    {prediction.trend === "bullish" ? "↑" : "↓"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 capitalize">{prediction.trend}</div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex justify-between text-xs text-muted-foreground mb-2">
                <span>AI Confidence Score</span>
                <span>{Math.round(prediction.confidence_score * 100)}%</span>
              </div>
              <div className="bg-muted rounded-full h-2">
                <motion.div
                  initial={{ width: 0 }} animate={{ width: `${prediction.confidence_score * 100}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="bg-gradient-to-r from-neon-green to-neon-blue h-2 rounded-full"
                />
              </div>
            </div>
          </motion.div>

          {/* AI Invest / Withdraw Advice */}
          {prediction.advice && <AdvicePanel advice={prediction.advice} />}

          {/* ── Graph 1: Full Price History ── */}
          <div>
            {historyLoading ? (
              <div className="glass-card flex items-center justify-center h-48 gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-neon-green" />
                <span className="text-sm text-muted-foreground">Loading price history...</span>
              </div>
            ) : history && history.length > 0 ? (
              <PriceHistoryChart data={history} symbol={prediction.symbol} predictedPrices={prediction.predicted_prices} />
            ) : null}
          </div>

          {/* ── Graph 2: 7-Day Candlestick ── */}
          <div>
            {historyLoading ? (
              <div className="glass-card flex items-center justify-center h-48 gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-neon-green" />
                <span className="text-sm text-muted-foreground">Loading candlestick chart...</span>
              </div>
            ) : history && history.length >= 7 ? (
              <CandlestickChart data={history} symbol={prediction.symbol} />
            ) : null}
          </div>

          {/* Technical Indicators */}
          {prediction.indicators && (
            <div className="glass-card">
              <h3 className="font-semibold mb-4">Technical Indicators</h3>
              <IndicatorsPanel indicators={prediction.indicators} />
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card text-center py-12 text-muted-foreground">
          Enter a stock symbol to get AI predictions
        </div>
      )}
    </div>
  );
}
