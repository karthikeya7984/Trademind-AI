"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

type Step = "credentials" | "otp";

export default function LoginPage() {
  const router = useRouter();
  const { loginWithName } = useAuthStore();

  const [step, setStep] = useState<Step>("credentials");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState(""); // returned from backend after step 1
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  // Step 1 — verify credentials, send OTP
  const handleCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/signin/send-otp", { identifier, password });
      setEmail(data.email);
      setStep("otp");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  };

  // Step 2 — verify OTP
  const handleOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.join("").length !== 6) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/signin/verify-otp", {
        email: email || identifier,
        otp: otp.join(""),
      });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      loginWithName(data.user.name);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Invalid or expired OTP.");
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (i: number, val: string) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...otp]; next[i] = val; setOtp(next);
    if (val && i < 5) inputs.current[i + 1]?.focus();
  };

  const handleOtpKey = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) inputs.current[i - 1]?.focus();
  };

  return (
    <main className="h-screen bg-background flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass neon-border rounded-2xl p-8 w-full max-w-md"
      >
        <div className="flex items-center gap-2 mb-6">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-black" />
          </div>
          <span className="font-bold text-lg gradient-text">TradeMind AI</span>
        </div>

        {/* Step 1 — Credentials */}
        {step === "credentials" && (
          <>
            <h1 className="text-2xl font-bold mb-1">Welcome back</h1>
            <p className="text-muted-foreground text-sm mb-6">Sign in with your username or email</p>
            <form onSubmit={handleCredentials} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Username or Email</label>
                <input
                  type="text" required value={identifier} onChange={e => setIdentifier(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="john_trader or you@example.com"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Password</label>
                <input
                  type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="••••••••"
                />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-2.5">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Continue
              </button>
            </form>
            <div className="mt-4 flex items-center justify-between text-sm">
              <button onClick={() => router.push("/forgot-password")} className="text-muted-foreground hover:text-foreground transition-colors">
                Forgot password?
              </button>
              <button onClick={() => router.push("/register")} className="text-neon-green hover:underline">
                Create account
              </button>
            </div>
          </>
        )}

        {/* Step 2 — OTP */}
        {step === "otp" && (
          <>
            <h1 className="text-2xl font-bold mb-1">Check your email</h1>
            <p className="text-muted-foreground text-sm mb-6">
              Enter the 6-digit OTP sent to your registered email
            </p>
            <form onSubmit={handleOTP}>
              <div className="flex gap-2 justify-center mb-6">
                {otp.map((digit, i) => (
                  <input
                    key={i} ref={el => { inputs.current[i] = el; }}
                    type="text" inputMode="numeric" maxLength={1} value={digit}
                    onChange={e => handleOtpChange(i, e.target.value)}
                    onKeyDown={e => handleOtpKey(i, e)}
                    className="w-11 h-12 text-center text-xl font-bold bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  />
                ))}
              </div>
              {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
              <button type="submit" disabled={loading || otp.join("").length !== 6} className="btn-primary w-full flex items-center justify-center gap-2 py-2.5">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Verify & Sign In
              </button>
            </form>
            <button onClick={() => { setStep("credentials"); setOtp(["","","","","",""]); setError(""); }} className="mt-3 w-full text-sm text-muted-foreground hover:text-foreground transition-colors">
              ← Back
            </button>
          </>
        )}
      </motion.div>
    </main>
  );
}
