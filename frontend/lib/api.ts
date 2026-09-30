import type { Country, Notification, QueryResponse, Trust, User } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  demoUsers: () => call<User[]>("/api/auth/demo-users", null),
  login: (user_id: string) =>
    call<{ access_token: string; user: User }>("/api/auth/demo-login", null, {
      method: "POST", body: JSON.stringify({ user_id }),
    }),
  query: (token: string, query: string, country: Country) =>
    call<QueryResponse>("/api/query", token, { method: "POST", body: JSON.stringify({ query, country }) }),
  flag: (token: string, docId: string, country: Country, channel: string, text: string) =>
    call<{ score_before: number; trust: Trust; notified: string[] }>(
      `/api/documents/${encodeURIComponent(docId)}/conflicts`, token,
      { method: "POST", body: JSON.stringify({ country, channel, text }) }),
  verify: (token: string, docId: string, country: Country) =>
    call<{ score_before: number; trust: Trust }>(
      `/api/documents/${encodeURIComponent(docId)}/verify`, token,
      { method: "POST", body: JSON.stringify({ country, reviewed_contradictions: true }) }),
  notifications: (token: string) => call<Notification[]>("/api/notifications", token),
  markRead: (token: string, id: string) =>
    call<{ ok: boolean }>(`/api/notifications/${encodeURIComponent(id)}/read`, token, { method: "POST" }),
};
