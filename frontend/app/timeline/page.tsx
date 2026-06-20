"use client";
import { useState } from "react";
import { getTimeline, getSummary } from "@/lib/api";
import type { TimelineData, SummaryData, TimelineEntry } from "@/lib/types";

export default function TimelinePage() {
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = { seed: 42, capacity_mw: 50, scheduled_mw: 35 };
      const [tl, sm] = await Promise.all([
        getTimeline("primary-site", params),
        getSummary("primary-site", params),
      ]);
      setTimeline(tl);
      setSummary(sm);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const riskColor = (level: string) => {
    switch (level) {
      case "LOW": return "text-green-600";
      case "MEDIUM": return "text-yellow-600";
      case "HIGH": return "text-orange-600";
      case "CRITICAL": return "text-red-600";
      default: return "";
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Generation Timeline</h1>
      <p className="text-sm text-gray-500 mb-6">24-hour solar generation forecast with DSM deviation tracking</p>
      <button onClick={load} disabled={loading} className="px-5 py-2 bg-blue-600 text-white rounded font-medium mb-6 hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Loading..." : "Generate 24h Forecast"}
      </button>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-xs text-gray-500 uppercase">Total Predicted</div>
            <div className="text-xl font-bold mt-1">{summary.total_predicted_mw.toFixed(1)} <span className="text-sm text-gray-500">MW</span></div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-xs text-gray-500 uppercase">Total Scheduled</div>
            <div className="text-xl font-bold mt-1">{summary.total_scheduled_mw.toFixed(1)} <span className="text-sm text-gray-500">MW</span></div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-xs text-gray-500 uppercase">Penalty Intervals</div>
            <div className="text-xl font-bold mt-1 text-red-600">{summary.penalty_intervals} <span className="text-sm text-gray-500">/ {summary.total_intervals}</span></div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-xs text-gray-500 uppercase">Max Deviation</div>
            <div className="text-xl font-bold mt-1">{summary.max_deviation_percent.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {timeline && (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 border-b sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Time (UTC)</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Irradiance W/m²</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Cloud %</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Predicted MW</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Scheduled MW</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Deviation %</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">Status</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">Risk</th>
              </tr>
            </thead>
            <tbody>
              {timeline.timeline.map((e: TimelineEntry, i: number) => (
                <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono">{e.timestamp.split("T")[1]?.slice(0, 5) || e.timestamp}</td>
                  <td className="px-3 py-2 text-right">{e.irradiance_w_m2.toFixed(0)}</td>
                  <td className="px-3 py-2 text-right">{e.cloud_cover_percent.toFixed(0)}</td>
                  <td className="px-3 py-2 text-right font-medium">{e.predicted_generation_mw.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right">{e.scheduled_generation_mw.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right">{e.deviation_percent.toFixed(1)}</td>
                  <td className={`px-3 py-2 text-center font-semibold ${e.penalty_status === "PENALTY_RISK" ? "text-red-600" : "text-green-600"}`}>
                    {e.penalty_status === "PENALTY_RISK" ? "PENALTY" : "OK"}
                  </td>
                  <td className={`px-3 py-2 text-center font-semibold ${riskColor(e.fuzzy_risk_level)}`}>
                    {e.fuzzy_risk_level}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
