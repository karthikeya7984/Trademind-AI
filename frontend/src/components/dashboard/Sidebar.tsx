"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useUIStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import {
  LayoutDashboard, TrendingUp, PieChart, Eye, Activity,
  MessageSquare, Newspaper, Shield, Settings, LogOut,
  ChevronLeft, ChevronRight, BarChart3, Users
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/predictions", icon: TrendingUp, label: "AI Predictions" },
  { href: "/portfolio", icon: PieChart, label: "Portfolio" },
  { href: "/watchlist", icon: Eye, label: "Watchlist" },
  { href: "/trading", icon: BarChart3, label: "Trading Sim" },
  { href: "/assistant", icon: MessageSquare, label: "AI Assistant" },
  { href: "/news", icon: Newspaper, label: "News" },
  { href: "/risk", icon: Shield, label: "Risk Analysis" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { user, logout } = useAuthStore();
  const pathname = usePathname();

  return (
    <aside className={cn(
      "fixed left-0 top-0 h-full z-40 hidden md:flex flex-col bg-card border-r border-border transition-all duration-300",
      sidebarOpen ? "w-64" : "w-16"
    )}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center flex-shrink-0">
          <TrendingUp className="w-5 h-5 text-black" />
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="font-bold gradient-text whitespace-nowrap">
              TradeMind AI
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={href} href={href} className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group",
              active ? "bg-neon-green/10 text-neon-green neon-border" : "text-muted-foreground hover:text-foreground hover:bg-muted"
            )}>
              <Icon className={cn("w-5 h-5 flex-shrink-0", active && "text-neon-green")} />
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="whitespace-nowrap">
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}

        {user?.role === "admin" && (
          <Link href="/admin" className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
            pathname === "/admin" ? "bg-neon-purple/10 text-neon-purple" : "text-muted-foreground hover:text-foreground hover:bg-muted"
          )}>
            <Users className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span>Admin</span>}
          </Link>
        )}
      </nav>

      {/* User + Collapse */}
      <div className="border-t border-border p-3 space-y-2">
        {sidebarOpen && user && (
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center text-black font-bold text-sm flex-shrink-0">
              {user.name[0].toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user.account_type}</p>
            </div>
          </div>
        )}
        <button onClick={logout} className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-all w-full">
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {sidebarOpen && <span>Sign Out</span>}
        </button>
        <button onClick={toggleSidebar} className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-all w-full">
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {sidebarOpen && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
