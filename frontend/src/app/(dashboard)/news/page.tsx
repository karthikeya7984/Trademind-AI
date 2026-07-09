"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { motion } from "framer-motion";
import api from "@/lib/api";
import { Newspaper, ExternalLink, TrendingUp, TrendingDown, Minus, Search, Loader2 } from "lucide-react";
import { format } from "date-fns";

export default function NewsPage() {
  const [query, setQuery] = useState("stock market");
  const [input, setInput] = useState("stock market");

  const { data: news = [], isLoading, isError } = useQuery({
    queryKey: ["news", query],
    queryFn: () => api.get(`/news/?q=${encodeURIComponent(query)}&page_size=30`).then((r) => r.data),
    staleTime: 300_000,
    retry: 2,
  });

  const SentimentIcon = ({ sentiment }: { sentiment: string }) => {
    if (sentiment === "positive") return <TrendingUp className="w-3 h-3 text-neon-green" />;
    if (sentiment === "negative") return <TrendingDown className="w-3 h-3 text-red-400" />;
    return <Minus className="w-3 h-3 text-yellow-400" />;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Newspaper className="w-6 h-6 text-neon-green" /> News Intelligence</h1>
          <p className="text-muted-foreground text-sm mt-1">AI-powered sentiment analysis on financial news</p>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); setQuery(input); }} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input value={input} onChange={(e) => setInput(e.target.value)}
              className="bg-muted border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-48" />
          </div>
          <button type="submit" className="btn-primary text-sm px-4 py-2">Search</button>
        </form>
      </div>

      {/* Sentiment Summary */}
      {news.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Positive", count: news.filter((n: any) => n.sentiment === "positive").length, color: "text-neon-green", bg: "bg-neon-green/10" },
            { label: "Neutral", count: news.filter((n: any) => n.sentiment === "neutral").length, color: "text-yellow-400", bg: "bg-yellow-400/10" },
            { label: "Negative", count: news.filter((n: any) => n.sentiment === "negative").length, color: "text-red-400", bg: "bg-red-400/10" },
          ].map((s) => (
            <div key={s.label} className={`glass p-4 rounded-xl text-center ${s.bg}`}>
              <div className={`text-2xl font-bold ${s.color}`}>{s.count}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-neon-green" /></div>
      ) : isError ? (
        <div className="glass-card text-center py-12 text-red-400 text-sm">Failed to load news. Please check your NEWS_API_KEY in backend/.env and try again.</div>
      ) : news.length === 0 ? (
        <div className="glass-card text-center py-12 text-muted-foreground text-sm">No news articles found for &quot;{query}&quot;. Try a different search term or stock symbol.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {news.map((article: any, i: number) => (
            <motion.a key={i} href={article.url} target="_blank" rel="noopener noreferrer"
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
              className="glass-card hover:border-neon-green/20 transition-all group block">
              {article.image && (
                <img src={article.image} alt="" className="w-full h-40 object-cover rounded-lg mb-3" onError={(e) => (e.currentTarget.style.display = "none")} />
              )}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">{article.source}</span>
                <div className="flex items-center gap-1">
                  <SentimentIcon sentiment={article.sentiment} />
                  <span className={`text-xs ${article.sentiment === "positive" ? "text-neon-green" : article.sentiment === "negative" ? "text-red-400" : "text-yellow-400"}`}>
                    {article.sentiment}
                  </span>
                </div>
              </div>
              <h3 className="font-medium text-sm leading-snug mb-2 group-hover:text-neon-green transition-colors line-clamp-2">{article.title}</h3>
              {article.description && <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{article.description}</p>}
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{article.published_at ? format(new Date(article.published_at), "MMM d, yyyy") : ""}</span>
                <ExternalLink className="w-3 h-3 group-hover:text-neon-green transition-colors" />
              </div>
            </motion.a>
          ))}
        </div>
      )}
    </div>
  );
}
