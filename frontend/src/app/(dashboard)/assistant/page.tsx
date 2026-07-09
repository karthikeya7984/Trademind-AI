"use client";
import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import api from "@/lib/api";
import {
  MessageSquare, Send, Loader2, Bot, User,
  TrendingUp, TrendingDown, BarChart2,
} from "lucide-react";


// ── Signal detection for the new engine's markdown responses ──────────────────
function parseSignal(text: string): "buy" | "sell" | "hold" | null {
  if (/STRONG BUY|✅.*BUY|🚀.*BUY/i.test(text)) return "buy";
  if (/STRONG SELL|⚠️.*SELL|🔴.*SELL/i.test(text)) return "sell";
  if (/🔄.*HOLD/i.test(text)) return "hold";
  return null;
}

function SignalBanner({ signal }: { signal: "buy" | "sell" | "hold" | null }) {
  if (!signal) return null;
  const cfg = {
    buy:  { label: "BUY SIGNAL",  icon: <TrendingUp  className="w-3 h-3" />, cls: "text-green-400  bg-green-400/10  border-green-400/30"  },
    sell: { label: "SELL SIGNAL", icon: <TrendingDown className="w-3 h-3" />, cls: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30" },
    hold: { label: "HOLD",        icon: <BarChart2    className="w-3 h-3" />, cls: "text-blue-400   bg-blue-400/10   border-blue-400/30"   },
  }[signal];
  return (
    <div className={`flex items-center gap-1 text-xs font-semibold border rounded-full px-3 py-1 mb-3 w-fit ${cfg.cls}`}>
      {cfg.icon} {cfg.label}
    </div>
  );
}

// ── Markdown renderer — maps markdown elements to Tailwind classes ─────────────
function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2 text-neon-green/80">{children}</h3>,
        p:  ({ children }) => <p  className="mb-2 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-sm">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
        em:     ({ children }) => <em className="text-muted-foreground text-xs">{children}</em>,
        hr: () => <hr className="border-border my-2" />,
        table: ({ children }) => (
          <div className="overflow-x-auto mb-2">
            <table className="text-xs w-full border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
        th: ({ children }) => <th className="border border-border px-2 py-1 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
        code: ({ children }) => <code className="bg-muted px-1 rounded text-xs font-mono">{children}</code>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// ── Suggestion chips ──────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "Should I buy AAPL?",
  "Predict Tesla tomorrow",
  "Compare NVDA and AMD",
  "What is the RSI for MSFT?",
  "Best stocks to buy this week",
  "I have $500, which stocks can I buy?",
  "How risky is TSLA?",
  "Explain MACD",
];

// ── Main component ────────────────────────────────────────────────────────────
export default function AssistantPage() {
  const [input, setInput]   = useState("");
  const [symbol, setSymbol] = useState("");
  const bottomRef           = useRef<HTMLDivElement>(null);
  const qc                  = useQueryClient();

  const { data: history = [] } = useQuery({
    queryKey: ["chat-history"],
    queryFn:  () => api.get("/assistant/history").then((r) => r.data.reverse()),
  });

  const sendMutation = useMutation({
    mutationFn: (data: { prompt: string; symbol?: string }) =>
      api.post("/assistant/chat", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chat-history"] }),
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMutation.mutate({ prompt: input, symbol: symbol || undefined });
    setInput("");
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, sendMutation.isPending]);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fade-in">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-neon-green" /> AI Trading Assistant
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Powered by a domain-specific Stock Intelligence Engine — no hallucinations, pure data
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 glass rounded-xl overflow-y-auto p-4 space-y-4 mb-4">

        {/* Empty state */}
        {history.length === 0 && !sendMutation.isPending && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-neon-green/20 to-neon-blue/20 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-neon-green" />
            </div>
            <h3 className="font-semibold text-lg mb-2">TradeMind Stock AI</h3>
            <p className="text-muted-foreground text-sm mb-6 max-w-sm">
              Ask about any US stock — I'll run live technical analysis and give you a
              structured BUY / HOLD / SELL signal with entry, target, and stop-loss.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="glass p-3 rounded-lg text-sm text-left hover:border-neon-green/30 transition-all text-muted-foreground hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message history */}
        <AnimatePresence>
          {(history as any[]).map((msg) => {
            const signal = parseSignal(msg.response || "");
            return (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-3"
              >
                {/* User bubble */}
                <div className="flex justify-end">
                  <div className="flex items-start gap-2 max-w-[80%]">
                    <div className="bg-neon-green/10 border border-neon-green/20 rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
                      {msg.prompt}
                    </div>
                    <div className="w-7 h-7 rounded-full bg-neon-green/20 flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="w-4 h-4 text-neon-green" />
                    </div>
                  </div>
                </div>

                {/* AI bubble */}
                <div className="flex justify-start">
                  <div className="flex items-start gap-2 max-w-[88%]">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-4 h-4 text-black" />
                    </div>
                    <div className="glass rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed min-w-0">
                      <SignalBanner signal={signal} />
                      <MarkdownMessage content={msg.response || ""} />
                      <div className="text-xs text-muted-foreground mt-2">
                        {new Date(msg.created_at).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: true })}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {/* Typing indicator */}
        {sendMutation.isPending && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
                <Bot className="w-4 h-4 text-black" />
              </div>
              <div className="glass rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2 h-2 bg-neon-green rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form onSubmit={handleSend} className="flex gap-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="Symbol (opt.)"
          className="bg-muted border border-border rounded-lg px-3 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 w-28"
        />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend(e as any)}
          placeholder="Ask about stocks, signals, indicators, comparisons..."
          className="flex-1 bg-muted border border-border rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
        />
        <button
          type="submit"
          disabled={sendMutation.isPending || !input.trim()}
          className="btn-primary px-4 py-3"
        >
          {sendMutation.isPending
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <Send    className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
}
