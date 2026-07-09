"use client";
import { Suspense, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Loader2, TrendingUp } from "lucide-react";
import toast from "react-hot-toast";

function GoogleCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loginWithGoogle } = useAuthStore();
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error || !code) {
      toast.error("Google sign-in was cancelled");
      router.replace("/login");
      return;
    }

    loginWithGoogle(code)
      .then(({ otp_required, email }) => {
        if (otp_required) {
          router.replace(`/auth/verify-otp?email=${encodeURIComponent(email)}`);
        } else {
          toast.success("Signed in with Google!");
          router.replace("/dashboard");
        }
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail || "Google sign-in failed");
        router.replace("/login");
      });
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
        <TrendingUp className="w-6 h-6 text-black" />
      </div>
      <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
      <p className="text-muted-foreground text-sm">Verifying with Google...</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-neon-green" />
      </div>
    }>
      <GoogleCallback />
    </Suspense>
  );
}
