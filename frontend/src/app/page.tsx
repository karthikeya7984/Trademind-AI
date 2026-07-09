"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { TrendingUp, Brain, Shield, BarChart3, Zap, Globe } from "lucide-react";
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
      <nav className="relative z-10 flex items-center justify-between px-6 py-4 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-black" />
          </div>
          <span className="font-bold text-xl gradient-text">TradeMind AI</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-muted-foreground hover:text-foreground transition-colors text-sm">Sign In</Link>
          <Link href="/register" className="btn-primary text-sm">Get Started Free</Link>
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
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register" className="btn-primary text-sm px-6 py-2.5">Start Trading Free</Link>
            <Link href="/dashboard" className="glass px-6 py-2.5 rounded-lg text-sm font-medium hover:border-neon-green/30 transition-all">
              View Dashboard
            </Link>
          </div>
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

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          className="glass neon-border rounded-xl px-6 py-4 text-center"
        >
          <h2 className="text-lg font-bold mb-1">Ready to Trade Smarter?</h2>
          <p className="text-muted-foreground text-sm mb-3">Join thousands of investors using AI to make better decisions.</p>
          <Link href="/register" className="btn-primary text-sm px-8 py-2.5">Create Free Account</Link>
        </motion.div>

      </div>
    </main>
  );
}
