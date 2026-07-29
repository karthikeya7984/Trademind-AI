"use client";
import { Shield } from "lucide-react";

export default function AdminPage() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <Shield className="w-12 h-12 text-muted-foreground" />
      <h1 className="text-2xl font-bold">Admin Panel</h1>
      <p className="text-muted-foreground text-sm max-w-sm">
        Admin features require a backend account with the <span className="text-neon-green font-medium">admin</span> role.
        Log in with an admin account to access this panel.
      </p>
    </div>
  );
}
