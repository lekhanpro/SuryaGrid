"use client";
// SubstationWorkflowPanel
//
// Pick a substation from the dropdown -> the whole agent workflow runs on the backend
// (weather -> solar -> cloud -> generation timeline -> DSM) and the result is shown
// verbatim: the substation context, the agent trace, the generation timeline, and an
// honest DSM forecast. Nothing is fabricated here - missing real fields (capacity_mva,
// voltage) are shown as "not available" and their DSM calculations are listed as blocked.

import { useState } from "react";
import { orchestrateSubstation } from "@/lib/api";
import { useSubstationSelection } from "@/lib/substation-selection";

function Chip({ label }: { label: string }) {
  const bad = label === "NOT_AVAILABLE" || label === "NEEDS_OFFICIAL_SOURCE";
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded-full border ${
        bad
          ? "bg-orange-500/10 text-orange-300 border-orange-500/30"
          : "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
      }`}
    >
      {label}
    </span>
  );
}

function Stat({ label, value, accent }: { label: string; value: any; accent?: string }) {
  return (
    <div>
      <div className="text-[10px] text-white/40 uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold ${accent || "text-white"}`}>
        {value === null || value === undefined ? "—" : String(value)}
      </div>
    </div>
  );
}

export default function SubstationWorkflowPanel() {
  const {
    catalog,
    selectedId: selected,
    setSelectedId: setSelected,
    error: catalogError,
  } = useSubstationSelection();
  const [form, setForm] = useState({
    site_capacity_mw: 50,
    scheduled_generation_mw: 20,
    forecast_horizon_hours: 12,
    use_live_weather: true,
  });
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string>("");
  const [result, setResult] = useState<any>(null);
  const error = runError || catalogError;

  const run = async () => {
    if (!selected) return;
    setBusy(true);
    setRunError("");
    try {
      const r = await orchestrateSubstation({
        substation_id: selected,
        site_capacity_mw: form.site_capacity_mw || null,
        scheduled_generation_mw: form.scheduled_generation_mw || null,
        forecast_horizon_hours: form.forecast_horizon_hours,
        use_live_weather: form.use_live_weather,
      });
      setResult(r);
    } catch (e: any) {
      setRunError(e?.message || "Workflow failed");
      setResult(null);
    }
    setBusy(false);
  };

  const sub = result?.substation;
  const dsm = result?.dsm_forecast;
  const summary = result?.generation_summary;
  const trace: any[] = result?.workflow?.agent_trace || [];
  const timeline: any[] = result?.generation_timeline || [];

  return (
    <div className="glass-card p-5 mb-6">
      <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-1">
        Substation-Driven Agent Workflow
      </div>
      <p className="text-white/40 text-xs mb-4">
        Select a substation — its real OpenStreetMap context flows through weather → solar →
        cloud → generation → DSM. Generation is ESTIMATED from irradiance; missing fields are
        never fabricated.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
        <div className="md:col-span-2">
          <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">
            Substation ({catalog.length} available)
          </label>
          <select
            className="input-field"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {catalog.map((s) => (
              <option key={s.substation_id} value={s.substation_id} className="bg-slate-800">
                {s.display_label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">
            Plant capacity (MW)
          </label>
          <input
            type="number"
            step="any"
            className="input-field"
            value={form.site_capacity_mw}
            onChange={(e) => setForm({ ...form, site_capacity_mw: parseFloat(e.target.value) || 0 })}
          />
        </div>
        <div>
          <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">
            Scheduled gen (MW)
          </label>
          <input
            type="number"
            step="any"
            className="input-field"
            value={form.scheduled_generation_mw}
            onChange={(e) =>
              setForm({ ...form, scheduled_generation_mw: parseFloat(e.target.value) || 0 })
            }
          />
        </div>
        <div>
          <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">
            Horizon (hours)
          </label>
          <input
            type="number"
            className="input-field"
            value={form.forecast_horizon_hours}
            onChange={(e) =>
              setForm({ ...form, forecast_horizon_hours: parseInt(e.target.value) || 12 })
            }
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-white/60 mt-5">
          <input
            type="checkbox"
            checked={form.use_live_weather}
            onChange={(e) => setForm({ ...form, use_live_weather: e.target.checked })}
          />
          Live weather (Open-Meteo)
        </label>
      </div>

      <button className="btn-primary" disabled={busy || !selected} onClick={run}>
        {busy ? "Running workflow…" : "Run Agent Workflow"}
      </button>
      {error && <div className="mt-3 text-sm text-red-300">{error}</div>}

      {result && sub && (
        <div className="mt-5 space-y-5">
          {/* Substation context */}
          <div className="bg-white/5 rounded-lg p-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="font-semibold text-white">{sub.display_label}</div>
              <div className="flex gap-2 flex-wrap">
                <Chip label={sub.source_status} />
                <Chip label={`capacity: ${sub.capacity_status}`} />
                <Chip label={`voltage: ${sub.voltage_status}`} />
              </div>
            </div>
            <div className="text-xs text-white/40 mt-2 font-mono">
              {sub.latitude?.toFixed?.(4)}, {sub.longitude?.toFixed?.(4)} · voltage:{" "}
              {sub.voltage_kv ?? "unknown"} kV · capacity_mva: {sub.capacity_mva ?? "unavailable"}
            </div>
            {sub.missing_fields?.length > 0 && (
              <div className="text-xs text-orange-300/80 mt-1">
                missing (not fabricated): {sub.missing_fields.join(", ")}
              </div>
            )}
          </div>

          {/* Agent trace */}
          <div>
            <div className="eyebrow mb-2">Agent workflow trace</div>
            <div className="space-y-1">
              {trace.map((t) => (
                <div key={t.step} className="flex items-start gap-3 text-sm">
                  <span className="text-white/30 font-mono text-xs mt-0.5">#{t.step}</span>
                  <span className="text-white/80 font-medium min-w-[180px]">{t.agent}</span>
                  <span className="text-white/40 flex-1">{t.action}</span>
                  <Chip label={t.status} />
                </div>
              ))}
            </div>
          </div>

          {/* Generation summary */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Stat label="Peak est. gen (MW)" value={summary.peak_estimated_generation_mw} />
              <Stat label="Total est. energy (MWh)" value={summary.total_estimated_energy_mwh} />
              <Stat label="Daylight intervals" value={summary.daylight_intervals} />
              <Stat label="Generation type" value="ESTIMATED" accent="text-orange-300" />
            </div>
          )}

          {/* DSM forecast */}
          {dsm && (
            <div className="bg-white/5 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-bold text-white/70 uppercase tracking-wider">
                  DSM forecast (framework-only)
                </div>
                <Chip label={dsm.emits_rupee_values ? "RUPEES" : "NO RUPEE CHARGE"} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                <Stat label="Deviation %" value={dsm.deviation_percent} />
                <Stat label="Band" value={dsm.deviation_band} />
                <Stat
                  label="Breach risk"
                  value={
                    dsm.breach_risk?.prediction_value?.breach_risk ??
                    dsm.breach_risk?.status ??
                    "—"
                  }
                />
                <Stat label="Capacity status" value={dsm.capacity_status} accent="text-orange-300" />
              </div>
              {dsm.blocked_calculations?.length > 0 && (
                <div className="text-xs text-white/50">
                  <span className="text-white/40 uppercase tracking-wider">Blocked calculations: </span>
                  {dsm.blocked_calculations.map((b: any) => b.calculation).join(", ")}
                </div>
              )}
            </div>
          )}

          {/* Timeline (compact) */}
          {timeline.length > 0 && (
            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-900/80">
                  <tr className="text-left text-white/40 border-b border-white/10">
                    <th className="py-2 pr-3">Time</th>
                    <th className="py-2 pr-3">GHI (W/m²)</th>
                    <th className="py-2 pr-3">Est. gen (MW)</th>
                    <th className="py-2 pr-3">Cloud-drop risk</th>
                    <th className="py-2 pr-3">Substation</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.map((r, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1.5 pr-3 text-white/60 font-mono text-xs">
                        {String(r.timestamp).replace("T", " ").slice(5, 16)}
                      </td>
                      <td className="py-1.5 pr-3 text-white/70">{r.forecast_ghi_wm2 ?? "—"}</td>
                      <td className="py-1.5 pr-3 text-white/70">{r.estimated_generation_mw ?? "—"}</td>
                      <td className="py-1.5 pr-3 text-white/50">
                        {r.cloud_drop_risk ? `${(r.cloud_drop_risk.probability * 100).toFixed(0)}%` : "—"}
                      </td>
                      <td className="py-1.5 pr-3 text-white/30 font-mono text-xs">{r.substation_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Limitations */}
          {result.limitations?.length > 0 && (
            <div className="text-xs text-white/50 bg-white/5 rounded-lg p-3">
              <div className="text-white/40 uppercase tracking-wider mb-1">Honest limitations</div>
              <ul className="list-disc list-inside space-y-0.5">
                {result.limitations.map((l: string, i: number) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
