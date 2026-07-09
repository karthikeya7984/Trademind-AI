"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, PieChart, MessageSquare, Newspaper } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Home" },
  { href: "/predictions", icon: TrendingUp, label: "AI" },
  { href: "/portfolio", icon: PieChart, label: "Portfolio" },
  { href: "/assistant", icon: MessageSquare, label: "Chat" },
  { href: "/news", icon: Newspaper, label: "News" },
];

export default function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-card/95 backdrop-blur-xl border-t border-border">
      <div className="flex items-center justify-around py-2">
        {items.map(({ href, icon: Icon, label }) => {
          const active = pathname === href;
          return (
            <Link key={href} href={href} className={cn(
              "flex flex-col items-center gap-1 px-3 py-1.5 rounded-lg transition-all",
              active ? "text-neon-green" : "text-muted-foreground"
            )}>
              <Icon className="w-5 h-5" />
              <span className="text-xs">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
