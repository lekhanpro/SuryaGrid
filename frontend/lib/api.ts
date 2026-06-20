import type { ApiResponse, Site, PredictRequest, PredictResult, TimelineData, SummaryData } from "./types";
import { mockPredict, mockTimeline, mockSummary } from "./mock";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const IS_STATIC = typeof window !== "undefined" && (window.location.hostname.includes("github.io") || !process.env.NEXT_PUBLIC_API_URL);

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json: ApiResponse<T> = await res.json();
  if (!json.success) throw new Error(json.error || "Unknown error");
  return json.data;
}

export async function getHealth() {
  if (IS_STATIC) return { status: "healthy", version: "0.1.0", environment: "demo" };
  return fetchJson<any>(`${BASE}/health`);
}

export async function createSite(data: Partial<Site>) {
  if (IS_STATIC) return { id: "demo-site", ...data, created_at: new Date().toISOString() } as Site;
  return fetchJson<Site>(`${BASE}/sites`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
}

export async function getSites() {
  if (IS_STATIC) return [] as Site[];
  return fetchJson<Site[]>(`${BASE}/sites`);
}

export async function predict(data: PredictRequest): Promise<PredictResult> {
  if (IS_STATIC) return mockPredict(data);
  return fetchJson<PredictResult>(`${BASE}/predict`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
}

export async function getTimeline(siteId: string, params?: Record<string, string | number>): Promise<TimelineData> {
  if (IS_STATIC) return mockTimeline(params?.capacity_mw as number || 50, params?.scheduled_mw as number || 35);
  const qs = new URLSearchParams();
  if (params) Object.entries(params).forEach(([k, v]) => qs.set(k, String(v)));
  return fetchJson<TimelineData>(`${BASE}/timeline/${siteId}?${qs}`);
}

export async function getSummary(siteId: string, params?: Record<string, string | number>): Promise<SummaryData> {
  if (IS_STATIC) return mockSummary(params?.capacity_mw as number || 50, params?.scheduled_mw as number || 35);
  const qs = new URLSearchParams();
  if (params) Object.entries(params).forEach(([k, v]) => qs.set(k, String(v)));
  return fetchJson<SummaryData>(`${BASE}/summary/${siteId}?${qs}`);
}
