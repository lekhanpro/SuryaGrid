"use client";
import { useEffect, useState } from "react";
import { API_BASE, getDataSourcesStatus, getSources, probeBackend } from "@/lib/api";
import OfflineBanner from "@/components/OfflineBanner";

function StatusChip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`text-[11px] px-2 py-0.5 rounded-full border ${
        ok
          ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
          : "bg-amber-500/10 text-amber-300 border-amber-500/30"
      }`}
    >
      {label}
    </span>
  );
}

const CLASS_COLORS: Record<string, string> = {
  OFFICIAL_SOURCE: "text-emerald-300",
  DATASET_DERIVED: "text-cyan-300",
  MODEL_LEARNED: "text-purple-300",
  USER_CONFIGURABLE: "text-amber-300",
  FALLBACK_DEFAULT: "text-white/50",
  USER_CONFIGURABLE_PENDING_OFFICIAL_SOURCE: "text-orange-300",
};

export default function DataSourcesPage() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    (async () => {
      const p = await probeBackend();
      setOnline(p.online);
      if (p.online) {
        try {
          const [st, sr] = await Promise.all([getDataSourcesStatus(), getSources()]);
          setStatus(st);
          setSources(sr.sources || []);
        } catch {
          setOnline(false);
        }
      }
    })();
  }, []);

  return (
    <div className="max-w-6xl mx-auto animate-fade-up">
      <h1 className="text-3xl font-bold text-white">Data Sources</h1>
      <p className="text-white/40 mt-1 mb-6">
        Every dataset, API and formula the platform relies on — with live status and
        source classification. No source is silently substituted.
      </p>

      {online === false && <OfflineBanner base={API_BASE} />}
      {online === null && <div className="glass-card p-6 text-white/50">Checking backend…</div>}

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {(status.providers || []).map((p: any, i: number) => (
            <div key={i} className="glass-card p-5">
              <div className="flex items-center justify-between">
                <div className="font-semibold text-white">{p.name}</div>
                <StatusChip ok={p.available} label={p.available ? "available" : "unavailable"} />
              </div>
              <div className="text-xs text-white/40 mt-1 uppercase tracking-wider">{p.provider_type} · {p.mode}</div>
              <div className="text-sm text-white/55 mt-2">{p.detail}</div>
              {p.record_count != null && (
                <div className="text-xs text-white/35 mt-1">~{p.record_count} records</div>
              )}
            </div>
          ))}
        </div>
      )}

      {sources.length > 0 && (
        <div className="glass-card p-5">
          <div className="text-sm font-bold text-white/70 uppercase tracking-wider mb-3">
            Source Registry ({sources.length})
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 border-b border-white/10">
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Classification</th>
                  <th className="py-2 pr-3">Verified</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s: any) => (
                  <tr key={s.id} className="border-b border-white/5">
                    <td className="py-2 pr-3 text-white/70 font-mono text-xs">{s.id}</td>
                    <td className="py-2 pr-3 text-white/80">
                      <a href={s.reference} target="_blank" rel="noreferrer" className="hover:text-cyan-300">
                        {s.name}
                      </a>
                    </td>
                    <td className="py-2 pr-3 text-white/50">{s.type}</td>
                    <td className={`py-2 pr-3 ${CLASS_COLORS[s.classification] || "text-white/60"}`}>
                      {s.classification}
                    </td>
                    <td className="py-2 pr-3">
                      <StatusChip ok={s.verified === "verified"} label={s.verified} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-xs text-white/30 mt-3">
            Full registry: docs/SOURCE_REGISTRY.md · classifications per the source-first rule.
          </div>
        </div>
      )}
    </div>
  );
}
