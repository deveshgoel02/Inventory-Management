import axios from "axios";

// In dev, Vite proxies "/api" to the local backend (see vite.config.ts), so
// the relative path works with no configuration. In production the
// frontend (Vercel) and backend (Render) are different origins, so
// VITE_API_BASE_URL must be set at build time to the backend's full URL,
// e.g. https://shoexpress-api.onrender.com/api.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

const TOKEN_KEY = "shoexpress_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setToken(null);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Downloads a file from an authenticated API endpoint.
 *
 * A plain `<a href="/api/...">` does NOT work for these routes: every
 * export endpoint requires a Bearer JWT, and a normal browser navigation
 * (clicking a link) never attaches the token from localStorage the way
 * axios's request interceptor does. So we fetch the file as a blob through
 * `api` (which does attach the header), then hand the browser a
 * short-lived object URL to save — the actual download still happens
 * natively, just triggered programmatically instead of via a real link.
 */
export async function downloadFile(path: string, filename: string, params?: Record<string, string>) {
  const response = await api.get(path, { params, responseType: "blob" });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg ?? JSON.stringify(d)).join("; ");
    }
    return error.message;
  }
  return String(error);
}
