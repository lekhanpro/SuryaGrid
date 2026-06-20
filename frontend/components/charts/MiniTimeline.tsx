"use client";
import type { TimelineEntry } from "@/lib/types";

interface Props {
  data: TimelineEntry[];
  maxMW: number;
}

export default function MiniTimeline({ data, maxMW }: Props) {
  if (!data.length) return null;

  return (
    <div className="glass-card p-5">
      <div className="text-[10px] text-white/40 uppercase tracking-wider mb-4">24h Generation Profile</div>
      <div className="flex items-end gap-[2px] h-44">
        {data.map((entry, i) => {
          const predH = (entry.predicted_generation_mw / maxMW) * 100;
          const schedH = (entry.scheduled_generation_mw / maxMW) * 100;
          const isPenalty = entry.penalty_status === "PENALTY_RISK";
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full relative group cursor-pointer">
              {/* Scheduled (ghost) */}
              <div className="absolute bottom-0 w-full bg-blue-500/10 rounded-t border-t border-blue-500/20" style={{ height: `${schedH}%` }} />
              {/* Predicted */}
              <div
                className={`relative w-full rounded-t transition-all duration-150 group-hover:brightness-125 ${
                  isPenalty
                    ? "bg-gradient-to-t from-red-600/80 to-red-400/60"
                    : "bg-gradient-to-t from-emerald-600/80 to-emerald-400/60"
                }`}
                style={{ height: `${predH}%` }}
              />
              {/* Tooltip */}
              <div className="absolute bottom-full mb-3 hidden group-hover:block z-30 glass-card p-2.5 text-[10px] whitespace-nowrap shadow-2xl border-white/20">
                <div className="text-white/80 font-bold">{entry.timestamp.split("T")[1]?.slice(0, 5)} UTC</div>
                <div className="text-cyan-300 mt-1">Predicted: {entry.predicted_generation_mw.toFixed(1)} MW</div>
                <div className="text-blue-300">Scheduled: {entry.scheduled_generation_mw.toFixed(1)} MW</div>
                <div className={isPenalty ? "text-red-300" : "text-emerald-300"}>{entry.penalty_status}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-3 text-[10px] text-white/30 font-mono">
        <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:30</span>
      </div>
      <div className="flex gap-5 mt-4 text-[10px] text-white/50">
        <div className="flex items-center gap-1.5"><div className="w-3 h-2 rounded-sm bg-gradient-to-t from-emerald-600 to-emerald-400"></div>Within Threshold</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-2 rounded-sm bg-gradient-to-t from-red-600 to-red-400"></div>Penalty Risk</div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-2 rounded-sm bg-blue-500/20 border border-blue-500/30"></div>Scheduled</div>
      </div>
    </div>
  );
}
