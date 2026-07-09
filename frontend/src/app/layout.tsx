import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "TradeMind AI – Algorithmic Trading & Stock Analysis",
  description: "AI-powered fintech platform for retail investors. Stock predictions, portfolio optimization, risk management.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "TradeMind AI" },
  openGraph: {
    title: "TradeMind AI",
    description: "AI-powered algorithmic trading platform",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#00ff88",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              style: { background: "#0f172a", color: "#f8fafc", border: "1px solid rgba(255,255,255,0.1)" },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
