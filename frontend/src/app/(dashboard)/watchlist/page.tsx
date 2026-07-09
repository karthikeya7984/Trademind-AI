"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { Eye, Plus, Trash2, TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

export default function WatchlistPage() {
  const [newSymbol, setNewSymbol] = useState("");
  const qc = useQueryClient();

  const { data: watchlist = [], isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api.get("/watchlist/").then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: (symbol: string) => api.post("/watchlist/", { stock_symbol: symbol }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Added to watchlist"); setNewSymbol(""); },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Failed to add"),
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => api.delete(`/watchlist/${symbol}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["watchlist"] }); toast.success("Removed from watchlist"); },
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (newSymbol.trim()) addMutation.mutate(newSymbol.trim().toUpperCase());
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Eye className="w-6 h-6 text-neon-green" /> Watchlist</h1>
          <p className="text-muted-foreground text-sm mt-1">Track your favorite stocks with live prices</p>
        </div>
        <form onSubmit={handleAdd} className="flex gap-2">
          <input value={newSymbol} onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            placeholder="Add symbol..." className="bg-muted border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-32" />
          <button type="submit" disabled={addMutation.isPending} className="btn-primary text-sm px-3 py-2 flex items-center gap-1">
            {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Add
          </button>
        </form>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-neon-green" /></div>
      ) : watchlist.length === 0 ? (
        <div className="glass-card text-center py-16">
          <Eye className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Your watchlist is empty. Add stocks to track them.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {watchlist.map((item: any, i: number) => (
            <WatchlistCard key={item.id} item={item} onRemove={() => removeMutation.mutate(item.stock_symbol)} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}

function WatchlistCard({ item, onRemove, index }: { item: any; onRemove: () => void; index: number }) {
  const { data: quote } = useQuery({
    queryKey: ["quote", item.stock_symbol],
    queryFn: () => api.get(`/market/quote/${item.stock_symbol}`).then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: prediction } = useQuery({
    queryKey: ["prediction-quick", item.stock_symbol],
    queryFn: () => api.get(`/predictions/${item.stock_symbol}`).then((r) => r.data),
    staleTime: 300_000,
  });

  const positive = (quote?.change_pct || 0) >= 0;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
      className="glass-card hover:border-neon-green/20 transition-all group">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-bold text-lg">{item.stock_symbol}</div>
          {prediction && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              prediction.signal === "BUY" ? "bg-neon-green/20 text-neon-green" :
              prediction.signal === "SELL" ? "bg-red-400/20 text-red-400" : "bg-yellow-400/20 text-yellow-400"
            }`}>{prediction.signal}</span>
          )}
        </div>
        <button onClick={onRemove} className="text-muted-foreground hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {quote ? (
        <>
          <div className="text-2xl font-bold">{formatCurrency(quote.price || 0)}</div>
          <div className={`flex items-center gap-1 text-sm mt-1 ${positive ? "positive" : "negative"}`}>
            {positive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {formatPercent(quote.change_pct || 0)}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
            <div>H: {formatCurrency(quote.high || 0)}</div>
            <div>L: {formatCurrency(quote.low || 0)}</div>
          </div>
        </>
      ) : (
        <div className="h-16 flex items-center justify-center">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
      )}
    </motion.div>
  );
}
