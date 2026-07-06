"use client";
import { useEffect, useState } from "react";
import SolarPanel3D from "@/components/svg/SolarPanel3D";
import RiskGauge3D from "@/components/svg/RiskGauge3D";
import MiniTimeline from "@/components/charts/MiniTimeline";
import MetricCard from "@/components/cards/MetricCard";
import OfflineBanner from "@/components/OfflineBanner";
import ModelProvenancePanel from "@/components/ModelProvenancePanel";
import { API_BASE, getTimeline, predictSite, probeBackend } from "@/lib/api";
import type { TimelineData, TimelineEntry } from "@/lib/types";

const LOCATIONS = [
  { label: "Pavagada, Karnataka", lat: 14.1, lon: 77.28, cap: 2050, regulator: "KERC/BESCOM" },
  { label: "Bhadla, Rajasthan", lat: 27.53, lon: 71.91, cap: 2245, regulator: "CERC" },
  { label: "Kurnool, Andhra Pradesh", lat: 15.68, lon: 78.28, cap: 1000, regulator: "CERC" },
  { label: "Bengaluru (Electronic City)", lat: 12.85, lon: 77.66, cap: 40, regulator: "KERC/BESCOM" },
];

export default function Dashboard() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [pred, setPred] = useState<any>(null);
  const [tl, setTl] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ location: 0, capacity_mw: 2050, mode: "auto", scheduled_mw: "" });

  useEffect(() => {
    probeBackend().then((p) => setOnline(p.online));
  }, []);

  const run = async () => {
    setLoading(true);
    setErr("");
    try {
      const loc = LOCATIONS[form.location];
      const params: Record<string, string | number> = {
        latitude: loc.lat,
        longitude: loc.lon,
        capacity_mw: form.capacity_mw,
        mode: form.mode,
        regulator: loc.regulator,
      };
      if (form.scheduled_mw !== "") params.scheduled_mw = Number(form.scheduled_mw);
      const [p, t] = await Promise.all([
        predictSite("primary-site", params),
        getTimeline("primary-site", {
          latitude: loc.lat,
          longitude: loc.lon,
          capacity_mw: form.capacity_mw,
          forecast_days: 1,
        }),
      ]);
      setPred(p);
      setTl(t);
    } catch (e: any) {
      setErr(e.message);
    }
    setLoading(false);
  };

  const timeline: TimelineEntry[] = tl?.timeline ?? [];
  const genPct = pred ? (pred.predicted_generation_mw / form.capacity_mw) * 100 : 0;
  const penalty = pred?.penalty_status === "PENALTY_RISK";

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Solar Generation Monitor</h1>
        <p className="text-white/40 mt-1">
          Real-data nowcast · ML/hybrid forecast · advanced DSM · fuzzy risk — live via Open-Meteo + pvlib.
        </p>
      </div>

      {online === false && <OfflineBanner base={API_BASE} />}

      {online && <ModelProvenancePanel />}

      {online && (
        <div className="glass-card p-6 mb-6">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <h2 className="text-sm font-bold text-white/70 uppercase tracking-wider">Site &amp; Forecast</h2>
            <button onClick={run} disabled={loading} className="btn-primary">
              {loading ? "Running full prediction…" : "Run Full Prediction"}
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="eyebrow block mb-1">Location</label>
              <select className="input-field" value={form.location}
                onChange={(e) => {
                  const i = Number(e.target.value);
                  setForm({ ...form, location: i, capacity_mw: LOCATIONS[i].cap });
                }}>
                {LOCATIONS.map((l, i) => (
                  <option key={i} value={i} className="bg-slate-800">{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="eyebrow block mb-1">Capacity (MW)</label>
              <input type="number" step="any" className="input-field" value={form.capacity_mw}
                onChange={(e) => setForm({ ...form, capacity_mw: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="eyebrow block mb-1">Forecast mode</label>
              <select className="input-field" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
                {["auto", "formula", "ml", "hybrid"].map((m) => <option key={m} value={m} className="bg-slate-800">{m}</option>)}
              </select>
            </div>
            <div>
              <label className="eyebrow block mb-1">Scheduled MW (blank=clear-sky)</label>
              <input type="number" step="any" className="input-field" placeholder="auto" value={form.scheduled_mw}
                onChange={(e) => setForm({ ...form, scheduled_mw: e.target.value })} />
            </div>
          </div>
          {err && <div className="mt-4 text-red-300 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">{err}</div>}
        </div>
      )}

      {pred && (
        <>
          {/* data-source coverage strip */}
          <div className="flex flex-wrap items-center gap-2 mb-5 text-xs">
            <span className="text-white/40">Sources:</span>
            {(pred.data_sources || []).map((d: string) => (
              <span key={d} className="badge badge-blue">{d}</span>
            ))}
            <span className={`badge ${pred.weather_mode === "synthetic" ? "badge-orange" : "badge-green"}`}>
              weather: {pred.weather_mode}
            </span>
            <span className="badge badge-blue">mode: {pred.forecast_mode}</span>
            {pred.model_version && <span className="badge badge-blue">model {pred.model_version}</span>}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Predicted (now)" value={pred.predicted_generation_mw.toFixed(2)} unit="MW" color="blue" subtitle={`${genPct.toFixed(0)}% of capacity`} />
            <MetricCard title="Scheduled" value={pred.scheduled_generation_mw.toFixed(2)} unit="MW" color="purple" subtitle="clear-sky / declared" />
            <MetricCard title="Deviation" value={`${pred.deviation_percent}%`} color={penalty ? "red" : "green"} subtitle={pred.deviation_direction} />
            <MetricCard title="Est. DSM Charge" value={`₹${(pred.estimated_dsm_charge || 0).toLocaleString()}`} color={penalty ? "red" : "green"} subtitle={pred.dsm_band || "within band"} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="eyebrow mb-2">Generation Now</div>
              <SolarPanel3D generation={genPct} className="w-full max-w-[200px] animate-float" />
              <div className="text-2xl font-bold text-white mt-2">{pred.predicted_generation_mw.toFixed(1)} <span className="text-base text-white/40">MW</span></div>
              <div className="text-[11px] text-white/35">GHI {pred.ghi_w_m2?.toFixed(0)} W/m² · cloud {pred.cloud_cover_percent?.toFixed(0)}%</div>
            </div>

            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="eyebrow mb-2">Fuzzy Risk</div>
              <RiskGauge3D score={pred.fuzzy_risk_score} level={pred.fuzzy_risk_level} className="w-full max-w-[180px]" />
              <div className="text-[11px] text-white/35 mt-1">confidence {(pred.confidence_score * 100).toFixed(0)}%</div>
            </div>

            <div className="glass-card p-5 flex flex-col justify-between">
              <div>
                <div className="eyebrow mb-1">Penalty Status</div>
                <div className={`text-2xl font-bold ${penalty ? "text-red-400" : "text-emerald-400"}`}>{pred.penalty_status}</div>
                <div className="text-sm text-white/40 mt-1">Profile: {pred.dsm_profile}</div>
                <div className="text-xs text-white/30 mt-0.5">{pred.rule_source?.status}</div>
              </div>
              <div className="mt-4 pt-3 border-t border-white/5">
                <div className="eyebrow mb-1">Nearest Substation</div>
                {pred.nearest_substation ? (
                  <div className="text-sm text-white/70">
                    {pred.nearest_substation.name}
                    <span className="text-white/40"> · {pred.nearest_substation.distance_km} km · {pred.nearest_substation.source}</span>
                  </div>
                ) : (
                  <div className="text-sm text-white/40">None imported — see Locations.</div>
                )}
              </div>
            </div>
          </div>

          <div className="glass-card p-5 mb-6">
            <div className="eyebrow mb-2">Explanation</div>
            <p className="text-white/70 text-sm leading-relaxed">{pred.explanation}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              {(pred.sources || []).map((s: any) => (
                <a key={s.id} href={s.reference} target="_blank" rel="noreferrer"
                  className="text-[11px] px-2 py-0.5 rounded-full border border-white/10 text-white/50 hover:text-cyan-300 hover:border-cyan-500/30">
                  {s.name} ({s.classification})
                </a>
              ))}
            </div>
          </div>

          {timeline.length > 0 && <MiniTimeline data={timeline} maxMW={form.capacity_mw} />}
        </>
      )}

      {online && !pred && !loading && (
        <div className="glass-card text-center py-16">
          <SolarPanel3D generation={0} className="w-40 mx-auto mb-6 opacity-50" />
          <h3 className="text-lg font-medium text-white/60">Ready to Forecast</h3>
          <p className="text-white/30 mt-1 text-sm">Pick a site and run a full real-data prediction.</p>
        </div>
      )}
    </div>
  );
}
