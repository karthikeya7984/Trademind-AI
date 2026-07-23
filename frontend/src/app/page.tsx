"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Brain, Shield, BarChart3, Zap, Globe, ArrowRight } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

const features = [
  { icon: Brain, title: "AI Predictions", desc: "LSTM-powered stock forecasting" },
  { icon: BarChart3, title: "Portfolio Optimizer", desc: "Sharpe ratio maximization" },
  { icon: Shield, title: "Risk Management", desc: "VaR analysis & stop-loss" },
  { icon: TrendingUp, title: "Live Markets", desc: "Real-time prices & charts" },
  { icon: Zap, title: "AI Assistant", desc: "GPT-4 financial advisor" },
  { icon: Globe, title: "News Intelligence", desc: "Sentiment from 50+ sources" },
];

export default function HomePage() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    } else {
      setChecked(true);
    }
  }, [isAuthenticated]);

  if (!checked) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-neon-green/30 border-t-neon-green rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <main className="h-screen bg-background overflow-hidden flex flex-col">
      {/* Ambient blobs */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-10 left-1/4 w-72 h-72 bg-neon-green/5 rounded-full blur-3xl" />
        <div className="absolute bottom-10 right-1/4 w-56 h-56 bg-neon-purple/5 rounded-full blur-3xl" />
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex items-center px-6 py-4 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-black" />
          </div>
          <span className="font-bold text-xl gradient-text">TradeMind AI</span>
        </div>
      </nav>

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col justify-between max-w-7xl mx-auto w-full px-6 pb-4">

        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="text-center pt-2"
        >
          <div className="inline-flex items-center gap-2 glass px-3 py-1.5 rounded-full text-xs text-neon-green mb-3">
            <Zap className="w-3 h-3" />
            <span>AI-Powered • Real-Time • Enterprise Grade</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-3 leading-tight">
            Trade Smarter with{" "}
            <span className="gradient-text">Artificial Intelligence</span>
          </h1>
          <p className="text-base text-muted-foreground max-w-xl mx-auto mb-4">
            Institutional-grade AI predictions, portfolio optimization, and risk management — built for retail investors.
          </p>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
          className="grid grid-cols-4 gap-3"
        >
          {[["10K+", "Active Traders"], ["94.2%", "AI Accuracy"], ["$2.4B", "Volume Tracked"], ["50ms", "Latency"]].map(([val, label]) => (
            <div key={label} className="glass p-3 rounded-xl text-center">
              <div className="text-xl font-bold neon-text">{val}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
            </div>
          ))}
        </motion.div>

        {/* Features */}
        <div>
          <div className="text-center mb-3">
            <h2 className="text-xl font-bold">Everything You Need to Trade Like a Pro</h2>
            <p className="text-muted-foreground text-xs">Powered by cutting-edge AI and real-time market data</p>
          </div>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}
                className="glass p-3 rounded-xl hover:border-neon-green/20 transition-all group text-center"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green/20 to-neon-blue/20 flex items-center justify-center mx-auto mb-2 group-hover:scale-110 transition-transform">
                  <f.icon className="w-4 h-4 text-neon-green" />
                </div>
                <h3 className="font-semibold text-xs mb-1">{f.title}</h3>
                <p className="text-muted-foreground text-xs leading-tight">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Sign in box */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          className="glass neon-border rounded-xl px-6 py-4"
        >
          <h2 className="text-lg font-bold mb-1 text-center">Get Started</h2>
          <p className="text-muted-foreground text-sm mb-4 text-center">Sign in to your TradeMind AI account.</p>
          <div className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <button
              onClick={() => router.push("/login")}
              className="flex-1 flex items-center justify-center gap-2 bg-muted border border-border rounded-lg px-5 py-2.5 text-sm font-medium hover:border-neon-green/40 transition-all"
            >
              <ArrowRight className="w-4 h-4" />
              Sign In
            </button>
            <button
              onClick={() => {
                window.location.href = `http://localhost:8000/api/v1/auth/google`;
              }}
              className="flex-1 flex items-center justify-center gap-2 bg-white text-gray-800 rounded-lg px-5 py-2.5 text-sm font-medium hover:bg-gray-100 transition-all"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
          </div>
        </motion.div>

      </div>
    </main>
  );
}
