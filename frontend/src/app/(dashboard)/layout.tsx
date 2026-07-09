"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Sidebar from "@/components/dashboard/Sidebar";
import TopBar from "@/components/dashboard/TopBar";
import MobileNav from "@/components/dashboard/MobileNav";
import { useUIStore } from "@/store/uiStore";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { fetchMe } = useAuthStore();
  const { sidebarOpen } = useUIStore();
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const authChecked = useRef(false);

  // Run auth check ONCE on mount only
  useEffect(() => {
    if (authChecked.current) return;
    authChecked.current = true;

    fetchMe().then(() => {
      const state = useAuthStore.getState();
      if (!state.isAuthenticated) {
        router.replace("/login");
        return;
      }
      setReady(true);
    });
  }, []);

  // Guard admin route synchronously after auth is ready
  useEffect(() => {
    if (!ready) return;
    const state = useAuthStore.getState();
    if (pathname.startsWith("/admin") && state.user?.role !== "admin") {
      router.replace("/dashboard");
    }
  }, [pathname, ready]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-neon-green/30 border-t-neon-green rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className={`flex-1 flex flex-col ${sidebarOpen ? "md:ml-64" : "md:ml-16"}`}>
        <TopBar />
        <main className="flex-1 p-4 md:p-6 pb-20 md:pb-6 overflow-auto">
          {children}
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
