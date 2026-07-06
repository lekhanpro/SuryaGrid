"use client";

// Phase 1.7 - read-only model/data provenance panel.
// Shows the Bengaluru data mode, source & model geography, training/production
// readiness, and honesty warnings (non-local load, estimated PV, missing capacity).
// It renders backend-provided status verbatim and never fabricates state.

import { useEffect, useState } from "react";
import { getAgentsStatus } from "@/lib/api";

type AgentCard = {
  model_present?: boolean;
  prediction_type?: string;
  training_geography?: string;
  target_geography?: string;
  local_data_available?: boolean;
  domain_shift_risk?: string;
  production_ready?: boolean;
  reason_if_not_production_ready?: string | null;
};

type Status = {
  data_mode?: string;
  region?: string;
  coordinates?: number[];
  agents?: Record<string, AgentCard>;
  warnings?: string[];
};

function Badge({ ok, label }: { ok: boolean; label: string }) {
  const cls = ok
    ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
    : "bg-amber-500/10 text-amber-300 border-amber-500/30";
  return <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>{label}</span>;
}

export default function ModelProvenancePanel() {
  const [status, setStatus] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getAgentsStatus()
      .then(setStatus)
      .catch((e) => setErr(e?.message || "unavailable"));
  }, []);

  if (err) return null; // backend offline -> stay silent (never fake status)
  if (!status) return null;

  const agents = status.agents || {};
  return (
    <div className="glass-card border border-white/10 p-5 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div className="text-white/80 font-semibold">
          Model & Data Provenance — {status.region || "Bengaluru"}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-white/40">Data mode</span>
          <Badge ok={status.data_mode === "real"} label={(status.data_mode || "?").toUpperCase()} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        {Object.entries(agents).map(([name, a]) => (
          <div key={name} className="rounded-lg bg-white/[0.02] border border-white/5 p-3">
            <div className="flex items-center justify-between">
              <span className="text-white/70 font-medium capitalize">{name}</span>
              <Badge
                ok={!!a.production_ready}
                label={a.production_ready ? "production-ready" : "not production"}
              />
            </div>
            <div className="text-xs text-white/40 mt-1">{a.prediction_type || "—"}</div>
            <div className="text-xs text-white/50 mt-1">
              train: {a.training_geography || "—"}
            </div>
            {a.domain_shift_risk && a.domain_shift_risk !== "LOW" && a.domain_shift_risk !== "NONE" && (
              <div className="text-xs text-amber-300/80 mt-1">
                domain shift: {a.domain_shift_risk}
              </div>
            )}
            {!a.production_ready && a.reason_if_not_production_ready && (
              <div className="text-[11px] text-white/40 mt-1 leading-snug">
                {a.reason_if_not_production_ready}
              </div>
            )}
          </div>
        ))}
      </div>

      {status.warnings && status.warnings.length > 0 && (
        <div className="border-t border-white/10 pt-3">
          <div className="text-xs text-amber-300/90 font-medium mb-1">Honesty warnings</div>
          <ul className="list-disc list-inside space-y-0.5">
            {status.warnings.map((w, i) => (
              <li key={i} className="text-[11px] text-white/45 leading-snug">
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
