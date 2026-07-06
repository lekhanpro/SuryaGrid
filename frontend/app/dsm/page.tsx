"use client";
import { useEffect, useState } from "react";
import { advancedDsmCheck, API_BASE, getRuleProfiles, probeBackend } from "@/lib/api";
import OfflineBanner from "@/components/OfflineBanner";

function StatusChip({ status }: { status: string }) {
  const official = status === "OFFICIAL_SOURCE";
  return (
    <span
      className={`text-[10px] px-2 py-0.5 rounded-full border ${
        official
          ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
          : "bg-orange-500/10 text-orange-300 border-orange-500/30"
      }`}
    >
      {status}
    </span>
  );
}

export default function DSMPage() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [form, setForm] = useState({
    scheduled_generation_mw: 30,
    predicted_generation_mw: 24,
    installed_capacity_mw: 50,
    regulator: "KERC/BESCOM",
  });
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const p = await probeBackend();
      setOnline(p.online);
      if (p.online) {
        try {
          setProfiles((await getRuleProfiles()).profiles || []);
        } catch {
          setOnline(false);
        }
      }
    })();
  }, []);

  const run = async () => {
    setBusy(true);
    try {
      setResult(await advancedDsmCheck(form));
    } catch (e: any) {
      setResult({ error: e.message });
    }
    setBusy(false);
  };

  return (
    <div className="max-w-6xl mx-auto animate-fade-up">
      <h1 className="text-3xl font-bold text-white">Advanced DSM Engine</h1>
      <p className="text-white/40 mt-1 mb-6">
        Configurable rule profiles (region · regulator · denominator · slab bands). DSM rules are
        not universal — every profile carries a source status; nothing claims regulatory accuracy.
      </p>

      {online === false && <OfflineBanner base={API_BASE} />}
      {online === null && <div className="glass-card p-6 text-white/50">Checking backend…</div>}

      {online && (
        <>
          {/* Advanced check */}
          <div className="glass-card p-5 mb-6">
            <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-4">Advanced DSM Check</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              {(["scheduled_generation_mw", "predicted_generation_mw", "installed_capacity_mw"] as const).map((k) => (
                <div key={k}>
                  <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">{k.replace(/_/g, " ")}</label>
                  <input type="number" step="any" className="input-field" value={(form as any)[k]}
                    onChange={(e) => setForm({ ...form, [k]: parseFloat(e.target.value) || 0 })} />
                </div>
              ))}
              <div>
                <label className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">Regulator</label>
                <select className="input-field" value={form.regulator} onChange={(e) => setForm({ ...form, regulator: e.target.value })}>
                  <option value="KERC/BESCOM" className="bg-slate-800">KERC/BESCOM</option>
                  <option value="CERC" className="bg-slate-800">CERC</option>
                  <option value="" className="bg-slate-800">generic-configurable</option>
                </select>
              </div>
            </div>
            <button className="btn-primary" disabled={busy} onClick={run}>{busy ? "Evaluating…" : "Run Advanced Check"}</button>

            {result && !result.error && (
              <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="Deviation" value={`${result.deviation_percent}%`} />
                <Stat label="Direction" value={result.deviation_direction} />
                <Stat label="Band" value={result.dsm_band || "—"} />
                <Stat label="Status" value={result.penalty_status} accent={result.penalty_status === "PENALTY_RISK" ? "text-red-300" : "text-emerald-300"} />
                <Stat label="Charge (₹)" value={result.estimated_dsm_charge?.toLocaleString?.() ?? result.estimated_dsm_charge} />
                <Stat label="Profile" value={result.profile} />
                <div className="col-span-2 md:col-span-2">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Rule Source</div>
                  <div className="text-sm text-white/70">{result.rule_source?.name} <StatusChip status={result.rule_source?.status} /></div>
                </div>
                <div className="col-span-2 md:col-span-4 text-sm text-white/50 bg-white/5 rounded-lg p-3">{result.explanation}</div>
              </div>
            )}
            {result?.error && <div className="mt-4 text-red-300 text-sm">{result.error}</div>}
          </div>

          {/* Profiles */}
          <div className="space-y-4">
            {profiles.map((p) => (
              <div key={p.id} className="glass-card p-5">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="font-semibold text-white">{p.name} <span className="text-white/40 text-sm">· {p.regulator || "operator"}</span></div>
                  <StatusChip status={p.source_status} />
                </div>
                <div className="text-xs text-white/40 mt-1">
                  region: {p.region || "—"} · denominator: {p.denominator} · tolerance ±{p.tolerance_percent}% · block {p.time_block_minutes}min
                </div>
                {p.source_url && <a href={p.source_url} target="_blank" rel="noreferrer" className="text-xs text-cyan-300/70 hover:text-cyan-300">{p.source_name}</a>}
                {p.bands?.length > 0 && (
                  <table className="w-full text-sm mt-3">
                    <thead>
                      <tr className="text-left text-white/40 border-b border-white/10">
                        <th className="py-1 pr-3">Deviation band</th>
                        <th className="py-1 pr-3">Direction</th>
                        <th className="py-1 pr-3">Rate</th>
                        <th className="py-1 pr-3">Source ref</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.bands.map((b: any, i: number) => (
                        <tr key={i} className="border-b border-white/5">
                          <td className="py-1 pr-3 text-white/70">{b.min_deviation_percent}–{b.max_deviation_percent >= 10000 ? "∞" : b.max_deviation_percent}%</td>
                          <td className="py-1 pr-3 text-white/50">{b.direction}</td>
                          <td className="py-1 pr-3 text-white/70">{b.charge_rate} {b.unit}</td>
                          <td className="py-1 pr-3 text-white/40 font-mono text-xs">{b.source_reference}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: any; accent?: string }) {
  return (
    <div>
      <div className="text-[10px] text-white/40 uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold ${accent || "text-white"}`}>{value}</div>
    </div>
  );
}
