"use client";
import { useEffect, useState } from "react";
import { getBescomStatus, getKarnatakaRegions, seedKarnataka } from "@/lib/api";
import MetricCard from "@/components/cards/MetricCard";
import type { BescomStatus, KarnatakaRegions } from "@/lib/types";

export default function KarnatakaPage() {
  const [regions, setRegions] = useState<KarnatakaRegions | null>(null);
  const [bescom, setBescom] = useState<BescomStatus | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => {
    getKarnatakaRegions().then(setRegions).catch(() => {});
    getBescomStatus().then(setBescom).catch(() => {});
  };
  useEffect(load, []);

  const seed = async () => {
    setSeeding(true);
    try {
      const r = await seedKarnataka();
      setMsg(`Registered ${r.created.length} site(s) of ${r.total_registry}.`);
      load();
    } catch (e: any) {
      setMsg(e.message);
    }
    setSeeding(false);
  };

  const totalGw = regions ? (regions.total_capacity_mw / 1000).toFixed(2) : "—";

  return (
    <div className="max-w-7xl mx-auto animate-fade-up">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Karnataka Grid · BESCOM</h1>
          <p className="text-white/40 mt-1">
            State-wide solar fleet under the KERC / Karnataka SLDC deviation settlement framework
          </p>
        </div>
        <button onClick={seed} disabled={seeding} className="btn-primary">
          {seeding ? "Seeding…" : "Seed Karnataka Sites"}
        </button>
      </div>
      {msg && <div className="glass-card p-3 mb-6 text-sm text-cyan-300">{msg}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard title="Fleet Capacity" value={totalGw} unit="GW" color="green" subtitle="Across Karnataka" />
        <MetricCard title="KERC DSM Band" value={regions ? `±${regions.dsm_band_percent}` : "—"} unit="%" color="orange" subtitle="Solar tolerance" />
        <MetricCard title="Regions" value={regions ? Object.keys(regions.regions).length : "—"} color="blue" subtitle="Solar zones" />
        <MetricCard title="BESCOM Feed" value={bescom ? bescom.connector.mode : "—"} color="purple" subtitle={bescom?.connector.is_live ? "Live" : "Simulated"} />
      </div>

      {/* Regions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {regions &&
          Object.entries(regions.regions).map(([region, sites]) => (
            <div key={region} className="glass-card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="font-semibold text-white">{region}</div>
                <span className="badge badge-blue">{sites.length} site{sites.length > 1 ? "s" : ""}</span>
              </div>
              <div className="space-y-2">
                {sites.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-white/70">{s.name}</span>
                    <span className="text-white/50 font-mono">{s.capacity_mw} MW · {s.discom}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
      </div>

      {/* BESCOM / KERC framework */}
      {bescom && (
        <div className="glass-card p-5">
          <div className="eyebrow mb-3">KERC / BESCOM DSM Framework</div>
          <p className="text-sm text-white/60 mb-4">{bescom.connector.note}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">Operator</div>
              <div className="text-white/80">{bescom.connector.operator}</div>
              <div className="mt-3 text-[11px] text-white/40 uppercase tracking-wider mb-1">Solar band</div>
              <div className="text-white/80">±{bescom.kerc_solar_band_percent}% of available capacity</div>
            </div>
            <div>
              <div className="text-[11px] text-white/40 uppercase tracking-wider mb-2">Deviation charge slabs</div>
              <table className="w-full text-sm">
                <tbody>
                  {bescom.slabs.map((s, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1.5 text-white/60">{s.range_percent}% beyond band</td>
                      <td className="py-1.5 text-right font-mono text-amber-300">₹{s.rate_inr_per_kwh}/kWh</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
