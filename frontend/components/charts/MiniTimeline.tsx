"use client";
import type { TimelineEntry } from "@/lib/types";

interface Props {
  data: TimelineEntry[];
  maxMW: number;
}

export default function MiniTimeline({ data, maxMW }: Props) {
  if (!data.length) return null;
  const barWidth = 100 / data.length;

  return (
    <div className="card">
      <div className="card-header">24h Generation Profile</div>
      <div className="flex items-end gap-px h-40 mt-3">
        {data.map((entry, i) => {
          const predH = (entry.predicted_generation_mw / maxMW) * 100;
          const schedH = (entry.scheduled_generation_mw / maxMW) * 100;
          const isPenalty = entry.penalty_status === "PENALTY_RISK";
          return (
            <div key={i} className="flex-1 flex flex-col items-center justify-end h-full relative group">
              {/* Scheduled (background) */}
              <div
                className="absolute bottom-0 w-full bg-blue-100 rounded-t"
                style={{ height: `${schedH}%` }}
              />
              {/* Predicted (foreground) */}
              <div
                className={`relative w-full rounded-t transition-all ${isPenalty ? "bg-red-400" : "bg-emerald-400"}`}
                style={{ height: `${predH}%` }}
              />
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 hidden group-hover:block z-20 bg-gray-900 text-white text-xs rounded-lg p-2 whitespace-nowrap shadow-lg">
                <div>{entry.timestamp.split("T")[1]?.slice(0, 5)}</div>
                <div>Pred: {entry.predicted_generation_mw.toFixed(1)} MW</div>
                <div>Sched: {entry.scheduled_generation_mw.toFixed(1)} MW</div>
                <div className={isPenalty ? "text-red-300" : "text-green-300"}>{entry.penalty_status}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-400">
        <span>00:00</span>
        <span>06:00</span>
        <span>12:00</span>
        <span>18:00</span>
        <span>23:30</span>
      </div>
      <div className="flex gap-4 mt-3 text-xs">
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-emerald-400"></div> Predicted (OK)</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-red-400"></div> Predicted (Penalty)</div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-blue-100"></div> Scheduled</div>
      </div>
    </div>
  );
}
