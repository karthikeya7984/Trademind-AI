"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import {
  TrendingUp, TrendingDown, Activity, BarChart3,
  ArrowUpRight, ArrowDownRight, Search, ChevronUp, ChevronDown,
} from "lucide-react";
import SkeletonCard from "@/components/ui/SkeletonCard";
import StockDetailModal from "@/components/ui/StockDetailModal";

const ALL_STOCKS = [
  { symbol: "AAPL",  name: "Apple Inc.",            sector: "Technology" },
  { symbol: "MSFT",  name: "Microsoft Corp.",        sector: "Technology" },
  { symbol: "NVDA",  name: "NVIDIA Corp.",           sector: "Technology" },
  { symbol: "GOOGL", name: "Alphabet Inc.",          sector: "Technology" },
  { symbol: "META",  name: "Meta Platforms",         sector: "Technology" },
  { symbol: "AMD",   name: "Advanced Micro Devices", sector: "Technology" },
  { symbol: "INTC",  name: "Intel Corp.",            sector: "Technology" },
  { symbol: "ORCL",  name: "Oracle Corp.",           sector: "Technology" },
  { symbol: "CRM",   name: "Salesforce Inc.",        sector: "Technology" },
  { symbol: "ADBE",  name: "Adobe Inc.",             sector: "Technology" },
  { symbol: "QCOM",  name: "Qualcomm Inc.",          sector: "Technology" },
  { symbol: "TXN",   name: "Texas Instruments",      sector: "Technology" },
  { symbol: "PLTR",  name: "Palantir Technologies",  sector: "Technology" },
  { symbol: "SNOW",  name: "Snowflake Inc.",         sector: "Technology" },
  { symbol: "NET",   name: "Cloudflare Inc.",        sector: "Technology" },
  { symbol: "SHOP",  name: "Shopify Inc.",           sector: "Technology" },
  { symbol: "AMZN",  name: "Amazon.com Inc.",        sector: "Consumer"   },
  { symbol: "TSLA",  name: "Tesla Inc.",             sector: "Consumer"   },
  { symbol: "NFLX",  name: "Netflix Inc.",           sector: "Consumer"   },
  { symbol: "BABA",  name: "Alibaba Group",          sector: "Consumer"   },
  { symbol: "UBER",  name: "Uber Technologies",      sector: "Consumer"   },
  { symbol: "ABNB",  name: "Airbnb Inc.",            sector: "Consumer"   },
  { symbol: "NKE",   name: "Nike Inc.",              sector: "Consumer"   },
  { symbol: "SBUX",  name: "Starbucks Corp.",        sector: "Consumer"   },
  { symbol: "MCD",   name: "McDonald's Corp.",       sector: "Consumer"   },
  { symbol: "WMT",   name: "Walmart Inc.",           sector: "Consumer"   },
  { symbol: "JPM",   name: "JPMorgan Chase",         sector: "Finance"    },
  { symbol: "BAC",   name: "Bank of America",        sector: "Finance"    },
  { symbol: "GS",    name: "Goldman Sachs",          sector: "Finance"    },
  { symbol: "MS",    name: "Morgan Stanley",         sector: "Finance"    },
  { symbol: "BRK-B", name: "Berkshire Hathaway",     sector: "Finance"    },
  { symbol: "V",     name: "Visa Inc.",              sector: "Finance"    },
  { symbol: "MA",    name: "Mastercard Inc.",        sector: "Finance"    },
  { symbol: "PYPL",  name: "PayPal Holdings",        sector: "Finance"    },
  { symbol: "COIN",  name: "Coinbase Global",        sector: "Finance"    },
  { symbol: "HOOD",  name: "Robinhood Markets",      sector: "Finance"    },
  { symbol: "JNJ",   name: "Johnson & Johnson",      sector: "Healthcare" },
  { symbol: "PFE",   name: "Pfizer Inc.",            sector: "Healthcare" },
  { symbol: "MRNA",  name: "Moderna Inc.",           sector: "Healthcare" },
  { symbol: "UNH",   name: "UnitedHealth Group",     sector: "Healthcare" },
  { symbol: "ABBV",  name: "AbbVie Inc.",            sector: "Healthcare" },
  { symbol: "LLY",   name: "Eli Lilly & Co.",        sector: "Healthcare" },
  { symbol: "XOM",   name: "Exxon Mobil Corp.",      sector: "Energy"     },
  { symbol: "CVX",   name: "Chevron Corp.",          sector: "Energy"     },
  { symbol: "COP",   name: "ConocoPhillips",         sector: "Energy"     },
  { symbol: "SLB",   name: "SLB (Schlumberger)",     sector: "Energy"     },
  { symbol: "SPY",   name: "S&P 500 ETF",           sector: "ETF"        },
  { symbol: "QQQ",   name: "Nasdaq 100 ETF",        sector: "ETF"        },
  { symbol: "DIA",   name: "Dow Jones ETF",         sector: "ETF"        },
  { symbol: "IWM",   name: "Russell 2000 ETF",      sector: "ETF"        },
];

