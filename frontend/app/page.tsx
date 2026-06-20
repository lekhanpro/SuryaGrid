import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] relative">
      {/* Background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/5 rounded-full blur-2xl"></div>
      </div>

      <div className="text-center max-w-2xl relative z-10">
        {/* 3D Sun Icon */}
        <svg viewBox="0 0 120 120" className="w-24 h-24 mx-auto mb-8 animate-float" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <radialGradient id="sunCore" cx="50%" cy="40%" r="50%">
              <stop offset="0%" stopColor="#fde68a" />
              <stop offset="60%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#d97706" />
            </radialGradient>
            <filter id="sunShadow">
              <feDropShadow dx="0" dy="4" stdDeviation="8" floodColor="#f59e0b" floodOpacity="0.4" />
            </filter>
          </defs>
          <circle cx="60" cy="60" r="45" fill="#f59e0b" opacity="0.1">
            <animate attributeName="r" values="42;48;42" dur="4s" repeatCount="indefinite" />
          </circle>
          <circle cx="60" cy="60" r="30" fill="url(#sunCore)" filter="url(#sunShadow)" />
          {[0, 45, 90, 135, 180, 225, 270, 315].map((a, i) => (
            <line
              key={i}
              x1={60 + Math.cos(a * Math.PI / 180) * 35}
              y1={60 + Math.sin(a * Math.PI / 180) * 35}
              x2={60 + Math.cos(a * Math.PI / 180) * 48}
              y2={60 + Math.sin(a * Math.PI / 180) * 48}
              stroke="#fbbf24" strokeWidth="3" strokeLinecap="round" opacity="0.7"
            />
          ))}
        </svg>

        <h1 className="text-5xl font-bold text-white mb-3">
          Surya<span className="text-gradient">Grid</span> AI
        </h1>
        <p className="text-xl text-white/60 mb-3">Solar Nowcasting &amp; DSM Penalty Prediction</p>
        <p className="text-sm text-white/30 mb-10 max-w-md mx-auto leading-relaxed">
          Multi-agent intelligence system for solar generation forecasting, deviation settlement analysis, and grid compliance monitoring
        </p>
        <Link href="/dashboard" className="btn-primary inline-flex items-center gap-2 text-base px-8 py-3.5">
          Open Dashboard
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
        </Link>
      </div>
    </div>
  );
}
