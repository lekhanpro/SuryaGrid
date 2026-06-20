"use client";
import { useState } from "react";
import { predict } from "@/lib/api";
import type { PredictResult } from "@/lib/types";

const SCENARIOS = [
  { label: "Clear Sky", irradiance: 950, cloud: 5, temp: 25 },
  { label: "Partly Cloudy", irradiance: 700, cloud: 40, temp: 32 },
  { label: "Overcast", irradiance: 350, cloud: 75, temp: 30 },
  { label: "Heavy Cloud", irradiance: 100, cloud: 90, temp: 28 },
];

export default function Predictions() {
  const [results, setResults] = useState<(PredictResult & { label: string })[]>([]);
  const [loading, setLoading] = useState(false);

  const runScenarios = async () => {
    setLoading(true);
    const batch: (PredictResult & { label: string })[] = [];
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
      batch.push({ ...r, label: s.label });
    }
    setResults(batch);
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Scenario Analysis</h1>
      <p className="text-sm text-gray-500 mb-6">Compare DSM outcomes across different weather conditions</p>
      <button onClick={runScenarios} disabled={loading} className="px-5 py-2 bg-blue-600 text-white rounded font-medium mb-6 hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Analyzing..." : "Run Weather Scenarios"}
      </button>

      {results.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Scenario</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Predicted MW</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Deviation %</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Penalty Status</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Penalty Cost</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.label}</td>
                  <td className="px-4 py-3 text-right">{r.predicted_generation_mw.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{r.deviation_percent.toFixed(1)}%</td>
                  <td className={`px-4 py-3 text-center font-semibold ${r.penalty_status === "PENALTY_RISK" ? "text-red-600" : "text-green-600"}`}>
                    {r.penalty_status === "PENALTY_RISK" ? "PENALTY RISK" : "NO PENALTY"}
                  </td>
                  <td className="px-4 py-3 text-right">{r.estimated_penalty_cost > 0 ? `\u20B9${r.estimated_penalty_cost.toLocaleString()}` : "\u2014"}</td>
                  <td className={`px-4 py-3 text-center font-semibold ${
                    r.fuzzy_risk_level === "CRITICAL" ? "text-red-700" :
                    r.fuzzy_risk_level === "HIGH" ? "text-orange-600" :
                    r.fuzzy_risk_level === "MEDIUM" ? "text-yellow-600" : "text-green-600"
                  }`}>{r.fuzzy_risk_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
