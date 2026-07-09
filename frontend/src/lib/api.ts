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
    if (error.response?.status === 401 && typeof window !== "undefined") {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const base = getApiBase();
          const { data } = await axios.post(`${base}/auth/refresh`, { refresh_token: refresh });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api(error.config);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
