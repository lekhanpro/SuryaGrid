"use client";
import { useEffect, useState } from "react";
import {
  API_BASE,
  getAvailableLocations,
  getDataCoverage,
  getSubstations,
  importSubstations,
  probeBackend,
} from "@/lib/api";
import OfflineBanner from "@/components/OfflineBanner";

function Cov({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`w-2.5 h-2.5 rounded-full ${ok ? "bg-emerald-400" : "bg-white/20"}`} />
      <span className="text-white/60">{label}</span>
    </div>
  );
}

export default function LocationsPage() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [avail, setAvail] = useState<any>(null);
  const [subs, setSubs] = useState<any[]>([]);
  const [imp, setImp] = useState({ latitude: 12.97, longitude: 77.59, radius_km: 15 });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [coverage, setCoverage] = useState<any>(null);

  const refresh = async () => {
    const [a, s] = await Promise.all([getAvailableLocations(), getSubstations()]);
    setAvail(a);
    setSubs(s.substations || []);
  };

  useEffect(() => {
    (async () => {
      const p = await probeBackend();
      setOnline(p.online);
      if (p.online) {
        try {
          await refresh();
        } catch {
          setOnline(false);
        }
      }
    })();
  }, []);

  const runImport = async () => {
    setBusy(true);
    setMsg("");
    try {
      const r = await importSubstations(imp);
      setMsg(`Imported ${r.inserted} substation(s) from ${r.source}.`);
      await refresh();
    } catch (e: any) {
      setMsg(e.message);
    }
    setBusy(false);
  };

  const checkCoverage = async () => {
    try {
      setCoverage(await getDataCoverage("adhoc", { latitude: imp.latitude, longitude: imp.longitude }));
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-up">
      <h1 className="text-3xl font-bold text-white">Locations & Substations</h1>
      <p className="text-white/40 mt-1 mb-6">
        Solar sites, weather grid coverage, and grid substations (OpenStreetMap / operator CSV).
        Every substation keeps its source and confidence; coordinates are never invented.
      </p>

      {online === false && <OfflineBanner base={API_BASE} />}
      {online === null && <div className="glass-card p-6 text-white/50">Checking backend…</div>}

      {avail && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {Object.entries(avail.counts || {}).map(([k, v]) => (
              <div key={k} className="glass-card p-5">
                <div className="eyebrow">{k.replace(/_/g, " ")}</div>
                <div className="text-2xl font-bold text-white mt-1">{String(v)}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="glass-card p-5">
              <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-3">Import Substations</div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                {(["latitude", "longitude", "radius_km"] as const).map((k) => (
                  <div key={k}>
                    <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">{k}</label>
                    <input type="number" step="any" className="input-field" value={(imp as any)[k]}
                      onChange={(e) => setImp({ ...imp, [k]: parseFloat(e.target.value) || 0 })} />
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <button className="btn-primary" disabled={busy} onClick={runImport}>{busy ? "Importing…" : "Import from OSM"}</button>
                <button className="btn-secondary" onClick={checkCoverage}>Check Coverage</button>
              </div>
              {msg && <div className="mt-3 text-sm text-white/60">{msg}</div>}
              <div className="text-xs text-white/30 mt-2">Source: OpenStreetMap via Overpass (ODbL).</div>
            </div>

            <div className="glass-card p-5">
              <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-3">Data Coverage (point)</div>
              {coverage ? (
                <div className="space-y-2">
                  <Cov ok={coverage.weather_forecast_available} label={`Weather forecast (${coverage.weather_provider})`} />
                  <Cov ok={coverage.historical_kaggle_coverage} label="Historical Kaggle coverage" />
                  <Cov ok={coverage.nearest_substation_available} label={coverage.nearest_substation ? `Nearest substation: ${coverage.nearest_substation.name} (${coverage.nearest_substation.distance_km} km)` : "Nearest substation"} />
                  <Cov ok={coverage.dsm_rule_profile_available} label="DSM rule profile" />
                  <Cov ok={coverage.model_available} label="ML model" />
                </div>
              ) : (
                <div className="text-white/40 text-sm">Set a point and click “Check Coverage”.</div>
              )}
            </div>
          </div>

          <div className="glass-card p-5">
            <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-3">Substations ({subs.length})</div>
            {subs.length === 0 ? (
              <div className="text-white/40 text-sm">No substations imported yet. Import from OSM above.</div>
            ) : (
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-900/80">
                    <tr className="text-left text-white/40 border-b border-white/10">
                      <th className="py-2 pr-3">Name</th>
                      <th className="py-2 pr-3">Voltage</th>
                      <th className="py-2 pr-3">Operator</th>
                      <th className="py-2 pr-3">Lat, Lon</th>
                      <th className="py-2 pr-3">Source</th>
                      <th className="py-2 pr-3">Conf.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subs.map((s) => (
                      <tr key={s.id} className="border-b border-white/5">
                        <td className="py-1.5 pr-3 text-white/80">{s.name}</td>
                        <td className="py-1.5 pr-3 text-white/50">{s.voltage_level || "—"}</td>
                        <td className="py-1.5 pr-3 text-white/50">{s.operator || "—"}</td>
                        <td className="py-1.5 pr-3 text-white/50 font-mono text-xs">{s.latitude?.toFixed(3)}, {s.longitude?.toFixed(3)}</td>
                        <td className="py-1.5 pr-3 text-white/40 text-xs">{s.source_name}</td>
                        <td className="py-1.5 pr-3 text-white/60">{s.source_confidence}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
