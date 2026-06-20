"use client";
import { useState } from "react";
import { predict } from "@/lib/api";
import type { PredictResult } from "@/lib/types";

const SCENARIOS = [
  { label: "Clear Sky", desc: "Optimal conditions", irradiance: 950, cloud: 5, temp: 25, icon: "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" },
  { label: "Partly Cloudy", desc: "Moderate output", irradiance: 700, cloud: 40, temp: 32, icon: "M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.209-.563-.372-.902-.372H13.5" },
  { label: "Overcast", desc: "Significant losses", irradiance: 350, cloud: 75, temp: 30, icon: "M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" },
  { label: "Storm", desc: "Minimal generation", irradiance: 100, cloud: 90, temp: 28, icon: "M11.412 15.655L9.75 21.75l3.745-4.012M9.257 13.5H3.75l2.659-2.849m2.048-2.194L14.25 2.25 12 10.5h8.25l-4.707 5.043" },
];

export default function Predictions() {
  const [results, setResults] = useState<(PredictResult & { label: string; desc: string })[]>([]);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    const batch: (PredictResult & { label: string; desc: string })[] = [];
    for (const s of SCENARIOS) {
      const r = await predict({
        site_id: "primary-site",
        solar_capacity_mw: 50,
        irradiance_w_m2: s.irradiance,
        cloud_cover_percent: s.cloud,
        temperature_c: s.temp,
        scheduled_generation_mw: 35,
        allowed_dsm_threshold_percent: 10,
        penalty_rate_per_mw: 15000,
      });
      batch.push({ ...r, label: s.label, desc: s.desc });
    }
    setResults(batch);
    setLoading(false);
  };

  const riskBadge = (level: string) => {
    const cls: Record<string, string> = { LOW: "badge-green", MEDIUM: "badge-yellow", HIGH: "badge-orange", CRITICAL: "badge-red" };
    return <span className={`badge ${cls[level] || "badge-green"}`}>{level}</span>;
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Scenario Analysis</h1>
        <p className="text-gray-500 mt-1">Compare DSM outcomes across different weather conditions</p>
      </div>

      {/* Scenario Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {SCENARIOS.map((s, i) => (
          <div key={i} className="card text-center">
            <svg className="w-8 h-8 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d={s.icon} />
            </svg>
            <div className="font-medium text-sm">{s.label}</div>
            <div className="text-xs text-gray-400">{s.irradiance} W/m² · {s.cloud}% cloud</div>
          </div>
        ))}
      </div>

      <button onClick={run} disabled={loading} className="btn-primary mb-8">
        {loading ? "Analyzing Scenarios..." : "Run All Scenarios"}
      </button>

      {results.length > 0 && (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-5 py-3 text-left font-medium text-gray-600">Scenario</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">Predicted</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">Deviation</th>
                <th className="px-5 py-3 text-center font-medium text-gray-600">Status</th>
                <th className="px-5 py-3 text-right font-medium text-gray-600">Penalty Cost</th>
                <th className="px-5 py-3 text-center font-medium text-gray-600">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="font-medium">{r.label}</div>
                    <div className="text-xs text-gray-400">{r.desc}</div>
                  </td>
                  <td className="px-5 py-4 text-right font-mono">{r.predicted_generation_mw.toFixed(2)} MW</td>
                  <td className="px-5 py-4 text-right font-mono">{r.deviation_percent.toFixed(1)}%</td>
                  <td className="px-5 py-4 text-center">
                    <span className={`badge ${r.penalty_status === "PENALTY_RISK" ? "badge-red" : "badge-green"}`}>
                      {r.penalty_status === "PENALTY_RISK" ? "PENALTY" : "OK"}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right font-mono">
                    {r.estimated_penalty_cost > 0 ? `\u20B9${r.estimated_penalty_cost.toLocaleString()}` : "\u2014"}
                  </td>
                  <td className="px-5 py-4 text-center">{riskBadge(r.fuzzy_risk_level)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
