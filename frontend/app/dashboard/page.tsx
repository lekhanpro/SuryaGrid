"use client";
import { useState } from "react";
import SolarPanel3D from "@/components/svg/SolarPanel3D";
import RiskGauge3D from "@/components/svg/RiskGauge3D";
import EnergyFlow3D from "@/components/svg/EnergyFlow3D";
import MiniTimeline from "@/components/charts/MiniTimeline";
import MetricCard from "@/components/cards/MetricCard";
import { getTimeline } from "@/lib/api";
import type { TimelineData, TimelineEntry } from "@/lib/types";

const LOCATIONS = [
  { label: "Bhadla, Rajasthan", lat: 27.53, lon: 71.91 },
  { label: "Pavagada, Karnataka", lat: 14.1, lon: 77.28 },
  { label: "Kurnool, Andhra Pradesh", lat: 15.68, lon: 78.28 },
  { label: "New Delhi", lat: 28.61, lon: 77.21 },
];

export default function Dashboard() {
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    location: 0,
    capacity_mw: 100,
    tilt: 27,
    scheduled_mw: "",
    threshold_percent: 10,
    penalty_rate: 12000,
  });

  const run = async () => {
    setLoading(true);
    try {
      const loc = LOCATIONS[form.location];
      const params: Record<string, string | number> = {
        latitude: loc.lat,
        longitude: loc.lon,
        capacity_mw: form.capacity_mw,
        tilt: form.tilt,
        threshold_percent: form.threshold_percent,
        penalty_rate: form.penalty_rate,
        forecast_days: 1,
      };
      if (form.scheduled_mw !== "") params.scheduled_mw = Number(form.scheduled_mw);
      const tl = await getTimeline("primary-site", params);
      setData(tl);
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  const timeline: TimelineEntry[] = data?.timeline ?? [];
  // Headline = the interval with highest forecast generation.
  const peak = timeline.reduce<TimelineEntry | null>(
    (best, e) => (!best || e.predicted_generation_mw > best.predicted_generation_mw ? e : best),
    null
  );
  const worst = timeline.reduce<TimelineEntry | null>(
    (w, e) => (!w || e.risk_score > w.risk_score ? e : w),
    null
  );
  const genPct = peak ? (peak.predicted_generation_mw / form.capacity_mw) * 100 : 0;
  const s = data?.summary;

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Solar Generation Monitor</h1>
        <p className="text-white/40 mt-1">
          Live irradiance nowcasting and DSM penalty analysis · real data via Open-Meteo + pvlib
        </p>
      </div>

      {/* Input Panel */}
      <div className="glass-card p-6 mb-8">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-bold text-white/70 uppercase tracking-wider">Site &amp; Schedule</h2>
          <button onClick={run} disabled={loading} className="btn-primary">
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Fetching live data
              </span>
            ) : "Run Live Forecast"}
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="col-span-2 md:col-span-1">
            <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">Location</label>
            <select
              className="input-field"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: Number(e.target.value) })}
            >
              {LOCATIONS.map((l, i) => (
                <option key={i} value={i} className="bg-slate-800">{l.label}</option>
              ))}
            </select>
          </div>
          <Field label="Capacity" unit="MW" value={form.capacity_mw} onChange={(v) => setForm({ ...form, capacity_mw: v })} />
          <Field label="Tilt" unit="°" value={form.tilt} onChange={(v) => setForm({ ...form, tilt: v })} />
          <div>
            <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">Scheduled <span className="text-white/20">(MW, blank = clear-sky)</span></label>
            <input
              type="number" step="any" className="input-field" placeholder="auto"
              value={form.scheduled_mw}
              onChange={(e) => setForm({ ...form, scheduled_mw: e.target.value })}
            />
          </div>
          <Field label="Threshold" unit="%" value={form.threshold_percent} onChange={(v) => setForm({ ...form, threshold_percent: v })} />
          <Field label="Penalty Rate" unit="₹/MWh" value={form.penalty_rate} onChange={(v) => setForm({ ...form, penalty_rate: v })} />
        </div>
      </div>

      {/* Results */}
      {data && peak && worst && s && (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Predicted Energy" value={s.predicted_energy_mwh.toFixed(1)} unit="MWh" color="blue" subtitle="Today, cloud-adjusted" />
            <MetricCard title="Peak Output" value={s.peak_generation_mw.toFixed(1)} unit="MW" color="green" subtitle={`${((s.peak_generation_mw / form.capacity_mw) * 100).toFixed(0)}% of capacity`} />
            <MetricCard title="Penalty Intervals" value={`${s.penalty_intervals}/${s.daylight_intervals}`} color="orange" subtitle="Daylight hours over band" />
            <MetricCard title="Est. DSM Charge" value={`₹${s.total_penalty_cost.toLocaleString()}`} color="red" subtitle="Cumulative day" />
          </div>

          {/* Top visual row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Peak Generation</div>
              <SolarPanel3D generation={genPct} className="w-full max-w-[220px] animate-float" />
              <div className="text-2xl font-bold text-white mt-2">{peak.predicted_generation_mw.toFixed(1)} <span className="text-base text-white/40">MW</span></div>
              <div className="text-[11px] text-white/35">at {peak.timestamp.slice(11, 16)} · GHI {peak.ghi_w_m2.toFixed(0)} W/m²</div>
            </div>

            <div className="glass-card p-5 flex flex-col justify-between">
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Forecast Confidence (peak)</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full" style={{ width: `${peak.confidence_score * 100}%` }} />
                    </div>
                    <span className="text-sm font-bold text-cyan-300">{(peak.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Max Deviation</div>
                  <div className="text-2xl font-bold text-white mt-1">{s.max_deviation_percent.toFixed(1)}<span className="text-base text-white/40">%</span></div>
                </div>
                <div className="pt-3 border-t border-white/5">
                  <div className={`text-xl font-bold ${s.penalty_intervals > 0 ? "text-red-400" : "text-emerald-400"}`}>
                    {s.penalty_intervals > 0 ? "PENALTY RISK" : "WITHIN BAND"}
                  </div>
                  <div className="text-sm text-white/40 mt-1">Provider: {data.provider}</div>
                </div>
              </div>
            </div>

            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Worst-hour DSM Risk</div>
              <RiskGauge3D score={worst.risk_score} level={worst.risk_level} className="w-full max-w-[180px]" />
              <div className="text-[11px] text-white/35 mt-1">at {worst.timestamp.slice(11, 16)}</div>
            </div>
          </div>

          {/* Energy Flow at peak */}
          <div className="glass-card p-5 mb-6">
            <div className="text-[10px] text-white/40 uppercase tracking-wider mb-3">Peak-hour Energy Flow</div>
            <EnergyFlow3D
              predictedMW={peak.predicted_generation_mw}
              scheduledMW={peak.scheduled_generation_mw}
              capacityMW={form.capacity_mw}
              isPenalty={peak.penalty_status === "PENALTY_RISK"}
              className="w-full"
            />
          </div>

          {/* Timeline */}
          {timeline.length > 0 && <MiniTimeline data={timeline} maxMW={form.capacity_mw} />}
        </>
      )}

      {!data && !loading && (
        <div className="glass-card text-center py-20">
          <SolarPanel3D generation={0} className="w-48 mx-auto mb-6 opacity-50" />
          <h3 className="text-lg font-medium text-white/60">Ready to Forecast</h3>
          <p className="text-white/30 mt-1 text-sm">Pick a site and run a live forecast from real weather data</p>
        </div>
      )}
    </div>
  );
}

function Field({ label, unit, value, onChange }: { label: string; unit: string; value: number; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">{label} <span className="text-white/20">({unit})</span></label>
      <input
        type="number" step="any" className="input-field"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}
