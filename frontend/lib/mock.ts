/**
 * Client-side mock of the Phase 1 prediction engine for GitHub Pages static demo.
 * Same formulas as backend agents.
 */
import type { PredictRequest, PredictResult, TimelineData, SummaryData, TimelineEntry } from "./types";

function predictGeneration(capacity: number, irradiance: number, cloud: number, temp: number) {
  const base = capacity * (irradiance / 1000);
  const cloudLoss = 1 - (cloud / 100) * 0.75;
  const tempLoss = 1 - Math.max(0, temp - 25) * 0.005;
  return Math.max(0, Math.min(capacity, base * cloudLoss * tempLoss));
}

function fuzzyRisk(devPct: number, cloud: number, irr: number, conf: number) {
  let score = devPct * 0.5 + cloud * 0.2;
  if (irr < 300) score += 20;
  if (conf < 0.6) score += 15;
  score = Math.max(0, Math.min(100, score));
  const level = score < 25 ? "LOW" : score < 50 ? "MEDIUM" : score < 75 ? "HIGH" : "CRITICAL";
  return { fuzzy_risk_score: +score.toFixed(2), fuzzy_risk_level: level };
}

export function mockPredict(req: PredictRequest): PredictResult {
  const predicted = predictGeneration(req.solar_capacity_mw, req.irradiance_w_m2, req.cloud_cover_percent, req.temperature_c);
  const devMw = Math.abs(predicted - req.scheduled_generation_mw);
  const devPct = req.scheduled_generation_mw > 0 ? (devMw / req.scheduled_generation_mw) * 100 : 0;
  const threshold = req.allowed_dsm_threshold_percent || 10;
  const penaltyStatus = devPct > threshold ? "PENALTY_RISK" : "NO_PENALTY";
  const cost = penaltyStatus === "PENALTY_RISK" ? devMw * (req.penalty_rate_per_mw || 15000) : 0;
  const conf = req.cloud_cover_percent > 70 ? 0.8 : req.irradiance_w_m2 < 200 ? 0.85 : 1.0;
  const risk = fuzzyRisk(devPct, req.cloud_cover_percent, req.irradiance_w_m2, conf);

  let explanation = penaltyStatus === "PENALTY_RISK"
    ? "Penalty risk detected because predicted generation is lower than scheduled generation."
    : "No penalty risk. Predicted generation is within the allowed DSM threshold.";
  if (req.cloud_cover_percent > 50) explanation += " High cloud cover reduced expected solar output.";

  return {
    site_id: req.site_id,
    predicted_generation_mw: +predicted.toFixed(3),
    scheduled_generation_mw: req.scheduled_generation_mw,
    deviation_mw: +devMw.toFixed(3),
    deviation_percent: +devPct.toFixed(2),
    allowed_dsm_threshold_percent: threshold,
    penalty_status: penaltyStatus,
    estimated_penalty_cost: +cost.toFixed(2),
    fuzzy_risk_score: risk.fuzzy_risk_score,
    fuzzy_risk_level: risk.fuzzy_risk_level,
    confidence_score: conf,
    explanation,
  };
}

export function mockTimeline(capacity: number, scheduledMw: number): TimelineData {
  const timeline: TimelineEntry[] = [];
  for (let i = 0; i < 48; i++) {
    const hour = i * 0.5;
    const irr = hour >= 6 && hour <= 18 ? 950 * Math.sin(Math.PI * (hour - 6) / 12) : 0;
    const cloud = 30 + Math.sin(hour * 0.5) * 15;
    const temp = 25 + 8 * Math.sin(Math.PI * (hour - 6) / 16);
    const sched = hour >= 6 && hour <= 18 ? capacity * Math.sin(Math.PI * (hour - 6) / 12) * 0.7 : scheduledMw;
    const actualSched = sched > 0 ? sched : scheduledMw;
    const pred = predictGeneration(capacity, irr, cloud, temp);
    const devMw = Math.abs(pred - actualSched);
    const devPct = actualSched > 0 ? (devMw / actualSched) * 100 : 100;
    const status = devPct > 10 ? "PENALTY_RISK" : "NO_PENALTY";
    const risk = fuzzyRisk(devPct, cloud, irr, 0.9);

    timeline.push({
      timestamp: `2026-06-20T${String(Math.floor(hour)).padStart(2, "0")}:${i % 2 === 0 ? "00" : "30"}:00+00:00`,
      irradiance_w_m2: +irr.toFixed(1),
      cloud_cover_percent: +cloud.toFixed(1),
      temperature_c: +temp.toFixed(1),
      predicted_generation_mw: +pred.toFixed(3),
      scheduled_generation_mw: +actualSched.toFixed(3),
      deviation_mw: +devMw.toFixed(3),
      deviation_percent: +devPct.toFixed(2),
      penalty_status: status,
      fuzzy_risk_level: risk.fuzzy_risk_level,
    });
  }
  return { site_id: "demo", date: "2026-06-20", timeline };
}

export function mockSummary(capacity: number, scheduledMw: number): SummaryData {
  const tl = mockTimeline(capacity, scheduledMw);
  let totalPred = 0, totalSched = 0, penalties = 0, maxDev = 0;
  for (const e of tl.timeline) {
    totalPred += e.predicted_generation_mw;
    totalSched += e.scheduled_generation_mw;
    if (e.penalty_status === "PENALTY_RISK") penalties++;
    maxDev = Math.max(maxDev, e.deviation_percent);
  }
  return {
    site_id: "demo", date: "2026-06-20", total_intervals: 48,
    total_predicted_mw: +totalPred.toFixed(3),
    total_scheduled_mw: +totalSched.toFixed(3),
    penalty_intervals: penalties,
    max_deviation_percent: +maxDev.toFixed(2),
    capacity_mw: capacity,
  };
}
