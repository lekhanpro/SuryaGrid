// SuryaGrid AI API client.
//
// No silent faking: every call hits the real backend and throws on failure.
// Pages detect offline state via probeBackend() and show a clear banner; sample
// data is only ever shown behind an explicit, clearly-labelled "Offline Preview".

import type {
  ApiResponse,
  Site,
  PredictRequest,
  PredictResult,
  TimelineData,
  SummaryData,
  WeatherData,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch (e: any) {
    throw new ApiError(`Cannot reach backend at ${API_BASE}: ${e?.message || e}`);
  }
  if (!res.ok) throw new ApiError(`HTTP ${res.status} for ${path}`, res.status);
  const json: ApiResponse<T> = await res.json();
  if (json && json.success === false) {
    throw new ApiError(json.message || json.error || "Request failed");
  }
  return (json?.data ?? (json as unknown)) as T;
}

function qs(params?: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
    });
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ---- Backend status ----
export async function probeBackend(): Promise<{ online: boolean; version?: string; data?: any }> {
  try {
    const h = await apiFetch<any>("/health");
    return { online: true, version: h?.version, data: h };
  } catch {
    return { online: false };
  }
}

export async function getHealth() {
  return apiFetch<any>("/health");
}

export async function getSystemStatus() {
  return apiFetch<any>("/system/status");
}

