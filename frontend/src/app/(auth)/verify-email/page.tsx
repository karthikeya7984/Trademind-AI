"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { TrendingUp, CheckCircle, XCircle, Loader2 } from "lucide-react";
import api from "@/lib/api";

function VerifyEmail() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;
    const token = searchParams.get("token");
    if (!token) { setStatus("error"); return; }

    api.post("/auth/verify-email", { token })
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="glass-card text-center">
          <div className="flex items-center gap-2 mb-8 justify-center">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-black" />
            </div>
            <span className="font-bold text-xl gradient-text">TradeMind AI</span>
          </div>

          {status === "loading" && (
            <>
              <Loader2 className="w-12 h-12 animate-spin text-neon-green mx-auto mb-4" />
              <p className="text-muted-foreground">Verifying your email...</p>
            </>
          )}
          {status === "success" && (
            <>
              <CheckCircle className="w-12 h-12 text-neon-green mx-auto mb-4" />
              <h2 className="text-xl font-bold mb-2">Email verified!</h2>
              <p className="text-muted-foreground text-sm mb-6">Your account is now fully activated.</p>
              <Link href="/dashboard" className="btn-primary inline-block">Go to Dashboard</Link>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold mb-2">Verification failed</h2>
              <p className="text-muted-foreground text-sm mb-6">The link is invalid or has expired.</p>
              <Link href="/login" className="text-neon-green hover:underline text-sm">Back to sign in</Link>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
      </div>
    }>
      <VerifyEmail />
    </Suspense>
  );
}
