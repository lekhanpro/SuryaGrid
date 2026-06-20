"use client";

interface Props {
  predictedMW: number;
  scheduledMW: number;
  capacityMW: number;
  isPenalty: boolean;
  className?: string;
}

export default function EnergyFlow3D({ predictedMW, scheduledMW, capacityMW, isPenalty, className = "" }: Props) {
  const predPct = (predictedMW / capacityMW) * 100;
  const schedPct = (scheduledMW / capacityMW) * 100;

  return (
    <svg viewBox="0 0 300 100" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="predBar" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={isPenalty ? "#ef4444" : "#10b981"} />
          <stop offset="100%" stopColor={isPenalty ? "#dc2626" : "#059669"} />
        </linearGradient>
        <linearGradient id="schedBar" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#4f46e5" />
        </linearGradient>
        <filter id="barGlow">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Labels */}
      <text x="10" y="20" fontSize="8" fill="rgba(255,255,255,0.5)" fontWeight="bold" letterSpacing="1">PREDICTED</text>
      <text x="10" y="60" fontSize="8" fill="rgba(255,255,255,0.5)" fontWeight="bold" letterSpacing="1">SCHEDULED</text>

      {/* Track backgrounds */}
      <rect x="10" y="25" width="230" height="16" rx="8" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
      <rect x="10" y="65" width="230" height="16" rx="8" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />

      {/* Predicted bar */}
      <rect x="10" y="25" width={Math.max(2, predPct * 2.3)} height="16" rx="8" fill="url(#predBar)" filter="url(#barGlow)">
        <animate attributeName="width" from="0" to={Math.max(2, predPct * 2.3)} dur="1s" fill="freeze" />
      </rect>

      {/* Scheduled bar */}
      <rect x="10" y="65" width={Math.max(2, schedPct * 2.3)} height="16" rx="8" fill="url(#schedBar)" filter="url(#barGlow)">
        <animate attributeName="width" from="0" to={Math.max(2, schedPct * 2.3)} dur="1.2s" fill="freeze" />
      </rect>

      {/* Values */}
      <text x="250" y="37" fontSize="11" fill="white" fontWeight="bold" fontFamily="monospace">{predictedMW.toFixed(1)}</text>
      <text x="250" y="77" fontSize="11" fill="white" fontWeight="bold" fontFamily="monospace">{scheduledMW.toFixed(1)}</text>
      <text x="280" y="37" fontSize="8" fill="rgba(255,255,255,0.4)">MW</text>
      <text x="280" y="77" fontSize="8" fill="rgba(255,255,255,0.4)">MW</text>

      {/* Deviation connector */}
      <line x1={10 + predPct * 2.3} y1="41" x2={10 + schedPct * 2.3} y2="65" stroke={isPenalty ? "rgba(239,68,68,0.5)" : "rgba(16,185,129,0.3)"} strokeWidth="1" strokeDasharray="3 2" />
    </svg>
  );
}
