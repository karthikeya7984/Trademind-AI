"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/store/authStore";
import { TrendingUp, Loader2, ShieldCheck, RefreshCw, Mail, AlertTriangle, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";

function VerifyOTP() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { verifyOtp, resendOtp, pendingOtpEmail, setPendingOtpEmail } = useAuthStore();

  const email = searchParams.get("email") || pendingOtpEmail || "";

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const cooldownRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    if (!email) {
      router.replace("/login");
    }
    // Focus first input on mount
    inputRefs.current[0]?.focus();
  }, []);

  // Cooldown countdown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    cooldownRef.current = setInterval(() => {
      setResendCooldown((v) => {
        if (v <= 1) { clearInterval(cooldownRef.current); return 0; }
        return v - 1;
      });
    }, 1000);
    return () => clearInterval(cooldownRef.current);
  }, [resendCooldown]);

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const next = [...otp];
    next[index] = value.slice(-1);
    setOtp(next);
    setErrorMsg("");
    // Auto-advance
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      setOtp(pasted.split(""));
      inputRefs.current[5]?.focus();
    }
  };

  const handleVerify = async () => {
    const code = otp.join("");
    if (code.length < 6) {
      setErrorMsg("Please enter the complete 6-digit OTP.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      await verifyOtp(email, code);
      setSuccessMsg("Email verified! Redirecting to dashboard...");
      toast.success("Email verified successfully!");
      setTimeout(() => router.replace("/dashboard"), 1000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Invalid OTP. Please try again.";
      setErrorMsg(msg);
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || resending) return;
    setResending(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      await resendOtp(email);
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
      setSuccessMsg("A new OTP has been sent to your email.");
      setResendCooldown(60);
      toast.success("New OTP sent!");
    } catch {
      toast.error("Failed to resend OTP. Please try again.");
    } finally {
      setResending(false);
    }
  };

  const maskedEmail = email
    ? email.replace(/(.{2})(.*)(@.*)/, (_, a, b, c) => a + "*".repeat(Math.max(0, b.length)) + c)
    : "";

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      {/* Ambient background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/3 w-72 h-72 bg-neon-green/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/3 w-56 h-56 bg-neon-blue/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="glass-card">
          {/* Logo */}
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-black" />
            </div>
            <span className="font-bold text-xl gradient-text">TradeMind AI</span>
          </div>

          {/* Header */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-14 h-14 rounded-full bg-neon-green/10 border border-neon-green/30 flex items-center justify-center mb-4">
              <ShieldCheck className="w-7 h-7 text-neon-green" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Verify your email</h1>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Daily security verification required. OTP sent to your email.
            </p>
            {email && (
              <div className="flex items-center gap-2 mt-2 px-3 py-1.5 bg-muted/50 rounded-full">
                <Mail className="w-3.5 h-3.5 text-neon-green" />
                <span className="text-xs font-medium text-foreground">{maskedEmail}</span>
              </div>
            )}
          </div>

          {/* OTP Inputs */}
          <div className="flex gap-3 justify-center mb-6" onPaste={handlePaste}>
            {otp.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                className={`w-12 h-14 text-center text-xl font-bold rounded-xl border-2 bg-muted/50 focus:outline-none transition-all duration-200
                  ${digit ? "border-neon-green text-neon-green" : "border-border text-foreground"}
                  ${errorMsg ? "border-red-400/60" : ""}
                  focus:border-neon-green focus:ring-2 focus:ring-neon-green/20`}
              />
            ))}
          </div>

          {/* Status messages */}
          <AnimatePresence mode="wait">
            {errorMsg && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex items-start gap-2 p-3 mb-4 bg-red-400/10 border border-red-400/20 rounded-lg text-sm text-red-400"
              >
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{errorMsg}</span>
              </motion.div>
            )}
            {successMsg && (
              <motion.div
                key="success"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex items-center gap-2 p-3 mb-4 bg-neon-green/10 border border-neon-green/20 rounded-lg text-sm text-neon-green"
              >
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{successMsg}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Verify Button */}
          <button
            onClick={handleVerify}
            disabled={loading || otp.join("").length < 6}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Verifying...</>
            ) : (
              <><ShieldCheck className="w-4 h-4" /> Verify OTP</>
            )}
          </button>

          {/* Resend */}
          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-1">Didn't receive the code?</p>
            <button
              onClick={handleResend}
              disabled={resending || resendCooldown > 0}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-neon-green hover:text-neon-green/80 disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
            >
              {resending ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Sending...</>
              ) : resendCooldown > 0 ? (
                <><RefreshCw className="w-3.5 h-3.5" /> Resend in {resendCooldown}s</>
              ) : (
                <><RefreshCw className="w-3.5 h-3.5" /> Resend OTP</>
              )}
            </button>
          </div>

          {/* Expiry note */}
          <p className="text-center text-xs text-muted-foreground mt-6">
            OTP expires in 10 minutes · <button onClick={() => { setPendingOtpEmail(null); router.replace("/login"); }} className="text-neon-green hover:underline">Back to sign in</button>
          </p>
        </div>
      </motion.div>
    </div>
  );
}

export default function VerifyOTPPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
      </div>
    }>
      <VerifyOTP />
    </Suspense>
  );
}
