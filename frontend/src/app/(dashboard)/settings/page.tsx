"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "@/store/authStore";
import api from "@/lib/api";
import { Settings, User, Bell, Shield, Loader2, Phone, CheckCircle2 } from "lucide-react";
import toast from "react-hot-toast";

export default function SettingsPage() {
  const { user, fetchMe } = useAuthStore();
  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState("");
  const [otpStep, setOtpStep] = useState<"idle" | "sent" | "verified">("idle");
  const [otp, setOtp] = useState("");
  const [otpLoading, setOtpLoading] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch("/users/me", data),
    onSuccess: () => { fetchMe(); toast.success("Profile updated"); },
    onError: () => toast.error("Update failed"),
  });

  const handleSendOtp = async () => {
    if (!phone) return toast.error("Enter a phone number first");
    setOtpLoading(true);
    try {
      await api.post("/auth/send-sms-otp", { phone });
      setOtpStep("sent");
      setOtp("");
      toast.success("OTP sent to your phone");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to send OTP");
    } finally {
      setOtpLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!otp) return toast.error("Enter the OTP");
    setOtpLoading(true);
    try {
      await api.post("/auth/verify-sms-otp", { phone, otp });
      setOtpStep("verified");
      toast.success("Phone number verified!");
      await updateMutation.mutateAsync({ phone_number: phone });
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Invalid OTP");
    } finally {
      setOtpLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Settings className="w-6 h-6 text-neon-green" /> Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2"><User className="w-4 h-4" /> Profile</h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1.5 block">Full Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50" />
          </div>
          <div>
            <label className="text-sm font-medium mb-1.5 block">Email</label>
            <input value={user?.email || ""} disabled
              className="w-full bg-muted/50 border border-border rounded-lg px-4 py-2.5 text-sm text-muted-foreground cursor-not-allowed" />
          </div>

          {/* Phone Verification */}
          <div>
            <label className="text-sm font-medium mb-1.5 flex items-center gap-2">
              <Phone className="w-4 h-4" /> Phone Number
              {otpStep === "verified" && <CheckCircle2 className="w-4 h-4 text-neon-green" />}
            </label>
            <div className="flex gap-2">
              <input
                value={phone}
                onChange={(e) => { setPhone(e.target.value); setOtpStep("idle"); }}
                placeholder="+1234567890"
                disabled={otpStep === "verified"}
                className="flex-1 bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 disabled:opacity-50"
              />
              {otpStep !== "verified" && (
                <button
                  onClick={handleSendOtp}
                  disabled={otpLoading || !phone}
                  className="btn-primary text-sm px-4 whitespace-nowrap flex items-center gap-2"
                >
                  {otpLoading && otpStep === "idle" && <Loader2 className="w-4 h-4 animate-spin" />}
                  {otpStep === "sent" ? "Resend OTP" : "Verify"}
                </button>
              )}
            </div>

            {otpStep === "sent" && (
              <div className="flex gap-2 mt-2">
                <input
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="Enter 6-digit OTP"
                  maxLength={6}
                  className="flex-1 bg-muted border border-border rounded-lg px-4 py-2.5 text-sm tracking-widest text-center font-bold focus:outline-none focus:ring-2 focus:ring-neon-green/50"
                />
                <button
                  onClick={handleVerifyOtp}
                  disabled={otpLoading || otp.length !== 6}
                  className="btn-primary text-sm px-4 flex items-center gap-2"
                >
                  {otpLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                  Confirm
                </button>
              </div>
            )}
            {otpStep === "verified" && (
              <p className="text-xs text-neon-green mt-1">✓ Phone number verified and saved</p>
            )}
          </div>

          <button
            onClick={() => updateMutation.mutate({ name })}
            disabled={updateMutation.isPending}
            className="btn-primary text-sm flex items-center gap-2"
          >
            {updateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </div>

      {/* Account Plan */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2"><Shield className="w-4 h-4" /> Account Plan</h3>
        <div className="flex items-center justify-between p-4 bg-neon-green/5 border border-neon-green/20 rounded-xl">
          <div>
            <div className="font-semibold capitalize">{user?.account_type} Plan</div>
            <div className="text-sm text-muted-foreground mt-0.5">
              {user?.account_type === "free" ? "Upgrade for unlimited AI predictions" : "Full access to all features"}
            </div>
          </div>
          {user?.account_type === "free" && (
            <button className="btn-primary text-sm px-4 py-2">Upgrade to Pro</button>
          )}
        </div>
      </div>

      {/* Notifications */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2"><Bell className="w-4 h-4" /> Notifications</h3>
        <div className="space-y-3">
          {[
            { label: "Price Alerts", desc: "Get notified when stocks hit your targets" },
            { label: "AI Signals", desc: "Receive buy/sell/hold recommendations" },
            { label: "News Alerts", desc: "Breaking financial news for your watchlist" },
            { label: "Portfolio Updates", desc: "Daily portfolio performance summary" },
          ].map((n) => (
            <div key={n.label} className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium">{n.label}</div>
                <div className="text-xs text-muted-foreground">{n.desc}</div>
              </div>
              <button className="w-10 h-6 bg-neon-green/20 border border-neon-green/30 rounded-full relative transition-all">
                <div className="w-4 h-4 bg-neon-green rounded-full absolute right-1 top-1 transition-all" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
