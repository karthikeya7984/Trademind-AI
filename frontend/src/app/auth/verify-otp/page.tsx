"use client";
import { useState, useRef, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Loader2, Mail, ArrowLeft } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

function VerifyOTPInner() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get("email") ?? "";
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const { loginWithName } = useAuthStore();

  useEffect(() => {
    if (!email) router.replace("/login");
    else inputs.current[0]?.focus();
  }, [email]);

  const handleChange = (i: number, val: string) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...otp];
    next[i] = val;
    setOtp(next);
    if (val && i < 5) inputs.current[i + 1]?.focus();
  };

  const handleKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) inputs.current[i - 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const digits = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6).split("");
    if (digits.length === 6) {
      setOtp(digits);
      inputs.current[5]?.focus();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = otp.join("");
    if (code.length !== 6) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/google/verify-otp", { email, otp: code });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      loginWithName(data.user.name);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Invalid or expired code. Please try again.");
      setOtp(["", "", "", "", "", ""]);
      inputs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="h-screen bg-background flex items-center justify-center px-4">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/3 w-72 h-72 bg-neon-green/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass neon-border rounded-2xl p-8 w-full max-w-md relative z-10"
      >
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-black" />
          </div>
          <span className="font-bold text-lg gradient-text">TradeMind AI</span>
        </div>

        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-neon-green/10 border border-neon-green/20 mx-auto mb-4">
          <Mail className="w-6 h-6 text-neon-green" />
        </div>

        <h1 className="text-2xl font-bold text-center mb-1">Check your email</h1>
        <p className="text-muted-foreground text-sm text-center mb-6">
          We sent a 6-digit code to<br />
          <span className="text-foreground font-medium">{email}</span>
        </p>

        <form onSubmit={handleSubmit}>
          <div className="flex gap-2 justify-center mb-6" onPaste={handlePaste}>
            {otp.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className="w-11 h-12 text-center text-xl font-bold bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-neon-green/50 focus:border-neon-green/50 transition-all"
              />
            ))}
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center mb-4">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || otp.join("").length !== 6}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Verify & Sign In
          </button>
        </form>

        <button
          onClick={() => router.replace("/login")}
          className="mt-4 w-full flex items-center justify-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to login
        </button>

        <p className="text-xs text-muted-foreground text-center mt-4">
          Code expires in 10 minutes. Check your spam folder if you don't see it.
        </p>
      </motion.div>
    </main>
  );
}

export default function VerifyOTPPage() {
  return (
    <Suspense fallback={
      <div className="h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-neon-green animate-spin" />
      </div>
    }>
      <VerifyOTPInner />
    </Suspense>
  );
}
