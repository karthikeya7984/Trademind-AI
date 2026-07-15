import { create } from "zustand";
import { persist } from "zustand/middleware";
import api from "@/lib/api";

interface User {
  id: string;
  name: string;
  email: string;
  profile_image?: string;
  account_type: string;
  role: string;
  is_verified: boolean;
  is_suspended: boolean;
  auth_provider: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

const saveTokens = (access_token: string, refresh_token: string) => {
  localStorage.setItem("access_token", access_token);
  localStorage.setItem("refresh_token", refresh_token);
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await api.post("/auth/login", { email, password });
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true });
      },

      register: async (name, email, password) => {
        const { data } = await api.post("/auth/register", { name, email, password });
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, isAuthenticated: false });
        window.location.href = "/";
      },

      fetchMe: async () => {
        try {
          const { data } = await api.get("/users/me");
          set({ user: data, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },
    }),
    {
      name: "auth-store",
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
);
