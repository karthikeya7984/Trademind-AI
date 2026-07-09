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
  pendingOtpEmail: string | null;
  login: (email: string, password: string) => Promise<{ otp_required: boolean; email: string } | void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: (code: string) => Promise<{ otp_required: boolean; email: string }>;
  verifyOtp: (email: string, otp: string) => Promise<void>;
  resendOtp: (email: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  setPendingOtpEmail: (email: string | null) => void;
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
      pendingOtpEmail: null,

      login: async (email, password) => {
        const { data } = await api.post("/auth/login", { email, password });
        // Daily OTP required — backend returns otp_required instead of tokens
        if (data.otp_required) {
          set({ pendingOtpEmail: data.email });
          return { otp_required: true, email: data.email };
        }
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true, pendingOtpEmail: null });
      },

      register: async (name, email, password) => {
        const { data } = await api.post("/auth/register", { name, email, password });
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true, pendingOtpEmail: null });
      },

      loginWithGoogle: async (code: string) => {
        const { data } = await api.post("/auth/google", { code });
        // Backend now returns { otp_required: true, email }
        if (data.otp_required) {
          set({ pendingOtpEmail: data.email });
          return { otp_required: true, email: data.email };
        }
        // Fallback: direct token (shouldn't happen but handled)
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true, pendingOtpEmail: null });
        return { otp_required: false, email: "" };
      },

      verifyOtp: async (email: string, otp: string) => {
        const { data } = await api.post("/auth/verify-otp", { email, otp });
        saveTokens(data.access_token, data.refresh_token);
        const me = await api.get("/users/me");
        set({ user: me.data, isAuthenticated: true, pendingOtpEmail: null });
      },

      resendOtp: async (email: string) => {
        await api.post("/auth/resend-otp", { email });
      },

      setPendingOtpEmail: (email) => set({ pendingOtpEmail: email }),

      logout: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, isAuthenticated: false, pendingOtpEmail: null });
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
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated, pendingOtpEmail: s.pendingOtpEmail }),
    }
  )
);
