/**
 * Client-side approximation of the backend pipeline for the static (GitHub Pages)
 * demo where no API is reachable. The live app always uses the real backend
 * (Open-Meteo + pvlib); this is a simplified bell-curve stand-in with the same
 * response shape so the UI renders without a server.
 */
import type {
  PredictRequest,
  PredictResult,
  TimelineData,
  TimelineEntry,
  SummaryData,
} from "./types";

function genFromGhi(capacity: number, ghi: number, temp: number): number {
  const dc = capacity * (ghi / 1000) * (1 - Math.max(0, temp - 25) * 0.0035);
  return Math.max(0, Math.min(capacity, dc * 0.96));
}

function risk(devPct: number, threshold: number, conf: number) {
  const band = Math.max(threshold, 1);
  const breach = Math.max(0, devPct - threshold) / band;
  const score = Math.max(0, Math.min(100, breach * 60 + (1 - conf) * 40));
  const level = score < 25 ? "LOW" : score < 50 ? "MEDIUM" : score < 75 ? "HIGH" : "CRITICAL";
  return { risk_score: +score.toFixed(2), risk_level: level };
}

export function mockPredict(req: PredictRequest): PredictResult {
  const predicted = genFromGhi(req.capacity_mw, req.ghi_w_m2, req.temperature_c);
  const threshold = req.allowed_dsm_threshold_percent || 10;
  const rate = req.penalty_rate_per_mwh || 12000;
  const sched = req.scheduled_generation_mw;
  const devMw = Math.abs(predicted - sched);
  const devPct = sched > 0 ? (devMw / sched) * 100 : 0;
  const status = sched <= 0 ? "INVALID_SCHEDULE" : devPct > threshold ? "PENALTY_RISK" : "NO_PENALTY";
  const allowedMw = sched * (threshold / 100);
  const cost = status === "PENALTY_RISK" ? Math.max(0, devMw - allowedMw) * rate : 0;
  const conf = Math.max(0.4, Math.min(0.99, 1 - 0.35 * (req.cloud_cover_percent / 100)));
  const r = risk(devPct, threshold, conf);

  const explanation =
    status === "PENALTY_RISK"
      ? `Penalty risk: forecast ${predicted.toFixed(2)} MW deviates ${devPct.toFixed(1)}% from the scheduled ${sched.toFixed(2)} MW.`
      : status === "INVALID_SCHEDULE"
      ? "Schedule is zero or negative, so no DSM deviation can be assessed."
      : `Within band: forecast ${predicted.toFixed(2)} MW tracks the scheduled ${sched.toFixed(2)} MW.`;

  return {
    timestamp: new Date().toISOString(),
    ghi_w_m2: req.ghi_w_m2,
    poa_w_m2: req.ghi_w_m2,
    cloud_cover_percent: req.cloud_cover_percent,
    temperature_c: req.temperature_c,
    predicted_generation_mw: +predicted.toFixed(3),
    energy_mwh: +predicted.toFixed(3),
    scheduled_generation_mw: sched,
    deviation_mw: +devMw.toFixed(3),
    deviation_percent: +devPct.toFixed(2),
    allowed_dsm_threshold_percent: threshold,
    penalty_status: status,
    estimated_penalty_cost: +cost.toFixed(2),
    ...r,
    confidence_score: +conf.toFixed(2),
    explanation,
    capacity_mw: req.capacity_mw,
  };
}

function buildTimeline(capacity: number): TimelineEntry[] {
  const rate = 12000;
  const threshold = 10;
  const out: TimelineEntry[] = [];
  for (let h = 0; h < 24; h++) {
    const day = h >= 6 && h <= 18;
    const bell = day ? Math.sin((Math.PI * (h - 6)) / 12) : 0;
    const ghiClear = 950 * bell;
    const cloud = day ? 25 + 30 * Math.abs(Math.sin(h * 0.7)) : 0;
    const ghiActual = ghiClear * (1 - (cloud / 100) * 0.6);
    const temp = 26 + 10 * bell;
    const sched = +genFromGhi(capacity, ghiClear, temp).toFixed(3);
    const predicted = +genFromGhi(capacity, ghiActual, temp).toFixed(3);
    const devMw = Math.abs(predicted - sched);
    const devPct = sched > 0 ? (devMw / sched) * 100 : 0;
    const status = sched <= 0 ? "INVALID_SCHEDULE" : devPct > threshold ? "PENALTY_RISK" : "NO_PENALTY";
    const allowedMw = sched * (threshold / 100);
    const cost = status === "PENALTY_RISK" ? Math.max(0, devMw - allowedMw) * rate : 0;
    const conf = Math.max(0.4, Math.min(0.99, 1 - 0.35 * (cloud / 100)));
    const r = risk(devPct, threshold, conf);
    out.push({
      timestamp: `2026-06-25T${String(h).padStart(2, "0")}:00:00+05:30`,
      ghi_w_m2: +ghiActual.toFixed(1),
      poa_w_m2: +ghiActual.toFixed(1),
      cloud_cover_percent: +cloud.toFixed(1),
      temperature_c: +temp.toFixed(1),
      predicted_generation_mw: predicted,
      energy_mwh: predicted,
      scheduled_generation_mw: sched,
      deviation_mw: +devMw.toFixed(3),
      deviation_percent: +devPct.toFixed(2),
      allowed_dsm_threshold_percent: threshold,
      penalty_status: status,
      estimated_penalty_cost: +cost.toFixed(2),
      confidence_score: +conf.toFixed(2),
      explanation: "",
      ...r,
    });
  }
  return out;
}

function summarize(timeline: TimelineEntry[], capacity: number): SummaryData {
  const predicted_energy = timeline.reduce((a, e) => a + e.energy_mwh, 0);
  const scheduled_energy = timeline.reduce((a, e) => a + e.scheduled_generation_mw, 0);
  return {
    intervals: timeline.length,
    daylight_intervals: timeline.filter((e) => e.predicted_generation_mw > 0.01).length,
    predicted_energy_mwh: +predicted_energy.toFixed(3),
    scheduled_energy_mwh: +scheduled_energy.toFixed(3),
    peak_generation_mw: +Math.max(...timeline.map((e) => e.predicted_generation_mw)).toFixed(3),
    penalty_intervals: timeline.filter((e) => e.penalty_status === "PENALTY_RISK").length,
    total_penalty_cost: +timeline.reduce((a, e) => a + e.estimated_penalty_cost, 0).toFixed(2),
    max_deviation_percent: +Math.max(...timeline.map((e) => e.deviation_percent)).toFixed(2),
    capacity_mw: capacity,
    provider: "demo",
  };
}

export function mockTimeline(params?: Record<string, string | number>): TimelineData {
  const capacity = Number(params?.capacity_mw) || 50;
  const timeline = buildTimeline(capacity);
  return {
    site_id: "demo",
    capacity_mw: capacity,
    provider: "demo",
    summary: summarize(timeline, capacity),
    timeline,
  };
}

export function mockSummary(params?: Record<string, string | number>): SummaryData {
  const capacity = Number(params?.capacity_mw) || 50;
  return summarize(buildTimeline(capacity), capacity);
}