// ---- Sites ----
export async function createSite(data: Partial<Site>) {
  return apiFetch<Site>("/sites", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
export async function getSites() {
  return apiFetch<Site[]>("/sites");
}

// ---- Sources ----
export async function getSources(type?: string) {
  return apiFetch<any>(`/sources${qs({ type })}`);
}
export async function getSource(id: string) {
  return apiFetch<any>(`/sources/${id}`);
}
export async function getDataSourcesStatus() {
  return apiFetch<any>("/data-sources/status");
}

// ---- Weather ----
export async function getWeather(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<WeatherData>(`/weather/${siteId}${qs(params)}`);
}
export async function weatherFetch(params: Record<string, string | number>) {
  return apiFetch<any>(`/weather/fetch${qs(params)}`, { method: "POST" });
}
export async function weatherLatest(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/weather/latest/${siteId}${qs(params)}`);
}
export async function weatherForecast(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/weather/forecast/${siteId}${qs(params)}`);
}
export async function getWeatherProviders() {
  return apiFetch<any>("/weather/providers/status");
}

// ---- ML ----
export async function getModelStatus() {
  return apiFetch<any>("/ml/model/status");
}
export async function ingestKaggle() {
  return apiFetch<any>("/ml/datasets/ingest-kaggle", { method: "POST" });
}
export async function buildAugmented(params: Record<string, string | number>) {
  return apiFetch<any>(`/ml/datasets/build-augmented${qs(params)}`, { method: "POST" });
}
export async function trainModel(params: Record<string, string | number>) {
  return apiFetch<any>(`/ml/train${qs(params)}`, { method: "POST" });
}
export async function mlPredict(body: Record<string, any>) {
  return apiFetch<any>("/ml/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---- Locations & substations ----
export async function getLocations() {
  return apiFetch<any>("/locations");
}
export async function getAvailableLocations() {
  return apiFetch<any>("/locations/available");
}
export async function getSubstations(limit = 500) {
  return apiFetch<any>(`/substations${qs({ limit })}`);
}
export async function importSubstations(body: {
  csv_text?: string;
  latitude?: number;
  longitude?: number;
  radius_km?: number;
}) {
  return apiFetch<any>("/substations/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function getNearestSubstation(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/substations/nearest/${siteId}${qs(params)}`);
}
export async function getDataCoverage(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/sites/${siteId}/data-coverage${qs(params)}`);
}

// ---- DSM ----
export async function getRuleProfiles() {
  return apiFetch<any>("/dsm/rule-profiles");
}
export async function createRuleProfile(body: Record<string, any>) {
  return apiFetch<any>("/dsm/rule-profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function advancedDsmCheck(body: Record<string, any>) {
  return apiFetch<any>("/dsm/advanced-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---- Prediction / forecast ----
export async function predict(data: PredictRequest): Promise<PredictResult> {
  return apiFetch<PredictResult>("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
export async function predictSite(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/predict/${siteId}${qs(params)}`);
}
export async function getForecast(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/forecast/${siteId}${qs(params)}`);
}
export async function getTimeline(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<TimelineData>(`/timeline/${siteId}${qs(params)}`);
}
export async function getSummary(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<SummaryData>(`/summary/${siteId}${qs(params)}`);
}

// ---- Existing extras (energy / settlement / rl / karnataka) ----
import type { EnergyBalance, SettlementDay, RLRates, TrainingRun } from "./types";

export async function getEnergy(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<EnergyBalance>(`/energy/${siteId}${qs(params)}`);
}
export async function settleDay(siteId: string, params?: Record<string, string | number | boolean>) {
  return apiFetch<SettlementDay>(`/settle/day/${siteId}${qs(params)}`, { method: "POST" });
}
export async function getRLRates() {
  return apiFetch<RLRates>("/rl/rates");
}
export async function getRLRuns() {
  return apiFetch<TrainingRun[]>("/rl/runs");
}
export async function trainRL(params: Record<string, string | number | boolean>) {
  return apiFetch<any>(`/rl/train${qs(params)}`, { method: "POST" });
}
export async function getProfiles() {
  return apiFetch<Record<string, any>>("/consumption/profiles");
}
export async function seedKarnataka() {
  return apiFetch<any>("/karnataka/seed", { method: "POST" });
}
export async function getKarnatakaRegions() {
  return apiFetch<any>("/karnataka/regions");
}
export async function getBescomStatus() {
  return apiFetch<any>("/bescom/status");
}
export async function getKarnatakaDSM(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/dsm/karnataka/${siteId}${qs(params)}`, { method: "POST" });
}
export async function getCurrentWeather(siteId: string, params?: Record<string, string | number>) {
  return apiFetch<any>(`/weather/current/${siteId}${qs(params)}`);
}


// ---- Phase 1.7 agents (Bengaluru real-data models + provenance) ----
// Every response carries the provenance envelope (geography, production_ready,
// source_status, warnings). The UI shows these verbatim; it never fabricates status.
export async function getAgentsStatus() {
  return apiFetch<any>("/agents/status");
}
export async function getAgentsDataStatus() {
  return apiFetch<any>("/agents/data-status");
}
export async function agentSolarForecast(body: Record<string, any>) {
  return apiFetch<any>("/agents/solar/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function agentCloudRisk(body: Record<string, any>) {
  return apiFetch<any>("/agents/cloud/risk", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function agentDsmAssess(body: Record<string, any>) {
  return apiFetch<any>("/agents/dsm/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}


// ---- Substation-driven agent workflow ----
// A selected substation becomes the central context object flowing through
// weather -> solar -> cloud -> generation timeline -> DSM. Every response carries
// agent_trace + calculation_trace + provenance; missing real fields stay null
// (capacity_mva/district are unavailable in OSM and are never fabricated).
export async function getSubstationCatalog(limit = 1000) {
  return apiFetch<any>(`/substations/catalog${qs({ limit })}`);
}
export async function getSubstationContext(
  substationId: string,
  params?: Record<string, string | number>
) {
  return apiFetch<any>(`/substations/${encodeURIComponent(substationId)}${qs(params)}`);
}
export async function orchestrateSubstation(body: {
  substation_id: string;
  site_capacity_mw?: number | null;
  forecast_horizon_hours?: number;
  scheduled_generation_mw?: number | null;
  use_live_weather?: boolean;
  site_latitude?: number | null;
  site_longitude?: number | null;
}) {
  return apiFetch<any>("/orchestrate/substation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function substationDsmForecast(body: {
  substation_id: string;
  site_capacity_mw?: number | null;
  forecast_horizon_hours?: number;
  scheduled_generation_mw?: number | null;
  use_live_weather?: boolean;
}) {
  return apiFetch<any>("/dsm/forecast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
export async function getGenerationTimeline(params: {
  substation_id: string;
  site_capacity_mw?: number;
  forecast_horizon_hours?: number;
  allow_estimated?: boolean;
  use_live_weather?: boolean;
}) {
  return apiFetch<any>(`/generation/timeline${qs(params)}`);
}
