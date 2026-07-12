"use client";
// AI reasoning layer panel (Phase 1.5).
//
// Explicit opt-in: insights are generated only when the operator clicks the
// button (no surprise LLM calls). Numbers always come from the deterministic
// run; if no LLM is configured/reachable the backend returns an honest
// deterministic explanation labelled "deterministic_fallback".

import { useState } from "react";
import { orchestrateSubstationAI } from "@/lib/api";

const SEV_STYLE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-300 border-red-500/30",
  warning: "bg-orange-500/10 text-orange-300 border-orange-500/30",
  info: "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",
};

export default function AIInsightsPanel({
  substationId,
  form,
}: {
  substationId: string;
  form: {
    site_capacity_mw: number;
    scheduled_generation_mw: number;
    forecast_horizon_hours: number;
    use_live_weather: boolean;
  };
}) {
  const [ai, setAi] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await orchestrateSubstationAI({
        substation_id: substationId,
        site_capacity_mw: form.site_capacity_mw || null,
        scheduled_generation_mw: form.scheduled_generation_mw || null,
        forecast_horizon_hours: form.forecast_horizon_hours,
        use_live_weather: form.use_live_weather,
      });
      setAi(r?.ai || null);
    } catch (e: any) {
      setErr(e?.message || "AI insights failed");
      setAi(null);
    }
    setLoading(false);
  };

  const ins = ai?.insights;
  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div className="eyebrow">AI Insights — narrative over deterministic numbers</div>
        <button onClick={generate} disabled={loading || !substationId} className="btn-primary">
          {loading ? "Reasoning…" : "Generate AI insights"}
        </button>
      </div>

      {err && (
        <div className="text-red-300 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
          {err}
        </div>
      )}

      {!ai && !err && (
        <p className="text-white/30 text-xs">
          Runs the same deterministic workflow, then adds an LLM narrative. Without a
          configured LLM the backend returns a deterministic explanation — never
          fabricated numbers.
        </p>
      )}

      {ai && ins && (
        <div className="text-xs space-y-3">
          <div className="flex gap-2 flex-wrap items-center">
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full border ${
                ai.status === "llm"
                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                  : "bg-orange-500/10 text-orange-300 border-orange-500/30"
              }`}
            >
              {ai.status === "llm" ? `LLM: ${ai.model}` : "deterministic fallback"}
            </span>
            {ai.reason && <span className="text-white/30">{ai.reason}</span>}
          </div>

          <p className="text-white/70 text-sm">{ins.summary}</p>

          {ins.key_findings?.length > 0 && (
            <div>
              <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">
                Key findings
              </div>
              <ul className="list-disc list-inside text-white/50 space-y-0.5">
                {ins.key_findings.map((f: string, i: number) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {ins.anomalies?.length > 0 && (
            <div>
              <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">
                Anomalies (rule-based, deterministic)
              </div>
              <div className="space-y-1">
                {ins.anomalies.map((a: any, i: number) => (
                  <div key={i} className="flex items-start gap-2">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full border shrink-0 ${
                        SEV_STYLE[a.severity] || SEV_STYLE.info
                      }`}
                    >
                      {a.severity}
                    </span>
                    <span className="text-white/50">{a.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {ins.operator_suggestions?.length > 0 && (
            <div>
              <div className="text-white/40 uppercase tracking-wider text-[10px] mb-1">
                Operator suggestions
              </div>
              <ul className="list-disc list-inside text-white/50 space-y-0.5">
                {ins.operator_suggestions.map((sug: string, i: number) => (
                  <li key={i}>{sug}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="text-white/30">{ins.confidence_note}</div>
        </div>
      )}
    </div>
  );
}
