"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { TrendingUp, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

type Step = "details" | "otp" | "password";

export default function RegisterPage() {
  const router = useRouter();
  const { loginWithName } = useAuthStore();

  const [step, setStep] = useState<Step>("details");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  // Step 1 — send OTP
  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.post("/auth/register/send-otp", { name, email });
      setStep("otp");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Failed to send OTP.");
    } finally {
      setLoading(false);
    }
  };

  // Step 2 — verify OTP
  const handleVerifyOTP = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.join("").length !== 6) return;
    setStep("password");
  };

  // Step 3 — set password & complete
  const handleComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/auth/register/complete", {
        name, email, otp: otp.join(""), password,
      });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      loginWithName(data.user.name);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Registration failed.");
      setStep("otp");
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

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-6">
          {(["details", "otp", "password"] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === s || (i < ["details","otp","password"].indexOf(step)) ? "bg-neon-green text-black" : "bg-muted text-muted-foreground"}`}>
                {i + 1}
              </div>
              {i < 2 && <div className="flex-1 h-px bg-border w-8" />}
            </div>
          ))}
        </div>

        {/* Step 1 — Name + Email */}
        {step === "details" && (
          <>
            <h1 className="text-2xl font-bold mb-1">Create account</h1>
            <p className="text-muted-foreground text-sm mb-6">Enter your details to get started</p>
            <form onSubmit={handleSendOTP} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Username</label>
                <input
                  type="text" required value={name} onChange={e => setName(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="e.g. john_trader"
                />
                <p className="text-xs text-muted-foreground mt-1">Must be unique across all users</p>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Email</label>
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="you@example.com"
                />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-2.5">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Send OTP
              </button>
            </form>
          </>
        )}

        {/* Step 2 — OTP */}
        {step === "otp" && (
          <>
            <h1 className="text-2xl font-bold mb-1">Verify your email</h1>
            <p className="text-muted-foreground text-sm mb-6">
              Enter the 6-digit code sent to <span className="text-foreground font-medium">{email}</span>
            </p>
            <form onSubmit={handleVerifyOTP}>
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
              <button type="submit" disabled={otp.join("").length !== 6} className="btn-primary w-full py-2.5">
                Verify OTP
              </button>
            </form>
            <button onClick={() => { setStep("details"); setError(""); }} className="mt-3 w-full text-sm text-muted-foreground hover:text-foreground transition-colors">
              ← Back
            </button>
          </>
        )}

        {/* Step 3 — Password */}
        {step === "password" && (
          <>
            <h1 className="text-2xl font-bold mb-1">Set your password</h1>
            <p className="text-muted-foreground text-sm mb-6">Choose a strong password for your account</p>
            <form onSubmit={handleComplete} className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Password</label>
                <input
                  type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="Min. 8 characters"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Confirm Password</label>
                <input
                  type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                  placeholder="Re-enter password"
                />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-2.5">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Account
              </button>
            </form>
          </>
        )}

        {step === "details" && (
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <button onClick={() => router.push("/login")} className="text-neon-green hover:underline">Sign in</button>
          </p>
        )}
      </motion.div>
    </main>
  );
}
