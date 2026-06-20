"use client";
import { useState } from "react";
import MetricCard from "@/components/cards/MetricCard";
import PenaltyStatusCard from "@/components/cards/PenaltyStatusCard";
import { predict } from "@/lib/api";
import type { PredictResult } from "@/lib/types";

export default function Dashboard() {
  const [result, setResult] = useState<PredictResult | null>(null);
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

  const fieldLabels: Record<string, string> = {
    solar_capacity_mw: "Solar Capacity (MW)",
    irradiance_w_m2: "Irradiance (W/m\u00B2)",
    cloud_cover_percent: "Cloud Cover (%)",
    temperature_c: "Temperature (\u00B0C)",
    scheduled_generation_mw: "Scheduled Generation (MW)",
    allowed_dsm_threshold_percent: "DSM Threshold (%)",
    penalty_rate_per_mw: "Penalty Rate (\u20B9/MW)",
  };

  const runPrediction = async () => {
    setLoading(true);
    try {
      const res = await predict({ site_id: "primary-site", ...form });
      setResult(res);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Solar Generation Monitoring</h1>
      <p className="text-sm text-gray-500 mb-6">DSM deviation analysis and penalty risk assessment</p>

      {/* Input Panel */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="font-semibold mb-4 text-gray-700">Site &amp; Weather Parameters</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(form).map(([key, val]) => (
            <div key={key}>
              <label className="text-xs text-gray-500 block mb-1">{fieldLabels[key] || key}</label>
              <input
                type="number"
                step="any"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={val}
                onChange={(e) => setForm({ ...form, [key]: parseFloat(e.target.value) || 0 })}
              />
            </div>
          ))}
        </div>
        <button
          onClick={runPrediction}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "Analyzing..." : "Run Prediction"}
        </button>
      </div>

      {/* Results */}
      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Predicted Generation" value={result.predicted_generation_mw.toFixed(2)} unit="MW" color="blue" />
            <MetricCard title="Scheduled Generation" value={result.scheduled_generation_mw.toFixed(2)} unit="MW" color="purple" />
            <MetricCard title="Deviation" value={result.deviation_percent.toFixed(1)} unit="%" color="yellow" />
            <MetricCard title="Confidence" value={(result.confidence_score * 100).toFixed(0)} unit="%" color="green" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <PenaltyStatusCard status={result.penalty_status} cost={result.estimated_penalty_cost} riskLevel={result.fuzzy_risk_level} />
            <MetricCard title="DSM Risk Score" value={result.fuzzy_risk_score.toFixed(1)} unit="/100" color="red" />
            <MetricCard title="Deviation" value={result.deviation_mw.toFixed(3)} unit="MW" color="yellow" />
          </div>

          <div className="bg-white rounded-lg shadow p-5">
            <h3 className="font-semibold mb-2 text-gray-700">Analysis</h3>
            <p className="text-gray-700 leading-relaxed">{result.explanation}</p>
          </div>
        </>
      )}
    </div>
  );
}
