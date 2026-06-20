"use client";
import { useState } from "react";
import SolarPanel3D from "@/components/svg/SolarPanel3D";
import RiskGauge3D from "@/components/svg/RiskGauge3D";
import EnergyFlow3D from "@/components/svg/EnergyFlow3D";
import MiniTimeline from "@/components/charts/MiniTimeline";
import { predict, getTimeline } from "@/lib/api";
import type { PredictResult, TimelineEntry } from "@/lib/types";

export default function Dashboard() {
  const [result, setResult] = useState<PredictResult | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    solar_capacity_mw: 50,
    irradiance_w_m2: 750,
    cloud_cover_percent: 40,
    temperature_c: 32,
    scheduled_generation_mw: 35,
    allowed_dsm_threshold_percent: 10,
    penalty_rate_per_mw: 15000,
  });

  const fields: { key: keyof typeof form; label: string; unit: string }[] = [
    { key: "solar_capacity_mw", label: "Capacity", unit: "MW" },
    { key: "irradiance_w_m2", label: "Irradiance", unit: "W/m\u00B2" },
    { key: "cloud_cover_percent", label: "Cloud", unit: "%" },
    { key: "temperature_c", label: "Temp", unit: "\u00B0C" },
    { key: "scheduled_generation_mw", label: "Scheduled", unit: "MW" },
    { key: "allowed_dsm_threshold_percent", label: "Threshold", unit: "%" },
    { key: "penalty_rate_per_mw", label: "Penalty Rate", unit: "\u20B9" },
  ];

  const run = async () => {
    setLoading(true);
    try {
      const [pred, tl] = await Promise.all([
        predict({ site_id: "primary-site", ...form }),
        getTimeline("primary-site", { seed: 42, capacity_mw: form.solar_capacity_mw, scheduled_mw: form.scheduled_generation_mw }),
      ]);
      setResult(pred);
      setTimeline(tl.timeline);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  const genPct = result ? (result.predicted_generation_mw / form.solar_capacity_mw) * 100 : 0;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Solar Generation Monitor</h1>
        <p className="text-white/40 mt-1">Real-time DSM deviation analysis and penalty risk assessment</p>
      </div>

      {/* Input Panel */}
      <div className="glass-card p-6 mb-8">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-bold text-white/70 uppercase tracking-wider">Parameters</h2>
          <button onClick={run} disabled={loading} className="btn-primary">
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Analyzing
              </span>
            ) : "Run Prediction"}
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">{f.label} <span className="text-white/20">({f.unit})</span></label>
              <input
                type="number" step="any" className="input-field"
                value={form[f.key]}
                onChange={(e) => setForm({ ...form, [f.key]: parseFloat(e.target.value) || 0 })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Top visual row: Solar Panel + Metrics + Risk Gauge */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Solar Panel 3D */}
            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <SolarPanel3D generation={genPct} className="w-full max-w-[220px] animate-float" />
            </div>

            {/* Key Metrics */}
            <div className="glass-card p-5 flex flex-col justify-between">
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Predicted Generation</div>
                  <div className="text-3xl font-bold text-white mt-1">{result.predicted_generation_mw.toFixed(2)} <span className="text-lg text-white/40">MW</span></div>
                </div>
                <div>
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Confidence</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full" style={{ width: `${result.confidence_score * 100}%` }} />
                    </div>
                    <span className="text-sm font-bold text-cyan-300">{(result.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className="pt-3 border-t border-white/5">
                  <div className={`text-xl font-bold ${result.penalty_status === "PENALTY_RISK" ? "text-red-400" : "text-emerald-400"}`}>
                    {result.penalty_status === "PENALTY_RISK" ? "PENALTY RISK" : "NO PENALTY"}
                  </div>
                  {result.estimated_penalty_cost > 0 && (
                    <div className="text-sm text-red-300/70 mt-1">{"\u20B9"}{result.estimated_penalty_cost.toLocaleString()} estimated</div>
                  )}
                </div>
              </div>
            </div>

            {/* Risk Gauge */}
            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="text-[10px] text-white/40 uppercase tracking-wider mb-2">DSM Risk Score</div>
              <RiskGauge3D score={result.fuzzy_risk_score} level={result.fuzzy_risk_level} className="w-full max-w-[180px]" />
            </div>
          </div>

          {/* Energy Flow */}
          <div className="glass-card p-5 mb-6">
            <div className="text-[10px] text-white/40 uppercase tracking-wider mb-3">Energy Flow Comparison</div>
            <EnergyFlow3D
              predictedMW={result.predicted_generation_mw}
              scheduledMW={result.scheduled_generation_mw}
              capacityMW={form.solar_capacity_mw}
              isPenalty={result.penalty_status === "PENALTY_RISK"}
              className="w-full"
            />
          </div>

          {/* Deviation + Explanation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="glass-card p-5">
              <div className="text-[10px] text-white/40 uppercase tracking-wider mb-3">Deviation Analysis</div>
              <div className="flex items-end gap-4">
                <div>
                  <div className="text-4xl font-bold text-white">{result.deviation_percent.toFixed(1)}<span className="text-lg text-white/40">%</span></div>
                  <div className="text-sm text-white/40">{result.deviation_mw.toFixed(3)} MW</div>
                </div>
                <div className="flex-1">
                  <div className="relative h-4 bg-white/5 rounded-full overflow-hidden">
                    <div className="absolute h-full w-px bg-white/30" style={{ left: `${Math.min(result.allowed_dsm_threshold_percent, 100)}%` }} />
                    <div className={`h-full rounded-full transition-all ${result.penalty_status === "PENALTY_RISK" ? "bg-gradient-to-r from-red-500 to-red-400" : "bg-gradient-to-r from-emerald-500 to-emerald-400"}`}
                      style={{ width: `${Math.min(result.deviation_percent, 100)}%` }} />
                  </div>
                  <div className="flex justify-between mt-1 text-[10px] text-white/30">
                    <span>0%</span>
                    <span>Threshold: {result.allowed_dsm_threshold_percent}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card p-5">
              <div className="text-[10px] text-white/40 uppercase tracking-wider mb-3">AI Analysis</div>
              <p className="text-white/70 text-sm leading-relaxed">{result.explanation}</p>
            </div>
          </div>

          {/* Timeline */}
          {timeline.length > 0 && <MiniTimeline data={timeline} maxMW={form.solar_capacity_mw} />}
        </>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="glass-card text-center py-20">
          <SolarPanel3D generation={0} className="w-48 mx-auto mb-6 opacity-50" />
          <h3 className="text-lg font-medium text-white/60">Ready to Analyze</h3>
          <p className="text-white/30 mt-1 text-sm">Configure parameters and run a prediction</p>
        </div>
      )}
    </div>
  );
}
