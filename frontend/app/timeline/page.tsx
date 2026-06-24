"use client";
import { useState } from "react";
import { getTimeline, getSummary } from "@/lib/api";
import MiniTimeline from "@/components/charts/MiniTimeline";
import MetricCard from "@/components/cards/MetricCard";
import type { TimelineData, SummaryData, TimelineEntry } from "@/lib/types";

export default function TimelinePage() {
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = { seed: 42, capacity_mw: 50, scheduled_mw: 35 };
      const [tl, sm] = await Promise.all([getTimeline("primary-site", params), getSummary("primary-site", params)]);
      setTimeline(tl);
      setSummary(sm);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  const riskBadge = (level: string) => {
    const cls: Record<string, string> = { LOW: "badge-green", MEDIUM: "badge-yellow", HIGH: "badge-orange", CRITICAL: "badge-red" };
    return <span className={`badge ${cls[level] || "badge-green"}`}>{level}</span>;
  };

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Generation Timeline</h1>
        <p className="text-white/40 mt-1">24-hour solar generation forecast with DSM deviation tracking</p>
      </div>

      <button onClick={load} disabled={loading} className="btn-primary mb-8">
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Generating…
          </span>
        ) : "Generate 24h Forecast"}
      </button>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard title="Total Predicted" value={summary.total_predicted_mw.toFixed(1)} unit="MW" color="blue" subtitle="Cumulative day output" />
          <MetricCard title="Total Scheduled" value={summary.total_scheduled_mw.toFixed(1)} unit="MW" color="purple" subtitle="Agreement total" />
          <MetricCard title="Penalty Intervals" value={`${summary.penalty_intervals}/${summary.total_intervals}`} color="red" subtitle="Intervals above threshold" />
          <MetricCard title="Max Deviation" value={summary.max_deviation_percent.toFixed(1)} unit="%" color="orange" subtitle="Peak deviation recorded" />
        </div>
      )}

      {timeline && (
        <>
          <div className="mb-6">
            <MiniTimeline data={timeline.timeline} maxMW={50} />
          </div>

          <div className="glass-card overflow-hidden p-0">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="table-head sticky top-0 backdrop-blur-md">
                  <tr>
                    <th className="px-3 py-2.5 text-left font-medium">Time</th>
                    <th className="px-3 py-2.5 text-right font-medium">Irradiance</th>
                    <th className="px-3 py-2.5 text-right font-medium">Cloud</th>
                    <th className="px-3 py-2.5 text-right font-medium">Predicted</th>
                    <th className="px-3 py-2.5 text-right font-medium">Scheduled</th>
                    <th className="px-3 py-2.5 text-right font-medium">Deviation</th>
                    <th className="px-3 py-2.5 text-center font-medium">Status</th>
                    <th className="px-3 py-2.5 text-center font-medium">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.timeline.map((e: TimelineEntry, i: number) => (
                    <tr key={i} className="table-row">
                      <td className="px-3 py-2 font-mono text-white/70">{e.timestamp.split("T")[1]?.slice(0, 5)}</td>
                      <td className="px-3 py-2 text-right text-white/80">{e.irradiance_w_m2.toFixed(0)} <span className="text-white/30">W/m²</span></td>
                      <td className="px-3 py-2 text-right text-white/80">{e.cloud_cover_percent.toFixed(0)}%</td>
                      <td className="px-3 py-2 text-right font-medium text-white">{e.predicted_generation_mw.toFixed(2)} MW</td>
                      <td className="px-3 py-2 text-right text-white/50">{e.scheduled_generation_mw.toFixed(2)} MW</td>
                      <td className="px-3 py-2 text-right font-mono text-white/70">{e.deviation_percent.toFixed(1)}%</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`badge ${e.penalty_status === "PENALTY_RISK" ? "badge-red" : "badge-green"}`}>
                          {e.penalty_status === "PENALTY_RISK" ? "PENALTY" : "OK"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">{riskBadge(e.fuzzy_risk_level)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!timeline && !loading && (
        <div className="glass-card text-center py-16">
          <svg className="w-16 h-16 mx-auto text-white/15 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <h3 className="text-lg font-medium text-white/60">No Timeline Data</h3>
          <p className="text-white/30 mt-1 text-sm">Generate a 24-hour forecast to view the timeline</p>
        </div>
      )}
    </div>
  );
}
