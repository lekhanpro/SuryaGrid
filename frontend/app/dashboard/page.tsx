"use client";
// Substation-driven dashboard.
//
// The selected substation (shared across pages, persisted) is the single agent
// input context: weather, solar GHI, cloud risk, generation timeline, DSM and
// the agent trace all come from one POST /orchestrate/substation run at the
// substation's real OSM coordinates. No hardcoded preset sites, no rupee DSM
// values (NEEDS_OFFICIAL_SOURCE), missing fields shown explicitly.

import { useEffect, useState } from "react";
import SolarPanel3D from "@/components/svg/SolarPanel3D";
import RiskGauge3D from "@/components/svg/RiskGauge3D";
import MetricCard from "@/components/cards/MetricCard";
import OfflineBanner from "@/components/OfflineBanner";
import ModelProvenancePanel from "@/components/ModelProvenancePanel";
import AIInsightsPanel from "@/components/AIInsightsPanel";
import { API_BASE, orchestrateSubstation, probeBackend } from "@/lib/api";
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

export default function Dashboard() {
  const { catalog, selectedId, setSelectedId, loading: catalogLoading, error: catalogError } =
    useSubstationSelection();
  const [online, setOnline] = useState<boolean | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    site_capacity_mw: 50,
    scheduled_generation_mw: 20,
    forecast_horizon_hours: 12,
    use_live_weather: true,
  });

  useEffect(() => {
    probeBackend().then((p) => setOnline(p.online));
  }, []);

  const run = async () => {
    if (!selectedId) return;
    setLoading(true);
    setErr("");
    try {
      const r = await orchestrateSubstation({
        substation_id: selectedId,
        site_capacity_mw: form.site_capacity_mw || null,
        scheduled_generation_mw: form.scheduled_generation_mw || null,
        forecast_horizon_hours: form.forecast_horizon_hours,
        use_live_weather: form.use_live_weather,
      });
      setResult(r);
    } catch (e: any) {
      setErr(e?.message || "Workflow failed");
      setResult(null);
    }
    setLoading(false);
  };

  const sub = result?.substation;
  const dsm = result?.dsm_forecast;
  const summary = result?.generation_summary;
  const weather = result?.weather;
  const trace: any[] = result?.workflow?.agent_trace || [];
  const calc = result?.workflow?.calculation_trace;
  const timeline: any[] = result?.generation_timeline || [];
  const maxGhi = Math.max(1, ...timeline.map((r) => r.forecast_ghi_wm2 || 0));
  const peakMw = summary?.peak_estimated_generation_mw;
  const genPct =
    peakMw != null && form.site_capacity_mw > 0 ? (peakMw / form.site_capacity_mw) * 100 : 0;
  const breachProb = dsm?.breach_risk?.prediction_value?.probability;
  const riskScore = breachProb != null ? Math.round(breachProb * 100) : null;
  const riskLevel =
    riskScore == null ? "LOW" : riskScore >= 75 ? "CRITICAL" : riskScore >= 50 ? "HIGH" : riskScore >= 25 ? "MEDIUM" : "LOW";

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Substation Solar Monitor</h1>
        <p className="text-white/40 mt-1">
          One selected substation drives every agent: weather → solar → cloud → generation → DSM.
          Real OSM coordinates, honest missing-data handling, no rupee values.
        </p>
      </div>

      {online === false && <OfflineBanner base={API_BASE} />}

      {online && <ModelProvenancePanel />}

      {online && (
        <div className="glass-card p-6 mb-6">
          <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
            <h2 className="text-sm font-bold text-white/70 uppercase tracking-wider">
              Substation &amp; Forecast Context
            </h2>
            <button onClick={run} disabled={loading || !selectedId} className="btn-primary">
              {loading ? "Running agent workflow…" : "Run Agent Workflow"}
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="col-span-2">
              <label className="eyebrow block mb-1">
                Substation ({catalogLoading ? "loading…" : `${catalog.length} available`})
              </label>
              <select
                className="input-field"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                disabled={catalogLoading || !catalog.length}
              >
                {catalog.map((s) => (
                  <option key={s.substation_id} value={s.substation_id} className="bg-slate-800">
                    {s.display_label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="eyebrow block mb-1">Plant capacity (MW)</label>
              <input type="number" step="any" className="input-field" value={form.site_capacity_mw}
                onChange={(e) => setForm({ ...form, site_capacity_mw: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="eyebrow block mb-1">Scheduled (MW)</label>
              <input type="number" step="any" className="input-field" value={form.scheduled_generation_mw}
                onChange={(e) => setForm({ ...form, scheduled_generation_mw: parseFloat(e.target.value) || 0 })} />
            </div>
            <div>
              <label className="eyebrow block mb-1">Horizon (hours)</label>
              <input type="number" className="input-field" value={form.forecast_horizon_hours}
                onChange={(e) => setForm({ ...form, forecast_horizon_hours: parseInt(e.target.value) || 12 })} />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-white/60 mt-3">
            <input type="checkbox" checked={form.use_live_weather}
              onChange={(e) => setForm({ ...form, use_live_weather: e.target.checked })} />
            Live weather (Open-Meteo at substation coordinates)
          </label>
          {(err || catalogError) && (
            <div className="mt-4 text-red-300 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
              {err || catalogError}
            </div>
          )}
        </div>
      )}

      {result && sub && (
        <>
          {/* Substation context card */}
          <div className="glass-card p-5 mb-6">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <div className="eyebrow mb-1">Active Substation Context</div>
                <div className="font-semibold text-white">{sub.display_label}</div>
                <div className="text-xs text-white/40 mt-1">
                  {sub.substation_id} · ({sub.latitude}, {sub.longitude}) ·{" "}
                  {sub.voltage_kv != null ? `${sub.voltage_kv} kV` : "voltage unknown"} ·{" "}
                  {sub.operator || "operator unknown"}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Chip label={sub.source_status} />
                <Chip label={`capacity: ${sub.capacity_status}`} />
                <Chip label={`voltage: ${sub.voltage_status}`} />
                <Chip label={`load: ${sub.load_data_status}`} />
                <Chip label={`tariff: ${sub.tariff_status}`} />
              </div>
            </div>
            {sub.missing_fields?.length > 0 && (
              <div className="text-xs text-orange-300/70 mt-2">
                Missing real fields (never fabricated): {sub.missing_fields.join(", ")}
              </div>
            )}
          </div>

          {/* Source strip */}
          <div className="flex flex-wrap items-center gap-2 mb-5 text-xs">
            <span className="text-white/40">Sources:</span>
            {(result.data_sources || []).map((d: any, i: number) => (
              <span key={i} className="badge badge-blue">
                {typeof d === "string" ? d : `${d.name}${d.label ? ` (${d.label})` : ""}`}
              </span>
            ))}
            <span className={`badge ${weather?.mode === "live" ? "badge-green" : "badge-orange"}`}>
              weather: {weather?.mode} ({weather?.source_label})
            </span>
            {weather?.live_error && (
              <span className="badge badge-orange">live weather failed → clear-sky</span>
            )}
          </div>

          {/* Metric cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <MetricCard
              title="Peak Estimated Generation"
              value={peakMw != null ? peakMw.toFixed(2) : "—"}
              unit={peakMw != null ? "MW" : undefined}
              color="blue"
              subtitle={summary?.generation_type || "ESTIMATED_FROM_IRRADIANCE"}
            />
            <MetricCard
              title="Estimated Energy"
              value={summary?.total_estimated_energy_mwh != null ? summary.total_estimated_energy_mwh.toFixed(2) : "—"}
              unit={summary?.total_estimated_energy_mwh != null ? "MWh" : undefined}
              color="purple"
              subtitle={`${summary?.daylight_intervals ?? 0}/${summary?.intervals ?? 0} daylight hours`}
            />
            <MetricCard
              title="DSM Deviation"
              value={dsm?.deviation_percent != null ? `${dsm.deviation_percent}%` : "—"}
              color={dsm?.deviation_band && dsm.deviation_band !== "WITHIN_BAND" ? "red" : "green"}
              subtitle={dsm?.deviation_band || "no schedule given"}
            />
            <MetricCard
              title="Breach Risk"
              value={breachProb != null ? `${(breachProb * 100).toFixed(0)}%` : "—"}
              color={riskScore != null && riskScore >= 50 ? "red" : "green"}
              subtitle="dsm_classifier.pkl probability"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="eyebrow mb-2">Peak Generation (Estimated)</div>
              <SolarPanel3D generation={genPct} className="w-full max-w-[200px] animate-float" />
              <div className="text-2xl font-bold text-white mt-2">
                {peakMw != null ? peakMw.toFixed(1) : "—"}{" "}
                <span className="text-base text-white/40">MW</span>
              </div>
              <div className="text-[11px] text-white/35">
                {form.site_capacity_mw > 0
                  ? `${genPct.toFixed(0)}% of ${form.site_capacity_mw} MW plant`
                  : "no plant capacity given — irradiance only"}
              </div>
            </div>

            <div className="glass-card p-4 flex flex-col items-center justify-center glass-hover">
              <div className="eyebrow mb-2">DSM Breach Risk</div>
              {breachProb != null ? (
                <>
                  <RiskGauge3D score={riskScore!} level={riskLevel} className="w-full max-w-[180px]" />
                  <div className="text-[11px] text-white/35 mt-1">
                    P(breach) {(breachProb * 100).toFixed(1)}%
                  </div>
                </>
              ) : (
                <div className="text-sm text-white/40 text-center px-3">
                  NOT_AVAILABLE
                  <div className="text-[11px] text-white/30 mt-1">
                    {dsm?.breach_risk?.reason || "breach risk needs schedule + capacity inputs"}
                  </div>
                </div>
              )}
            </div>

            <div className="glass-card p-5 flex flex-col justify-between">
              <div>
                <div className="eyebrow mb-1">DSM (Framework Only)</div>
                <div className="text-sm text-white/70 leading-relaxed">
                  {dsm?.framework_recommendation || "No recommendation available."}
                </div>
                <div className="text-xs text-white/30 mt-2">
                  Rupee values: {dsm?.emits_rupee_values ? "emitted" : "NOT emitted (NEEDS_OFFICIAL_SOURCE)"}
                </div>
              </div>
              {dsm?.blocked_calculations?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <div className="eyebrow mb-1">Blocked calculations ({dsm.blocked_calculations.length})</div>
                  <ul className="text-[11px] text-orange-300/70 space-y-0.5">
                    {dsm.blocked_calculations.map((b: any, i: number) => (
                      <li key={i}>
                        {b.calculation} — needs {b.needs}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Hourly GHI + cloud risk + estimated MW */}
          {timeline.length > 0 && (
            <div className="glass-card p-5 mb-6">
              <div className="eyebrow mb-4">
                Hourly Forecast @ ({sub.latitude}, {sub.longitude}) — GHI, cloud drop risk, estimated MW
              </div>
              <div className="flex items-end gap-[3px] h-40">
                {timeline.map((r, i) => {
                  const h = ((r.forecast_ghi_wm2 || 0) / maxGhi) * 100;
                  const risky = (r.cloud_drop_risk?.probability ?? 0) >= 0.5;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center justify-end h-full relative group cursor-pointer">
                      <div
                        className={`relative w-full rounded-t transition-all duration-150 group-hover:brightness-125 ${
                          risky
                            ? "bg-gradient-to-t from-orange-600/80 to-orange-400/60"
                            : "bg-gradient-to-t from-cyan-600/80 to-cyan-400/60"
                        }`}
                        style={{ height: `${h}%` }}
                      />
                      <div className="absolute bottom-full mb-3 hidden group-hover:block z-30 glass-card p-2.5 text-[10px] whitespace-nowrap shadow-2xl border-white/20">
                        <div className="text-white/80 font-bold">{String(r.timestamp).split("T")[1]?.slice(0, 5)}</div>
                        <div className="text-cyan-300 mt-1">GHI {r.forecast_ghi_wm2?.toFixed(0)} W/m² ({r.ghi_source})</div>
                        <div className={risky ? "text-orange-300" : "text-emerald-300"}>
                          cloud drop risk {((r.cloud_drop_risk?.probability ?? 0) * 100).toFixed(0)}%
                        </div>
                        <div className="text-blue-300">
                          {r.estimated_generation_mw != null
                            ? `est. ${r.estimated_generation_mw.toFixed(1)} MW`
                            : "MW blocked (no capacity)"}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-5 mt-4 text-[10px] text-white/50">
                <div className="flex items-center gap-1.5"><div className="w-3 h-2 rounded-sm bg-gradient-to-t from-cyan-600 to-cyan-400"></div>Forecast GHI</div>
                <div className="flex items-center gap-1.5"><div className="w-3 h-2 rounded-sm bg-gradient-to-t from-orange-600 to-orange-400"></div>Cloud drop risk ≥ 50%</div>
              </div>
            </div>
          )}

          {/* Agent trace */}
          {trace.length > 0 && (
            <div className="glass-card p-5 mb-6">
              <div className="eyebrow mb-3">Agent Workflow Trace</div>
              <div className="space-y-2">
                {trace.map((t: any) => (
                  <div key={t.step} className="flex items-start gap-3 text-sm">
                    <span className="text-white/30 font-mono w-5 shrink-0">{t.step}</span>
                    <div className="min-w-0">
                      <span className="text-white/80 font-medium">{t.agent}</span>
                      <span
                        className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full border ${
                          t.status === "ok"
                            ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                            : "bg-orange-500/10 text-orange-300 border-orange-500/30"
                        }`}
                      >
                        {t.status}
                      </span>
                      <span className="ml-2 text-[10px] text-white/30">{t.source_label}</span>
                      <div className="text-xs text-white/40">{t.action} — {t.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Calculation trace — fields, models, formulas, skips (plan §11) */}
          {calc && (
            <div className="glass-card p-5 mb-6">
              <div className="eyebrow mb-3">Calculation Trace — inputs, models &amp; skipped calculations</div>
              <div className="grid md:grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1.5">Substation fields</div>
                  <div className="flex flex-wrap gap-1.5">
                    {(calc.selected_substation_fields_used || []).map((f: string) => (
                      <span key={f} className="text-[10px] px-2 py-0.5 rounded-full border bg-emerald-500/10 text-emerald-300 border-emerald-500/30">{f}</span>
                    ))}
                    {(calc.selected_substation_fields_missing || []).map((f: string) => (
                      <span key={f} className="text-[10px] px-2 py-0.5 rounded-full border bg-orange-500/10 text-orange-300 border-orange-500/30">{f}: missing</span>
                    ))}
                  </div>
                  {calc.weather_features_used?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">Weather features used</div>
                      <div className="text-white/50">{calc.weather_features_used.join(", ")}</div>
                    </div>
                  )}
                  {calc.solar_features_used?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">Solar model features</div>
                      <div className="text-white/50">{calc.solar_features_used.join(", ")}</div>
                    </div>
                  )}
                  {calc.model_files_used?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">Model files used</div>
                      <ul className="font-mono text-[10px] text-cyan-300/70 space-y-0.5">
                        {calc.model_files_used.map((m: string, i: number) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                <div>
                  {calc.formulas_or_rules_used?.length > 0 && (
                    <div>
                      <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">Formulas / rules used</div>
                      <ul className="list-disc list-inside text-white/50 space-y-0.5">
                        {calc.formulas_or_rules_used.map((f: string, i: number) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {calc.calculations_skipped?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">Skipped calculations (honest)</div>
                      <ul className="text-[11px] text-orange-300/70 space-y-0.5">
                        {calc.calculations_skipped.map((s: string) => (
                          <li key={s}>
                            {s} — {calc.skip_reasons?.[s] || "no reason recorded"}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* AI reasoning layer (Phase 1.5): explicit opt-in, honest fallback */}
          <AIInsightsPanel substationId={selectedId} form={form} />

          {/* Limitations */}
          {result.limitations?.length > 0 && (
            <div className="text-xs text-white/50 bg-white/5 rounded-lg p-4 glass-card mb-6">
              <div className="text-white/40 uppercase tracking-wider mb-1">Honest limitations</div>
              <ul className="list-disc list-inside space-y-0.5">
                {result.limitations.map((l: string, i: number) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {online && !result && !loading && (
        <div className="glass-card text-center py-16">
          <SolarPanel3D generation={0} className="w-40 mx-auto mb-6 opacity-50" />
          <h3 className="text-lg font-medium text-white/60">Ready to Forecast</h3>
          <p className="text-white/30 mt-1 text-sm">
            Pick a substation — its real coordinates drive the full agent workflow.
          </p>
        </div>
      )}
    </div>
  );
}
