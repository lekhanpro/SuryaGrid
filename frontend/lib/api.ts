import type { ApiResponse, Site, PredictRequest, PredictResult, TimelineData, SummaryData } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json: ApiResponse<T> = await res.json();
  if (!json.success) throw new Error(json.error || "Unknown error");
  return json.data;
}

export async function getHealth() {
  return fetchJson<any>(`${BASE}/health`);
}

export async function createSite(data: Partial<Site>) {
  return fetchJson<Site>(`${BASE}/sites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getSites() {
  return fetchJson<Site[]>(`${BASE}/sites`);
}

export async function predict(data: PredictRequest) {
  return fetchJson<PredictResult>(`${BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getTimeline(siteId: string, params?: Record<string, string | number>) {
  const qs = new URLSearchParams();
  if (params) Object.entries(params).forEach(([k, v]) => qs.set(k, String(v)));
  return fetchJson<TimelineData>(`${BASE}/timeline/${siteId}?${qs}`);
}

export async function getSummary(siteId: string, params?: Record<string, string | number>) {
  const qs = new URLSearchParams();
  if (params) Object.entries(params).forEach(([k, v]) => qs.set(k, String(v)));
  return fetchJson<SummaryData>(`${BASE}/summary/${siteId}?${qs}`);
}
