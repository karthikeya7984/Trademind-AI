"use client";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const code = params.get("code");
    const error = params.get("error");

    if (error || !code) {
      router.replace("/login?error=google_cancelled");
      return;
    }

    // Send code to backend — backend exchanges it, sends OTP, redirects to verify-otp
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    window.location.href = `${apiBase}/api/v1/auth/google/callback?code=${encodeURIComponent(code)}`;
  }, []);

  return (
    <div className="h-screen bg-background flex flex-col items-center justify-center gap-4">
      <Loader2 className="w-8 h-8 text-neon-green animate-spin" />
      <p className="text-muted-foreground text-sm">Signing you in with Google…</p>
    </div>
  );
}
