"use client";

interface Props {
  deviationPercent: number;
  threshold: number;
}

export default function DeviationBar({ deviationPercent, threshold }: Props) {
  const clamped = Math.min(deviationPercent, 100);
  const isOver = deviationPercent > threshold;

  return (
    <div className="card">
      <div className="card-header">Deviation vs Threshold</div>
      <div className="mt-3">
        <div className="relative h-6 bg-gray-100 rounded-full overflow-hidden">
          {/* Threshold marker */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-gray-800 z-10"
            style={{ left: `${Math.min(threshold, 100)}%` }}
          />
          {/* Deviation fill */}
          <div
            className={`h-full rounded-full transition-all duration-500 ${isOver ? "bg-gradient-to-r from-red-400 to-red-600" : "bg-gradient-to-r from-emerald-400 to-emerald-500"}`}
            style={{ width: `${clamped}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>0%</span>
          <span className="font-medium text-gray-700">Threshold: {threshold}%</span>
          <span>100%</span>
        </div>
        <div className="text-center mt-2">
          <span className={`text-lg font-bold ${isOver ? "text-red-600" : "text-emerald-600"}`}>
            {deviationPercent.toFixed(1)}%
          </span>
          <span className="text-sm text-gray-500 ml-1">deviation</span>
        </div>
      </div>
    </div>
  );
}
