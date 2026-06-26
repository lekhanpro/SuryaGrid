"use client";
import { useEffect, useState } from "react";
import { getRLRuns, trainRL } from "@/lib/api";
import { LOCATIONS } from "@/lib/locations";
import MetricCard from "@/components/cards/MetricCard";
import type { TrainingRun } from "@/lib/types";

export default function RLPage() {
  const [runs, setRuns] = useState<TrainingRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [loc, setLoc] = useState(0);
  const [episodes, setEpisodes] = useState(200);
  const [daysBack, setDaysBack] = useState(90);
  const [useReal, setUseReal] = useState(true);
  const [lastRun, setLastRun] = useState<any>(null);

  const refresh = () => getRLRuns().then(setRuns).catch(() => {});
  useEffect(() => { refresh(); }, []);

  const train = async () => {
    setLoading(true);
    try {
      const l = LOCATIONS[loc];
      const res = await trainRL({
        episodes,
        use_real_data: useReal,
        latitude: l.latitude,
        longitude: l.longitude,
        capacity_mw: l.capacity_mw,
        days_back: daysBack,
      });
      setLastRun(res);
      await refresh();
    } catch (e: any) {
      alert(e.message);
    }
    setLoading(false);
  };

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Reinforcement Learning Lab</h1>
        <p className="text-white/40 mt-1">
          Train the reward policy on real historical irradiance (Open-Meteo archive → pvlib digital twin)
        </p>
      </div>

      <div className="glass-card p-6 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
          <div>
            <label className="eyebrow block mb-1">Site</label>
            <select className="input-field" value={loc} onChange={(e) => setLoc(Number(e.target.value))}>
              {LOCATIONS.map((l, i) => (
                <option key={i} value={i} className="bg-slate-800">{l.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="eyebrow block mb-1">Episodes</label>
            <input type="number" className="input-field" value={episodes} onChange={(e) => setEpisodes(Number(e.target.value) || 100)} />
          </div>
          <div>
            <label className="eyebrow block mb-1">History (days)</label>
            <input type="number" className="input-field" value={daysBack} onChange={(e) => setDaysBack(Number(e.target.value) || 30)} />
          </div>
          <label className="flex items-center gap-2 text-sm text-white/60 pb-2">
            <input type="checkbox" checked={useReal} onChange={(e) => setUseReal(e.target.checked)} className="accent-blue-500" />
            Real data
          </label>
          <button onClick={train} disabled={loading} className="btn-primary">
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                Training
              </span>
            ) : "Train Policy"}
          </button>
        </div>
        <p className="text-[11px] text-white/30 mt-3">
          Real-data training fetches genuine past weather, runs pvlib physics to build production/target curves, then optimizes penalty/bonus/discount rates with a REINFORCE policy gradient.
        </p>
      </div>

      {lastRun && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard title="Data Source" value={lastRun.real_days_used > 0 ? `${lastRun.real_days_used} real days` : "Synthetic"} color="green" subtitle={lastRun.data_source} />
          <MetricCard title="Best Reward" value={lastRun.best_reward.toFixed(1)} color="blue" subtitle="Top episode" />
          <MetricCard title="Penalty Rate" value={`₹${lastRun.final_rates.penalty_rate}`} color="red" subtitle="Learned" />
          <MetricCard title="Bonus Rate" value={`₹${lastRun.final_rates.bonus_rate}`} color="purple" subtitle="Learned" />
        </div>
      )}

      <div className="glass-card overflow-hidden p-0">
        <div className="px-5 py-3 border-b border-white/5 eyebrow">Training Run History</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="table-head">
              <tr>
                <th className="px-5 py-3 text-left font-medium">When</th>
                <th className="px-5 py-3 text-left font-medium">Algorithm</th>
                <th className="px-5 py-3 text-right font-medium">Episodes</th>
                <th className="px-5 py-3 text-left font-medium">Data Source</th>
                <th className="px-5 py-3 text-right font-medium">Best Reward</th>
                <th className="px-5 py-3 text-right font-medium">Rates (P/B/D)</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="table-row">
                  <td className="px-5 py-3 text-white/60 font-mono text-xs">{r.created_at?.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-5 py-3 text-white/80">{r.algorithm}</td>
                  <td className="px-5 py-3 text-right text-white/70">{r.episodes}</td>
                  <td className="px-5 py-3 text-white/60 text-xs">{r.data_source}</td>
                  <td className="px-5 py-3 text-right font-mono text-white/80">{r.best_reward.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right font-mono text-white/70">
                    {r.final_rates ? `${r.final_rates.penalty_rate}/${r.final_rates.bonus_rate}/${r.final_rates.discount_rate}` : "—"}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-10 text-center text-white/30">No training runs yet — train a policy above.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
