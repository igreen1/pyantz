import axios, { isAxiosError } from "axios";

// All requests are relative to the versioned API, e.g. `api.get("/jobs/get_all_jobs")`.
// In development Vite proxies `/api` to the server (see vite.config.ts).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api/v1.0",
  headers: {
    "Content-Type": "application/json",
  },
});

const TOKEN_KEY = "pyantz-api-token";

/**
 * The token the user gave for the api, kept for this tab only (not in
 * localStorage, which outlives it). It is only ever sent in a header.
 */
export const getToken = (): string | null => {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setToken = (token: string | null): void => {
  try {
    if (token === null) sessionStorage.removeItem(TOKEN_KEY);
    else sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // storage may be blocked; the token is then asked for on each reload
  }
};

let onUnauthorized: (() => void) | undefined;

/** Call this when the api turns a request down for a missing or wrong token. */
export const setUnauthorizedHandler = (handler: (() => void) | undefined) => {
  onUnauthorized = handler;
};

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.set("Authorization", `Bearer ${token}`);
  return config;
});

api.interceptors.response.use(undefined, (error: unknown) => {
  if (isAxiosError(error) && error.response?.status === 401) onUnauthorized?.();
  return Promise.reject(error);
});

/**
 * Get a message a person can read from a failed request.
 * Prefers the `detail` the server sent over the generic axios message.
 */
export const errorMessage = (error: unknown): string => {
  if (isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(String).join("; ");
    return error.message;
  }
  return error instanceof Error ? error.message : String(error);
};

/** The problems of a rejected config, when the server listed them. */
export const errorList = (error: unknown): string[] => {
  if (isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (Array.isArray(detail)) return detail.map(String);
  }
  return [errorMessage(error)];
};

export default api;
