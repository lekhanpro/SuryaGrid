"use client";

interface Props {
  score: number; // 0-100
  level: string;
  className?: string;
}

export default function RiskGauge3D({ score, level, className = "" }: Props) {
  const angle = (score / 100) * 180 - 90; // -90 to 90 degrees
  const rad = (angle * Math.PI) / 180;
  const needleX = 80 + Math.cos(rad) * 50;
  const needleY = 90 + Math.sin(rad) * 50;

  const levelColors: Record<string, { main: string; glow: string }> = {
    LOW: { main: "#10b981", glow: "rgba(16,185,129,0.4)" },
    MEDIUM: { main: "#f59e0b", glow: "rgba(245,158,11,0.4)" },
    HIGH: { main: "#f97316", glow: "rgba(249,115,22,0.4)" },
    CRITICAL: { main: "#ef4444", glow: "rgba(239,68,68,0.4)" },
  };
  const c = levelColors[level] || levelColors.LOW;

  return (
    <svg viewBox="0 0 160 110" className={className} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="gaugeArc" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="33%" stopColor="#f59e0b" />
          <stop offset="66%" stopColor="#f97316" />
          <stop offset="100%" stopColor="#ef4444" />
        </linearGradient>
        <filter id="needleGlow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="arcShadow">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000" floodOpacity="0.5" />
        </filter>
      </defs>

      {/* Background arc track */}
      <path
        d="M20 90 A60 60 0 0 1 140 90"
        fill="none"
        stroke="rgba(255,255,255,0.05)"
        strokeWidth="12"
        strokeLinecap="round"
        filter="url(#arcShadow)"
      />

      {/* Colored arc */}
      <path
        d="M20 90 A60 60 0 0 1 140 90"
        fill="none"
        stroke="url(#gaugeArc)"
        strokeWidth="10"
        strokeLinecap="round"
        opacity="0.8"
      />

      {/* Tick marks */}
      {[0, 25, 50, 75, 100].map((tick) => {
        const a = ((tick / 100) * 180 - 90) * Math.PI / 180;
        const x1 = 80 + Math.cos(a) * 52;
        const y1 = 90 + Math.sin(a) * 52;
        const x2 = 80 + Math.cos(a) * 58;
        const y2 = 90 + Math.sin(a) * 58;
        return <line key={tick} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" strokeLinecap="round" />;
      })}

      {/* Needle */}
      <line
        x1="80" y1="90" x2={needleX} y2={needleY}
        stroke={c.main}
        strokeWidth="2.5"
        strokeLinecap="round"
        filter="url(#needleGlow)"
      />
      {/* Needle center */}
      <circle cx="80" cy="90" r="5" fill={c.main} />
      <circle cx="80" cy="90" r="3" fill="#1e1b4b" />

      {/* Score text */}
      <text x="80" y="82" textAnchor="middle" fontSize="18" fontWeight="bold" fill={c.main} fontFamily="monospace">
        {score.toFixed(0)}
      </text>

      {/* Level text */}
      <text x="80" y="105" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.6)" fontWeight="bold" letterSpacing="2">
        {level}
      </text>
    </svg>
  );
}
