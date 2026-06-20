"use client";
import { useState } from "react";
import MetricCard from "@/components/cards/MetricCard";
import PenaltyStatusCard from "@/components/cards/PenaltyStatusCard";
import DeviationBar from "@/components/charts/DeviationBar";
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
    { key: "solar_capacity_mw", label: "Solar Capacity", unit: "MW" },
    { key: "irradiance_w_m2", label: "Irradiance", unit: "W/m\u00B2" },
    { key: "cloud_cover_percent", label: "Cloud Cover", unit: "%" },
    { key: "temperature_c", label: "Temperature", unit: "\u00B0C" },
    { key: "scheduled_generation_mw", label: "Scheduled Gen.", unit: "MW" },
    { key: "allowed_dsm_threshold_percent", label: "DSM Threshold", unit: "%" },
    { key: "penalty_rate_per_mw", label: "Penalty Rate", unit: "\u20B9/MW" },
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
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Solar Generation Monitor</h1>
        <p className="text-gray-500 mt-1">Real-time DSM deviation analysis and penalty risk assessment</p>
      </div>

      {/* Input Panel */}
      <div className="card mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-700">Site Parameters</h2>
          <button onClick={run} disabled={loading} className="btn-primary">
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Analyzing...
              </span>
            ) : "Run Prediction"}
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="text-xs text-gray-500 block mb-1">{f.label} <span className="text-gray-400">({f.unit})</span></label>
              <input
                type="number"
                step="any"
                className="input-field"
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
          {/* Key Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Predicted Generation" value={result.predicted_generation_mw.toFixed(2)} unit="MW" color="blue" subtitle="Current forecast" />
            <MetricCard title="Scheduled Generation" value={result.scheduled_generation_mw.toFixed(2)} unit="MW" color="purple" subtitle="Agreement MW" />
            <MetricCard title="Deviation" value={result.deviation_mw.toFixed(3)} unit="MW" color={result.penalty_status === "PENALTY_RISK" ? "red" : "green"} subtitle={`${result.deviation_percent.toFixed(1)}% from schedule`} />
            <MetricCard title="Confidence" value={(result.confidence_score * 100).toFixed(0)} unit="%" color="green" subtitle="Forecast reliability" />
          </div>

          {/* Status + Deviation Visual */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <PenaltyStatusCard status={result.penalty_status} cost={result.estimated_penalty_cost} riskLevel={result.fuzzy_risk_level} riskScore={result.fuzzy_risk_score} />
            <DeviationBar deviationPercent={result.deviation_percent} threshold={result.allowed_dsm_threshold_percent} />
          </div>

          {/* Timeline Chart */}
          {timeline.length > 0 && (
            <div className="mb-6">
              <MiniTimeline data={timeline} maxMW={form.solar_capacity_mw} />
            </div>
          )}

          {/* Explanation */}
          <div className="card">
            <div className="card-header">Analysis Summary</div>
            <p className="text-gray-700 leading-relaxed mt-2">{result.explanation}</p>
            <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-gray-100 text-sm">
              <div><span className="text-gray-500">Irradiance:</span> <span className="font-medium">{form.irradiance_w_m2} W/m²</span></div>
              <div><span className="text-gray-500">Cloud Cover:</span> <span className="font-medium">{form.cloud_cover_percent}%</span></div>
              <div><span className="text-gray-500">Temperature:</span> <span className="font-medium">{form.temperature_c}°C</span></div>
            </div>
          </div>
        </>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="card text-center py-16">
          <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-600">Ready to Analyze</h3>
          <p className="text-gray-400 mt-1">Configure site parameters above and run a prediction</p>
        </div>
      )}
    </div>
  );
}