const SECTORS = ["All", ...Array.from(new Set(ALL_STOCKS.map((s) => s.sector)))];

export default function DashboardPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("All");
  const [sortKey, setSortKey] = useState<"symbol" | "price" | "change_pct">("symbol");
  const [sortAsc, setSortAsc] = useState(true);

  const allSymbols = ALL_STOCKS.map((s) => s.symbol).join(",");

  const { data: indices, isLoading: indicesLoading } = useQuery({
    queryKey: ["indices"],
    queryFn: () => api.get("/market/indices").then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 55_000,
    refetchOnWindowFocus: false,
  });

  const { data: movers, isLoading: moversLoading } = useQuery({
    queryKey: ["movers"],
    queryFn: () => api.get("/market/movers").then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 55_000,
    refetchOnWindowFocus: false,
  });

  const { data: quotes, isLoading: quotesLoading } = useQuery({
    queryKey: ["all-quotes"],
    queryFn: () =>
      api.get(`/market/quotes/batch?symbols=${allSymbols}`).then((r) => r.data ?? {}),
    refetchInterval: 120_000,
    staleTime: 110_000,
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
    retry: 2,
    retryDelay: 3000,
  });

  // Signals load lazily — table shows immediately with quotes, signals fill in
  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ["all-signals"],
    queryFn: () => api.get(`/predictions/signals?symbols=${allSymbols}`).then((r) => r.data ?? {}),
    refetchInterval: 3_600_000,
    staleTime: 3_600_000,
    placeholderData: (prev) => prev,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  const indexList = indices
    ? [
        { label: "S&P 500", ...indices["S&P 500"], Icon: TrendingUp  },
        { label: "NASDAQ",  ...indices["NASDAQ"],  Icon: Activity    },
        { label: "DOW",     ...indices["DOW"],     Icon: BarChart3   },
        { label: "VIX",     ...indices["VIX"],     Icon: TrendingDown},
      ]
    : null;

  const filtered = ALL_STOCKS
    .filter((s) => sector === "All" || s.sector === sector)
    .filter((s) =>
      !search ||
      s.symbol.toLowerCase().includes(search.toLowerCase()) ||
      s.name.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const qa = quotes?.[a.symbol], qb = quotes?.[b.symbol];
      const av = sortKey === "symbol" ? a.symbol : (qa?.[sortKey] ?? 0);
      const bv = sortKey === "symbol" ? b.symbol : (qb?.[sortKey] ?? 0);
      return av < bv ? (sortAsc ? -1 : 1) : av > bv ? (sortAsc ? 1 : -1) : 0;
    });

  function toggleSort(k: typeof sortKey) {
    if (sortKey === k) setSortAsc(!sortAsc);
    else { setSortKey(k); setSortAsc(true); }
  }

  const SortIcon = ({ k }: { k: typeof sortKey }) =>
    sortKey === k ? (sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />) : null;

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Market Overview</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Live market data · Alpha Vantage · Click any stock for details
        </p>
      </div>

      {/* Index Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {indicesLoading || !indexList
          ? [1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)
          : indexList.map(({ label, value, change, change_pct, Icon }) => (
              <div key={label} className="stat-card">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-muted-foreground">{label}</span>
                  <Icon className={`w-4 h-4 ${(change_pct ?? 0) >= 0 ? "text-neon-green" : "text-red-400"}`} />
                </div>
                <div className="text-xl font-bold">{value?.toLocaleString()}</div>
                <div className={`text-sm mt-1 ${(change_pct ?? 0) >= 0 ? "positive" : "negative"}`}>
                  {(change ?? 0) >= 0 ? "+" : ""}{change?.toFixed(2)} ({formatPercent(change_pct ?? 0)})
                </div>
              </div>
            ))}
      </div>

      {/* Gainers / Losers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {(["gainers", "losers"] as const).map((type) => (
          <div key={type} className="glass-card">
            <h3 className="font-semibold mb-3 flex items-center gap-2 text-sm">
              {type === "gainers"
                ? <><TrendingUp className="w-4 h-4 text-neon-green" /> Top Gainers</>
                : <><TrendingDown className="w-4 h-4 text-red-400" /> Top Losers</>}
            </h3>
            {moversLoading ? (
              <div className="space-y-2">{[1,2,3].map((i) => <SkeletonCard key={i} className="h-10" />)}</div>
            ) : (
              <div className="space-y-1">
                {movers?.[type]?.slice(0, 5).map((s: any) => (
                  <button
                    key={s.symbol}
                    onClick={() => setSelected(s.symbol)}
                    className="w-full flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-white/5 transition-colors text-left"
                  >
                    <div>
                      <span className="font-medium text-sm">{s.symbol}</span>
                      <div className="text-xs text-muted-foreground">{formatCurrency(s.price ?? 0)}</div>
                    </div>
                    <span className={`text-sm font-medium ${type === "gainers" ? "positive" : "negative"}`}>
                      {formatPercent(s.change_pct ?? 0)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Stock Table */}
      <div className="glass-card !p-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3 p-4 border-b border-border/50">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search symbol or company..."
              className="w-full bg-muted/50 border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-neon-green/50"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {SECTORS.map((s) => (
              <button
                key={s} onClick={() => setSector(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  sector === s
                    ? "bg-neon-green/20 text-neon-green border border-neon-green/30"
                    : "bg-muted/50 text-muted-foreground hover:text-foreground"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 text-muted-foreground text-xs">
                <th className="text-left px-4 py-3 font-medium">
                  <button onClick={() => toggleSort("symbol")} className="flex items-center gap-1 hover:text-foreground">
                    Symbol <SortIcon k="symbol" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Company</th>
                <th className="text-left px-4 py-3 font-medium hidden lg:table-cell">Sector</th>
                <th className="text-right px-4 py-3 font-medium">
                  <button onClick={() => toggleSort("price")} className="flex items-center gap-1 ml-auto hover:text-foreground">
                    Price <SortIcon k="price" />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium">
                  <button onClick={() => toggleSort("change_pct")} className="flex items-center gap-1 ml-auto hover:text-foreground">
                    Change <SortIcon k="change_pct" />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium hidden sm:table-cell">Volume</th>
                <th className="text-right px-4 py-3 font-medium hidden md:table-cell">52W Range</th>
                <th className="text-center px-4 py-3 font-medium">Signal</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((stock) => {
                const q = quotes?.[stock.symbol];
                const isUp = (q?.change_pct ?? 0) >= 0;
                return (
                  <tr
                    key={stock.symbol}
                    onClick={() => setSelected(stock.symbol)}
                    className="border-b border-border/30 hover:bg-white/4 cursor-pointer transition-colors group"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-bold text-muted-foreground group-hover:border-neon-green/30 group-hover:text-neon-green transition-all">
                          {stock.symbol.slice(0, 2)}
                        </div>
                        <span className="font-bold group-hover:text-neon-green transition-colors">{stock.symbol}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs hidden md:table-cell">{stock.name}</td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-muted/60 text-muted-foreground">{stock.sector}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">
                      {q?.price != null ? formatCurrency(q.price) : (
                        quotesLoading ? <span className="inline-block w-14 h-3 bg-muted/60 rounded animate-pulse" /> : "—"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {q?.change_pct != null ? (
                        <span className={`inline-flex items-center justify-end gap-0.5 text-xs font-medium ${isUp ? "text-neon-green" : "text-red-400"}`}>
                          {isUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                          {formatPercent(q.change_pct)}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground hidden sm:table-cell">
                      {q?.volume
                        ? q.volume >= 1_000_000
                          ? `${(q.volume / 1_000_000).toFixed(1)}M`
                          : `${(q.volume / 1_000).toFixed(0)}K`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right hidden md:table-cell">
                      {q?.high && q?.low ? (
                        <div className="text-xs space-y-0.5">
                          <div className="text-neon-green">{formatCurrency(q.high)}</div>
                          <div className="text-red-400">{formatCurrency(q.low)}</div>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      {(() => {
                        const sig = signals?.[stock.symbol];
                        if (!sig) return signalsLoading
                          ? <span className="inline-block w-12 h-4 bg-muted/60 rounded animate-pulse" />
                          : <span className="text-xs text-muted-foreground/40">—</span>;
                        const s = sig.signal as string;
                        const pct = Math.round((sig.confidence ?? 0.5) * 100);
                        return (
                          <span className="inline-flex flex-col items-center gap-0.5">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                              s === "BUY"  ? "bg-neon-green/15 text-neon-green border-neon-green/40" :
                              s === "SELL" ? "bg-red-400/15 text-red-400 border-red-400/40" :
                                             "bg-yellow-400/15 text-yellow-400 border-yellow-400/40"
                            }`}>{s}</span>
                            <span className="text-[10px] text-muted-foreground">{pct}%</span>
                          </span>
                        );
                      })()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">No stocks match your search.</div>
          )}
        </div>

        <div className="px-4 py-2 border-t border-border/30 text-xs text-muted-foreground flex items-center justify-between">
          <span>{filtered.length} stocks · USD · Prices refresh every 2m · Signals refresh every 30m</span>
          {quotesLoading && <span className="text-neon-green animate-pulse">Refreshing prices…</span>}
        </div>
      </div>

      {/* Stock Detail Modal */}
      <StockDetailModal symbol={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
