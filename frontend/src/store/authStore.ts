import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  name: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loginWithName: (name: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      loginWithName: (name: string) => {
        set({ user: { name }, isAuthenticated: true });
      },

      logout: () => {
        set({ user: null, isAuthenticated: false });
        window.location.href = "/";
      },
    }),
    {
      name: "auth-store",
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
);
