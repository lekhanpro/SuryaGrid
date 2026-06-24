"use client";

interface Props {
  deviationPercent: number;
  threshold: number;
}

export default function DeviationBar({ deviationPercent, threshold }: Props) {
  const clamped = Math.min(deviationPercent, 100);
  const isOver = deviationPercent > threshold;

  return (
    <div className="glass-card p-5">
      <div className="eyebrow mb-3">Deviation vs Threshold</div>
      <div className="relative h-6 bg-white/5 rounded-full overflow-hidden border border-white/5">
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white/60 z-10"
          style={{ left: `${Math.min(threshold, 100)}%` }}
        />
        <div
          className={`h-full rounded-full transition-all duration-500 ${isOver ? "bg-gradient-to-r from-red-500 to-rose-400" : "bg-gradient-to-r from-emerald-500 to-emerald-400"}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <div className="flex justify-between mt-2 text-xs text-white/40">
        <span>0%</span>
        <span className="font-medium text-white/70">Threshold: {threshold}%</span>
        <span>100%</span>
      </div>
      <div className="text-center mt-2">
        <span className={`text-lg font-bold ${isOver ? "text-red-300" : "text-emerald-300"}`}>
          {deviationPercent.toFixed(1)}%
        </span>
        <span className="text-sm text-white/40 ml-1">deviation</span>
      </div>
    </div>
  );
}
