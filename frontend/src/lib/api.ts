import axios from "axios";

function getApiBase(): string {
  if (typeof window === "undefined") {
    // SSR fallback: if the frontend is rendered on the server, target the
    // configured backend host or localhost backend.
    return (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";
  }

  // In the browser, prefer the configured API host; otherwise use a relative
  // path so Next.js rewrites /api requests to the backend during local dev.
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL + "/api/v1";
  }

  return "/api/v1";
}

const api = axios.create({
  baseURL: getApiBase(),
});

api.interceptors.request.use((config) => {
  // Re-derive base URL on every request so it's always correct
  config.baseURL = getApiBase();
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    // Only redirect on 401 for auth-required endpoints
    if (error.response?.status === 401 && typeof window !== "undefined") {
      const url = error.config?.url ?? "";
      const isAuthRequired = url.includes("/portfolio") || url.includes("/trading") || url.includes("/admin");
      if (isAuthRequired) {
        localStorage.clear();
        window.location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
