"use client";
import { useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { Settings, User, Bell } from "lucide-react";
import toast from "react-hot-toast";

const DEFAULT_NOTIFS = {
  "Price Alerts": true,
  "AI Signals": true,
  "News Alerts": false,
  "Portfolio Updates": false,
};

export default function SettingsPage() {
  const { user, loginWithName } = useAuthStore();
  const [name, setName] = useState(user?.name || "");
  const [notifs, setNotifs] = useState<Record<string, boolean>>(DEFAULT_NOTIFS);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    loginWithName(name.trim());
    toast.success("Profile updated");
  };

  const NOTIF_LIST = [
    { label: "Price Alerts",      desc: "Get notified when stocks hit your targets" },
    { label: "AI Signals",        desc: "Receive buy/sell/hold recommendations" },
    { label: "News Alerts",       desc: "Breaking financial news for your watchlist" },
    { label: "Portfolio Updates", desc: "Daily portfolio performance summary" },
  ];

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2"><Settings className="w-6 h-6 text-neon-green" /> Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2"><User className="w-4 h-4" /> Profile</h3>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1.5 block">Display Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50"
            />
          </div>
          <button type="submit" className="btn-primary text-sm">Save Changes</button>
        </form>
      </div>

      {/* Notifications */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2"><Bell className="w-4 h-4" /> Notifications</h3>
        <div className="space-y-3">
          {NOTIF_LIST.map((n) => (
            <div key={n.label} className="flex items-center justify-between py-2">
              <div>
                <div className="text-sm font-medium">{n.label}</div>
                <div className="text-xs text-muted-foreground">{n.desc}</div>
              </div>
              <button
                type="button"
                onClick={() => setNotifs((prev) => ({ ...prev, [n.label]: !prev[n.label] }))}
                className={`w-10 h-6 rounded-full relative transition-all border ${
                  notifs[n.label]
                    ? "bg-neon-green/20 border-neon-green/30"
                    : "bg-muted border-border"
                }`}
              >
                <div className={`w-4 h-4 rounded-full absolute top-1 transition-all ${
                  notifs[n.label] ? "bg-neon-green right-1" : "bg-muted-foreground left-1"
                }`} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
