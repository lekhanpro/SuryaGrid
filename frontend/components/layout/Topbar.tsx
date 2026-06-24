"use client";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

export default function Topbar() {
  const [mode, setMode] = useState<"checking" | "live" | "demo">("checking");
  const [version, setVersion] = useState<string>("");

  useEffect(() => {
    let active = true;
    const usingApi = typeof window !== "undefined" && !!process.env.NEXT_PUBLIC_API_URL && !window.location.hostname.includes("github.io");
    getHealth()
      .then((h: any) => {
        if (!active) return;
        setVersion(h?.version || "0.1.0");
        setMode(usingApi ? "live" : "demo");
      })
      .catch(() => active && setMode("demo"));
    return () => { active = false; };
  }, []);

  const dot =
    mode === "live" ? "bg-emerald-400 shadow-emerald-400/50"
    : mode === "demo" ? "bg-amber-400 shadow-amber-400/50"
    : "bg-white/40";
  const label = mode === "live" ? "Live API" : mode === "demo" ? "Demo Mode" : "Connecting…";

  return (
    <header className="h-14 flex items-center justify-between px-5 md:px-8 border-b border-white/5 bg-black/20 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex items-center gap-2 text-sm text-white/50">
        <span className="hidden sm:inline">SuryaGrid AI</span>
        <span className="hidden sm:inline text-white/20">/</span>
        <span className="text-white/80 font-medium">Solar DSM Intelligence</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] text-white/40 px-2.5 py-1 rounded-full border border-white/10">
          v{version || "0.1.0"} · Phase 1
        </span>
        <span className="inline-flex items-center gap-2 text-xs font-medium text-white/70 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
          <span className={`w-2 h-2 rounded-full animate-pulse shadow-lg ${dot}`} />
          {label}
        </span>
      </div>
    </header>
  );
}
