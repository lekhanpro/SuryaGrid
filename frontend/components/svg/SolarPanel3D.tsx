"use client";

interface Props {
  generation: number; // 0-100 percentage of capacity
  className?: string;
}

export default function SolarPanel3D({ generation, className = "" }: Props) {
  const intensity = Math.max(0, Math.min(100, generation));
  const glowOpacity = intensity / 100;
  const sunY = 30 - (intensity / 100) * 15;

  return (
    <svg viewBox="0 0 200 160" className={`${className}`} xmlns="http://www.w3.org/2000/svg">
      {/* Sky gradient */}
      <defs>
        <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>
        <linearGradient id="panelGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e40af" />
          <stop offset="100%" stopColor="#1e3a8a" />
        </linearGradient>
        <linearGradient id="panelReflect" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
          <stop offset="50%" stopColor="rgba(255,255,255,0)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0.05)" />
        </linearGradient>
        <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fbbf24" stopOpacity={glowOpacity} />
          <stop offset="70%" stopColor="#f59e0b" stopOpacity={glowOpacity * 0.4} />
          <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
        </radialGradient>
        <filter id="shadow3d">
          <feDropShadow dx="3" dy="6" stdDeviation="4" floodColor="#000" floodOpacity="0.5" />
        </filter>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* Background */}
      <rect width="200" height="160" fill="url(#skyGrad)" rx="12" />

      {/* Sun */}
      <circle cx="160" cy={sunY} r="20" fill="url(#sunGlow)" className="animate-pulse-glow" />
      <circle cx="160" cy={sunY} r="8" fill="#fbbf24" opacity={glowOpacity}>
        <animate attributeName="r" values="7;9;7" dur="3s" repeatCount="indefinite" />
      </circle>

      {/* Sun rays */}
      {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
        <line
          key={i}
          x1={160 + Math.cos(angle * Math.PI / 180) * 12}
          y1={sunY + Math.sin(angle * Math.PI / 180) * 12}
          x2={160 + Math.cos(angle * Math.PI / 180) * 18}
          y2={sunY + Math.sin(angle * Math.PI / 180) * 18}
          stroke="#fbbf24"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity={glowOpacity * 0.7}
        />
      ))}

      {/* Ground plane (3D perspective) */}
      <path d="M0 130 L200 130 L200 160 L0 160 Z" fill="#064e3b" opacity="0.3" />
      <path d="M0 130 L200 130 L180 160 L20 160 Z" fill="#065f46" opacity="0.2" />

      {/* Solar panel - 3D perspective */}
      <g filter="url(#shadow3d)">
        {/* Panel body */}
        <path d="M35 95 L95 70 L165 95 L105 120 Z" fill="url(#panelGrad)" stroke="#3b82f6" strokeWidth="0.5" />
        {/* Panel reflection */}
        <path d="M35 95 L95 70 L165 95 L105 120 Z" fill="url(#panelReflect)" />
        {/* Grid lines */}
        <path d="M55 89 L125 78" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
        <path d="M45 97 L135 86" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
        <path d="M55 105 L145 94" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" />
        <path d="M65 75 L75 115" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
        <path d="M95 70 L105 120" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
        <path d="M130 80 L135 112" stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" />
        {/* Panel edge highlight */}
        <path d="M35 95 L95 70 L165 95" fill="none" stroke="rgba(96,165,250,0.5)" strokeWidth="1" />
      </g>

      {/* Panel stand */}
      <line x1="100" y1="120" x2="100" y2="140" stroke="#4b5563" strokeWidth="3" />
      <line x1="85" y1="140" x2="115" y2="140" stroke="#4b5563" strokeWidth="2" />

      {/* Energy flow particles */}
      {intensity > 20 && (
        <g filter="url(#glow)">
          <circle cx="80" cy="85" r="1.5" fill="#60a5fa" opacity="0.8">
            <animate attributeName="cy" values="85;60;85" dur="2s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.8;0;0.8" dur="2s" repeatCount="indefinite" />
          </circle>
          <circle cx="110" cy="90" r="1.5" fill="#34d399" opacity="0.8">
            <animate attributeName="cy" values="90;55;90" dur="2.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.8;0;0.8" dur="2.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="130" cy="88" r="1" fill="#fbbf24" opacity="0.6">
            <animate attributeName="cy" values="88;50;88" dur="3s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.6;0;0.6" dur="3s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* Generation percentage */}
      <text x="100" y="152" textAnchor="middle" fontSize="10" fill="rgba(255,255,255,0.6)" fontFamily="monospace">
        {intensity.toFixed(0)}% capacity
      </text>
    </svg>
  );
}
